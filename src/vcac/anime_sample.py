"""anime route — 2D cel-style clip: 飞檐少年 (the boy on the temple eave).

A style-level homage to modern Chinese fantasy animation (赛璐璐 cel shading,
dusk palette, upswept temple eaves, drifting embers). **No copyrighted
characters**: the boy is a generic silhouette; what is quoted is the *visual
grammar* — two-tone hard shadows, a warm rim light against a dusk sky,
parallax depth, one hard cut on the beat.

The route proves the video contract generalises beyond the first loop:
  spec.load (video contract) → seeded scene → pure frame function of t
  → content-hash determinism gate → encode → acceptance → manifest.
The shot cut at 6s is *measured* from the rendered frames (luma-histogram total
variation), not asserted: a clip that loses its cut fails the gate.

Determinism: every element is seeded at setup and a pure function of the
frame index — same (spec, seed) ⇒ same payload hash.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageStat

from . import cli, ffmpeg, provenance, spec as spec_mod, validate

# world canvas the scene is authored on (camera crops/zooms into it)
WORLD_W, WORLD_H = 1280, 720

# --- shot-boundary detector ---------------------------------------------------
# The cut position is authored in the spec's timeline; this is how the route
# *verifies* it survived the renderer. Both numbers below come from measurement
# (scripts/probes/hist_cut_probe.py, then the first full run of this route):
#
#   * ordinary inter-frame motion inside a shot: total variation <= 0.0009
#   * the scripted cut at frame 144:                     0.2992
#   * a 0.75s fade: 0.07-0.51 across the ramp -- most of it trips the threshold,
#     so a fade is larger than a cut far more often than not, and amplitude alone
#     cannot tell the two apart
#
# Hence 0.10 as the spike threshold (110x the motion floor, a third of the cut)
# *plus* the isolated-peak test below, which is what separates a cut from a fade.
# On the shipped clip that leaves exactly one hard cut, with the loudest shift the
# gate ignores being a ramp frame at 0.072 -- a margin of 4.2x, carried in the
# report rather than asserted here.
# The first version of this gate used |mean luma| > 18.0 and counted the real cut
# as zero: same clip, two shots, 15.1 of mean shift -- an exposure threshold has
# to know the scene's brightness, and a gate calibrated by guess does not.
_CUT_BINS = 32
_CUT_L1_THRESHOLD = 0.10


def _luma_hist(img: Image.Image) -> np.ndarray:
    """32-bin normalised luma histogram (integer bins; float only at the end)."""
    hist = img.convert("L").histogram()                     # 256 exact counts
    bins = np.array(hist, dtype=np.float64).reshape(_CUT_BINS, -1).sum(axis=1)
    return bins / bins.sum()


def classify_cuts(hists: list, threshold: float = _CUT_L1_THRESHOLD):
    """Split frame-to-frame luma-distribution shifts into cuts and gradual edits.

    Signal is total variation between histograms (sum |h1 - h2| / 2: the share of
    pixels that would have to change bin). A **hard cut is an isolated spike** --
    the pair exceeds the threshold while both neighbouring pairs sit below it. A
    fade or a dissolve is the same shift smeared across a run of consecutive
    pairs, and every one of those pairs can be larger than the cut's spike; the
    shape is the evidence, not the size. Returning only the isolated peaks keeps
    'at least 1 scene cut' meaning one edit rather than one edit plus N ramp
    frames; the gradual frames are reported too, because a gate that silently
    discards a category is how a green run hides an unverified claim.

    Returns ``(hard_cut_frames, gradual_frames, diffs)``; ``diffs[i]`` compares
    frames ``i`` and ``i+1``.
    """
    diffs = [float(np.abs(a - b).sum() / 2.0) for a, b in zip(hists, hists[1:])]
    hard, gradual = [], []
    for i, d in enumerate(diffs):
        if d <= threshold:
            continue
        left = diffs[i - 1] if i > 0 else 0.0
        right = diffs[i + 1] if i + 1 < len(diffs) else 0.0
        (hard if left <= threshold and right <= threshold else gradual).append(i + 1)
    return hard, gradual, diffs


def _shade(c: tuple, k: float) -> tuple:
    return tuple(max(0, min(255, int(v * k))) for v in c)


def _mix(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# --- seeded scene ---------------------------------------------------------------

def _ridge_poly(seed: int, n: int, base_y: float, amp: float, freq: int,
                peakiness: float = 0.62) -> list:
    """A mountain silhouette polyline across the world.

    The pure ridged fold (``1 - |2v-1|``) makes every crossing a symmetrical V,
    and a row of those is a picket fence: the shipped sheet's ranges were exactly
    that. ``peakiness`` mixes the folded and the plain profile, so a mass keeps
    its bulk and only some of its crests come to a point -- the same fix the ink
    route had to make for the same reason.
    """
    rng = random.Random(seed)
    g = [rng.random() for _ in range(freq + 1)]
    g2 = [rng.random() for _ in range(freq * 2 + 1)]
    pts = []
    for i in range(n + 1):
        x = i / n * WORLD_W
        u = i / n * freq
        i0, i1 = int(u), min(int(u) + 1, freq)
        t = u - i0
        t = t * t * (3 - 2 * t)
        v = g[i0] * (1 - t) + g[i1] * t
        u2 = i / n * freq * 2
        j0, j1 = int(u2), min(int(u2) + 1, freq * 2)
        t2 = u2 - j0
        t2 = t2 * t2 * (3 - 2 * t2)
        v2 = g2[j0] * (1 - t2) + g2[j1] * t2
        plain = 0.72 * v + 0.28 * v2
        fold = (1 - abs(2 * v - 1)) ** 1.6
        v = peakiness * fold + (1 - peakiness) * plain
        pts.append((x, base_y - v * amp))
    return pts


def _cloud_blobs(seed: int, n: int, y0: float, y1: float) -> list:
    """Cel clouds as ONE envelope each, never a pile of puffs.

    Two successive faults, both from the same function. The first drew a wobbly
    ellipse per cloud with a darker band under half of it, and the band's edge cut
    across the mass so every cloud read as two shapes slightly out of register. The
    fix drew an upper envelope, but only 55% of each lobe's radius above its centre
    and with the centres all at one height -- which flattens the mass to a pancake,
    and a pancake with a straight base and a clipped cap reads as a paper aeroplane.
    A cumulus is TALL (height about half its width) and domes with full circles;
    the flat base is what makes the dome legible against it.
    """
    rng = random.Random(seed)
    out = []
    for k in range(n):
        cx = rng.uniform(0, WORLD_W)
        yb = rng.uniform(y0, y1)                       # the flat base IS the anchor
        span = rng.uniform(130, 250)
        hgt = span * rng.uniform(0.40, 0.56)
        nlobes = int(rng.uniform(5, 8))
        lobes = []
        for j in range(nlobes):
            f = (j + 0.5) / nlobes
            lr = span * rng.uniform(0.17, 0.26)
            lx = cx + (f - 0.5) * span * 0.86
            ly = yb - lr - hgt * math.sin(math.pi * f) ** 0.9 * rng.uniform(0.55, 1.0)
            lobes.append((lx, ly, lr))
        lobes.append((cx, yb - hgt * 0.55, span * 0.26))      # the belly dome
        x0 = min(x - r for x, _, r in lobes)
        x1 = max(x + r for x, _, r in lobes)
        top = []
        for s in range(65):
            x = x0 + (x1 - x0) * s / 64.0
            ys = [y - r * math.sqrt(max(0.0, 1 - ((x - xc) / max(1e-6, r)) ** 2))
                  for xc, y, r in lobes if abs(x - xc) <= r]
            if ys:
                top.append((x, min(ys)))
        if len(top) < 8:
            continue
        out.append({"cx": cx, "cy": yb, "w": x1 - x0, "top": top, "yb": yb})
    return out


def _embers(seed: int, n: int) -> list:
    rng = random.Random(seed)
    return [{"x0": rng.uniform(0, WORLD_W), "y0": rng.uniform(0, WORLD_H),
             "rise": rng.uniform(14, 42), "drift": rng.uniform(-10, 14),
             "phase": rng.uniform(0, 2 * math.pi), "r": rng.uniform(1.2, 2.8),
             "tw": rng.uniform(1.5, 3.5)} for _ in range(n)]


def make_scene(spec) -> dict:
    """Everything static, all from spec.seed — the frame function's input."""
    rng = random.Random(spec.seed)
    far = _ridge_poly(spec.seed + 1, 72, WORLD_H * 0.66, WORLD_H * 0.20, 6,
                      peakiness=0.34)
    # The sun is PLACED where the far range actually dips. Authored at a fixed
    # height it was buried completely -- at seed 7 the ridge rose over the disc
    # and the shot named for a dusk sun had no sun in it. A sunset needs the
    # ridge to be a horizon, so the ridge gets to choose where the sun goes.
    left = [p for p in far if p[0] < WORLD_W * 0.42] or far
    sx, sy = max(left, key=lambda p: p[1])
    return {
        "mtn_far": far,
        "mtn_near": _ridge_poly(spec.seed + 2, 72, WORLD_H * 0.78, WORLD_H * 0.16, 7,
                                peakiness=0.52),
        "clouds_hi": _cloud_blobs(spec.seed + 3, 4, WORLD_H * 0.12, WORLD_H * 0.28),
        "clouds_lo": _cloud_blobs(spec.seed + 4, 3, WORLD_H * 0.38, WORLD_H * 0.50),
        "embers": _embers(spec.seed + 5, 34),
        # the boy SITS on the eave, and his seat is computed from the roof curve
        # rather than typed: a figure whose feet are a magic number is a figure
        # floating in front of the building behind him
        "boy_x": WORLD_W * 0.705, "boy_y": _eave_y(WORLD_W * 0.705) - 12.0,
        # well clear of the figure, so the close dolly-in cannot park a disc
        # behind his head, which is what the shipped clip did
        "sun_x": sx, "sun_y": sy - 30.0,
        "lean": rng.uniform(-0.03, 0.03),
    }


