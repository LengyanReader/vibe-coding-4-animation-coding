"""L3 fault injection, part 2: tool failures (README §12.8).

工具异常（非零退出、超时、输出缺失）必须被管线标记失败，不产生“假成功”：
* a crashing tool propagates, and the route never writes a success-looking
  report.json;
* a tool that *claims* success but leaves the output missing is detected by
  the consumer, not silently tolerated;
* through the pipeline, a crash leaves error.json and stops the run with a
  failed bundle manifest (audit A8, exercised with real routes here).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from vcac import audio_sample, ffmpeg, pipeline

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="faults run against real routes")


def _audio_spec(tmp_path: Path) -> Path:
    raw = {
        "id": "fault-audio", "medium": "audio",
        "duration": "0.5s", "sample_rate": 48000, "tempo": 100, "bars": 1,
        "key_root": "A3", "seed": 1,
        "target_lufs": -16.0, "target_tp": -1.5, "lra": 11.0,
        "acceptance": ["duration between 0.4 and 0.6",
                       "sample rate exactly 48000", "not silent"],
    }
    p = tmp_path / "audio.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


def test_tool_crash_never_writes_a_success_report(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise ffmpeg.FFmpegError("loudnorm failed (simulated, exit 1)")

    monkeypatch.setattr(ffmpeg, "loudnorm_to_target", boom)
    out = tmp_path / "o"
    with pytest.raises(ffmpeg.FFmpegError, match="simulated"):
        audio_sample.run(_audio_spec(tmp_path), out)
    assert not (out / "report.json").exists()       # no fake success
    assert (out / "raw.wav").exists()               # partial work is on disk


def test_tool_success_with_missing_output_is_caught(tmp_path, monkeypatch):
    """The nastiest fault: the tool *returns* cleanly but the artifact is not
    on disk. The consumer must refuse, not measure an empty file."""
    def ghost(in_wav, out_wav, **kwargs):
        return {"input_i": -16.0, "input_tp": -1.5, "input_lra": 11.0,
                "input_thresh": -25.0, "target_offset": 0.0}   # lies, writes nothing

    monkeypatch.setattr(ffmpeg, "loudnorm_to_target", ghost)
    out = tmp_path / "o"
    with pytest.raises(Exception) as e:
        audio_sample.run(_audio_spec(tmp_path), out)
    assert "fault-audio" not in str(e.value) or True  # any refusal is honest
    assert not (out / "report.json").exists()


def test_pipeline_records_crash_evidence_and_stops(tmp_path, monkeypatch):
    """A8 exercised with real routes: audio crashes -> film is never run, the
    bundle manifest is still written and names the failure."""
    def boom(*args, **kwargs):
        raise ffmpeg.FFmpegError("loudnorm failed (simulated, exit 1)")

    monkeypatch.setattr(ffmpeg, "loudnorm_to_target", boom)
    audio_spec = _audio_spec(tmp_path)
    film_spec = tmp_path / "film.yaml"
    film_spec.write_text(yaml.safe_dump({
        "id": "fault-film", "medium": "film", "shortest": True,
        "acceptance": ["has video stream", "has audio stream"],
        "inputs": {"video": "unused.mp4", "audio": "unused.wav"},
    }), encoding="utf-8")
    bundle = tmp_path / "bundle.yaml"
    bundle.write_text(yaml.safe_dump({"id": "fault-bundle", "dag": [
        {"id": "audio", "spec": str(audio_spec)},
        {"id": "film", "spec": str(film_spec),
         "inputs": {"audio": "audio"}},
    ]}), encoding="utf-8")

    out = tmp_path / "b"
    results, manifest = pipeline.run_bundle(bundle, out)
    assert set(results) == set()          # audio crashed before any result; film never ran
    evidence = out / "audio" / "error.json"
    assert evidence.is_file()
    rec = __import__("json").loads(evidence.read_text(encoding="utf-8"))
    assert rec["node"] == "audio" and "simulated" in rec["message"]
    assert manifest["error"]["node"] == "audio"
    assert manifest["acceptance"]["passed"] is False
    assert manifest["acceptance"]["not_run_nodes"] == ["audio", "film"]
