"""Does `ink weight spread` on the shipped page measure pressure, or quantisation?

The gate is `p90 - p10` of the half-width recovered from the ink pixels' distance
transform, times two. The page reports spread = 2.00 and median = 2.00 -- one and
the same number -- and passes its 1.4 px bound. Two equal percentiles means the
recovered weights have essentially ONE value, so the gate is green without having
seen a pressure curve. This prints the actual distribution.

    $env:PYTHONPATH="src"; python scripts/probes/manga_weight_probe.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from scipy import ndimage

from vcac.manga_ink import _rgb

PAGE = Path("outputs/manga-guild/page.png")
SPEC = Path("specs/examples/manga-guild.yaml")


def main() -> None:
    pal = yaml.safe_load(SPEC.read_text(encoding="utf-8"))["palette"]
    art = np.asarray(Image.open(PAGE).convert("RGB"))
    ink = np.abs(art.astype(int) - np.array(_rgb(pal, "ink"), int)).sum(-1) < 24
    print(f"ink pixels: {int(ink.sum()):,} of {ink.size:,} "
          f"({100.0 * ink.mean():.2f}%)")
    for max_px in (13.0, 13.0 * 3):
        dt = ndimage.distance_transform_edt(ink)
        ridge = (ink & (ndimage.maximum_filter(dt, size=9) == dt)
                 & (dt > 0.45) & (dt <= max_px))
        v = dt[ridge] * 2.0
        if v.size < 60:
            print(f"max_px={max_px}: only {v.size} ridge samples -> the function "
                  f"returns 0.0,0.0 (refusal), not a green")
            continue
        u, c = np.unique(np.round(v, 3), return_counts=True)
        print(f"\nmax_px={max_px}: samples={v.size:,}  min={v.min():.2f} "
              f"p10={np.percentile(v,10):.2f} p50={np.percentile(v,50):.2f} "
              f"p90={np.percentile(v,90):.2f} max={v.max():.2f}  "
              f"spread={np.percentile(v,90)-np.percentile(v,10):.2f}")
        print(f"  distinct recovered weights: {u.size}")
        for w_, n_ in sorted(zip(u.tolist(), c.tolist()), key=lambda t: -t[1])[:8]:
            print(f"    {w_:6.2f} px  {n_:>7,}  ({100.0*n_/v.size:5.1f}%)")
    print("\nThe sheet is rendered at supersample 3 and then Lanczos-downsampled "
          "to print px, so a recovered thickness is pinned to a ~1 px lattice: "
          "widening the sampling window cannot invent intermediate widths that "
          "the downsample did not leave behind.")


if __name__ == "__main__":
    main()