# --- the boy: a generic silhouette (no IP likeness) ------------------------------
#
# He SITS on the ridge with his legs over the eave, which is the shot. The first
# version drew him standing: a head blob, a rectangle torso and two sticks, with
# a three-pixel red polyline for a ribbon -- a diagram of a boy, and the reason
# the clip was called 粗疏. A cel figure is built in a fixed order (shadow mass,
# hair behind the skull, body, garment, limb, fringe and face on top) and every
# limb is a tapered quad, because a constant-width line at this scale is a wire.


def _streamer(anchor, t: float, phase: float, length: float, amp: float,
              w0: float, n: int = 30) -> list:
    """A cloth streamer as one closed polygon: a travelling wave along a spine,
    amplitude growing as the cloth leaves the tie, width tapering to a point.

    The first version sampled the wave at FIVE points and joined them with
    straight tapered quads, which drew a broken arrow rather than cloth -- the
    corners of a polyline are read as folds only when the polyline is dense.
    ``n`` samples and a perpendicular offset along the local tangent is the
    difference between a ribbon and a set of planks.
    """
    pts = []
    for i in range(n + 1):
        f = i / n
        pts.append((anchor[0] - length * f,
                    anchor[1] + math.sin(t * 2.4 + phase + f * 5.2) * amp * (0.25 + f)
                    - amp * 0.5 * f * f))
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        f = i / n
        j, k = min(n, i + 1), max(0, i - 1)
        dx, dy = pts[j][0] - pts[k][0], pts[j][1] - pts[k][1]
        nn = math.hypot(dx, dy) or 1.0
        hw = w0 * (1.0 - 0.80 * f)
        nx, ny = -dy / nn * hw, dx / nn * hw
        left.append((x + nx, y + ny))
        right.append((x - nx, y - ny))
    return left + right[::-1]


