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

from . import cli, ffmpeg, provenance, spec as spec_mod, validate


def _resolve_input(spec_path: Path, value: str) -> Path:
    """Declared inputs resolve against the cwd first (the historical contract,
    and how film-mux.yaml's repo-root-relative paths are written), then against
    the spec file's own directory — so the route also works from any cwd when
    the spec carries its inputs with it."""
    p = Path(value)
    if p.is_absolute():
        return p
    from_cwd = Path(".") / p
    if from_cwd.exists():
        return from_cwd
    from_spec = Path(spec_path).resolve().parent / p
    if from_spec.exists():
        return from_spec
    return from_cwd  # neither exists — report the cwd-relative miss


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    video = _resolve_input(spec_path, spec_dict["inputs"]["video"])
    audio = _resolve_input(spec_path, spec_dict["inputs"]["audio"])
    if not video.exists() or not audio.exists():
        raise FileNotFoundError(
            f"inputs missing — run the video and audio routes first "
            f"(need {video} and {audio}; tried cwd and the spec's directory)")

    out_dir.mkdir(parents=True, exist_ok=True)
    film = out_dir / "film.mp4"
    ffmpeg.mux(video, audio, film, shortest=bool(spec_dict.get("shortest", True)))

    summary = ffmpeg.av_summary(film)
    report = validate.run_acceptance(spec_dict["acceptance"], summary)
    report["measured"] = summary
    report["film"] = {"video_codec": summary["video_codec"],
                      "audio_codec": summary["audio_codec"],
                      "duration": summary["duration"]}
    cli.write_report(out_dir, report)

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
    a = cli.parse_args("vcac composability (mux) sample", argv)
    spec_dict = spec_mod.load_raw(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec_dict["id"]))
    m = r["report"]["measured"]
    return cli.finish("film", r, summaries=[
        f"{spec_dict['id']} -> {r['out_dir']}",
        f"{m['duration']:.2f}s video={m['video_codec']} audio={m['audio_codec']} "
        f"av_delta={m['av_delta_seconds']:.3f}s"])


if __name__ == "__main__":
    raise SystemExit(main())
