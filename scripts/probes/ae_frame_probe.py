"""Render selected frames of the anime route to PNG for looking at.

`python scripts/probes/ae_frame_probe.py 3 9` -> outputs/_probe/ae_t03.png etc.
A full 288-frame run costs minutes and re-encodes; a still is what decides
whether a figure reads as a figure, so the still has to be cheap to get.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vcac import anime_sample, spec as spec_mod  # noqa: E402

spec = spec_mod.load(Path("specs/examples/anime-eave.yaml"))
scene = anime_sample.make_scene(spec)
out = Path("outputs/_probe")
out.mkdir(parents=True, exist_ok=True)
for arg in sys.argv[1:] or ["3", "9"]:
    t = float(arg)
    img = anime_sample.frame_image(spec, scene, t)
    p = out / f"ae_t{int(t):02d}.png"
    img.save(p)
    print(p)