def _boy(scale: float) -> dict:
    """Unit geometry for a seated figure, hips at the origin, facing -x."""
    s = scale
    def P(*pts):
        return [(x * s, y * s) for x, y in pts]
    return {
        "s": s,
        "head": (-6, -80), "hrx": 19.0, "hry": 22.0,
        "torso": P((-15, -62), (13, -62), (17, -6), (-19, -6)),
        "thigh": P((-14, -10), (-46, -16), (-52, -4), (-12, 2)),
        "shin": P((-46, -14), (-40, 30), (-30, 30), (-34, -12)),
        "foot": P((-42, 28), (-30, 28), (-28, 36), (-46, 36)),
        "thigh2": P((-8, -6), (-38, -10), (-42, 2), (-6, 6)),
        "shin2": P((-38, -8), (-32, 34), (-24, 34), (-28, -6)),
        "arm": P((-12, -56), (-34, -34), (-44, -14), (-36, -10), (-26, -30), (-6, -48)),
        "sleeve": P((-16, -60), (-40, -32), (-30, -18), (-4, -46)),
        "hem": P((-22, -14), (18, -14), (26, 16), (-4, 22), (-30, 8)),
        "hair_back": P((-24, -92), (-6, -104), (16, -94), (20, -70), (-20, -68)),
        "topknot": (-2, -104),
        "ribbon_anchor": (-4, -100),
    }


def _draw_boy(d: ImageDraw.ImageDraw, pal, scene, cam, t: float) -> None:
    """The seated boy, painted in cel order with three garment tones.

    He faces the low sun in both takes: the previous version flipped him at the
    cut, which is a second act with no first one -- nothing in the shot asks him
    to turn around.
    """
    bx, by = scene["boy_x"], scene["boy_y"]
    breathe = 1.0 + 0.012 * math.sin(t * 2.1)
    b = _boy(1.0 * breathe)
    s = b["s"]
    z = cam["zoom"]
    ink = _shade(pal[6], 0.6)
    cloth = _mix(pal[6], pal[0], 0.18)
    cloth_mid = _mix(pal[6], pal[3], 0.35)
    cloth_lit = _mix(pal[3], pal[2], 0.35)
    skin = _mix(pal[2], (255, 226, 196), 0.55)
    skin_shade = _shade(skin, 0.80)
    hair = _mix(pal[6], pal[0], 0.06)
    hair_lit = _mix(pal[0], pal[2], 0.30)
    ribbon_col = pal[5]
    ribbon_lit = _mix(pal[5], (255, 220, 190), 0.35)
    lw = max(1, int(round(1.4 * z)))
    dirx = -1.0

    def W(x: float, y: float):
        return _cam_pt(bx + x * s * dirx, by + y * s, cam)

    def poly(pts, fill, outline=None, width=0):
        d.polygon([W(x, y) for x, y in pts], fill=fill, outline=outline, width=width)

    # 0 the cast onto the ridge: a figure with no contact shadow is a sticker
    d.ellipse([W(-26, 20)[0] - 26 * z, W(-26, 20)[1] - 6 * z,
               W(-26, 20)[0] + 34 * z, W(-26, 20)[1] + 7 * z], fill=ink)

    # 1 the two streamers, BEHIND everything. Length and amplitude both had to
    # come down: at 168 px long and 15 px of swing the close take put a red awning
    # across the whole frame, and a streamer that is wider than the head reading
    # it is not cloth but a set dressing.
    for phase, amp, lenf, tone in ((0.3, 9.0, 0.62, ribbon_col),
                                   (2.4, 7.0, 0.46, ribbon_lit)):
        poly(_streamer((-4, -100), t, phase, 168.0 * lenf, amp, 5.0 * s), tone)
    # 2 hair behind the skull, so the head has volume
    poly(b["hair_back"], hair)
    # 3 the far leg, one tone down, so the two legs do not fuse
    poly(b["thigh2"], cloth_mid)
    poly(b["shin2"], cloth_mid)
    poly([(-38, 32), (-26, 32), (-24, 40), (-40, 40)], ink)   # the far shoe
    # 4 the robe hem over the thighs, then the lit near leg on top of it
    poly(b["hem"], cloth)
    poly(b["thigh"], cloth)
    poly(b["shin"], cloth)
    poly(b["foot"], ink)
    # the fold shadow under the hem and along the thigh -- cel shade, hard edge
    poly([(-16, -6), (-48, -12), (-50, -2), (-14, 6)], cloth_mid)
    # 5 torso, with the lapel crossing (衽) as a lighter wedge
    poly(b["torso"], cloth)
    poly([(-13, -60), (-2, -58), (10, -12), (-2, -10)], cloth_lit)
    poly([(12, -60), (17, -8), (6, -8), (4, -56)], cloth_mid)
    # 6 the near sleeve and arm resting on the knee
    poly(b["sleeve"], cloth)
    poly([(-16, -58), (-38, -32), (-30, -22), (-6, -46)], cloth_mid)
    poly(b["arm"], cloth_lit)
    d.line([W(-34, -30), W(-44, -14)], fill=skin, width=max(2, int(5 * s * z)))
    hand = W(-46, -12)
    d.ellipse([hand[0] - 5 * z, hand[1] - 4 * z, hand[0] + 5 * z, hand[1] + 4 * z],
              fill=skin)
    # 7 the head: a jaw, not a circle, and the face turned toward the sun
    hx, hy = W(*b["head"])
    # a jaw with a CHIN: the first version was an eight-point blob 42 px wide and
    # 42 tall, which is a circle, and a circle with eyes is a chibi not a boy
    jaw = [(-25, -92), (-26, -76), (-20, -64), (-9, -56), (2, -58), (11, -66),
           (15, -82), (11, -97), (-4, -101)]
    poly(jaw, skin)
    # the far side of the face falls into shade: two tones, one hard boundary
    poly([(-26, -86), (-26, -72), (-18, -62), (-8, -60), (-14, -74), (-18, -90)],
         skin_shade)
    # 8 hair over the skull with a fringe and loose 发丝 strands
    poly([(-27, -92), (-16, -104), (4, -106), (18, -96), (16, -80),
          (8, -88), (-4, -84), (-14, -92), (-22, -84)], hair)
    for i, (x0, y0, x1, y1) in enumerate((
            (-24, -92, -30, -70), (-16, -98, -24, -78), (-2, -104, -8, -84),
            (10, -102, 14, -80), (18, -94, 26, -74), (20, -86, 30, -66))):
        d.line([W(x0, y0), W(x1, y1)], fill=hair, width=lw + 1)
    for x0, y0, x1, y1 in ((-22, -90, -28, -74), (8, -100, 12, -84)):
        d.line([W(x0, y0), W(x1, y1)], fill=hair_lit, width=lw)   # the highlight
    # the topknot and its tie
    tk = W(*b["topknot"])
    d.ellipse([tk[0] - 7 * z, tk[1] - 8 * z, tk[0] + 7 * z, tk[1] + 6 * z], fill=hair)
    d.line([W(-8, -100), W(4, -98)], fill=ribbon_col, width=max(2, int(3 * s * z)))
    # 9 the face: two eyes with a highlight each, a brow, a nose and mouth line
    for ex in (-19, -7):
        c = W(ex, -78)
        d.ellipse([c[0] - 3.0 * z, c[1] - 4.2 * z, c[0] + 3.0 * z, c[1] + 4.2 * z],
                  fill=ink)
        d.ellipse([c[0] - 1.6 * z, c[1] - 2.6 * z, c[0] + 0.2 * z, c[1] - 0.2 * z],
                  fill=_mix(pal[2], (255, 255, 255), 0.6))
        d.line([W(ex - 4, -86), W(ex + 3, -87)], fill=hair, width=lw)   # the brow
    d.line([W(-24, -70), W(-26, -66)], fill=skin_shade, width=lw)       # the nose
    d.line([W(-21, -63), W(-15, -63)], fill=_shade(skin_shade, 0.7), width=lw)
    # 10 the rim light: a CRESCENT on the sun side, not a shifted copy of the
    # whole silhouette (which is what put a pink halo around the black head)
    for x0, y0, x1, y1 in ((-10, -100, -27, -92), (-27, -92, -26, -74),
                           (-15, -60, 13, -62), (13, -62, 17, -8)):
        d.line([W(x0, y0), W(x1, y1)], fill=ribbon_lit, width=lw + 1)


