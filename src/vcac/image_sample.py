"""Image route sample — value-noise poster (README §11 milestone: image line).

Zero-install, deterministic, self-verifying: seeded fractal value-noise is mapped
through the spec palette, saved as PNG, then measured against acceptance rules
(resolution, colour richness, information content) plus a determinism re-render.
This proves the *image* branch of the pipeline (spec -> render -> validate ->
manifest) independently of the video branch that already shipped in loop #1.

Run:
    $env:PYTHONPATH="src"; python -m vcac.image_sample specs/examples/poster-noise.yaml
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import cli, ffmpeg, media, provenance, spec as spec_mod, validate


def _smooth(t: np.ndarray) -> np.ndarray:
    return t * t * (3 - 2 * t)


def _noise_layer(g: np.ndarray, freq: int, w: int, h: int) -> np.ndarray:
    xs = np.linspace(0, freq, w)
    ys = np.linspace(0, freq, h)
    x0 = np.floor(xs).astype(int); xf = _smooth(xs - x0)
    y0 = np.floor(ys).astype(int); yf = _smooth(ys - y0)
    x1 = np.minimum(x0 + 1, freq)
    y1 = np.minimum(y0 + 1, freq)
    lerp = lambda a, b, t: a + (b - a) * t
    top = lerp(g[np.ix_(y0, x0)], g[np.ix_(y0, x1)], xf[None, :])
    bot = lerp(g[np.ix_(y1, x0)], g[np.ix_(y1, x1)], xf[None, :])
    return lerp(top, bot, yf[:, None])


def render_image(spec_dict: dict) -> np.ndarray:
    """(H,W,3) uint8 — deterministic from (seed, size, palette, octaves)."""
    w, h = int(spec_dict["width"]), int(spec_dict["height"])
    seed = int(spec_dict.get("seed", 42))
    octaves = int(spec_dict.get("octaves", 5))
    base = int(spec_dict.get("base_freq", 6))
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w)); amp = 1.0; norm = 0.0
    for o in range(octaves):
        freq = base * (2 ** o)
        g = rng.random((freq + 1, freq + 1))
        acc += amp * _noise_layer(g, freq, w, h)
        norm += amp; amp *= 0.5
    v = acc / norm
    lo, hi = float(v.min()), float(v.max())  # auto-contrast: fBm clusters near 0.5
    v = (v - lo) / (hi - lo) if hi > lo else np.zeros_like(v)
    v = np.clip(v, 0.0, 1.0)
    pal = np.asarray([spec_mod.parse_hex(c) for c in spec_dict["palette"]], dtype=np.float64)
    n = len(pal) - 1
    x = v * n
    i = np.clip(x.astype(int), 0, n - 1)
    f = (x - i)[..., None]
    rgb = pal[i] * (1 - f) + pal[i + 1] * f
    # triangular dither breaks up gradient banding (a real poster defect) and
    # lifts colour depth; amplitude is a spec knob so the field stays honest.
    strength = float(spec_dict.get("dither", 8.0))
    dither = (rng.random((h, w, 1)) - rng.random((h, w, 1))) * strength
    rgb = np.clip(rgb + dither, 0, 255).astype(np.uint8)
    return rgb


def _content_hash(arr: np.ndarray) -> str:
    return provenance.sha256_bytes(arr.tobytes())


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    arr = render_image(spec_dict)
    img = media.arr_to_image(arr)
    poster = out_dir / "poster.png"
    img.save(poster)

    # determinism gate: re-render and compare content hash
    deterministic = _content_hash(render_image(spec_dict)) == _content_hash(arr)

    measured = {
        # the artifact's dimensions (read back off the saved PNG), not the
        # spec's claim — a declared size the pixels don't honour must fail,
        # and a quoted YAML number must not false-fail on a str/int compare
        "width": media.image_size(poster.read_bytes())[0],
        "height": media.image_size(poster.read_bytes())[1],
        "unique_colors": media.unique_colors(img),
        "entropy_bits": media.entropy_bits(img),
        "deterministic": deterministic,
    }
    report = validate.run_acceptance(spec_dict["acceptance"], measured)
    report["measured"] = measured
    cli.write_report(out_dir, report)

    chash = _content_hash(arr)
    tools_ff = ffmpeg.version()
    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict, content_hash=chash,
        artifact_hashes={"poster.png": provenance.sha256_file(poster)},
        ffmpeg_version=tools_ff, acceptance=report,
        artifacts=["poster.png", "report.json", "manifest.json"],
        notes=spec_dict.get("assumptions", []), pipeline="vcac-image/0.1")
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    a = cli.parse_args("vcac image route sample", argv)
    spec_dict = spec_mod.load_raw(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec_dict["id"]))
    m = r["report"]["measured"]
    return cli.finish("image", r, summaries=[
        f"{spec_dict['id']} -> {r['out_dir']}",
        f"{m['width']}x{m['height']} unique_colors={m['unique_colors']} "
        f"entropy={m['entropy_bits']:.2f}b"])


if __name__ == "__main__":
    raise SystemExit(main())
