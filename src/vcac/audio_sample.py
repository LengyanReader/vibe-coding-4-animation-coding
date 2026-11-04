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
from pathlib import Path

import numpy as np

from . import audio, ffmpeg, media, provenance, spec as spec_mod, validate


def _content_hash(a: np.ndarray) -> str:
    return provenance.sha256_bytes(np.asarray(a, dtype=np.float32).tobytes())


def synth(spec_dict: dict) -> np.ndarray:
    sr = int(spec_dict.get("sample_rate", 48000))
    tempo = float(spec_dict.get("tempo", 100.0))
    bars = int(spec_dict.get("bars", 4))
    duration = float(spec_mod.parse_duration(spec_dict["duration"]))
    events = audio.chord_events(tempo, spec_dict.get("key_root", "A3"), bars, sr)
    return audio.render(events, sr, duration, seed=int(spec_dict.get("seed", 42)))


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    sr = int(spec_dict.get("sample_rate", 48000))
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = synth(spec_dict)
    raw_wav = media.write_wav(out_dir / "raw.wav", raw, sr)

    master_wav = out_dir / "master.wav"
    measured_ln = ffmpeg.loudnorm_to_target(
        raw_wav, master_wav, i=float(spec_dict.get("target_lufs", -16.0)),
        tp=float(spec_dict.get("target_tp", -1.5)), lra=float(spec_dict.get("lra", 11.0)))

    samples, sr_out = media.read_wav(master_wav)
    lufs_out = ffmpeg.measure_lufs(master_wav)

    deterministic = _content_hash(synth(spec_dict)) == _content_hash(raw)

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
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict,
        content_hash=_content_hash(raw),
        artifact_hashes={"master.wav": provenance.sha256_file(master_wav),
                         "raw.wav": provenance.sha256_file(raw_wav)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["master.wav", "raw.wav", "report.json", "manifest.json"],
        notes=spec_dict.get("assumptions", []), pipeline="vcac-audio/0.1")
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="vcac audio route sample")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    spec_dict = spec_mod.load_raw(a.spec)
    out_dir = a.out or (Path("outputs") / spec_dict["id"])
    r = run(a.spec, out_dir)
    rep, m = r["report"], r["report"]["measured"]
    print(f"[vcac:audio] {spec_dict['id']} -> {r['out_dir']}")
    print(f"[vcac:audio] {m['duration']:.2f}s @{m['sample_rate']}Hz "
          f"ch={m['channels']} LUFS={m['lufs_i']:.1f} peak={m['peak_dbfs']:.1f}dBFS "
          f"RMS={m['rms_dbfs']:.1f} clip={m['clipping_pct']:.3f}% DC={m['dc_offset']:.5f}")
    for c in rep["checks"]:
        extra = (f"  (exp {c.get('expected')}, act {c.get('actual')})"
                 if c["status"] in ("pass", "fail") else f"  ({c.get('reason','')})")
        print(f"  [{c['status'].upper():7}] {c['id']}{extra}")
    print(f"[vcac:audio] run_id={r['manifest']['run_id']}")
    print(f"[vcac:audio] ACCEPTANCE {'PASSED' if rep['passed'] else 'FAILED'}")
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