# --- eave (飞檐): the upswept temple roof corner ---------------------------------
#
# The shot is NAMED after this element and the shipped clip did not show it: the
# roof was one filled band hanging off a polyline, in a colour only two steps off
# the mountain behind it, so it read as a black shard. A 飞檐 is not a silhouette
# at all: it is a stack of parts, each at its own scale, and the roof only reads
# once the building it caps is in the frame too.

_CORNER_X = 1085.0        # world x of the lifted corner the shot is named for
_HIP_SLOPE = 0.55         # past the tip the eave edge turns away and descends


def _eave_y(x: float) -> float:
    """World y of the eave edge: one function, so a figure can be placed ON it.

    Three segments, because a 飞檐 is three facts: a long shallow sweep toward the
    corner, a 起翘 flick that lifts the last stretch, and past the tip the edge
    turns away from the viewer and drops along the hip. That last segment is what
    the first version lacked, and its absence is why the close take showed a huge
    triangle of sky to the right of the corner: the corner ended in mid-air.
    """
    t = max(0.0, min(1.0, (x + 40.0) / 1000.0))
    y = 640.0 + (352.0 - 640.0) * (t ** 1.25)
    if x > 980.0:
        y -= (x - 980.0) * 0.90                    # 起翘: the corner lifts
    if x > _CORNER_X:
        y += (x - _CORNER_X) * _HIP_SLOPE          # the returned edge past the tip
    return y


def _roof_depth(x: float) -> float:
    """World thickness of the visible roof slope at this x.

    The plane recedes from the eave, so the band narrows toward the far end of
    the sweep. The first version used ``90 + 0.115x``, which reached 230 px at the
    corner and filled the whole frame with a dark band -- the reason the roof read
    as a fence embankment rather than as a roof. The next version over-corrected to
    26 px, and a band that thin cannot hold a tile pattern: the crests spanned it
    end to end and the roof became a ruler. This is the middle, where the plane has
    room to read as a surface with a texture on it.
    """
    return 48.0 + 0.055 * (x + 160.0)


def _roof_cols(pal):
    """The exact colours the roof is painted with, kept in ONE place.

    The gate that checks whether the title element is on screen reads the same
    four tile values, so the checker cannot drift away from the painter: two
    copies of a colour recipe is how a gate ends up measuring a roof that no
    longer exists.
    """
    tile = _mix(pal[4], pal[0], 0.14)
    return (tile, _shade(tile, 0.58), _mix(tile, pal[2], 0.34),
            _mix(tile, pal[2], 0.19), _mix(pal[4], pal[0], 0.30),
            _shade(pal[4], 0.55), _mix(pal[1], pal[2], 0.42))


