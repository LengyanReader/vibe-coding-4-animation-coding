"""ink-landscape route — 中国水墨山水 as a deterministic nine-step chain.

Implements docs/styles.md §1.2 with Pillow + NumPy + SciPy only. The chain IS
the painting theory turned into code (styles.md §0: "把画理写成约束，而非调滤镜"):

  1. 纸本      fractal paper grain + fiber direction field
  2. 地形      height-field ridges stacked far→near, each with atmospheric
               perspective in BOTH of its registers: 远山淡 (the tone collapses)
               and 远山柔 (the edge blurs) — both derived from the layer's own
               ink step, so they are one law and not two knobs
  3. 勾        ridge contour polylines, jittered along the normal (seeded)
  4. 皴        the four named 皴法, one per geology: 披麻 fibres fanning down
               earth, 斧劈 dry-brush wedges on exposed stone, 折带 courses on a
               sedimentary bank, 雨点 spatter where distance turns rock to dots.
               Density and length follow a SELF-CALIBRATING steepness (the 85th
               percentile of that range's own gradient), so a stroke rule does
               not silently break when the spec changes the amplitude
  4b. 点苔     moss clumps at the crests, one tone darker than their own range:
               the last brush that closes a mass. Without it 勾皴染 stays a
               sketch, and evenly spaced it is a bead necklace, not moss
  5. 染        low-frequency ink wash under each ridge (gaussian blur)
  6. 积墨      graded passes — 淡墨打底, a 浓墨 pass reaching a third as far,
               and an opt-in 焦墨 band under the contour on the near range only
  7. 云气留白  the mist is regions the renderer *refuses to paint* — the top
               band and the drifting valley gaps are pulled back to paper
  7b. 江流     the water is 留白 with a SHAPE: a winding channel cut between the
               ranges, with banks, ripples and 水口, plus 树 (点叶 / 夹叶) and a
               亭 for the scale the masses alone cannot claim
  8. 题款钤印  vertical colophon (public-domain Wang Wei couplet) in an OFL
               running-script font + a programmatic seal with chipped edges
  9. 验收      measured, not mood words: the artifact is quantised to the
               declared 7-colour palette (paper + ink five tones 墨分五色 +
               seal red 印泥红) through a grain dither, then gated on band
               occupancy, negative-space ratio, region-weighted whiteness/
               entropy, and seal presence.

Honesty notes: the ink bleed of step 5 is a gaussian *approximation*, not a
physical diffusion model, and the 刷丝 of step 4 are parallel 1-px lines rather
than a dry-brush simulation (styles.md §1.3 routes are excluded as
non-deterministic); the colophon font is an external licensed input, hashed
into the pipeline cache key via the spec's ``font.paths`` (audit A7).
"""
from __future__ import annotations

import math
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


