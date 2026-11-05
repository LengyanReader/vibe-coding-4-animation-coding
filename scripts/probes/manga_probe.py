"""Render one cast member of a manga spec, big and alone, for looking at.

`python scripts/probes/manga_probe.py specs/examples/manga-guild.yaml 0 640 v3`
  -> outputs/_probe/manga_guild_f0_v3.png

A full page costs seconds and a mistake in an eyelash is four pixels wide on a
1400 px sheet, so it cannot be judged there. This paints one figure into its own
frame at a size where the nib can actually be seen. No gates run on it: a page
cropped to one face is not the artifact, it is the drafting table.

The version suffix is not decoration — the image viewer caches by path, so a
re-render under the same name shows the previous attempt.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

from vcac import manga_ink, spec as spec_mod


def main() -> int:
    spec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "specs/examples/manga-guild.yaml")
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 640
    tag = sys.argv[4] if len(sys.argv) > 4 else "v1"

    spec = spec_mod.load_raw(spec_path)
    manga_ink._refuse(spec)
    name = str(spec["figures"][idx].get("id", idx))
    out = Path("outputs/_probe")
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"manga_{spec['id']}_f{idx}_{name}_{tag}.png"
    Image.fromarray(manga_ink.figure(spec, idx, size)).save(p)
    print(f"{p}  figure={name} size={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