def _draw_eave(d: ImageDraw.ImageDraw, pal, cam) -> None:
    """The roof corner, painted as a structure rather than as a silhouette.

    Every part is drawn at its own scale, in the order a painter would lay it: the
    屋身 under the eave (wall, 柱, a warm interior) so the figure sits on a
    building and not on a line drawn across the sky; the 檐口 soffit and its 椽
    ends; the roof plane; 瓦垄 fine enough that the eye counts a texture instead
    of a picket fence; 瓦当 discs on the edge; then the 起翘 tip with its 套兽,
    the 戗脊 running back from it, the 脊兽 marching along the ridge, and the
    斗拱 stacked under the corner.
    """
    z = cam["zoom"]
    xs = list(range(-160, 1521, 10))
    edge = [_cam_pt(x, _eave_y(x), cam) for x in xs]
    dep = [_roof_depth(x) for x in xs]
    ridge = [_cam_pt(x, _eave_y(x) - dd, cam) for x, dd in zip(xs, dep)]
    tile, tile_dark, tile_lit, crest, wood, wood_deep, warm = _roof_cols(pal)

    # 1 屋身: the wall stands in the roof's shadow, lit only where the interior
    # lamp reaches out under the eave. Painted FIRST because it is behind
    skirt = [_cam_pt(x, WORLD_H + 90.0, cam) for x in xs]
    d.polygon(edge + skirt[::-1], fill=wood)
    frieze = [_cam_pt(x, _eave_y(x) + 46.0 + 0.03 * x, cam) for x in xs]
    d.polygon(edge + frieze[::-1], fill=_mix(wood, warm, 0.30))
    # light spilled from inside dies as it climbs the wall, so the band under the
    # frieze is a second, dimmer step. A wall that is one flat dark value is a
    # void, and a void under a roof reads as a hole cut in the picture.
    spill = [_cam_pt(x, _eave_y(x) + 100.0 + 0.045 * x, cam) for x in xs]
    d.polygon(frieze + spill[::-1], fill=_mix(wood, warm, 0.13))
    for cx in range(-120, 1400, 170):                        # 柱
        y0 = _eave_y(cx) + 40.0
        d.line([_cam_pt(cx, y0, cam), _cam_pt(cx, WORLD_H + 90.0, cam)],
               fill=wood_deep, width=max(2, int(11 * z)))
    rail = [_cam_pt(x, _eave_y(x) + 232.0 + 0.05 * x, cam) for x in xs]
    d.line(rail, fill=wood_deep, width=max(2, int(5 * z)))    # 栏杆
    for i in range(0, len(xs), 3):
        p = _cam_pt(xs[i], _eave_y(xs[i]) + 232.0 + 0.05 * xs[i], cam)
        q = _cam_pt(xs[i], _eave_y(xs[i]) + 268.0 + 0.05 * xs[i], cam)
        d.line([p, q], fill=wood_deep, width=max(1, int(3.4 * z)))
    for cx in (60.0, 250.0, 610.0, 1180.0):                   # 窗: lit panels
        y0, y1 = _eave_y(cx) + 104.0, _eave_y(cx) + 182.0
        p0 = _cam_pt(cx, y0, cam)
        p1 = _cam_pt(cx + 76.0, y1, cam)
        d.rectangle([p0[0], p0[1], p1[0], p1[1]], fill=_mix(warm, pal[0], 0.34))
        # a 棂花 grid: a lit rectangle with nothing in it is a colour swatch, and
        # the eye reads it as a floating card rather than as a window people live
        # behind. Three verticals and one transom is the minimum that says 窗
        for k in (1, 2, 3):
            gx = _cam_pt(cx + 76.0 * k / 4.0, y0, cam)
            gy = _cam_pt(cx + 76.0 * k / 4.0, y1, cam)
            d.line([gx, gy], fill=wood_deep, width=max(1, int(2.2 * z)))
        tm = [_cam_pt(cx, _eave_y(cx) + 143.0, cam), _cam_pt(cx + 76.0, _eave_y(cx) + 143.0, cam)]
        d.line(tm, fill=wood_deep, width=max(1, int(2.2 * z)))
        d.rectangle([p0[0], p0[1], p1[0], p1[1]], outline=wood_deep,
                    width=max(1, int(3 * z)))

    # 2 the soffit: the underside of the eave, the darkest part of the roof, and
    # its 椽 are the last thing seen before the eye moves up the slope
    soffit = [_cam_pt(x, _eave_y(x) + 24.0, cam) for x in xs]
    d.polygon(edge + soffit[::-1], fill=wood_deep)
    for i in range(0, len(xs), 2):
        d.line([edge[i], soffit[i]], fill=_shade(wood_deep, 1.7),
               width=max(1, int(2 * z)))

    # 3 the roof plane, in two tones: the upper half of a receding slope turns
    # away from a sun that is already below its own eave, so it must be darker
    # than the lower half or the plane reads as flat paper
    d.polygon(edge + ridge[::-1], fill=tile)
    midln = [_cam_pt(x, _eave_y(x) - dd * 0.52, cam) for x, dd in zip(xs, dep)]
    d.polygon(midln + ridge[::-1], fill=_shade(tile, 0.80))

    # 4 封檐板: the fascia board at the eave, LEFT PLAIN. Tile rolls never run
    # off the edge itself, and a striped band that reaches the contour is exactly
    # what made the previous render read as a barcode comb rather than as a roof.
    fascia = [_cam_pt(x, _eave_y(x) - 15.0, cam) for x in xs]
    d.polygon(edge + fascia[::-1], fill=_mix(tile, pal[2], 0.10))
    d.line(fascia, fill=tile_dark, width=max(1, int(1.6 * z)))

    # 5 瓦垄: ONE lit crest per roll on the mid field, not a crest and a gutter.
    # A dark gutter of the same weight as the crest doubles the line count and the
    # eye then counts stripes instead of reading a surface -- measured on the
    # previous render, where the 8 px pair stride filled the band with a comb.
    for x in range(-160, 1521, 8):
        y0 = _eave_y(x) - 16.0
        dd = _roof_depth(x) - 16.0
        d.line([_cam_pt(x, y0, cam), _cam_pt(x, y0 - dd, cam)],
               fill=crest, width=max(1, int(1.3 * z)))

    # 6 瓦当: the round tile-ends along the eave, which is what makes the edge
    # read as a roof rather than as a plane
    for x in range(-160, 1521, 16):
        e = _cam_pt(x, _eave_y(x) + 3, cam)
        r = 4.2 * z
        d.ellipse([e[0] - r, e[1] - r, e[0] + r, e[1] + r], fill=tile_lit,
                  outline=tile_dark)

    # 7 the hip past the corner: the roof turns away, so it foreshortens into a
    # narrow panel with its own 戗脊 rather than ending in air. It gets its own
    # tile crests too -- an untextured grey trapezoid read as a loose plank.
    hip_x = list(range(int(_CORNER_X), 1521, 10))
    hip_e = [_cam_pt(x, _eave_y(x), cam) for x in hip_x]
    hip_r = [_cam_pt(x, _eave_y(x) - _roof_depth(x) * 0.52, cam) for x in hip_x]
    d.polygon(hip_e + hip_r[::-1], fill=_mix(tile, pal[2], 0.16))
    for x in range(int(_CORNER_X) + 6, 1521, 13):
        d.line([_cam_pt(x, _eave_y(x) - 2, cam),
                _cam_pt(x, _eave_y(x) - _roof_depth(x) * 0.5 + 2, cam)],
               fill=tile_lit, width=max(1, int(1.3 * z)))
    d.line(hip_r, fill=tile_dark, width=max(2, int(2.6 * z)))
    d.line(hip_e, fill=_mix(tile_lit, warm, 0.45), width=max(2, int(2.2 * z)))

    # 8 the two contours, hard: the eave line catching the last of the sun, the
    # ridge line in shadow
    d.line(edge, fill=_mix(tile_lit, warm, 0.45), width=max(2, int(3.2 * z)))
    d.line(ridge, fill=tile_dark, width=max(2, int(2.2 * z)))

    # 9 套兽: the corner hook has to lie ALONG the returned edge, not along a
    # curve of its own. Drawn from a hand-typed tangent it ended 16 px above the
    # eave line the roof actually follows and came out as a fish floating off the
    # corner -- so its spine is now sampled from ``_eave_y`` itself.
    hook = [(_CORNER_X + f * 34.0, _eave_y(_CORNER_X + f * 34.0) - 5.0)
            for f in (0.0, 0.34, 0.67, 1.0)]
    hkw = (6.0, 4.6, 3.0, 1.0)
    d.polygon([_cam_pt(hx, hy - k, cam) for (hx, hy), k in zip(hook, hkw)]
              + [_cam_pt(hx, hy + k, cam) for (hx, hy), k in zip(hook[::-1], hkw[::-1])],
              fill=tile_lit, outline=tile_dark)

    # 10 脊兽: small crouching silhouettes ON the ridge line, each with a hump and
    # a head, and each sunk 2 px into the plane so it stands on something. A plain
    # triangle floating at the top of a dark band reads as an arrow.
    for bx in (960.0, 1000.0, 1038.0):
        p = _cam_pt(bx, _eave_y(bx) - _roof_depth(bx) + 2.0, cam)
        w = 4.6 * z
        d.polygon([p, (p[0] + w * 0.7, p[1] - w * 1.5), (p[0] + w * 1.3, p[1] - w * 1.3),
                   (p[0] + w * 1.6, p[1] - w * 0.35), (p[0] + w * 2.3, p[1])],
                  fill=tile_dark)

    # 11 斗拱: ONE bracket set under the corner, three tiers of bearing blocks
    # touching each other and tied by a 斗 stem. The first version put three
    # columns of 17 x 15 px blocks down the slope (a floating staircase), and the
    # second spaced them so far apart they read as three unrelated planks.
    for dx in (-52.0, -14.0):
        bx = _CORNER_X + dx
        by = _eave_y(bx) + 27.0
        d.line([_cam_pt(bx, by, cam), _cam_pt(bx, by + 22.0, cam)],
               fill=_shade(wood, 1.1), width=max(2, int(5 * z)))
        for j, (bw, bh) in enumerate(((13.0, 3.4), (9.5, 3.2), (6.0, 3.0))):
            p = _cam_pt(bx, by + j * 7.0, cam)
            d.rectangle([p[0] - bw * z, p[1] - bh * z, p[0] + bw * z, p[1] + bh * z],
                        fill=_shade(wood, 1.35), outline=wood_deep)


