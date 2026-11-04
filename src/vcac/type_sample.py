"""Type route sample — a variable-font weight axis proven in the pixels.

A "variable font animation" is easy to fake: pick a static Bold, scale it, and
nobody can tell from the output. This route refuses that. Two claims are checked
against the rendered bitmap, not against metadata:

  1. the axis really exists in the file (``fvar`` range read by fontTools, and it
     has to survive subsetting, or the animation would be flat), and
  2. the axis is *visible* -- ink area increases strictly while text, position and
     size are held fixed, so nothing else can account for the pixel-count change.

Claim 2 is not pedantry: ``instancer`` does not rewrite the name table, so the
instantiated face at wght 900 still reports its subfamily as "Thin". A pipeline
that trusted ``getname()`` would ship a fake ramp and report it as a real axis.

Memory, not disk: the source face is ~10 MB. The naive loop writes one temp font
per frame. Here the face is subset to the drawn glyphs once (10 MB -> ~9 KB) and
each frame instantiates from that inside a BytesIO, so nothing but the mp4 lands
on disk.

Run:
    $env:PYTHONPATH="src"; python -m vcac.type_sample specs/examples/variable-weight.yaml
"""
from __future__ import annotations

import argparse
import io
import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import ffmpeg, provenance, spec as spec_mod, validate


class FontCapabilityError(ValueError):
    pass


def find_font(spec_dict: dict) -> Path:
    """Resolve the declared face, or fail loudly. An absent font is a capability
    gap, not a licence to fall back to a default (the xkcd() finding, docs/coverage-audit.md §0)."""
    for raw in spec_dict["font"]["paths"]:
        p = Path(raw)
        if p.exists():
            return p
    raise FontCapabilityError(
        f"none of the declared font paths exist: {spec_dict['font']['paths']}")


def subset_face(path: Path, text: str):
    """Trim the variable face to the glyphs we actually draw, keeping ``fvar``.
    Returns (TTFont, bytes) -- the second number is the whole point of this route's
    footprint: the working font never exceeds this many bytes, and never on disk."""
    from fontTools import subset
    from fontTools.ttLib import TTFont

    opts = subset.Options()
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    opts.recalc_bounds = False
    font = TTFont(path)
    ss = subset.Subsetter(opts)
    ss.populate(text=text)
    ss.subset(font)
    buf = io.BytesIO()
    font.flavor = None
    font.save(buf)
    n = buf.getbuffer().nbytes
    buf.seek(0)
    return TTFont(buf), n


def instance_font(face, wght: float, size_px: int) -> ImageFont.FreeTypeFont:
    """Pin one axis instance and hand it to Pillow as an in-memory TTF."""
    from fontTools.varLib import instancer

    inst = instancer.instantiateVariableFont(face, {"wght": wght}, inplace=False)
    out = io.BytesIO()
    inst.flavor = None
    inst.save(out)
    out.seek(0)
    return ImageFont.truetype(out, size_px)


def weight_at(t: int, n: int, lo: float, hi: float) -> float:
    """lo -> hi -> lo over the clip, smoothstepped so no frame-to-frame jump.
    The ramp up is the half the monotonicity gate reads; the ramp back down is the
    mirror, which the report checks for reversibility."""
    if n <= 1:
        return lo
    u = t / (n - 1)
    tri = 2 * u if u < 0.5 else 2.0 - 2 * u
    return lo + (hi - lo) * (tri * tri * (3 - 2 * tri))


def render_masks(spec_dict: dict, face, lo: float, hi: float) -> list[dict]:
    """One mask per frame plus the weight and the name the instance claims."""
    n = int(spec_dict["frames"])
    pad = int(spec_dict["pad"])
    size = int(spec_dict["size_px"])
    text = spec_dict["text"]
    out = []
    for t in range(n):
        w = weight_at(t, n, lo, hi)
        font = instance_font(face, w, size)
        box = font.getbbox(text)
        w_px = math.ceil(box[2] - box[0]) + 2 * pad
        h_px = math.ceil(size * 1.6) + 2 * pad
        mask = Image.new("L", (w_px, h_px), 0)
        ImageDraw.Draw(mask).text((pad, pad - box[1]), text, font=font, fill=255)
        out.append({"t": t, "wght": w, "mask": mask, "name": font.getname()})
    return out


def render_frames(spec_dict: dict, masks: list[dict]) -> list[Image.Image]:
    """Left-align every frame on the same origin, then centre the block in the
    canvas once. Alignment must not move between frames or the ink count stops
    being evidence about the axis."""
    size = (int(spec_dict["width"]), int(spec_dict["height"]))
    paper = spec_mod.parse_hex(spec_dict["palette"]["paper"])
    ink = spec_mod.parse_hex(spec_dict["palette"]["ink"])
    pad = int(spec_dict["pad"])
    widest = max(m["mask"].width for m in masks)
    tallest = max(m["mask"].height for m in masks)
    if widest > size[0] or tallest > size[1]:
        raise FontCapabilityError(
            f"canvas too small for the heaviest instance: needs {widest}x{tallest}, "
            f"spec says {size[0]}x{size[1]}. Refusing to clip: clipped ink would "
            "fake the monotonicity gate.")
    ox, oy = (size[0] - widest) // 2, (size[1] - tallest) // 2
    frames = []
    for m in masks:
        canvas = Image.new("RGB", size, paper)
        canvas.paste(ink, (ox, oy), m["mask"])
        frames.append(canvas)
    return frames


