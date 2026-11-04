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
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageStat

from . import ffmpeg, provenance, render, spec as spec_mod, validate


def run(spec_path: Path, out_dir: Path, seed_override: int | None = None,
        keep_frames: bool = True) -> dict:
    spec = spec_mod.load(spec_path)
    if seed_override is not None:
        spec.seed = seed_override
        spec.raw.setdefault("render", {})["seed"] = seed_override

    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # --- stage: render frames (single pass: save PNG + fold content hash + luma)
    h = hashlib.sha256()
    luma_by_frame = []
    cubes, _ = render._make_cubes(spec)
    for t in range(spec.n_frames):
        img = render.frame_image(spec, cubes, t)
        raw = img.tobytes()
        h.update(raw)
        luma_by_frame.append(ImageStat.Stat(img.convert("L")).mean[0])
        img.save(frames_dir / f"{t:04d}.png", optimize=True)
    h.update((spec.n_frames).to_bytes(8, "big"))
    frame_hash = "sha256:" + h.hexdigest()

    # --- determinism gate: re-render in-memory and compare content hash
    h2 = hashlib.sha256()
    n2 = 0
    for raw in render.render_frames(spec):
        h2.update(raw)
        n2 += 1
    h2.update(n2.to_bytes(8, "big"))
    deterministic = ("sha256:" + h2.hexdigest()) == frame_hash

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

    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- archive: manifest
    tools = provenance.tool_versions(ffmpeg.version())
    spec_dict = spec.to_dict()
    run_id = provenance.derive_run_id(spec_dict, frame_hash, tools)
    manifest = provenance.build_manifest(
        spec_path=str(spec_path), spec_dict=spec_dict, run_id=run_id,
        frame_hash=frame_hash, mp4_hash=provenance.sha256_file(mp4),
        ffmpeg_version=tools["ffmpeg"], acceptance=report,
        artifacts=["final.mp4", "contact-sheet.jpg", "report.json", "manifest.json"],
        notes=spec.assumptions,
    )
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
    ap = argparse.ArgumentParser(description="vcac first closed loop")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--no-keep-frames", action="store_true")
    a = ap.parse_args(argv)

    spec = spec_mod.load(a.spec)
    out_dir = a.out or (Path("outputs") / spec.id)
    result = run(a.spec, out_dir, seed_override=a.seed,
                 keep_frames=not a.no_keep_frames)

    rep = result["report"]
    print(f"[vcac] spec={spec.id} out={result['out_dir']}")
    print(f"[vcac] duration={rep['video']['duration']:.3f}s "
          f"{rep['video']['width']}x{rep['video']['height']} "
          f"{rep['video']['codec_name']}/{rep['video']['pix_fmt']}")
    for c in rep["checks"]:
        line = f"  [{c['status'].upper():7}] {c['id']}"
        if c["status"] in ("pass", "fail"):
            line += f"  (expected {c['expected']}, actual {c['actual']})"
        elif "reason" in c:
            line += f"  ({c['reason']})"
        print(line)
    print(f"[vcac] run_id={result['manifest']['run_id']}")
    print(f"[vcac] ACCEPTANCE {'PASSED' if rep['passed'] else 'FAILED'}")
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
