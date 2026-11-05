"""Audio route sample — deterministic pad+arpeggio, EBU-R128 mastered (README §11).

Zero-install, self-verifying music branch of the pipeline:
    spec -> additive synthesis (NumPy) -> two-pass loudnorm (FFmpeg) -> WAV
      -> measure (LUFS / peak / RMS / DC / clipping / duration / sample-rate)
      -> acceptance + determinism -> manifest.json

The synthesiser is our own (audio.py), so the *creative content* is bit-reproducible
from (tempo, key, bars, seed); loudnorm is a deterministic ffmpeg pass. When
music21/LilyPond/FluidSynth are adopted later they replace audio.render as an
alternative renderer behind the capability registry — the validate/manifest
contract here does not change.

Run:
    $env:PYTHONPATH="src"; python -m vcac.audio_sample specs/examples/synth-pad.yaml
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

from . import audio, cli, ffmpeg, media, provenance, registry, spec as spec_mod, validate


def _content_hash(a: np.ndarray) -> str:
    return provenance.sha256_bytes(np.asarray(a, dtype=np.float32).tobytes())


class EngineError(RuntimeError):
    """A rendering engine the spec asked for ran and refused to produce audio.

    Named separately from ``ffmpeg.FFmpegError`` because the tool at fault is not
    FFmpeg: mislabelling a fluidsynth failure as an ffmpeg one sends whoever reads
    the log to the wrong binary's docs (and the wrong capability in the registry).
    """


def _resolve_soundfont(spec_dict: dict) -> tuple[Path, str]:
    """First existing sf2 from the spec's declared paths; an absent SoundFont
    must be a named error, never a silent fallback to whatever is installed."""
    sf = spec_dict.get("soundfont") or {}
    tried = []
    for p in sf.get("paths", []):
        cand = Path(p)
        tried.append(str(cand))
        if cand.is_file():
            return cand, str(sf.get("licence", "unverified"))
    raise spec_mod.SpecError(
        f"fluidsynth engine needs a SoundFont: none of the declared paths exist "
        f"({', '.join(tried) or 'no soundfont.paths declared'}); run "
        f"python scripts/fetch_assets.py")


def synth(spec_dict: dict, out_dir: Path | None = None) -> np.ndarray:
    """``engine`` picks the renderer behind the same event contract:
    ``additive`` (default, zero-install) or ``fluidsynth`` (sampled piano via
    a MIDI render). Both are deterministic; both are gated by the registry."""
    sr = int(spec_dict.get("sample_rate", 48000))
    duration = spec_mod.parse_duration(spec_dict["duration"])
    engine = spec_dict.get("engine", "additive")
    if engine == "fluidsynth":
        # the declared duration is not passed in: the score's own note list sets
        # the render length, and the acceptance gate is what proves the two agree
        return _render_fluidsynth(spec_dict, sr, Path(out_dir))
    tempo = float(spec_dict.get("tempo", 100.0))
    bars = int(spec_dict.get("bars", 4))
    events = audio.chord_events(tempo, spec_dict.get("key_root", "A3"), bars, sr)
    return audio.render(events, sr, duration, seed=int(spec_dict.get("seed", 42)))


def _render_fluidsynth(spec_dict: dict, sr: int, out_dir: Path) -> np.ndarray:
    entry = registry.require("fluidsynth")      # raises loudly if not fetched
    sf2, _sf2_licence = _resolve_soundfont(spec_dict)
    events = audio.piano_events(spec_dict)
    midi_path = out_dir / "score.mid"
    audio.write_midi(events, midi_path, tempo=float(spec_dict.get("tempo", 72.0)))
    render_wav = out_dir / "render.wav"
    r = subprocess.run(
        [str(entry["path"]), "-ni", "-F", str(render_wav), "-r", str(sr),
         str(sf2), str(midi_path)],
        capture_output=True, text=True)
    if r.returncode != 0 or not render_wav.is_file():
        raise EngineError(
            f"fluidsynth render failed (exit {r.returncode}):\n{r.stderr}")
    samples, sr_out = media.read_wav(render_wav)
    render_wav.unlink()   # a transport, not a deliverable: keeping it would put
    #                       three copies of the same 30 s stereo track on disk
    if sr_out != sr:
        raise EngineError(f"fluidsynth rendered at {sr_out}Hz, spec says {sr}")
    return audio.apply_room(samples, sr, spec_dict.get("reverb"))


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    sr = int(spec_dict.get("sample_rate", 48000))
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = synth(spec_dict, out_dir)
    channels = 1 if raw.ndim == 1 else int(raw.shape[1])
    raw_wav = media.write_wav(out_dir / "raw.wav", raw, sr, channels=channels)

    master_wav = out_dir / "master.wav"
    measured_ln = ffmpeg.loudnorm_to_target(
        raw_wav, master_wav, i=float(spec_dict.get("target_lufs", -16.0)),
        tp=float(spec_dict.get("target_tp", -1.5)), lra=float(spec_dict.get("lra", 11.0)),
        sample_rate=sr)

    samples, sr_out = media.read_wav(master_wav)
    lufs_out = ffmpeg.measure_lufs(master_wav)

    deterministic = _content_hash(synth(spec_dict, out_dir)) == _content_hash(raw)

    measured = {
        "sample_rate": sr_out,
        "channels": int(samples.shape[1]),
        "duration": media.duration_s(samples, sr_out),
        "peak_dbfs": media.peak_dbfs(samples),
        "rms_dbfs": media.rms_dbfs(samples),
        "dc_offset": media.dc_offset(samples),
        "clipping_pct": media.clipping_pct(samples),
        "lufs_i": lufs_out,
        "deterministic": deterministic,
    }
    report = validate.run_acceptance(spec_dict["acceptance"], measured)
    report["measured"] = measured
    report["loudnorm"] = {"input_measured": measured_ln, "master_lufs": lufs_out}
    report["audio"] = ffmpeg.audio_summary(master_wav)
    report["engine"] = spec_dict.get("engine", "additive")
    artifact_hashes = {"master.wav": provenance.sha256_file(master_wav),
                       "raw.wav": provenance.sha256_file(raw_wav)}
    artifacts = ["master.wav", "raw.wav", "report.json", "manifest.json"]
    extra = {}
    if spec_dict.get("engine") == "fluidsynth":
        sf2, sf2_licence = _resolve_soundfont(spec_dict)
        extra["soundfont"] = {"path": str(sf2), "licence": sf2_licence,
                              "sha256": provenance.sha256_file(sf2)}
        report["soundfont"] = extra["soundfont"]
        # score.mid is the authored substance -- every note of the piece, and the
        # only artifact a reader can review without a DAW. The wav fluidsynth
        # rendered from it is a discarded transport, so the MIDI gets recorded
        artifact_hashes["score.mid"] = provenance.sha256_file(out_dir / "score.mid")
        artifacts.append("score.mid")
    cli.write_report(out_dir, report)

    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict,
        content_hash=_content_hash(raw),
        artifact_hashes=artifact_hashes,
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=artifacts,
        notes=spec_dict.get("assumptions", []), pipeline="vcac-audio/0.1",
        extra=extra or None)
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    a = cli.parse_args("vcac audio route sample", argv)
    spec_dict = spec_mod.load_raw(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec_dict["id"]))
    m = r["report"]["measured"]
    return cli.finish("audio", r, summaries=[
        f"{spec_dict['id']} -> {r['out_dir']}",
        f"{m['duration']:.2f}s @{m['sample_rate']}Hz ch={m['channels']} "
        f"LUFS={m['lufs_i']:.1f} peak={m['peak_dbfs']:.1f}dBFS "
        f"RMS={m['rms_dbfs']:.1f} clip={m['clipping_pct']:.3f}% "
        f"DC={m['dc_offset']:.5f}"])


if __name__ == "__main__":
    raise SystemExit(main())
