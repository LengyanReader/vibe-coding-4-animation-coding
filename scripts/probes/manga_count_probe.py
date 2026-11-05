"""Why did the manga page report `figures=11` and `eyes=67` when the spec authors
five faces and ten eyes? Both gates passed, so on the sheet the claims were
indistinguishable from true. This prints every candidate the two counters accept,
with the numbers that decided each one, and draws the accepted boxes on an overlay
so a human can see WHAT the gate was actually looking at.

    $env:PYTHONPATH="src"; python scripts/probes/manga_count_probe.py

Overlay written to outputs/_probe/manga_count_overlay.png.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw
from scipy import ndimage

from vcac.manga_ink import _rgb

PAGE = Path("outputs/manga-guild/page.png")
SPEC = Path("specs/examples/manga-guild.yaml")


def eye_candidates(art, pal, w, h):
    """The body of _eye_count, with the decisions exposed instead of summed."""
    paper = np.abs(art.astype(int) - np.array(_rgb(pal, "paper"), int)).sum(-1) < 40
    ink = np.abs(art.astype(int) - np.array(_rgb(pal, "ink"), int)).sum(-1) < 40
    dark = np.abs(art.astype(int) - np.array(_rgb(pal, "eye_dark"), int)).sum(-1) < 40
    ink_or_dark = ink | dark
    lbl, n = ndimage.label(paper)
    ring = ndimage.binary_dilation(ink_or_dark, iterations=3)
    out = []
    for ids, sl in enumerate(ndimage.find_objects(lbl), 1):
        m = lbl[sl] == ids
        area = int(m.sum())
        if not (0.000018 * w * h <= area <= 0.0012 * w * h):
            continue
        tall, wide = sl[0].stop - sl[0].start, max(1, sl[1].stop - sl[1].start)
        if tall > 2.2 * wide or wide > 3.2 * tall:
            continue
        edge = ndimage.binary_dilation(m, iterations=2) & ~m
        share = float((ring[sl][edge]).mean()) if edge.size else 0.0
        # the discriminator the counter is missing: an eye is a white island with
        # an iris INSIDE it. A punched 毛筋 highlight or a glyph hole has none.
        # The iris is not a hole in the PAPER mask (the eye's white is a ring
        # around it, the iris itself is eye_dark), so "inside" means the pixels
        # the island encloses, whichever colour they are.
        holes = ndimage.binary_fill_holes(m) & ~m
        inside_dark = int((holes & ink_or_dark[sl]).sum())
        inside_any = int(holes.sum())
        out.append({"id": ids, "box": (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop),
                    "area": area, "ar": round(wide / tall, 2), "ring": round(share, 3),
                    "accept": share > 0.55, "inside_dark": inside_dark,
                    "inside_any": inside_any})
    return out


def dark_on_skin(art, pal, w, h, lo=0.000006, hi=0.0006, onskin_min=0.5):
    """Candidate #2 for an honest eye counter: eyes are the DARK things sitting on
    SKIN, not the white things sitting anywhere. The iris and pupil are drawn as
    small closed marks in ink/eye_dark on a face, and nothing else in this grammar
    is a compact dark island whose bbox is mostly skin -- hair sits on cloth, brows
    are thin arcs, the logotype is on paper. `lo`/`hi` are fractions of the sheet;
    `onskin_min` is the share of the island's own pixels that land on skin.
    """
    A = art.astype(int)
    dark = ((np.abs(A - np.array(_rgb(pal, "ink"), int)).sum(-1) < 40)
            | (np.abs(A - np.array(_rgb(pal, "eye_dark"), int)).sum(-1) < 40))
    skin = np.abs(A - np.array(_rgb(pal, "skin"), int)).sum(-1) < 40
    lbl, n = ndimage.label(dark)
    if not n:
        return []
    objs = ndimage.find_objects(lbl)
    sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, n + 1))
    out = []
    for i, sl in enumerate(objs, 1):
        if not (lo * w * h <= sizes[i - 1] <= hi * w * h):
            continue
        tall, wide = sl[0].stop - sl[0].start, max(1, sl[1].stop - sl[1].start)
        if tall > 2.4 * wide or wide > 3.6 * tall:
            continue
        m = lbl[sl] == i
        share = float((skin[sl][m]).mean())
        if share < onskin_min:
            continue
        out.append({"box": (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop),
                    "area": int(sizes[i - 1]), "ar": round(wide / tall, 2),
                    "onskin": round(share, 3)})
    return out


def main() -> None:
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    pal = spec["palette"]
    img = Image.open(PAGE).convert("RGB")
    art = np.asarray(img)
    h, w = art.shape[:2]
    cands = eye_candidates(art, pal, w, h)
    acc = [c for c in cands if c["accept"]]
    print(f"paper islands that pass the shape filter: {len(cands)}")
    print(f"accepted as EYES: {len(acc)}   (spec authors {len(spec['figures'])} faces "
          f"= {2 * len(spec['figures'])} eyes)")
    for c in sorted(acc, key=lambda c: -c["inside_dark"]):
        print(f"  box={c['box']} area={c['area']:>6} ar={c['ar']:>4} "
              f"ring={c['ring']:.3f} dark_inside={c['inside_dark']:>4} "
              f"enclosed={c['inside_any']:>4}")
    print("\nrejected (shape ok, ring too thin) — sample of 12:")
    for c in [x for x in cands if not x["accept"]][:12]:
        print(f"  box={c['box']} area={c['area']:>6} ar={c['ar']:>4} ring={c['ring']:.3f} "
              f"dark_inside={c['inside_dark']:>4} enclosed={c['inside_any']:>4}")

    ov = img.copy()
    d = ImageDraw.Draw(ov)
    for c in cands:
        col = "#2E8B57" if c["accept"] and c["inside_dark"] > 0 else "#C0392B"
        d.rectangle(c["box"], outline=col, width=3)
    ov.save(Path("outputs/_probe/manga_count_overlay.png"))
    print("\nwrote outputs/_probe/manga_count_overlay.png "
          "(green = accepted AND has a dark pixel inside, red = accepted as an "
          "empty white island)")

    for lo, hi, mn in ((0.000006, 0.0006, 0.5), (0.000004, 0.0009, 0.6)):
        alt = dark_on_skin(art, pal, w, h, lo, hi, mn)
        print(f"\ncandidate #2 (dark island on skin, area {lo}-{hi} of sheet, "
              f"onskin>{mn}): {len(alt)}")
        for c in alt:
            print(f"  box={c['box']} area={c['area']:>5} ar={c['ar']:>4} "
                  f"onskin={c['onskin']}")


if __name__ == "__main__":
    main()