# --- camera ----------------------------------------------------------------------

def _cam_for(t: float, cut: float | None, scene: dict, w: int, h: int) -> dict:
    """Shot 1: a wide drift taking in the whole sweep. Shot 2: a closer dolly-in
    that puts the boy's head at the upper-third line.

    The camera is expressed as a crop rectangle (``world`` units shown per frame),
    because the world canvas is 4:3 and the frame is 16:9: the first version used
    ``zoom = 1.0`` for the wide take, which showed world y 0..540 of a 720-tall
    canvas and therefore CROPPED OFF THE EAVE ENTIRELY -- the title element of the
    shot was below the frame for the first six seconds, and the wide take read as
    a boy standing on nothing against mountains.

    ``cut is None`` means the spec authors no edit at all: the take stays wide
    and keeps drifting, so nothing switches and the cut gate has nothing to find.
    (There used to be a hardcoded default cut at 6s here, which let a spec delete
    the timeline event and still get the visual cut -- a gate measuring a shot the
    spec never asked for.)
    """
    if cut is None or t < cut:
        u = min(1.0, t / max(1e-6, cut or 6.0))
        return {"x": 10.0 + 46.0 * u, "y": 26.0, "zoom": w / 1160.0}
    z2 = w / 500.0                                  # ~1.92: the corner fills the frame
    hx, hy = scene["boy_x"], scene["boy_y"] - 78.0  # aim at the head, not the hips
    u = min(1.0, (t - cut) / 5.0)
    z = z2 * (1.0 + 0.05 * u)                       # a slow push in through the shot
    return {"x": hx - w * 0.44 / z, "y": hy - h * 0.34 / z, "zoom": z}


def _cam_pt(x: float, y: float, cam: dict) -> tuple:
    return ((x - cam["x"]) * cam["zoom"], (y - cam["y"]) * cam["zoom"])


def _fade(spec, t: float) -> float:
    b = 1.0
    for ev in spec.timeline:
        if ev.get("action") == "fade-in":
            a = spec.seconds_at(ev["at"]); d = max(1e-6, spec.seconds_at(ev.get("duration", "1s")))
            if t < a + d:
                b = min(b, max(0.0, (t - a) / d))
        if ev.get("action") == "fade-out":
            a = spec.seconds_at(ev["at"]); d = max(1e-6, spec.seconds_at(ev.get("duration", "1s")))
            if t > a:
                b = min(b, max(0.0, 1 - (t - a) / d))
    return b


