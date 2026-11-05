"""Where does the page's width sample actually come from? Paths, not adjectives.

The first reading of this used the widest nib in `figures[].parts[]` (3.60 px) and
concluded that a third of the width sample must be filled masses. The route's own
`_widest_nib` walk finds 6.36 px, so that conclusion was an artifact of looking in
only one place -- which is the mistake this session keeps making, so it gets
measured instead of argued.

Prints, for the authored page and for the constant-width mutant:
  * the widest authored nibs with the path they live at, so "a pen stroke" can be
    checked against the thing that authored it;
  * the recovered width percentiles and the share above the widest authored nib;
  * the share above each candidate cap, because `measure_max_px: 13` is where the
    sample is currently cut and that cut is a choice.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import yaml
from scipy import ndimage

from vcac import manga_ink
from vcac.manga_ink import _rgb, _widest_nib

SPEC = Path("specs/examples/manga-guild.yaml")
OUT = Path("outputs/_probe/nib_leak")


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


def widest_with_paths(spec, limit=12):
    """(width, path) for every authored nib on the page, heaviest first."""
    found: list[tuple[float, str]] = []

    def val(w):
        if isinstance(w, dict):
            a = float(w.get("a", w.get("w", 1.6)))
            return max(a, float(w.get("b", w.get("peak", a))))
        if isinstance(w, (int, float)):
            return float(w)
        if isinstance(w, (list, tuple)) and len(w) >= 2:
            return max(float(w[0]), float(w[1]))
        return None

    def walk(node, path):
        if isinstance(node, dict):
            if "w" in node:
                v = val(node["w"])
                if v is not None:
                    prof = node["w"].get("profile", "?") if isinstance(node["w"], dict) \
                        else "?"
                    found.append((v, f"{path} kind={node.get('kind', 'ink')} "
                                     f"profile={prof}"))
            for k, x in node.items():
                if k not in ("w", "_fonts"):
                    walk(x, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, x in enumerate(node):
                walk(x, f"{path}[{i}]")

    walk({k: v for k, v in spec.items() if k != "_fonts"}, "")
    heaviest = max([float(f.get("nib", 1.0))
                    for f in (spec.get("figures") or [])] + [1.0])
    found.sort(reverse=True)
    print(f"    heaviest figure nib multiplier: {heaviest}")
    for v, p in found[:limit]:
        print(f"      {v * heaviest:6.2f} px  {p[:120]}")


def widths(tag: str, spec: dict) -> None:
    S = float(spec.get("supersample", 3))
    spec["_fonts"] = manga_ink._resolve_fonts(spec)
    cap = float(spec["nib"].get("measure_max_px", 14))
    widest = _widest_nib(spec)
    art, hi = manga_ink.render(spec, OUT / tag)
    ink = np.abs(hi.astype(int) - np.array(_rgb(spec["palette"], "ink"),
                                           dtype=int)).sum(-1) < 24
    dt = ndimage.distance_transform_edt(ink)
    ridge = (ink & (ndimage.maximum_filter(dt, size=int(round(9 * S))) == dt)
             & (dt > 0.45) & (dt <= cap * S))
    v = dt[ridge] * 2.0 / S
    print(f"\n=== {tag}: widest authored nib = {widest} px, cap = {cap} px ===")
    widest_with_paths(spec)
    hist = Counter(np.round(v, 2).tolist())
    print(f"    n={v.size} p10={np.percentile(v, 10):.2f} "
          f"p50={np.percentile(v, 50):.2f} p90={np.percentile(v, 90):.2f} "
          f"p99={np.percentile(v, 99):.2f} max={v.max():.2f} "
          f"spread={np.percentile(v, 90) - np.percentile(v, 10):.2f}")
    print("    top widths: " + ", ".join(
        f"{w}px {n * 100.0 / v.size:.1f}%" for w, n in hist.most_common(6)))
    for thr in (widest, 4.0, 5.0, 6.0):
        print(f"    share above {thr:5.2f} px : {(v > thr).mean() * 100:5.1f}%")


authored = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
flat = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
_flat(flat)
widths("authored", authored)
widths("flat-pen", flat)
