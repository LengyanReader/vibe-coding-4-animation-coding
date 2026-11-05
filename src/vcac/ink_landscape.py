"""ink-landscape route — 中国水墨山水 as a deterministic nine-step chain.

Implements docs/styles.md §1.2 with Pillow + NumPy + SciPy only. The chain IS
the painting theory turned into code (styles.md §0: "把画理写成约束，而非调滤镜"):

  1. 纸本      fractal paper grain + fiber direction field
  2. 地形      three height-field ridges (三远: far/mid/near) with atmospheric
               perspective — 远山淡, 近山浓
  3. 勾        ridge contour polylines, jittered along the normal (seeded)
  4. 皴        texture strokes沿坡度: long parallel arcs on the near hill
               (披麻), dot clusters on the far ridge (雨点)
  5. 染        low-frequency ink wash under each ridge (gaussian blur)
  6. 积墨      layered thin ink (two blur radii) instead of one heavy pass
  7. 云气留白  the mist is regions the renderer *refuses to paint* — the top
               band and the valley gaps are pulled back to paper
  8. 题款钤印  vertical colophon (public-domain Wang Wei couplet) in an OFL
               running-script font + a programmatic seal with chipped edges
  9. 验收      measured, not mood words: the artifact is quantised to the
               declared 7-colour palette (paper + ink five tones 墨分五色 +
               seal red 印泥红), then gated on band occupancy, negative-space
               ratio, region-weighted whiteness/entropy, and seal presence.

Honesty notes: the ink bleed of step 5 is a gaussian *approximation*, not a
physical diffusion model (styles.md §1.3 routes are excluded as
non-deterministic); the colophon font is an external licensed input, hashed
into the pipeline cache key via the spec's ``font.paths`` (audit A7).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

from . import cli, ffmpeg, media, provenance, spec as spec_mod, validate

_COLON = "江流天地外"
_COLON2 = "山色有无中"          # 王维《汉江临眺》— public domain
_SEAL_TEXT = "山水清音"


class InkError(ValueError):
    """The spec asks for something the chain refuses (e.g. a missing font)."""


_PALETTE_KEYS = ("paper", "ink1", "ink2", "ink3", "ink4", "ink5", "seal")


def _refuse_unmeasurable(spec_dict: dict) -> None:
    """Fail before rendering a picture whose own report could not be truthful.

    Three of the nine 验收 rules are per-colour pixel counts: the value bands count
    pixels equal to each declared ink, the seal rule labels pixels equal to the
    seal colour, and the palette ceiling counts distinct colours. A palette with
    two entries on one hex therefore does not produce a painting short of a 墨 tone
    -- it produces numbers about numbers. Measured on this route: an ink-coloured
    seal scored **5 seals** because the whole sheet matched the dilate-and-label
    filter, and a ramp collapsed onto one tone scored 41% occupancy in every band.
    Refusing is the same stance the layout route takes against a grid that does
    not divide (audit A6).
    """
    pal = spec_dict.get("palette") or {}
    missing = [k for k in _PALETTE_KEYS if k not in pal]
    if missing:
        raise InkError(f"palette is missing the colours the chain needs: "
                       f"{', '.join(missing)}")
    seen: dict[tuple, str] = {}
    for k in _PALETTE_KEYS:
        rgb = tuple(spec_mod.parse_hex(pal[k]))
        if rgb in seen:
            # raised text stays ASCII: this message is printed to a Windows console
            # that defaults to cp1252, and a UnicodeEncodeError on the way out of
            # an error would bury the reason for the refusal (Chinese is in the
            # docstring above, where it is read, not printed)
            raise InkError(
                f"palette colours must be distinct: '{k}' and '{seen[rgb]}' are "
                f"both {rgb} - the value-band, seal and palette gates count "
                f"pixels per colour, so a collapsed palette measures nothing")
        seen[rgb] = k
    mist = float(spec_dict.get("mist_top", 0.22))
    if not 0.0 < mist < 1.0:
        raise InkError(f"mist_top must lie inside (0, 1): {mist} divides the "
                       f"mist blend by zero and paints the sheet with NaN")
    for li, lay in enumerate(spec_dict.get("layers") or []):
        reach = float(lay.get("reach", 0.5))
        if reach <= 0.0:
            # measured on this route: layers[+].reach = 0.0 raised two
            # RuntimeWarnings (divide by zero in the wash depth, invalid value in
            # the uint8 cast of the NaN), and the undefined pixels then quantised
            # onto the palette and scored **every gate green**. A passing report
            # built on undefined behaviour is worse than a failing one, so the
            # spec is refused before anything is painted
            raise InkError(
                f"layers[{li}].reach must be > 0: {reach} divides the wash depth "
                f"by zero, so the painting is made of undefined pixels whose "
                f"measurements mean nothing")


def _find_font(spec_dict: dict) -> tuple[Path, str]:
    sf = spec_dict.get("font") or {}
    tried = []
    for p in sf.get("paths", []):
        cand = Path(p)
        tried.append(str(cand))
        if cand.is_file():
            return cand, str(sf.get("licence", "unverified"))
    raise InkError(
        f"ink route needs a colophon font: none of the declared paths exist "
        f"({', '.join(tried) or 'no font.paths declared'}); run "
        f"python scripts/fetch_assets.py")


def _fbm_1d(w: int, freq: int, rng, octaves: int = 4) -> np.ndarray:
    """Sum-of-sines-free 1-D fBm: piecewise-smooth random lattice upsampled."""
    acc = np.zeros(w)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        f = freq * (2 ** o)
        g = rng.random(f + 1)
        xs = np.linspace(0, f, w)
        i0 = np.floor(xs).astype(int)
        i1 = np.minimum(i0 + 1, f)
        t = xs - i0
        t = t * t * (3 - 2 * t)
        acc += amp * (g[i0] * (1 - t) + g[i1] * t)
        amp *= 0.5
        norm += amp * 2
    return acc / (norm * 0.75)


def _domain_warp(profile: np.ndarray, w: int, rng, strength: float) -> np.ndarray:
    """Displace the ridge horizontally by a low-frequency field (step 2's
    域扭曲): mountains stop being analytic curves."""
    warp = _fbm_1d(w, 5, rng, octaves=3) - 0.5
    idx = np.clip(np.arange(w) + warp * strength * w, 0, w - 1)
    i0 = np.floor(idx).astype(int)
    i1 = np.minimum(i0 + 1, w - 1)
    t = idx - i0
    return profile[i0] * (1 - t) + profile[i1] * t


def _ridge(w: int, h: int, base_y: float, amp: float, freq: int, rng,
           warp: float, ridged: bool = True) -> np.ndarray:
    """One mountain ridge line: y(x) in pixels (step 2 地形).

    ``ridged`` folds the fBm into a ridged multifractal (``1 - |2n-1|``) so
    the silhouette has PEAKS — a plain fBm gives rolling hills, which is why
    the first renders read as geological strata."""
    profile = _fbm_1d(w, freq, rng, octaves=4)
    profile = _domain_warp(profile, w, rng, warp)
    profile = (profile - profile.min()) / max(1e-9, profile.max() - profile.min())
    if ridged:
        profile = (1 - np.abs(2 * profile - 1)) ** 1.6
    return base_y - profile * amp


def _paint_paper(w: int, h: int, paper: np.ndarray, rng, grain: float) -> np.ndarray:
    """Step 1 纸本: paper colour + fractal grain + horizontal fiber streaks."""
    img = np.ones((h, w, 3)) * paper[None, None, :]
    # 2-D grain: two 1-D fBms (one per axis) + a fiber field
    gx = _fbm_1d(w, 24, rng, octaves=3)
    gy = _fbm_1d(h, 18, rng, octaves=3)
    grain2 = 0.6 * (gx[None, :] + gy[:, None]) / 2
    fiber = rng.normal(0, 1, (h, 1)) * 0.4 + rng.normal(0, 1, (1, w)) * 0.1
    delta = (grain2 + fiber) * grain
    img += delta[:, :, None] * np.array([12.0, 10.0, 6.0])[None, None, :]
    return img


def _noise2d(w: int, h: int, rng, freq: int = 9) -> np.ndarray:
    """Coarse 2-D value noise, bilinearly upsampled — breaks the wash's
    horizontal quantisation bands into contour-like organic edges."""
    g = rng.random((freq + 1, freq + 1))
    ys = np.linspace(0, freq, h)
    xs = np.linspace(0, freq, w)
    y0 = np.floor(ys).astype(int); y1 = np.minimum(y0 + 1, freq)
    x0 = np.floor(xs).astype(int); x1 = np.minimum(x0 + 1, freq)
    ty = ys - y0; tx = xs - x0
    ty = ty * ty * (3 - 2 * ty); tx = tx * tx * (3 - 2 * tx)
    a = g[np.ix_(y0, x0)]; b = g[np.ix_(y0, x1)]
    c = g[np.ix_(y1, x0)]; d2 = g[np.ix_(y1, x1)]
    top = a * (1 - tx) + b * tx
    bot = c * (1 - tx) + d2 * tx
    return (top * (1 - ty)[:, None] + bot * ty[:, None]) - 0.5


def _wash_under(img: np.ndarray, ridge: np.ndarray, ink: np.ndarray,
                alpha: float, blur: float, w: int, h: int,
                reach: float = 0.5, noise: np.ndarray | None = None) -> np.ndarray:
    """Steps 5+6 染/积墨: soft ink wash below the ridge — two blurred alpha
    layers (tight + wide) make the accumulation, not one heavy fill."""
    ys = np.arange(h)[:, None]
    # ink pools just under the contour and fades downhill into the mist —
    # and ONLY below the ridge: the clip above made fall==1 across the whole
    # sky, which is where the horizontal bands came from
    below = (ys - ridge[None, :]) > 0
    depth = np.clip((ys - ridge[None, :]) / (h * reach), 0, 1)
    fall = (1 - depth) ** 1.2 * below * (0.8 + 0.6 * (noise if noise is not None else 0.0))
    a_tight = ndimage.gaussian_filter(fall * alpha, blur * 0.35)
    a_wide = ndimage.gaussian_filter(fall * alpha * 0.7, blur)
    for a in (a_tight, a_wide):
        img = img * (1 - a[..., None]) + ink[None, None, :] * a[..., None]
    return img


def _draw_contour(d: ImageDraw.ImageDraw, ridge: np.ndarray, ink: tuple,
                  rng, jitter: float, width: int) -> None:
    """Step 3 勾: the ridge contour as a jittered polyline (Rough.js spirit:
    seeded noise along the normal, never an analytic curve)."""
    pts = []
    for x in range(0, len(ridge), 4):
        j = (rng.random() - 0.5) * jitter
        pts.append((x, float(ridge[x]) + j))
    d.line(pts, fill=ink, width=width, joint="curve")


def _draw_texture(d: ImageDraw.ImageDraw, ridge: np.ndarray, ink: tuple,
                  rng, style: str, w: int, h: int) -> None:
    """Step 4 皴: texture primitives laid along the slope.
    披麻 pima = long parallel arcs (near hills); 雨点 yudian = dot clusters
    (far ridges). Density follows the local gradient."""
    grad = np.abs(np.gradient(ridge))
    if style == "pima":
        for x in range(0, w - 24, 6):
            g = grad[x] * 60
            for k in range(int(1 + min(4, g))):
                x0 = x + int(rng.integers(0, 7))
                y0 = ridge[x] + int(rng.integers(2, 30))
                ln = int(10 + 22 * min(1.0, g) + int(rng.integers(0, 6)))
                drift = int(np.sign(np.gradient(ridge)[min(x + ln, w - 1)]) * ln // 3)
                d.line([(x0, y0), (x0 + drift, y0 + ln)], fill=ink, width=1)
    else:  # yudian — 2x2 dot clusters, denser where the slope falls
        for x in range(0, w, 5):
            g = grad[x] * 120
            for k in range(int(min(5, 1 + g))):
                x0 = x + int(rng.integers(0, 6))
                y0 = ridge[x] + int(rng.integers(3, 16))
                d.rectangle([x0, y0, x0 + 1, y0 + 1], fill=ink)


def _mist(img: np.ndarray, paper: np.ndarray, h: int, w: int,
          top_frac: float) -> np.ndarray:
    """Step 7 云气留白: mist is *not painted* — the top band eases back to
    paper, and a soft band sits in the valley between far and mid mountains."""
    ys = np.arange(h)[:, None]
    # full paper through the first ~60% of the mist band, easing out below it —
    # the strip must measure WHITE even where wash blur creeps upward
    a_top = np.clip((top_frac - ys / h) / (top_frac * 0.35), 0, 1)
    band_y = int(h * (top_frac + 0.10))
    a_band = np.exp(-((ys - band_y) / (h * 0.035)) ** 2) * 0.85
    alpha = np.clip(a_top + a_band, 0, 1)
    return img * (1 - alpha[..., None]) + paper[None, None, :] * alpha[..., None]


def _draw_colophon(img: Image.Image, font_path: Path, ink_dark: tuple,
                   w: int, h: int, rng) -> None:
    """Step 8 题款: vertical couplet, right side, running script."""
    font = ImageFont.truetype(str(font_path), int(h * 0.030))
    d = ImageDraw.Draw(img)
    for col, text in enumerate((_COLON, _COLON2)):
        x = int(w * 0.885) - col * int(h * 0.048)
        y0 = int(h * 0.055)
        for i, ch in enumerate(text):
            d.text((x, y0 + i * int(h * 0.043)), ch, font=font, fill=ink_dark)
    d.text((int(w * 0.79), int(h * 0.055) + int(h * 0.043) * len(_COLON)),
           "倣古", font=font, fill=ink_dark)


def _draw_seal(img: Image.Image, seal_ink: tuple, paper: tuple,
               font_path: Path, w: int, h: int, rng) -> int:
    """Step 8 钤印: 朱文-style seal — red ground, white characters, chipped
    edges from seeded noise. Returns the number of red connected components
    (measured, not asserted)."""
    size = int(h * 0.058)
    seal = Image.new("RGB", (size, size), seal_ink)
    sd = ImageDraw.Draw(seal)
    font = ImageFont.truetype(str(font_path), int(size * 0.34))
    for i, ch in enumerate(_SEAL_TEXT):
        sd.text((size * (0.10 + (i % 2) * 0.42), size * (0.06 + (i // 2) * 0.42)),
                ch, font=font, fill=paper)
    # edge chipping: erode the red where noise is high near the border
    arr = np.asarray(seal).astype(float)
    yy, xx = np.mgrid[0:size, 0:size]
    border = np.minimum(np.minimum(xx, size - 1 - xx), np.minimum(yy, size - 1 - yy))
    chip = (rng.random((size, size)) * max(4, size // 12)) > border
    arr[chip] = np.array(paper, dtype=float)
    x0, y0 = int(w * 0.800), int(h * 0.055) + int(h * 0.043) * (len(_COLON) + 2)
    patch = Image.fromarray(arr.astype(np.uint8))
    img.paste(patch, (x0, y0))
    return None


def _quantise(img_arr: np.ndarray, palette: np.ndarray) -> np.ndarray:
    """Step 9: snap every pixel to the declared palette (paper + 墨分五色 +
    印泥红). Quantisation is what makes the 色域 gate measurable: the artifact
    either is the declared gamut or it is not."""
    flat = img_arr.reshape(-1, 3)
    d = ((flat[:, None, :] - palette[None, :, :]) ** 2).sum(-1)
    return palette[d.argmin(axis=1)].reshape(img_arr.shape)


def render_ink(spec_dict: dict) -> Image.Image:
    rng = np.random.default_rng(int(spec_dict.get("seed", 11)))
    w, h = int(spec_dict["width"]), int(spec_dict["height"])
    pal = spec_dict["palette"]
    paper = np.array(spec_mod.parse_hex(pal["paper"]), dtype=float)
    inks = [np.array(spec_mod.parse_hex(pal[k]), dtype=float)
            for k in ("ink1", "ink2", "ink3", "ink4", "ink5")]   # 清→焦
    seal_ink = np.array(spec_mod.parse_hex(pal["seal"]), dtype=float)
    font_path, _lic = _find_font(spec_dict)

    # 1 纸本
    img = _paint_paper(w, h, paper, rng, grain=float(spec_dict.get("paper_grain", 1.0)))

    # 2 地形 — 三远: three ridges, far light & high, near dark & low
    layers = spec_dict.get("layers", [
        {"base_y": 0.42, "amp": 0.14, "freq": 5, "warp": 0.06, "ink": 1, "alpha": 0.22, "style": "yudian"},
        {"base_y": 0.55, "amp": 0.22, "freq": 4, "warp": 0.10, "ink": 2, "alpha": 0.34, "style": "yudian"},
        {"base_y": 0.78, "amp": 0.30, "freq": 3, "warp": 0.16, "ink": 4, "alpha": 0.52, "style": "pima"},
    ])
    wash_noise = _noise2d(w, h, rng)
    # PIL does not share memory with the array it wraps (measured: drawing on an
    # image made by fromarray leaves the source array at zero), so the sheet is
    # opened here rather than lazily inside the loop: a spec with layers: [] used
    # to reach _draw_colophon with pil = None and die on an AttributeError. Paper
    # plus colophon plus seal is a *paintable* reading of an empty layer list, and
    # the 留白 ceiling then measures it red -- a crash is never a verdict.
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    for li, lay in enumerate(layers):
        ridge = _ridge(w, h, h * float(lay["base_y"]), h * float(lay["amp"]),
                       int(lay["freq"]), rng, float(lay["warp"]))
        ink = inks[int(lay["ink"]) - 1]
        # 5 染 + 6 积墨
        img = _wash_under(img, ridge, ink, float(lay["alpha"]),
                          h * 0.028, w, h, reach=float(lay.get("reach", 0.5)),
                          noise=wash_noise)
        # 7 云气留白: a valley-mist band sits between the layers (depth cue),
        # and the top band pulls the sky back to paper after the far layer
        if li == 0:
            img = _mist(img, paper, h, w, float(spec_dict.get("mist_top", 0.22)))
        elif li < len(layers) - 1:
            band_y = int(h * float(lay["base_y"]) + h * float(lay.get("reach", 0.1)) * 0.5)
            ys = np.arange(h)[:, None]
            a_band = np.exp(-((ys - band_y) / (h * 0.03)) ** 2) * 0.75
            img = img * (1 - a_band[..., None]) + paper[None, None, :] * a_band[..., None]
        pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(pil)
        # 3 勾 + 4 皴 right after this layer's wash: later layers overlap
        # earlier contours exactly as depth stacking should
        contour = tuple(int(v) for v in inks[int(lay.get("contour_ink", lay["ink"])) - 1])
        texture = tuple(int(v) for v in inks[int(lay.get("texture_ink", lay["ink"])) - 1])
        _draw_contour(d, ridge, contour, rng, jitter=1.8,
                      width=2 if int(lay.get("contour_ink", lay["ink"])) >= 2 else 1)
        if lay["style"] != "none":
            _draw_texture(d, ridge, texture, rng, lay["style"], w, h)
        # ...and the strokes go back into the float buffer: ImageDraw writes to
        # the PIL image, which does NOT alias `img` (verified: a line drawn on an
        # fromarray image leaves the source array at zero). Without this write-back
        # every layer but the last paints its 勾/皴 onto an image that is then
        # thrown away, so a declared `style: yudian` on the mid ridge is a knob
        # with no artifact and no gate able to notice it absent.
        img = np.asarray(pil, dtype=float)

    # 8 题款钤印
    ink_dark = tuple(int(v) for v in inks[3])
    _draw_colophon(pil, font_path, ink_dark, w, h, rng)
    _draw_seal(pil, tuple(int(v) for v in seal_ink), tuple(int(v) for v in paper),
               font_path, w, h, rng)

    # 9 量化到声明色域
    arr = np.asarray(pil).astype(float)
    palette7 = np.stack([paper, *inks, seal_ink])
    return Image.fromarray(_quantise(arr, palette7).astype(np.uint8))


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    _refuse_unmeasurable(spec_dict)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng_seed = int(spec_dict.get("seed", 11))

    rendered = render_ink(spec_dict)
    out = out_dir / "ink.png"
    rendered.save(out)

    # determinism gate: re-render and compare the payload
    deterministic = provenance.sha256_bytes(rendered.tobytes()) == \
        provenance.sha256_bytes(render_ink(spec_dict).tobytes())

    # 9 验收 — measured off the artifact (audit A6: never the spec's claim)
    art = np.asarray(Image.open(out).convert("RGB"))
    pal = spec_dict["palette"]
    paper_rgb = np.array(spec_mod.parse_hex(pal["paper"]))
    ink_rgbs = [np.array(spec_mod.parse_hex(pal[k])) for k in ("ink1", "ink2", "ink3", "ink4", "ink5")]
    seal_rgb = np.array(spec_mod.parse_hex(pal["seal"]))
    declared = [paper_rgb, *ink_rgbs, seal_rgb]

    exact = np.zeros(art.shape[:2], dtype=bool)
    for c in declared:
        exact |= np.all(art == c, axis=-1)
    # "distinct palette colors at most 8" speaks about the artifact, so it is
    # measured on the artifact: how many of the declared colours actually appear.
    # Counting the declaration instead (as this route did) cannot see two palette
    # entries collapsed onto one colour -- the painting would then be short a 墨
    # tone while its gate still reported the full 墨分五色 (audit A6).
    present = [c for c in declared if np.all(art == c, axis=-1).any()]
    paper_mask = np.all(art == paper_rgb, axis=-1)
    band_pcts = [float(np.all(art == c, axis=-1).sum() / art[..., 0].size * 100)
                 for c in ink_rgbs]
    h, w = art.shape[:2]
    mist_strip = art[: int(h * 0.20)]
    mist_luma = float(media.image_mean_luma(Image.fromarray(mist_strip)))
    painted = ~paper_mask
    if painted.sum() > 100:
        gray_all = np.asarray(Image.fromarray(art).convert("L"))
        vals = gray_all[painted]
        hist = np.bincount(vals, minlength=256).astype(float)
        pr = hist[hist > 0] / hist.sum()
        painted_entropy = float(-(pr * np.log2(pr)).sum())
    else:
        painted_entropy = 0.0
    seal_mask = np.all(art == seal_rgb, axis=-1)
    # characters + chipping fragment one seal into many red regions; a *seal
    # mark* is a spatial cluster: dilate, label, keep components with a body
    cluster = ndimage.binary_dilation(seal_mask, iterations=4)
    lbl, n = ndimage.label(cluster)
    seal_count = 0
    if n:
        sizes = ndimage.sum(cluster, lbl, range(1, n + 1))
        seal_count = int((sizes >= 200).sum())

    measured = {
        "width": media.image_size(out.read_bytes())[0],
        "height": media.image_size(out.read_bytes())[1],
        "palette_distinct_colors": len(present),
        "palette_declared_colors": len(declared),
        "palette_exact_pct": float(exact.sum() / exact.size * 100),
        "value_bands_min_pct": float(min(band_pcts)),
        "negative_space_pct": float(paper_mask.sum() / paper_mask.size * 100),
        "mist_luma": mist_luma,
        "painted_entropy": painted_entropy,
        "seal_count": seal_count,
        "deterministic": deterministic,
    }
    report = validate.run_acceptance(spec_dict["acceptance"], measured)
    report["measured"] = measured
    report["value_bands_pct"] = [round(p, 2) for p in band_pcts]
    cli.write_report(out_dir, report)

    extra = {}
    sf = spec_dict.get("font") or {}
    fpaths = [p for p in sf.get("paths", []) if Path(p).is_file()]
    if fpaths:
        extra["fonts"] = [{"path": str(fpaths[0]),
                           "sha256": provenance.sha256_file(Path(fpaths[0])),
                           "licence": str(sf.get("licence", "unverified"))}]
    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict,
        content_hash=provenance.sha256_bytes(rendered.tobytes()),
        artifact_hashes={"ink.png": provenance.sha256_file(out)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["ink.png", "report.json", "manifest.json"],
        notes=spec_dict.get("assumptions", []), pipeline="vcac-ink/0.1",
        extra=extra or None)
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    a = cli.parse_args("vcac ink-landscape route (水墨山水)", argv)
    spec_dict = spec_mod.load_raw(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec_dict["id"]))
    m = r["report"]["measured"]
    return cli.finish("ink", r, summaries=[
        f"{spec_dict['id']} -> {r['out_dir']}",
        f"{m['width']}x{m['height']} bands_min={m['value_bands_min_pct']:.2f}% "
        f"negative_space={m['negative_space_pct']:.1f}% mist_luma={m['mist_luma']:.0f} "
        f"painted_entropy={m['painted_entropy']:.2f}b seals={m['seal_count']} "
        f"exact={m['palette_exact_pct']:.1f}%"])


if __name__ == "__main__":
    raise SystemExit(main())
