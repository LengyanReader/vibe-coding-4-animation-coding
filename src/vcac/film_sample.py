"""Composability sample — mux the video route + audio route into one film.

This is the DAG payoff the README promises (spec -> plan -> codegen -> assemble):
two *independently produced* artifacts — the orbiting-cubes video (loop #1) and
the synth-pad master (audio route) — are joined on one clock by FFmpeg, then
checked for A/V integrity (both streams present, sync offset, duration). No new
creative code runs here; it *composes* prior nodes, which is exactly what the
pipeline's assemble stage is for.

Reproducibility is inherited from the pinned input artifacts (their sha256 are
recorded in the manifest); mp4 container bytes are secondary, so this route
verifies sync rather than re-muxing for a byte hash.

Run (after loop #1 and the audio sample have produced their outputs):
    $env:PYTHONPATH="src"; python -m vcac.film_sample specs/examples/film-mux.yaml
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import ffmpeg, provenance, spec as spec_mod, validate


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    root = Path(".")
    video = root / spec_dict["inputs"]["video"]
    audio = root / spec_dict["inputs"]["audio"]
    if not video.exists() or not audio.exists():
        raise FileNotFoundError(
            f"inputs missing — run the video and audio routes first "
            f"(need {video} and {audio})")

    out_dir.mkdir(parents=True, exist_ok=True)
    film = out_dir / "film.mp4"
    ffmpeg.mux(video, audio, film, shortest=bool(spec_dict.get("shortest", True)))

    summary = ffmpeg.av_summary(film)
    report = validate.run_acceptance(spec_dict["acceptance"], summary)
    report["measured"] = summary
    report["film"] = {"video_codec": summary["video_codec"],
                      "audio_codec": summary["audio_codec"],
                      "duration": summary["duration"]}
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    v_hash = provenance.sha256_file(video)
    a_hash = provenance.sha256_file(audio)
    content = provenance.sha256_bytes(f"{v_hash}|{a_hash}".encode())
    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict, content_hash=content,
        artifact_hashes={"film.mp4": provenance.sha256_file(film)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["film.mp4", "report.json", "manifest.json"],
        notes=(spec_dict.get("assumptions", [])
               + [f"composed from video={v_hash[:19]} audio={a_hash[:19]}"]),
        pipeline="vcac-film/0.1")
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="vcac composability (mux) sample")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    spec_dict = spec_mod.load_raw(a.spec)
    out_dir = a.out or (Path("outputs") / spec_dict["id"])
    r = run(a.spec, out_dir)
    rep, m = r["report"], r["report"]["measured"]
    print(f"[vcac:film] {spec_dict['id']} -> {r['out_dir']}")
    print(f"[vcac:film] {m['duration']:.2f}s video={m['video_codec']} "
          f"audio={m['audio_codec']} av_delta={m['av_delta_seconds']:.3f}s")
    for c in rep["checks"]:
        extra = (f"  (exp {c.get('expected')}, act {c.get('actual')})"
                 if c["status"] in ("pass", "fail") else f"  ({c.get('reason','')})")
        print(f"  [{c['status'].upper():7}] {c['id']}{extra}")
    print(f"[vcac:film] run_id={r['manifest']['run_id']}")
    print(f"[vcac:film] ACCEPTANCE {'PASSED' if rep['passed'] else 'FAILED'}")
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