# --- the frame function -----------------------------------------------------------

def frame_image(spec, scene: dict, t: float) -> Image.Image:
    # spec.load already resolved style.palette into RGB tuples; re-parsing them
    # as hex is a TypeError waiting for the first frame (found by running it)
    pal = list(spec.palette)
    w, h = spec.width, spec.height
    cut = None                                   # the spec owns the edit, or there is none
    for ev in spec.timeline:
        if ev.get("action") == "cut":
            cut = spec.seconds_at(ev["at"])
    cam = _cam_for(t, cut, scene, w, h)
    img = Image.new("RGB", (w, h), pal[0])
    d = ImageDraw.Draw(img)

    # 1 dusk sky: a five-stop continuous ramp. The first version interpolated
    # between three stops with hard switches at u=0.45 and u=0.70, which paints
    # two visible horizontal edges straight across the sky -- a colour band is
    # not a gradient, and a dusk sky is the one thing a shot like this cannot get
    # away with.
    stops = ((0.00, pal[0]), (0.32, _mix(pal[0], pal[3], 0.60)),
             (0.56, _mix(pal[3], pal[1], 0.50)), (0.78, pal[1]),
             (1.00, _mix(pal[1], pal[2], 0.50)))
    for y in range(h):
        u = y / max(1, h - 1)
        lo = max((s for s in stops if s[0] <= u), key=lambda s: s[0], default=stops[0])
        hi = min((s for s in stops if s[0] >= u), key=lambda s: s[0], default=stops[-1])
        f = 0.0 if hi[0] == lo[0] else (u - lo[0]) / (hi[0] - lo[0])
        d.line([(0, y), (w, y)], fill=_mix(lo[1], hi[1], f))

    # 2 the low sun: a wide soft glow, then the disc itself, flattened by the
    # horizon it is sitting on. It is placed well left of the figure (see
    # make_scene) so the close take cannot put it behind his head.
    sun_x, sun_y = _cam_pt(scene["sun_x"], scene["sun_y"], cam)
    glow_r = 330 * cam["zoom"]
    glow = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([sun_x - glow_r, sun_y - glow_r * 0.62,
                sun_x + glow_r, sun_y + glow_r * 0.62], fill=200)
    glow = glow.filter(ImageFilter.GaussianBlur(int(64 * cam["zoom"]) + 8))
    img = Image.composite(Image.new("RGB", (w, h),
                                    _mix(pal[1], (255, 214, 158), 0.55)), img, glow)
    d = ImageDraw.Draw(img)
    rd = 58 * cam["zoom"]
    d.ellipse([sun_x - rd, sun_y - rd * 0.52, sun_x + rd, sun_y + rd * 0.52],
              fill=_mix(pal[2], (255, 238, 206), 0.65))

    # 3 far mountains (three layers, parallax via camera x shift)
    for layer, col, par in (("mtn_far", _mix(pal[3], pal[0], 0.52), 0.18),
                            ("mtn_near", _mix(pal[3], pal[0], 0.18), 0.40),
                            ("mtn_near", pal[3], 0.62)):
        off = cam["x"] * (1 - par)
        pts = [_cam_pt(x - off, y, cam) for x, y in scene[layer]]
        d.polygon(pts + [(w, h), (0, h)], fill=col)

    # 4 clouds: one envelope each, lit from BELOW, because the sun is under them.
    # The cap has been gotten wrong three ways. Drawn as a separate ellipse it cut
    # a seam across the mass; drawn as the envelope offset down and filled raw it
    # self-intersected wherever the dome is steep and Pillow filled the
    # self-intersection as a block; clipped to a horizontal line it was correct
    # geometry and still read as a rectangle with a bump. The cap is now the
    # envelope and its own offset -- a band that follows the dome, clamped to the
    # base so it cannot spill past the tips. It is drawn per cloud rather than
    # through a shared mask, because a shared mask composites EVERY cap over EVERY
    # body and the cloud behind then paints its shadow across the one in front.
    for group, speed in (("clouds_hi", 6.0), ("clouds_lo", 12.0)):
        lit = _mix(pal[2], pal[1], 0.18)
        shad = _mix(pal[2], pal[0], 0.44)
        for c in scene[group]:
            dx = (t * speed) % (WORLD_W + 500) - 250
            prof = [(x + dx - cam["x"] * 0.2, y) for x, y in c["top"]]
            top = [_cam_pt(x, y, cam) for x, y in prof]
            # the base must be shifted with the dome. Taking it from the raw
            # envelope x instead put the flat base a whole drift off the mass it
            # closes, and the polygon between the two is a parallelogram -- the
            # render before this one was giant peach wedges for that reason alone
            yb = [_cam_pt(x, c["yb"], cam) for x, _ in prof]
            d.polygon(top + yb[::-1], fill=lit)
            floor = yb[0][1]
            off = 0.40 * (floor - min(p[1] for p in top))
            d.polygon(top + [(x, min(y + off, floor)) for x, y in top[::-1]],
                      fill=shad)

    # 5 the eave, then the boy ON it (world geometry, camera-transformed)
    _draw_eave(d, pal, cam)
    _draw_boy(d, pal, scene, cam, t)

    # 6 embers rising, twinkling (accent colour), with a few large soft ones in
    # the foreground so the air has depth instead of only specks
    for i, e in enumerate(scene["embers"]):
        et = (t * e["rise"] + e["y0"]) % (WORLD_H + 60)
        ex = (e["x0"] + math.sin(t * 0.7 + e["phase"]) * 18 + t * e["drift"]) % WORLD_W
        a = 0.45 + 0.55 * math.sin(t * e["tw"] + e["phase"]) ** 2
        near = i % 9 == 0
        col = _mix(pal[0], pal[5], 0.30 + 0.70 * a)
        r = (e["r"] * (3.4 if near else 1.0)) * cam["zoom"]
        p = _cam_pt(ex, WORLD_H + 30 - et, cam)
        if near:                                    # the bloom in front of the disc
            soft = Image.new("L", (w, h), 0)
            ImageDraw.Draw(soft).ellipse([p[0] - r * 3, p[1] - r * 3,
                                          p[0] + r * 3, p[1] + r * 3], fill=int(70 * a))
            soft = soft.filter(ImageFilter.GaussianBlur(int(r * 1.6) + 2))
            img = Image.composite(Image.new("RGB", (w, h), col), img, soft)
            d = ImageDraw.Draw(img)
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)

    # vignette (cinematic edge falloff)
    vig = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-w * 0.25, -h * 0.25, w * 1.25, h * 1.25], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGB", (w, h), _shade(pal[0], 0.45))
    img = Image.composite(img, dark, vig)

    # timeline fade
    b = _fade(spec, t)
    if b < 1.0:
        img = Image.blend(Image.new("RGB", (w, h), (0, 0, 0)), img, b)
    return img


