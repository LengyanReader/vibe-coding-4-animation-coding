"""Does the sky rule measure the composition or the quantiser? Both, side by side.

`sky_negative_pct` is claimed to be "the share of the sky carrying no mark". Two
mutants showed it was not: covering the dusk sky with two enormous smooth cloud
banks took the number 45.9 -> **75.6**, and deleting every cloud and the sun took
it 45.9 -> **44.7**. Drawing into the sky made it read emptier, because the sheet
is Bayer-dithered before the nearest-colour snap and a raw luma gradient counts
that alternation as a mark.

The route now judges busyness on a 5x5 median-filtered luma (dither cancels, hard
edges survive). This prints, for five sheets and mutants, both versions of the
number next to the band the spec asserts, so the recalibration is a measurement
and not a guess about which direction is which.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from scipy import ndimage

from vcac import illustration_sample

SPEC = Path("specs/examples")
OUT = Path("outputs/_probe/sky_gate")


def both(name: str, raw: dict) -> dict:
    p = illustration_sample.run(_write(name), OUT / name)
    art = np.asarray(Image.open(Path(p["out_dir"]) / "print.png").convert("RGB"))
    lum = art @ np.array([0.2126, 0.7152, 0.0722])
    h, w = lum.shape
    band = int(float(raw["frame"].get("logo_band", 0.14)) * h)
    top = int(h * 0.42)

    gx = np.abs(np.diff(lum, axis=1, prepend=lum[:, :1]))
    gy = np.abs(np.diff(lum, axis=0, prepend=lum[:1]))
    old = float((ndimage.maximum_filter(((gx + gy) > 24).astype(np.uint8),
                                        size=13)[band:top] == 0).mean() * 100)
    m = ndimage.median_filter(lum, size=5, mode="nearest")
    mx = np.abs(np.diff(m, axis=1, prepend=m[:, :1]))
    my = np.abs(np.diff(m, axis=0, prepend=m[:1]))
    new = float((ndimage.maximum_filter(((mx + my) > 24).astype(np.uint8),
                                        size=13)[band:top] == 0).mean() * 100)
    rule = next(r for r in raw["acceptance"] if "sky negative space" in r)
    got = p["report"]["measured"]["sky_negative_pct"]
    print(f"{name:22s} raw={old:6.2f}%  median5={new:6.2f}%  route={got:6.2f}%  "
          f"{rule}")
    return p


def _write(name: str) -> Path:
    p = OUT / f"{name}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(CASES[name], allow_unicode=True), encoding="utf-8")
    return p


def load(sheet: str) -> dict:
    return yaml.safe_load((SPEC / f"{sheet}.yaml").read_text(encoding="utf-8"))


def bare(raw: dict) -> dict:
    raw["backdrop"]["clouds"] = []
    raw["backdrop"].pop("sun", None)
    return raw


def flooded(raw: dict) -> dict:
    bank = {"at": [0.50, 0.20], "scale": 0.42, "shade": "sky_mid",
            "lit": "sky_low", "edge": "rim", "band": "top",
            "lobes": [[-1.2 + 0.3 * k, 0.0, 0.5] for k in range(9)]}
    raw["backdrop"]["clouds"].extend([dict(bank), dict(bank, at=[0.50, 0.40])])
    return raw


def speckled(raw: dict) -> dict:
    """Many SMALL hard-edged clouds: the honest way to busy a sky."""
    banks = []
    for i in range(10):
        banks.append({"at": [0.06 + 0.1 * (i % 5), 0.17 + 0.05 * (i // 5)],
                      "scale": 0.035, "shade": "shadow", "lit": "rim",
                      "edge": "ink", "band": "top",
                      "lobes": [[-0.6, 0.0, 0.5], [0.0, -0.2, 0.7], [0.6, 0.05, 0.45]]})
    raw["backdrop"]["clouds"].extend(banks)
    return raw


def no_lines(raw: dict) -> dict:
    """The shonen cover's sky is its radial speed lines: take them away and the
    band should empty out, which is the ceiling side of the rule."""
    raw["speed_lines"]["count"] = 0
    return raw


CASES = {
    "fox-authored": load("illust-fox"),
    "fox-bare": bare(load("illust-fox")),
    "fox-flooded": flooded(load("illust-fox")),
    "fox-speckled": speckled(load("illust-fox")),
    "guild-authored": load("illust-guild"),
    "guild-no-lines": no_lines(load("illust-guild")),
    "cumulus-authored": load("illust-cumulus"),
}

for name, spec in CASES.items():
    both(name, spec)
