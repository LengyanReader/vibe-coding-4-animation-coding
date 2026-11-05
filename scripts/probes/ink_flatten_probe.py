"""Which palette colours survive the flattened-ramp mutant, and where do they come
from? Printed by hand while the ink route's value-band gate was being re-derived;
kept because the gate's expected colour count is a claim about the *whole* sheet,
not just about `layers:`, and only a measurement can say what paints outside it.

    $env:PYTHONPATH="src"; python scripts/probes/ink_flatten_probe.py
"""
from __future__ import annotations

import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from vcac import ink_landscape
from vcac.spec import parse_hex

SPEC = Path("specs/examples/ink-landscape.yaml")


def run(raw: dict, tag: str) -> Counter:
    out = Path(tempfile.mkdtemp())
    p = out / f"{tag}.yaml"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    r = ink_landscape.run(p, out / "ink")
    art = np.asarray(Image.open(next((out / "ink").glob("*.png"))).convert("RGB"))
    inv = {parse_hex(h): n for n, h in raw["palette"].items()}
    c = Counter(map(tuple, art.reshape(-1, 3).tolist()))
    print(f"\n=== {tag}: {len(c)} distinct, gates said "
          f"{r['report']['measured']['palette_distinct_colors']} ===")
    for k, v in sorted(r["report"]["measured"].items()):
        print(f"    measured {k} = {v}")
    for col, n in c.most_common():
        print(f"  {inv.get(col, '?'):>7}  {col}  {n:>9,}  "
              f"{100.0 * n / art.reshape(-1, 3).shape[0]:5.2f}%")
    return c


def main() -> None:
    base = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    run(base, "golden")

    flat = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    for lay in flat["layers"]:
        lay["ink"] = lay["contour_ink"] = lay["texture_ink"] = 1
        lay.pop("jiao", None)
    run(flat, "flattened-layers-only")

    # the same sheet with the markers removed: if the escaping tones belong to the
    # trees / pavilion / water rather than to the ranges, this is what proves it
    nomark = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    for lay in nomark["layers"]:
        lay["ink"] = lay["contour_ink"] = lay["texture_ink"] = 1
        lay.pop("jiao", None)
    nomark["features"] = {}
    run(nomark, "flattened-no-features")


if __name__ == "__main__":
    main()