def render_frames(spec, scene: dict):
    """Yield raw RGB bytes per frame — pure function of (t, spec, seed)."""
    fps = spec.fps
    for f in range(spec.n_frames):
        yield frame_image(spec, scene, f / fps).tobytes()


# --- route driver (firstloop skeleton) --------------------------------------------

def run(spec_path: Path, out_dir: Path, keep_frames: bool = False) -> dict:
    spec = spec_mod.load(spec_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    scene = make_scene(spec)
    luma_by_frame: list[float] = []
    hist_by_frame: list[np.ndarray] = []
    # the four colours the ROOF is painted in (not the wall: the wall was in frame
    # the whole time the eave was not, which is precisely the bug this measures)
    tile_cols = np.array(_roof_cols(spec.palette)[:4], dtype=np.uint8)
    tile_shares: list[float] = []

    def _saved():
        fps = spec.fps
        for f in range(spec.n_frames):
            img = frame_image(spec, scene, f / fps)
            luma_by_frame.append(ImageStat.Stat(img.convert("L")).mean[0])
            hist_by_frame.append(_luma_hist(img))
            arr = np.asarray(img).astype(np.uint8)
            on = (arr[:, :, None, :] == tile_cols[None, None, :, :]).all(-1).any(-1)
            tile_shares.append(100.0 * float(on.mean()))
            img.save(frames_dir / f"{f:04d}.png", optimize=True)
            yield img.tobytes()

    payload = provenance.content_hash(_saved())
    deterministic = provenance.content_hash(render_frames(spec, scene)) == payload

    mp4 = out_dir / "clip.mp4"
    ffmpeg.encode_images(frames_dir, spec.fps, mp4)
    summary = ffmpeg.video_summary(mp4)

    # scene cuts: isolated spikes of frame-to-frame luma-distribution shift
    cuts, gradual, tv = classify_cuts(hist_by_frame)
    # the loudest shift that is neither a cut nor part of a ramp is the motion
    # floor the threshold clears. Reporting it alongside the cut's own spike is
    # what makes the threshold auditable: a number with no stated margin is an
    # uncalibrated check (audit B)
    flagged = set(cuts) | set(gradual)
    floor = max((d for i, d in enumerate(tv) if i + 1 not in flagged), default=0.0)
    at_cut = [tv[i - 1] for i in cuts]

    measured = {
        "duration": summary["duration"], "width": summary["width"],
        "height": summary["height"],
        "max_black_run_seconds": validate.max_black_run_seconds(luma_by_frame, spec.fps),
        "scene_cuts": len(cuts),
        # a frame "shows the title element" when the roof tiles cover more than
        # 1.5% of it; the fades cannot, and are expected to fail this
        "title_element_frame_pct": (
            100.0 * sum(1 for s in tile_shares if s > 1.5) / max(1, len(tile_shares))),
        "deterministic": deterministic,
    }
    report = validate.run_acceptance(spec.acceptance, measured)
    report["measured"] = measured
    report["cut_detection"] = {
        "method": f"luma histogram total variation, {_CUT_BINS} bins, isolated peak",
        "threshold": _CUT_L1_THRESHOLD,
        "hard_cut_frames": cuts,
        "gradual_frames": len(gradual),
        "diff_at_hard_cuts": [round(d, 4) for d in at_cut],
        "luma_delta_at_hard_cuts": [
            round(abs(luma_by_frame[i] - luma_by_frame[i - 1]), 2) for i in cuts],
        "largest_unflagged_diff": round(floor, 4),
        "margin_factor": round(min(at_cut, default=0.0) / max(floor, 1e-9), 1),
    }
    report["clip"] = {k: summary[k] for k in
                      ("duration", "width", "height", "codec_name", "pix_fmt", "nb_frames")}
    cli.write_report(out_dir, report)

    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec.to_dict(), content_hash=payload,
        artifact_hashes={"clip.mp4": provenance.sha256_file(mp4)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["clip.mp4", "report.json", "manifest.json"],
        notes=spec.assumptions, pipeline="vcac-anime/0.1")
    provenance.write_manifest(manifest, out_dir)

    if not keep_frames:
        import shutil
        shutil.rmtree(frames_dir, ignore_errors=True)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    a = cli.parse_args("vcac anime route (2D cel clip)", argv, extra=[
        (("--keep-frames",), dict(action="store_true")),
    ])
    spec = spec_mod.load(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec.id), keep_frames=a.keep_frames)
    m = r["report"]["measured"]
    return cli.finish("anime", r, summaries=[
        f"{spec.id} -> {r['out_dir']}",
        f"{m['duration']:.2f}s {m['width']}x{m['height']} "
        f"cuts={m['scene_cuts']} black_run={m['max_black_run_seconds']:.2f}s"])


if __name__ == "__main__":
    raise SystemExit(main())
