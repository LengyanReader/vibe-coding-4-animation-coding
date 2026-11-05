"""Is the nib measurement actually a nib measurement? Render both and compare.

The pen gate was moved onto the pre-downsample hard-edged raster after the print
raster turned out to be a 1-pixel lattice (see `manga_weight_probe.py`). That is
the fix that made the shipped page report `spread = 4.00 px`. The test this
probe serves asserts the opposite half: a page drawn with ONE constant width has
to go red. If it stays green, the supersample spread is not measuring the pen
either -- it would be measuring the interiors of filled masses, which are wide
whatever the nib does.

So: render the authored page and the flat-pen mutant, and print for each the
recovered width histogram on the nib raster, capped the way the gate caps it.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import yaml
from scipy import ndimage

from vcac import manga_ink
from vcac.manga_ink import _pen_weight, _rgb

SPEC = Path("specs/examples/manga-guild.yaml")
OUT = Path("outputs/_probe/nib_gate")


def _flat(node):
    if isinstance(node, dict):
        w = node.get("w")
        if isinstance(w, dict):
            node["w"] = {"profile": "flat", "a": 1.7, "b": 1.7}
        elif isinstance(w, list):
            node["w"] = [1.7, 1.7]
        for v in node.values():
            _flat(v)
    elif isinstance(node, list):
        for v in node:
            _flat(v)


def report(tag: str, spec: dict) -> None:
    S = float(spec.get("supersample", 3))
    spec["_fonts"] = manga_ink._resolve_fonts(spec)     # run() does this; render needs it
    art, hi = manga_ink.render(spec, OUT / tag)
    pal = spec["palette"]
    spread, median, ink_px = _pen_weight(hi, pal, S)
    print(f"\n=== {tag}: nib raster spread={spread:.2f} median={median:.2f} "
          f"ink_px={ink_px}  (gate floor 1.4) ===")

    # the same mask the gate builds, then the spine values it keeps
    ink = np.abs(hi.astype(int) - np.array(_rgb(pal, "ink"), dtype=int)).sum(-1) < 24
    dt = ndimage.distance_transform_edt(ink) * 2.0 / S      # print px widths
    ridge = (ink & (ndimage.maximum_filter(dt * S, size=int(round(9 * S))) == dt * S)
             & (dt * S > 0.45) & (dt * S <= 14.0 * S))
    v = dt[ridge]
    hist = Counter(np.round(v, 2).tolist())
    print(f"    ridge samples={v.size}  p10={np.percentile(v, 10):.2f} "
          f"p90={np.percentile(v, 90):.2f} p99={np.percentile(v, 99):.2f} "
          f"max={v.max():.2f}")
    print("    top widths (print px): " + ", ".join(
        f"{w}px {n * 100.0 / v.size:.1f}%" for w, n in hist.most_common(8)))
    # how much of the spread comes from things wider than any pen the spec wrote?
    widest = max(float((p.get("w") or {}).get("b", 0) if isinstance(p.get("w"), dict)
                       else 0)
                 for fig in spec["figures"] for p in fig.get("parts", []))
    over = float((v > max(widest, 4.0)).mean() * 100)
    print(f"    widest authored nib on the page: {widest:.2f} px print; "
          f"{over:.1f}% of ridge samples are WIDER than that "
          f"(those are filled masses, not pen strokes)")


authored = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
flat = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
_flat(flat)
report("authored", authored)
report("flat-pen", flat)