def content_hash(frames: list[Image.Image]) -> str:
    body = b"".join(f.tobytes() for f in frames)
    return provenance.sha256_bytes(body + len(frames).to_bytes(8, "big"))


def run(spec_path: Path, out_dir: Path, keep_frames: bool = False) -> dict:
    from fontTools.ttLib import TTFont

    spec_dict = spec_mod.load_raw(spec_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    font_path = find_font(spec_dict)

    src = TTFont(font_path)
    src_axes = {a.axisTag: (a.minValue, a.maxValue) for a in src["fvar"].axes}
    src.close()
    tag = spec_dict["font"].get("axis", "wght")
    if tag not in src_axes:
        raise FontCapabilityError(f"face has no '{tag}' axis; found {list(src_axes)}")
    lo, hi = src_axes[tag]

    face, subset_bytes = subset_face(font_path, spec_dict["text"])
    sub_axes = {a.axisTag: (a.minValue, a.maxValue) for a in face["fvar"].axes}
    if tag not in sub_axes:
        raise FontCapabilityError(
            "subsetting dropped the fvar axis -- the 'animation' would be flat")

    masks = render_masks(spec_dict, face, lo, hi)
    frames = render_frames(spec_dict, masks)

    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for t, img in enumerate(frames):
        img.save(frames_dir / f"{t:04d}.png", optimize=True)
    mp4 = out_dir / "type.mp4"
    ffmpeg.encode_images(frames_dir, int(spec_dict["fps"]), mp4)
    if not keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)

    ink = [int(np.count_nonzero(np.asarray(m["mask"]))) for m in masks]
    # The ramp-up is the first half of the palindrome, apex excluded: frame n/2 and
    # frame n/2-1 sit either side of the turn, and counting the turn twice would
    # compare a weight against itself and report a plateau as a rendering defect.
    half = len(ink) // 2
    ascending = ink[:half]
    monotonic = all(a < b for a, b in zip(ascending, ascending[1:]))
    reversible = all(ink[i] == ink[len(ink) - 1 - i] for i in range(half))

    # determinism gate: re-render from the same spec and compare the payload digest
    deterministic = content_hash(frames) == content_hash(
        render_frames(spec_dict, render_masks(spec_dict, face, lo, hi)))

    measured = {
        "width": int(spec_dict["width"]), "height": int(spec_dict["height"]),
        "axis_from": lo, "axis_to": hi,
        "ink_monotonic": monotonic,
        "deterministic": deterministic,
        "duration": len(frames) / int(spec_dict["fps"]),
    }
    report = validate.run_acceptance(spec_dict["acceptance"], measured)
    report["measured"] = measured
    report["ink"] = {"per_frame": ink, "ascending_run": ascending,
                     "reversible": reversible,
                     "gain_pct": round(100.0 * (ascending[-1] - ascending[0]) / ascending[0], 1)}
    report["font"] = {"file": str(font_path), "axis": tag, "source_axes":
                      {k: list(v) for k, v in src_axes.items()},
                      "subset_bytes": subset_bytes,
                      "name_table_says": [list(masks[i]["name"]) for i in (0, half - 1, len(masks) - 1)]}
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    chash = content_hash(frames)
    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict, content_hash=chash,
        artifact_hashes={"type.mp4": provenance.sha256_file(mp4)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=(["type.mp4", "report.json", "manifest.json"]
                   + (["frames/"] if keep_frames else [])),
        notes=list(spec_dict.get("assumptions", [])) + [
            "frames exist only long enough to encode, then are deleted: the "
            "deliverable is the mp4 plus its content hash, not loose PNGs",
            "instancer leaves the name table alone, so the reported subfamily is "
            "not evidence of the rendered weight -- the ink count is",
        ],
        pipeline="vcac-type/0.1",
        extra={"fonts": [{
            "family": spec_dict["font"]["family"],
            "path": str(font_path),
            "source_sha256": provenance.sha256_file(font_path),
            "subset_bytes": subset_bytes,
            "axes": {k: list(v) for k, v in sub_axes.items()},
            "licence": spec_dict["font"].get("licence", "UNKNOWN"),
            "licence_note": spec_dict["font"].get("licence_note", ""),
        }]})
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="vcac variable-font route sample")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--keep-frames", action="store_true")
    a = ap.parse_args(argv)
    spec_dict = spec_mod.load_raw(a.spec)
    out_dir = a.out or (Path("outputs") / spec_dict["id"])
    r = run(a.spec, out_dir, keep_frames=a.keep_frames)
    rep, m = r["report"], r["report"]["measured"]
    ink = rep["ink"]
    print(f"[vcac:type] {spec_dict['id']} -> {r['out_dir']}")
    print(f"[vcac:type] axis {rep['font']['axis']} {m['axis_from']}-{m['axis_to']} "
          f"ink {ink['ascending_run'][0]} -> {ink['ascending_run'][-1]} "
          f"(+{ink['gain_pct']}%) subset={rep['font']['subset_bytes']}B "
          f"reversible={ink['reversible']}")
    for c in rep["checks"]:
        extra = (f"  (exp {c.get('expected')}, act {c.get('actual')})"
                 if c["status"] in ("pass", "fail") else f"  ({c.get('reason','')})")
        print(f"  [{c['status'].upper():7}] {c['id']}{extra}")
    print(f"[vcac:type] name table says: {rep['font']['name_table_says']}")
    print(f"[vcac:type] run_id={r['manifest']['run_id']}")
    print(f"[vcac:type] ACCEPTANCE {'PASSED' if rep['passed'] else 'FAILED'}")
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
