"""First closed loop — end-to-end driver (README §5 workflow, §11 milestone #1).

    brief (already a spec file) -> render frames (Pillow) -> encode (FFmpeg)
      -> validate (ffprobe + 3 acceptance rules + determinism)
      -> assemble evidence (report.json, contact-sheet.jpg) -> manifest.json

Run (no install needed, from repo root):

    $env:PYTHONPATH="src"; python -m vcac.firstloop specs/examples/orbiting-cubes.yaml

Outputs land under ``outputs/<spec-id>/``. Exit code is non-zero if acceptance
fails, so this doubles as a smoke test the pipeline's own gates can call.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageStat

from . import cli, ffmpeg, provenance, render, spec as spec_mod, validate


def run(spec_path: Path, out_dir: Path, seed_override: int | None = None,
        keep_frames: bool = True) -> dict:
    spec = spec_mod.load(spec_path)
    if seed_override is not None:
        spec.seed = seed_override
        spec.raw.setdefault("render", {})["seed"] = seed_override

    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # --- stage: render frames (single pass: save PNG + fold content hash + luma)
    luma_by_frame = []
    cubes, _ = render._make_cubes(spec)

    def _saved_frames():
        for t in range(spec.n_frames):
            img = render.frame_image(spec, cubes, t)
            luma_by_frame.append(ImageStat.Stat(img.convert("L")).mean[0])
            img.save(frames_dir / f"{t:04d}.png", optimize=True)
            yield img.tobytes()

    frame_hash = provenance.content_hash(_saved_frames())

    # --- determinism gate: re-render in-memory and compare content hash
    deterministic = provenance.content_hash(render.render_frames(spec)) == frame_hash

    # --- stage: encode
    mp4 = out_dir / "final.mp4"
    ffmpeg.encode_images(frames_dir, spec.fps, mp4)

    # --- stage: validate
    summary = ffmpeg.video_summary(mp4)
    measured = {
        "duration": summary["duration"],
        "width": summary["width"],
        "height": summary["height"],
        "max_black_run_seconds": validate.max_black_run_seconds(luma_by_frame, spec.fps),
        "deterministic": deterministic,
    }
    report = validate.run_acceptance(spec.acceptance, measured)
    report["measured"] = measured
    report["video"] = {k: summary[k] for k in
                       ("duration", "width", "height", "codec_name", "pix_fmt",
                        "nb_frames", "avg_frame_rate", "format_name")}

    # --- evidence: contact sheet (key frames grid)
    _contact_sheet(spec, frames_dir, out_dir / "contact-sheet.jpg")

    cli.write_report(out_dir, report)

    # --- archive: manifest (the unified record; identical run_id material —
    # hash(spec + content + tools) — as the legacy build_manifest path)
    tools = provenance.tool_versions(ffmpeg.version())
    spec_dict = spec.to_dict()
    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict, content_hash=frame_hash,
        artifact_hashes={"final.mp4": provenance.sha256_file(mp4),
                         "contact-sheet.jpg": provenance.sha256_file(out_dir / "contact-sheet.jpg")},
        ffmpeg_version=tools["ffmpeg"], acceptance=report,
        artifacts=["final.mp4", "contact-sheet.jpg", "report.json", "manifest.json"],
        notes=spec.assumptions, pipeline="vcac-video/0.1")
    provenance.write_manifest(manifest, out_dir)

    if not keep_frames:
        import shutil
        shutil.rmtree(frames_dir, ignore_errors=True)

    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def _contact_sheet(spec, frames_dir: Path, out_path: Path, cols: int = 6):
    idx = [round(i * (spec.n_frames - 1) / (cols - 1)) for i in range(cols)]
    thumbs = [Image.open(frames_dir / f"{t:04d}.png") for t in idx]
    tw = 320
    th = round(tw * spec.height / spec.width)
    thumbs = [im.resize((tw, th)) for im in thumbs]
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    sheet.save(out_path, quality=90)


def main(argv=None) -> int:
    a = cli.parse_args("vcac video route (first closed loop)", argv, extra=[
        (("--seed",), dict(type=int, default=None)),
        (("--no-keep-frames",), dict(action="store_true")),
    ])
    spec = spec_mod.load(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec.id),
            seed_override=a.seed, keep_frames=not a.no_keep_frames)
    v = r["report"]["video"]
    return cli.finish("video", r, summaries=[
        f"spec={spec.id} out={r['out_dir']}",
        f"{v['duration']:.3f}s {v['width']}x{v['height']} "
        f"{v['codec_name']}/{v['pix_fmt']}"])


if __name__ == "__main__":
    raise SystemExit(main())