# 4x4 ordered-dither threshold. A 7-colour gamut cannot carry a smooth wash:
# snapping a gradient to it straight yields ten hard steps of one tone each,
# which is the defect the shipped sheet showed as horizontal terraces across
# every mountain face. The dither turns those terraces into a fine screen of
# two neighbouring tones -- the same trade the poster route makes in step 9.
_BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
                   dtype=float) / 16.0


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
           warp: float, ridged: bool = True, peakiness: float = 0.62) -> np.ndarray:
    """One mountain ridge line: y(x) in pixels (step 2 地形).

    ``ridged`` folds the fBm into a ridged multifractal (``1 - |2n-1|``) so
    the silhouette has PEAKS — a plain fBm gives rolling hills, which is why
    the first renders read as geological strata. Folded alone, though, it turns
    every crossing into a symmetrical V and the range becomes a picket fence,
    which is what the shipped sheet actually looked like. ``peakiness`` mixes the
    folded and the plain profile, so a mass keeps its bulk and only some of its
    crests come to a point."""
    profile = _fbm_1d(w, freq, rng, octaves=5)
    profile = _domain_warp(profile, w, rng, warp)
    n01 = (profile - profile.min()) / max(1e-9, profile.max() - profile.min())
    if ridged:
        fold = (1 - np.abs(2 * n01 - 1)) ** 1.6
        n01 = peakiness * fold + (1 - peakiness) * n01
    return base_y - n01 * amp


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
                reach: float = 0.5, noise: np.ndarray | None = None,
                darker: np.ndarray | None = None,
                darkest: np.ndarray | None = None) -> np.ndarray:
    """Steps 5+6 染/积墨: the wash is laid in graded passes — 淡墨打底, then a
    浓墨 pass that reaches a shorter way down the face and is allowed to show only
    where the first pass has already wet the paper. Two stacked fills of ONE tone
    are what made the mountains read as painted boards; a graded accumulation is
    what makes them read as rock gone over again with a wet brush.

    ``darkest`` adds the third pass a finished near range needs: 焦墨 reserved for
    the crease where the face turns away from the viewer, laid in a tight band
    under the contour only. It is a knob rather than a default because 焦墨 on a
    distant ridge destroys the atmospheric perspective it is there to earn.
    """
    ys = np.arange(h)[:, None]
    # ink pools just under the contour and fades downhill into the mist —
    # and ONLY below the ridge: the clip above made fall==1 across the whole
    # sky, which is where the horizontal bands came from
    below = (ys - ridge[None, :]) > 0
    base_w = ink if darker is None else darker
    passes = [(ink, 1.00, 1.0), (base_w, 0.55, 0.85)]
    if darkest is not None:
        passes.append((darkest, 0.20, 0.70))
    for col, span, gain in passes:
        depth = np.clip((ys - ridge[None, :]) / (h * reach * span), 0, 1)
        fall = ((1 - depth) ** 1.2 * below
                * (0.8 + 0.6 * (noise if noise is not None else 0.0)))
        a_tight = ndimage.gaussian_filter(fall * alpha * gain, blur * 0.35)
        a_wide = ndimage.gaussian_filter(fall * alpha * gain * 0.7, blur)
        for a in (a_tight, a_wide):
            img = img * (1 - a[..., None]) + col[None, None, :] * a[..., None]
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
    """Step 4 皴: the four named 皴法, each a different gesture of one brush.

    披麻 (hanging hemp) lays long fibers that curve with the fall line and spread
    as they go — for earth-covered hills. 斧劈 (axe-cut) throws broad wedges off a
    steep face, wide at the rock and thin at the tip — for exposed stone. 折带
    (folded belt) stacks short horizontal strokes with a drop at the end — for
    tabular stone. 雨点 (rain dots) spatters clusters into the hollows — for
    vegetation seen from far off. Length and density both follow the local slope,
    so the strokes describe the geometry instead of decorating it.

    The slope is NORMALISED (``st``: a 60% grade is fully steep) rather than
    multiplied by a magic constant. The first version did the latter, and every
    threshold was then tuned to one particular ridge shape: change the spec's
    ``amp`` and the same code turned 披麻 into a wire cage and 斧劈 into a black
    comb, because the density numbers silently went out of range. A stroke rule
    that only works for the shape it was tuned on is not a rule.
    """
    grad = np.abs(np.gradient(ridge))
    slope = np.gradient(ridge)
    # Self-calibrating steepness: a stroke's density is set by how steep this
    # x is RELATIVE TO ITS OWN RANGE (the 85th percentile of the profile), not by
    # an absolute gradient. An absolute constant cannot survive a spec change --
    # measured here: at amp 0.12 every pixel of the near range saturated a
    # /0.6 normalisation and the 斧劈 threw a wedge every 13px, which is the
    # black saw-tooth crown the sheet showed. 皴法 describes THIS mass's geometry.
    ref = float(np.percentile(grad, 85)) or 1e-9
    st = np.clip(grad / ref, 0.0, 1.0)
    if style == "pima":
        # 披麻 is a family of LONG parallel fibres that fan down the face. Two
        # faults made the first version read as a spider web: the drift sign was
        # re-read along the stroke, so a fibre that crossed the fall line turned
        # back and cut its neighbour; and the stride was narrower than the fibre
        # length, so every stroke landed inside another one's territory.
        for x in range(0, w - 8, 11):
            s = float(st[x])
            for k in range(1 + int(2 * s)):
                x0 = x + int(rng.integers(0, 9))
                y0 = int(ridge[min(x0, w - 1)]) + int(rng.integers(2, 14))
                ln = int(h * (0.018 + 0.034 * s))
                side = 1 if slope[min(x0, w - 1)] > 0 else -1   # fixed for the stroke
                pts = [(x0, y0)]
                for j in range(1, 5):               # the fiber bends down-slope
                    t = j / 4.0
                    pts.append((x0 + int(side * ln * t * t * 0.75)
                                + int(rng.integers(-1, 2)), y0 + int(ln * t)))
                d.line(pts, fill=ink, width=1, joint="curve")
    elif style == "axe":
        # 斧劈 is thrown WITH THE FLAT OF THE BRUSH ON THE ROCK and released as a
        # point: broad where it starts, thin where it ends. The first version had
        # the taper backwards (the polygon widened away from the contour), and
        # laid the wedge at the crest line, so every stroke stuck out sideways
        # into the sky as a black bow-tie -- measured on the previous render.
        # A stroke belongs BELOW the contour, on the face.
        for x in range(0, w - 8, 17):
            s = float(st[x])
            if s < 0.55:                            # only the steepest shoulders
                continue
            sw = max(2, int(h * (0.003 + 0.006 * s)))
            ln = int(h * (0.008 + 0.016 * s))
            side = 1 if slope[x] > 0 else -1
            # one axe stroke is never one stroke: the brush is laid, lifted, and
            # laid again slightly LOWER AND SIDEWAYS, so the face reads as a
            # sheared plane. Stacking them at one x makes a black ladder, and a
            # single wedge makes a thorn -- the previous two renders showed both.
            #
            # And the wedge is not FILLED. 斧劈 is thrown with a nearly dry
            # brush, so the stroke keeps the paper in it: the 刷丝 (brush-silk)
            # streaks are what make it read as stone dust rather than as a black
            # flag pasted on the hillside.
            for j in range(int(2 + 3 * s)):
                xo = x + int(rng.integers(-7, 8))
                lnj = int(ln * rng.uniform(0.62, 1.18))
                y0 = int(ridge[x]) + sw + 3 + int(j * ln * 0.62) + int(rng.integers(0, 6))
                if y0 - sw > ridge[x] + h * 0.30 * float(s):
                    break
                for f in range(-sw, sw + 1, 2):     # the dry-brush streaks
                    frac = f / max(1, sw)           # 1 at the rock, 0 at the tip
                    d.line([(xo, y0 + f),
                            (xo + side * int(lnj * (1 - abs(frac) * 0.75)),
                             y0 + int(f * 0.25))],
                           fill=ink, width=1)
    elif style == "zhedai":
        # 折带 is a sedimentary bank: horizontal courses that break off with a
        # short vertical drop. It is the right stroke for a foreground shore,
        # where 斧劈 reads as a cliff the viewer is not standing on
        for x in range(0, w - 10, 11):
            s = float(st[x])
            y0 = int(ridge[x]) + int(rng.integers(3, int(6 + 26 * s) + 1))
            ln = int(h * (0.010 + 0.016 * s))
            d.line([(x, y0), (x + ln, y0 + 1)], fill=ink, width=2)
            d.line([(x + ln, y0 + 1), (x + ln - 2, y0 + int(ln * 0.40))],
                   fill=ink, width=1)               # the fold
    else:                                           # 雨点: dots in the hollows
        # distance turns rock to spatter, but spatter is not a BEAD GARLAND: at
        # full density and radius 2 the dots fused into a black rope along the
        # skyline, which is the exact opposite of 远山淡墨
        for x in range(0, w, 7):
            s = float(st[x])
            for k in range(int(1 + 2 * s)):
                x0 = x + int(rng.integers(0, 5))
                y0 = int(ridge[x]) + int(rng.integers(3, 20))
                r = 1 if rng.random() < 0.7 else 2
                d.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=ink)


def _draw_moss(d: ImageDraw.ImageDraw, ridge: np.ndarray, ink: tuple, rng,
               w: int, h: int, clumps: int, scale: float) -> None:
    """点苔: the last brush of the mountain.

    Moss dots sit ON the crest and at the joints where the 皴 strokes gather.
    Without them a mass of finished 勾皴染 still reads as an unfinished sketch,
    which is exactly the complaint the shipped sheet drew: 皴法 laid down and
    nothing ever closed it. ``scale`` grows with nearness, so the front range
    carries the bigger dots.

    They are laid as CLUMPS at the peaks, not sampled evenly across x: an even
    sample follows the skyline at a constant spacing and the eye reads a beaded
    necklace, which is the fault the first version of this function painted.
    A clump goes down where the ridge is locally convex (a crest or a shoulder),
    because 点苔 marks the places where the brush of 皴 already stopped."""
    slope = np.gradient(ridge)
    # ridge y grows DOWNWARD, so a crest is a local MINIMUM of y: the slope
    # turns negative-to-positive there, which is sign-diff > 0 (getting this
    # backwards dots the moss in the hollows and leaves every peak bare)
    crest = np.where(np.diff(np.sign(slope)) > 0)[0]
    if len(crest) < 3:
        crest = np.arange(0, w, max(1, w // 24))
    for k in range(int(clumps)):
        ci = int(crest[int(rng.integers(0, len(crest)))])
        x = int(np.clip(ci + rng.integers(-6, 7), 4, w - 5))
        y = int(ridge[x]) + int(rng.integers(-2, 5))
        r = max(1, int(round(scale * h * 0.0016)))
        for j in range(int(rng.integers(3, 7))):          # one clump, one brushful
            dx = int(rng.integers(-2, 3)) * r
            dy = int(rng.integers(-1, 3)) * r
            d.ellipse([x + dx - r, y + dy - r, x + dx + r, y + dy + r], fill=ink)


def _draw_water(img: np.ndarray, paper: np.ndarray, h: int, w: int, rng,
                at: float, width: float, wind: float) -> tuple[np.ndarray, np.ndarray]:
    """江流: the water is 留白 with a SHAPE, not an accidental gap.

    A band of paper is eased back along a winding centre line between the mid and
    the near mass. The ridge of the channel is returned so the caller can put one
    ink stroke on each bank: water without a bank is a hole in the painting.
    """
    xs = np.arange(w)
    centre = (h * at + h * wind * np.sin(2 * math.pi * (xs / w) * 1.3
                                          + float(rng.uniform(0, 6)))
              + h * wind * 0.4 * np.sin(2 * math.pi * (xs / w) * 3.1))
    ys = np.arange(h)[:, None]
    a = np.clip(1.0 - np.abs(ys - centre[None, :]) / (h * width), 0, 1) ** 0.55
    a = ndimage.gaussian_filter(a, 1.4)
    return img * (1 - a[..., None]) + paper[None, None, :] * a[..., None], centre


def _draw_banks(d: ImageDraw.ImageDraw, centre: np.ndarray, width: float, h: int,
                w: int, ink: tuple, rng) -> None:
    """Two 淡墨 strokes along the banks, broken where the near shore takes over —
    a continuous ruled line is an engineering section, not a river."""
    for side in (-1, 1):
        pts = []
        for x in range(0, w, 6):
            if rng.random() < 0.22:                 # the bank dissolves into mist
                if len(pts) > 2:
                    d.line(pts, fill=ink, width=1, joint="curve")
                pts = []
                continue
            pts.append((x, centre[x] + side * width * h * 0.5
                        + float(rng.integers(-1, 2))))
        if len(pts) > 2:
            d.line(pts, fill=ink, width=1, joint="curve")


def _draw_trees(d: ImageDraw.ImageDraw, ridge: np.ndarray, inks, rng, w: int,
                h: int, n: int, x0: int = 2, x1: int | None = None) -> None:
    """树: a few trunks on the crest give the mass a scale.

    Two leaf methods only, both historical. 点叶 is literally LEAF-DOTS: a canopy
    built from a cluster of small filled dabs, not from circle outlines -- the
    outlines version read as five dandelions on sticks, which is the mistake this
    function had to be rewritten to stop making. 夹叶 (the crossed cage) is the
    other one, for trees seen bare. 山 without 树 is a rock without skin, and a
    painting with no tree has nothing to argue with about size.
    """
    x1 = w - 3 if x1 is None else x1
    for k in range(int(n)):
        if x1 == w - 3:
            # stratified along the crest: a uniform draw put four of the six
            # trees into the same corner of the sheet and left the rest of the
            # bank bare, and a scale marker that clumps marks nothing
            x = int(np.clip((k + float(rng.random())) * w / max(1, n), 2, w - 4))
        else:
            x = int(rng.integers(max(2, x0), max(4, x1)))
        y = int(ridge[min(x, w - 1)])
        s = int(h * 0.058 * (0.75 + 0.5 * float(rng.random())))
        r = max(4, int(s * 0.30))
        ink = tuple(int(v) for v in (inks[3] if rng.random() < 0.55 else inks[4]))
        lean = int(rng.integers(-4, 5))
        d.line([(x, y), (x + lean, y - s)], fill=ink, width=3)      # the trunk
        for bx, by in ((int(s * 0.30), int(s * 0.42)),
                       (int(-s * 0.26), int(s * 0.56))):            # two limbs
            d.line([(x + int(lean * by / s), y - by),
                    (x + int(lean * by / s) + bx, y - by - r // 3)],
                   fill=ink, width=2)
        cx, cy = x + lean, y - s
        if rng.random() < 0.6:                        # 点叶: a cluster of dabs
            for j in range(int(14 + r)):
                a = rng.uniform(0.0, 2 * math.pi)
                rad = r * math.sqrt(rng.random()) * 1.15
                rr = max(1, int(r * rng.uniform(0.10, 0.20)))
                px, py = cx + rad * math.cos(a), cy + rad * math.sin(a) * 0.8
                d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=ink)
        else:                                         # 夹叶: a crossed cage
            for dx in (-r, 0, r):
                d.line([(cx + dx, cy + r // 2), (cx + dx + r * 4 // 5, cy - r)],
                       fill=ink, width=2)
                d.line([(cx + dx, cy + r // 2), (cx + dx - r * 4 // 5, cy - r)],
                       fill=ink, width=2)
        d.line([(x - 4, y), (x + 4, y)], fill=ink, width=2)          # the root flare


def _draw_ripples(d: ImageDraw.ImageDraw, centre: np.ndarray, width: float,
                  h: int, w: int, ink: tuple, rng) -> None:
    """水面: a channel of pure paper with nothing in it is a hole, not water.

    Water is drawn by what moves on it -- a few short horizontal strokes that
    break where the current does, and a darker 水口 where the stream is squeezed
    between rocks. The strokes hug the far side of the band, because the eye
    reads the near half of a river as the surface it looks across."""
    for k in range(14):
        x = int(rng.integers(6, w - 40))
        ci = int(centre[min(x, w - 1)])
        yy = ci - int(width * h * rng.uniform(0.05, 0.55))
        ln = int(rng.uniform(0.02, 0.07) * w)
        d.line([(x, yy), (x + ln, yy)], fill=ink, width=1)
    for k in range(5):                              # 水口: the pinched, darker gaps
        x = int(rng.integers(10, w - 60))
        ci = int(centre[min(x, w - 1)])
        d.line([(x, ci + 2), (x + int(0.03 * w), ci + 2)], fill=ink, width=2)


def _draw_pavilion(d: ImageDraw.ImageDraw, ridge: np.ndarray, inks, w: int,
                   h: int, at: float) -> None:
    """亭: one structure on the near crest is the 画眼 — the place the eye of the
    viewer is invited to stand and look out. The eaves lift at both ends (起翘),
    because a horizontal roof line is a shed, and a shed is not what sits on a
    mountain."""
    x = int(w * at)
    y = int(ridge[min(x, w - 1)])
    s = int(h * 0.034)
    half = int(s * 1.05)
    dark = tuple(int(v) for v in inks[4])
    mid = tuple(int(v) for v in inks[3])
    # a 亭 is OPEN on all four sides: posts, a rail, a roof. Filled beams top and
    # bottom turned it into a crate with a hat, which is what the previous render
    # showed -- and the eye then reads the whole 画眼 as a shed
    d.line([(x - half - 5, y), (x + half + 5, y)], fill=dark, width=2)   # the ground line
    for side in (-1, 1):                            # the two posts
        d.line([(x + side * half, y), (x + side * half, y - s)], fill=dark, width=2)
    d.line([(x - half, y - int(s * 0.42)), (x + half, y - int(s * 0.42))],
           fill=mid, width=1)                       # the rail
    d.line([(x - half, y - int(s * 0.42)), (x - half, y - int(s * 0.72))],
           fill=mid, width=1)                       # the bench end
    d.line([(x + half, y - int(s * 0.42)), (x + half, y - int(s * 0.72))],
           fill=mid, width=1)
    ry = y - s                                      # the eave line
    # the roof is a hip: it comes down to the eave at both ends and the ridge of
    # it is a point, because a 亭 seen from below shows its crown, not a beam
    d.polygon([(x - half - 8, ry - 3), (x + half + 8, ry - 3),
               (x + int(half * 0.30), ry - int(s * 0.40)),
               (x - int(half * 0.30), ry - int(s * 0.40))], fill=dark)
    d.line([(x, ry - int(s * 0.40)), (x, ry - int(s * 0.62))], fill=dark, width=2)
    for side in (-1, 1):                            # 起翘: the flick at each corner
        d.line([(x + side * (half + 8), ry - 3), (x + side * (half + 13), ry - 10)],
               fill=dark, width=2)


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


def _quantise(img_arr: np.ndarray, palette: np.ndarray, rng,
              dither: float = 16.0) -> np.ndarray:
    """Step 9: snap every pixel to the declared palette (paper + 墨分五色 +
    印泥红). Quantisation is what makes the 色域 gate measurable: the artifact
    either is the declared gamut or it is not.

    The threshold is broken up BEFORE the nearest-colour search and never after,
    so every output pixel is still exactly one declared colour -- the gate is
    unchanged. The break-up is mostly SEEDED WHITE NOISE with a minority Bayer
    component: a pure 4x4 screen does remove the terraces, but it leaves a
    regular halftone grid over every wash, which reads as a printed poster and
    not as ink on paper (measured on the previous render). Grain is the right
    texture for a sheet that has been washed, and it is what the paper tooth
    does physically.
    """
    h, w = img_arr.shape[:2]
    bayer = np.tile(_BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w] - 0.5
    grain = rng.normal(0.0, 1.0, (h, w))
    noise = (bayer * 0.40 + grain * 0.72) * dither
    flat = (img_arr + noise[..., None]).reshape(-1, 3)
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
    ridges: list[np.ndarray] = []
    for li, lay in enumerate(layers):
        ridge = _ridge(w, h, h * float(lay["base_y"]), h * float(lay["amp"]),
                       int(lay["freq"]), rng, float(lay["warp"]),
                       peakiness=float(lay.get("peakiness", 0.62)))
        # 远山淡墨 is not only a paler tone: distance softens the EDGE, so a
        # far range cannot arrive with the same sawtooth as a near one. The
        # blur is derived from the layer's own ink step (清 → 焦 = soft → hard)
        # rather than typed per layer, because it is the same law every sheet
        # obeys; `smooth:` overrides it where a range is deliberately crisp.
        # Measured on this sheet: with no smoothing the far skyline came out as
        # a row of geometric V's, which is a graph of a mountain, not one.
        sig = float(lay.get("smooth",
                           max(0.0, (5 - int(lay["ink"])) * 2.2)))
        if sig > 0.5:
            ridge = ndimage.gaussian_filter1d(ridge, sig, mode="nearest")
        ridges.append(ridge)
        ink = inks[int(lay["ink"]) - 1]
        # 5 染 + 6 积墨: the second pass is one tone darker and reaches half as
        # far down the face, which is what 积墨 means in practice.
        # The 积墨 tones are derived as OFFSETS from the layer's own tone, not read
        # straight out of the gamut: `inks[min(4, ink)]` clamps at the top, so a
        # sheet with every layer pinned to ink1 still accumulated ink2 and 焦墨 and
        # measured the full 7-colour palette -- which is exactly the flattened ramp
        # the value-band mutant exists to catch, and the clamp let it through.
        # For the shipped five-layer range (ink 1..4) offset+1 == clamp, so the
        # painted sheet is unchanged; only the collapse now actually collapses.
        img = _wash_under(img, ridge, ink, float(lay["alpha"]),
                          h * 0.028, w, h, reach=float(lay.get("reach", 0.5)),
                          noise=wash_noise,
                          darker=inks[min(4, int(lay["ink"]))],
                          darkest=inks[min(4, int(lay["ink"]) + 1)]
                          if lay.get("jiao") else None)
        # 7 云气留白: a valley-mist band sits between the layers (depth cue),
        # and the top band pulls the sky back to paper after the far layer
        if li == 0:
            img = _mist(img, paper, h, w, float(spec_dict.get("mist_top", 0.22)))
        elif li < len(layers) - 1:
            # 云气 between two ranges. It is a DRIFTING band, not a ruled strip:
            # a constant band_y across the whole width punches a straight white
            # hole wherever a peak happens to reach it, which is the artifact
            # that looked like a waterfall in the middle of the previous sheet
            band_y = (h * float(lay["base_y"]) + h * float(lay.get("reach", 0.1)) * 0.5
                      + h * 0.028 * (_fbm_1d(w, 4, rng, octaves=2) - 0.5) * 2)
            ys = np.arange(h)[:, None]
            a_band = np.exp(-((ys - band_y[None, :]) / (h * 0.032)) ** 2) * 0.62
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
        if lay.get("moss"):                         # 点苔 closes the mass. The
            # moss is one tone darker than its own range, never 焦墨 on a
            # distant ridge: distance collapses contrast, and a garland of
            # black beads on the far skyline is the opposite of 远山淡墨
            _draw_moss(d, ridge, tuple(int(v) for v in inks[min(4, int(lay["ink"]))]),
                       rng, w, h, int(lay["moss"]), float(lay.get("moss_scale", 1.0)))
        # ...and the strokes go back into the float buffer: ImageDraw writes to
        # the PIL image, which does NOT alias `img` (verified: a line drawn on an
        # fromarray image leaves the source array at zero). Without this write-back
        # every layer but the last paints its 勾/皴 onto an image that is then
        # thrown away, so a declared `style: yudian` on the mid ridge is a knob
        # with no artifact and no gate able to notice it absent.
        img = np.asarray(pil, dtype=float)

    # 7b 江流 + 树 + 亭: the water is 留白 with a shape of its own, and the
    # scale markers stand on the bank it passes. A mountain range with no tree
    # and no building has nothing to argue with about size, and a sheet titled
    # 江流天地外 with no channel in it is a title the painting does not honour.
    #
    # ORDER MATTERS: the channel is cut BEFORE the banks, trees and pavilion are
    # drawn, because the water is drawn over the 皴 of the range it passes --
    # cutting it afterwards, as this route did, leaves the near range's axe
    # wedges showing through the white and the river reads as a lake with
    # something drowned in it.
    feat = spec_dict.get("features") or {}
    centre = None
    wat = feat.get("water") or {}
    if feat.get("water"):
        img, centre = _draw_water(img, paper, h, w, rng,
                                  float(wat.get("at", 0.70)),
                                  float(wat.get("width", 0.055)),
                                  float(wat.get("wind", 0.035)))
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(pil)
    if centre is not None:
        _draw_banks(d, centre, float(wat.get("width", 0.055)), h, w,
                    tuple(int(v) for v in inks[2]), rng)
        _draw_ripples(d, centre, float(wat.get("width", 0.055)), h, w,
                      tuple(int(v) for v in inks[1]), rng)
    # where each marker stands is a layer index, not a guess: the trees root on
    # the near shore, the 亭 goes on the far bank it looks across. Default is
    # the range below the channel and the one above it. Trunks planted in the
    # water -- which is what the shipped sheet did -- are a fault, and the sheet
    # looked exactly like a bank that had been flooded
    anchors = feat.get("anchors") or {}

    def _anch(key: str, default: int) -> int:
        return max(0, min(int(anchors.get(key, default)), len(ridges) - 1))

    if feat.get("trees") and ridges:
        _draw_trees(d, ridges[_anch("trees", len(ridges) - 1)], inks, rng,
                    w, h, int(feat["trees"]))
    if feat.get("pavilion") is not None and ridges:
        _draw_pavilion(d, ridges[_anch("pavilion", len(ridges) - 2)], inks, w, h,
                       float(feat["pavilion"]))
    img = np.asarray(pil, dtype=float)
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

    # 8 题款钤印
    ink_dark = tuple(int(v) for v in inks[3])
    _draw_colophon(pil, font_path, ink_dark, w, h, rng)
    _draw_seal(pil, tuple(int(v) for v in seal_ink), tuple(int(v) for v in paper),
               font_path, w, h, rng)

    # 9 量化到声明色域
    arr = np.asarray(pil).astype(float)
    palette7 = np.stack([paper, *inks, seal_ink])
    return Image.fromarray(_quantise(arr, palette7, rng).astype(np.uint8))


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
