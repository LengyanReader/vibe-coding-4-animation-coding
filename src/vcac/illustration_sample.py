"""illustration route — 群像插画 (an ensemble portrait) as a deterministic stack.

What is quoted here is a *visual grammar*, never a character: the shonen cover
mechanics (staggered ensemble, tapered ink line, screentone, radial speed
lines, rim light, logo band), the soft-edged yōkai-at-dusk mood, and the
cumulus-and-pastoral light of hand-painted cel backgrounds. Every figure is an
original design assembled from parameters (docs/styles.md §2 §4 §7, and the
same stance `specs/examples/anime-eave.yaml` declares).

The chain, in the order it paints:

  1. 底   backdrop    vertical multi-stop sky gradient, ridge bands, sun disc
  2. 面   floor       a perspective plane (planks or paddy) under the cast
  3. 云   clouds      union-of-circles cumulus: shaded body, lit crown
  4. 景   set         columns / banners / rooftops / gate — polygons
  5. 线   speed       tapered radial lines from a focus point, BEHIND the cast
                      (lines across a face read as a printing fault, not energy)
  6. 像   figures     parametric characters: neck, chest, waist, hip, hands,
                      shoes, a hair mass behind the skull and a fringe in front
                      of it, brows and mouth as an expression, an offset rim
                      pass for the lit edge, a shadow pass for the dark one
  7. 网点 screentone  a staggered dot screen whose radius comes from a density
                      field — the mechanism of tone paper, vectorised
  8. 框   frame       panel border + logo band + an original emblem
  9. 量化 quantise    nearest colour onto the declared palette with an ordered
                      (Bayer) dither, so the gates count pixels, not adjectives

Honest ceiling (docs/styles.md §0): this is *poster-grade* flat art. Hair
strands, fabric folds and facial acting are the human part of the craft, and
this route approximates them with parameters; it does not pretend to a key
animation drawing.

Two measurements are deliberately conservative rather than flattering.
figure_count counts faces a detector can actually find, so a distant figure
whose hair covers her own face is not counted -- the cast number is a lower
bound, and one spec had to change its haircut to keep its cast countable.
sky_negative_pct counts the share of the sky band carrying no drawn edge. Read
from a raw luma gradient it was reading the Bayer dither instead, and the numbers
inverted: two enormous smooth cloud banks took the dusk sheet 45.9 -> 75.6
(painting the sky made it "emptier"), while deleting every cloud took it 45.9 ->
44.7. Busyness is now judged on a 5x5 median of the luma, which cancels a 4x4
alternation and keeps a hard edge; measured after that fix, on the three shipped
sheets and three mutants: fox 82.6 authored / 85.4 with no clouds at all / 73.5
with ten small hard-edged clouds cluttering it / 81.4 flooded with two big
smooth banks; guild 58.9 / 63.2 with its 72 speed lines switched off; cumulus
79.6. The bands in the specs sit on those numbers, and the direction that has
been watched going red is the dusk sheet's floor (docs/styles.md §8.3).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

from . import cli, ffmpeg, media, provenance, spec as spec_mod, validate

_BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
                   dtype=float) / 16.0


class IllusError(ValueError):
    """The spec asks for something whose gates could not be measured."""


def _rgb(pal: dict, key: str) -> tuple[int, int, int]:
    return tuple(spec_mod.parse_hex(pal[key]))


# --- primitives ---------------------------------------------------------------

def _tapered(p0, p1, w0: float, w1: float) -> list:
    """A limb as a quad: two centres, two half-widths, offset perpendicular."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / n, dx / n
    return [(p0[0] + nx * w0, p0[1] + ny * w0), (p1[0] + nx * w1, p1[1] + ny * w1),
            (p1[0] - nx * w1, p1[1] - ny * w1), (p0[0] - nx * w0, p0[1] - ny * w0)]


def _shape(d, poly, fill, line, width: int = 2, rim=None, lit: int = 1,
           roff: float = 0.0) -> None:
    """One cel shape.

    The rim is a copy of the mass pushed toward the light and laid down first,
    so only a crescent survives on the lit edge: an outline-wide rim around
    every shape reads as a halo, which is not what a rim light is.
    """
    if rim and roff:
        d.polygon([(x + lit * roff, y) for x, y in poly], fill=rim)
    d.polygon(poly, fill=fill, outline=line, width=width)


def _blob(d, c, rx: float, ry: float, fill, line, width: int = 2, rim=None,
          lit: int = 1, roff: float = 0.0) -> None:
    box = [c[0] - rx, c[1] - ry, c[0] + rx, c[1] + ry]
    if rim and roff:
        d.ellipse([b + lit * roff for b in (box[0], box[1], box[2], box[3])], fill=rim)
    d.ellipse(box, fill=fill, outline=line, width=width)


# --- 1-4: backdrop, floor, clouds, set dressing -------------------------------

def _sky(arr: np.ndarray, stops: list, pal: dict) -> None:
    """Vertical gradient between declared stops; stops name palette keys, so a
    stop cannot smuggle an undeclared colour past the quantiser."""
    h, w, _ = arr.shape
    pts = sorted(((float(s["at"]), np.array(_rgb(pal, s["color"]), dtype=float))
                  for s in stops))
    ramp = np.zeros((h, 3), dtype=float)
    for y in range(h):
        t = y / max(1, h - 1)
        lo = max((p for p in pts if p[0] <= t), key=lambda p: p[0], default=pts[0])
        hi = min((p for p in pts if p[0] >= t), key=lambda p: p[0], default=pts[-1])
        f = 0.0 if hi[0] == lo[0] else (t - lo[0]) / (hi[0] - lo[0])
        ramp[y] = lo[1] * (1 - f) + hi[1] * f
    arr[:] = ramp[:, None, :]


def _ridge(d, w: int, h: int, at: float, amp: float, freq: float, colour,
           seed: int, phase: float = 0.0) -> None:
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, 1.0, 72)
    y = h * at + amp * h * (0.6 * np.sin(2 * math.pi * freq * t + phase)
                            + 0.4 * np.sin(2 * math.pi * freq * 2.7 * t + rng.uniform(0, 6)))
    pts = [(float(x), float(yy)) for x, yy in zip(np.linspace(0.0, w, 72), y)]
    d.polygon(pts + [(w, h), (0, h)], fill=colour)


def _floor(d, w: int, h: int, pal: dict, spec: dict) -> None:
    """A perspective plane: boards (or paddy lines) converging on a vanishing
    point, so the cast stands in a room rather than on a colour band."""
    fl = spec["backdrop"].get("floor")
    if not fl:
        return
    horizon = h * float(fl.get("at", 0.60))
    vp = (w * float(fl.get("vanish_x", 0.5)), horizon)
    d.polygon([(0, horizon), (w, horizon), (w, h), (0, h)], fill=_rgb(pal, fl["color"]))
    ink = _rgb(pal, "ink")
    n = int(fl.get("planks", 14))
    for k in range(n + 1):
        x0 = w * (k / n)
        x1 = vp[0] + (x0 - vp[0]) * 6.0          # spread wide by the time it exits
        d.line([vp, (x1, h)], fill=ink, width=1)
    for k in range(1, 6):                        # receding cross joints
        f = (k / 6) ** 2.2
        yy = horizon + (h - horizon) * f
        d.line([(0, yy), (w, yy)], fill=ink, width=1)
    d.line([(0, horizon), (w, horizon)], fill=ink, width=2)


def _cloud(d, cx: float, cy: float, scale: float, lobes: list, base, lit,
           edge=None, mid=None, band: str = "bottom") -> None:
    """A cumulus as ONE silhouette, not a pile of circles.

    Filled puffs laid over one another leave seams, and a seam as wide as a lobe
    is read by the eye as a separate ball: the tower came out as a cluster of
    lanterns and the dusk bands as strings of beads. So the lobes are treated as
    a height field instead -- their upper envelope is sampled across the width,
    closed by one flat base, and filled once.

    `band` says which side of the mass carries the shade. At midday the crown is
    lit and the underside is not (band=bottom); when the sun is low the weather
    is lit FROM BELOW and the crown goes dark (band=top), which is the whole
    difference between a fair-weather cloud and a dusk one. Two interior arcs
    keep the mass from reading as a plate.
    """
    rings = [(cx + dx * scale, cy + dy * scale, r * scale) for dx, dy, r in lobes]
    x0 = min(x - r for x, _, r in rings)
    x1 = max(x + r for x, _, r in rings)
    yb = max(y + r for _, y, r in rings)                  # the flat base
    top = []
    for k in range(73):
        x = x0 + (x1 - x0) * k / 72.0
        ys = [y - math.sqrt(max(0.0, r * r - (x - xc) ** 2))
              for xc, y, r in rings if abs(x - xc) <= r]
        if ys:
            top.append((x, min(ys)))
    if len(top) < 4:
        return
    span = (x1 - x0) or 1.0
    lift = max(2.0, 0.24 * (yb - min(y for _, y in top)))
    amp = lift * 0.32

    def offset(dy):
        return [(x, y + dy + amp * math.sin(5.5 * (x - x0) / span) * (1 if dy > 0 else -1))
                for x, y in top]

    if band == "top":                       # dusk: the low sun lights the floor
        d.polygon(top + [(x1, yb), (x0, yb)], fill=lit)
        d.polygon(top + list(reversed(offset(lift))), fill=base)
        if mid:
            inner = offset(lift * .55)
            d.polygon(offset(lift) + list(reversed(inner)), fill=mid)
    else:                                   # midday: the crown carries the light
        d.polygon(top + [(x1, yb), (x0, yb)], fill=base)
        # paint order is the value stack, darkest first: the mid band laid AFTER
        # the lit crown ate the white and left a blue plate where a cloud should
        # be -- which is the same mistake the render stack makes in reverse
        if mid:
            d.polygon(offset(-lift * .45) + [(x1, yb - lift * .45),
                                             (x0, yb - lift * .45)], fill=mid)
        d.polygon(offset(-lift) + [(x1, yb - lift), (x0, yb - lift)], fill=lit)
    line = edge or base
    rings_s = sorted(rings, key=lambda t: t[0])
    for (xa, ya, ra), (xb, yb2, rb) in zip(rings_s, rings_s[1:]):
        dd = math.hypot(xb - xa, yb2 - ya)
        if ra + rb <= dd or dd < 1e-6:                    # the lobes do not meet
            continue
        a = (ra * ra - rb * rb + dd * dd) / (2 * dd)
        hh = math.sqrt(max(0.0, ra * ra - a * a))
        px, py = xa + a * (xb - xa) / dd, ya + a * (yb2 - ya) / dd
        jx, jy = px + hh * (yb2 - ya) / dd, py - hh * (xb - xa) / dd
        px2, py2 = px - hh * (yb2 - ya) / dd, py + hh * (xb - xa) / dd
        if py2 < jy:
            jx, jy = px2, py2
        if jy > yb - lift:                                # below the break: no line
            continue
        ang = math.degrees(math.atan2(jy - yb2, jx - xb))
        d.arc([xb - rb, yb2 - rb, xb + rb, yb2 + rb], ang, ang + 46, fill=line,
              width=2)                                    # the scallop's hollow
    if edge:                                    # the weather line, and the base
        d.line(top, fill=edge, width=2)
        d.line([(x0, yb), (x1, yb)], fill=edge, width=1)


def _set_item(d, w: int, h: int, item: dict, pal: dict) -> None:
    kind = item["kind"]
    col = _rgb(pal, item.get("color", "structure"))
    dark = _rgb(pal, item.get("shade", "ink"))
    x, y = w * float(item["at"][0]), h * float(item["at"][1])
    s = float(item.get("scale", 0.1)) * h
    if kind == "column":
        # a pillar is masonry with a capital and a plinth: a plain rectangle
        # capped by a trapezoid reads as a coat stand the height of a room
        cap, plinth = s * .13, s * .11
        d.rectangle([x - plinth, y - s * .07, x + plinth, y], fill=col,
                    outline=dark, width=2)
        d.rectangle([x - s * .075, y - s * 1.46, x + s * .075, y - s * .07],
                    fill=col, outline=dark, width=2)
        d.polygon([(x - cap, y - s * 1.62), (x + cap, y - s * 1.62),
                   (x + s * .085, y - s * 1.46), (x - s * .085, y - s * 1.46)],
                  fill=col, outline=dark, width=2)
        for k in range(4):                        # fluting, so it reads as timber
            xx = x - s * .05 + k * s * .033
            d.line([(xx, y - s * 1.42), (xx, y - s * .11)], fill=dark, width=1)
        d.line([(x - s * .075, y - s * 1.10), (x + s * .075, y - s * 1.10)],
               fill=dark, width=1)                # a band, so the shaft has a joint
    elif kind == "mast":
        # an airfield mast is a STRUCTURE: legs, bracing, a platform, a swing
        # and guy wires. One filled bar argues with nothing and reads as a lamp
        top_y = y - s * 1.62
        bt, tt = s * .115, s * .055
        _shape(d, [(x - bt, y), (x - tt, top_y), (x + tt, top_y), (x + bt, y)],
               col, dark, 2)
        for k in range(6):                          # X bracing up the lattice
            f0, f1 = k / 6.0, (k + 1) / 6.0
            w0 = bt + (tt - bt) * f0
            w1 = bt + (tt - bt) * f1
            y0 = y + (top_y - y) * f0
            y1 = y + (top_y - y) * f1
            d.line([(x - w0, y0), (x + w1, y1)], fill=dark, width=1)
            d.line([(x + w0, y0), (x - w1, y1)], fill=dark, width=1)
            d.line([(x - w1, y1), (x + w1, y1)], fill=dark, width=1)
        d.rectangle([x - s * .17, top_y - s * .05, x + s * .17, top_y + s * .01],
                    fill=_rgb(pal, item.get("deck", "steel")), outline=dark,
                    width=2)                        # the observation platform
        d.line([(x, top_y - s * .05), (x, top_y - s * .30)], fill=dark, width=2)
        for k in range(4):                          # a windsock in the weather
            yy = top_y - s * (.28 + .035 * k)
            d.line([(x + s * .02, yy), (x + s * (.30 - .05 * k), yy + s * .012)],
                   fill=_rgb(pal, item.get("flag", "seal")), width=3)
        for side in (-1, 1):                        # guy wires anchored to the hill
            d.line([(x + tt * side, top_y + s * .04), (x + side * s * .50, y)],
                   fill=dark, width=1)
            d.line([(x + side * s * .50, y), (x + side * s * .50, y + s * .03)],
                   fill=dark, width=2)
    elif kind == "banner":
        d.line([(x, y - s * 1.34), (x, y - s * 1.2)], fill=dark, width=2)
        pts = [(x - s * .13, y - s * 1.2), (x + s * .13, y - s * 1.2),
               (x + s * .13, y - s * .26), (x, y - s * .40), (x - s * .13, y - s * .26)]
        _shape(d, pts, col, dark, 2)
        d.polygon([(x - s * .13, y - s * 1.2), (x + s * .13, y - s * 1.2),
                   (x + s * .10, y - s * 1.1), (x - s * .10, y - s * 1.1)],
                  fill=_rgb(pal, "rim"))
        for k in range(3):                        # hanging folds
            yy = y - s * (1.04 - 0.2 * k)
            d.line([(x - s * .10, yy), (x + s * .10, yy)], fill=dark, width=1)
    elif kind == "roof":
        # a building sits IN the ground: a hard ellipse of shade under the eaves
        # is what keeps it from floating like a sticker on the hill
        d.ellipse([x - s * .58, y + s * .26, x + s * .58, y + s * .42], fill=dark)
        wallc = _rgb(pal, item.get("wall", "wall"))
        d.rectangle([x - s * .3, y, x + s * .3, y + s * .34], fill=wallc,
                    outline=dark, width=2)
        d.polygon([(x - s * .58, y), (x + s * .58, y), (x + s * .34, y - s * .36),
                   (x - s * .34, y - s * .36)], fill=col, outline=dark, width=2)
        d.line([(x - s * .34, y - s * .36), (x + s * .34, y - s * .36)], fill=dark,
               width=2)                             # the ridge
        for k in range(3):                           # thatch courses
            yy = y - s * (.06 + .10 * k)
            inset = s * (.56 - .075 * k)
            d.line([(x - inset, yy), (x + inset, yy)], fill=dark, width=1)
        d.line([(x - s * .58, y), (x + s * .58, y)], fill=dark, width=2)  # eaves
        d.rectangle([x - s * .28, y - s * .50, x - s * .18, y - s * .30],
                    fill=wallc, outline=dark, width=1)      # chimney
        d.rectangle([x - s * .30, y - s * .54, x - s * .16, y - s * .50],
                    fill=dark)                                  # its cap
        d.rectangle([x - s * .04, y + s * .12, x + s * .10, y + s * .34],
                    fill=_rgb(pal, "structure"), outline=dark, width=1)  # door
        d.ellipse([x - s * .04, y + s * .12, x + s * .10, y + s * .20],
                  fill=_rgb(pal, "structure"), outline=dark, width=1)     # arch
        for k in range(2):                                       # lit windows
            wx = x - s * .24 + k * s * .09
            d.rectangle([wx, y + s * .10, wx + s * .07, y + s * .22],
                        fill=_rgb(pal, "light"), outline=dark, width=1)
    elif kind == "gate":
        for side in (-1, 1):
            d.polygon([(x + side * s * .42, y), (x + side * s * .34, y),
                       (x + side * s * .3, y - s * .92), (x + side * s * .38, y - s * .92)],
                      fill=col, outline=dark, width=2)
        d.polygon([(x - s * .56, y - s * .98), (x + s * .56, y - s * .98),
                   (x + s * .5, y - s * .86), (x - s * .5, y - s * .86)],
                  fill=col, outline=dark, width=2)
        d.rectangle([x - s * .44, y - s * .82, x + s * .44, y - s * .74], fill=col,
                    outline=dark, width=2)
    elif kind == "paddy":
        # a field is a PATCH with an edge before it is a set of lines: bare
        # strokes laid straight onto the ground read as scratches on the sheet,
        # which is why the furrows are now contained by a bank and carry water
        sheen = _rgb(pal, item.get("sheen", "steel"))
        half, dep = s * .54, s * .30
        bench = [(x - half, y), (x + half, y), (x + half * .80, y + dep),
                 (x - half * .80, y + dep)]
        _shape(d, bench, col, dark, 2)
        d.polygon([(x - half * .90, y + dep * .22), (x + half * .90, y + dep * .22),
                   (x + half * .84, y + dep * .58), (x - half * .84, y + dep * .58)],
                  fill=sheen)                       # the water takes the sky
        for k in range(5):                          # ridges across the water
            yy = y + dep * (.22 + .09 * k)
            inset = half * (.90 - .012 * k)
            d.line([(x - inset, yy), (x + inset, yy)], fill=dark, width=1)
        d.line([bench[3], bench[2]], fill=dark, width=2)     # the near bank
    elif kind == "reeds":
        # foreground silhouette breaks a large flat ground band, and a dusk field
        # without grass at its edge reads as an empty brown plate. Blades are
        # QUADS: a two-pixel line at this scale is the scratch mark again
        for k in range(13):
            xx = x + (k - 6) * s * .070
            hh = s * (.34 + .20 * ((k * 7) % 5) / 4.0)
            bend = s * (.055 if k % 2 else -.055) * (1 + k % 3)
            _shape(d, _tapered((xx, y), (xx + bend, y - hh), s * .014, 0.6),
                   dark, dark, 1)
            d.line([(xx + bend, y - hh), (xx + bend * 1.7, y - hh - s * .07)],
                   fill=dark, width=2)              # the seed head leans on


# --- 5: speed lines -----------------------------------------------------------

def _speed_lines(d, w: int, h: int, focus: list, n: int, pal: dict, seed: int,
                 skip: float = 0.12, wedge: list | None = None) -> None:
    """Tapered radial lines. They are drawn BEFORE the cast: energy lines over a
    face read as a printing fault rather than as momentum."""
    rng = np.random.default_rng(seed)
    fx, fy = w * float(focus[0]), h * float(focus[1])
    ink = _rgb(pal, "ink")
    outer = math.hypot(w, h)
    for k in range(int(n)):
        a = rng.uniform(0.0, 2 * math.pi)
        if wedge and not (wedge[0] <= (a % (2 * math.pi)) <= wedge[1]):
            continue
        r0, r1 = outer * skip, outer * rng.uniform(0.72, 1.05)
        w0, w1 = rng.uniform(0.4, 0.9), rng.uniform(1.3, 3.0)
        p0 = (fx + r0 * math.cos(a), fy + r0 * math.sin(a))
        p1 = (fx + r1 * math.cos(a), fy + r1 * math.sin(a))
        d.polygon(_tapered(p0, p1, w0, w1), fill=ink)


# --- 6: the parametric figure -------------------------------------------------

def _figure(d, f: dict, pal: dict, w: int, h: int) -> None:
    """A character in unit space: feet at y=0, crown at y=1, centred on x=0.

    Anatomy is a small set of numbers that the spec can move: head height,
    shoulder width, waist, hip, and the two-segment arm. What makes it read as
    a drawing rather than a diagram is the order — a shadow mass, then hair
    behind the skull, then the body, then the fringe and the face on top.
    """
    cx, ground = w * float(f["at"][0]), h * float(f["at"][1])
    s = float(f.get("scale", 0.5)) * h
    lit = 1 if float(f.get("lit", 1)) > 0 else -1
    ink = _rgb(pal, "ink")
    rimc = _rgb(pal, "rim")
    skin = _rgb(pal, f.get("skin", "skin"))
    hair = _rgb(pal, f["hair"])
    cloth = _rgb(pal, f["garment"])
    shade = _rgb(pal, f.get("garment_shade", "shadow"))
    accent = _rgb(pal, f.get("accent", "light"))
    paper = _rgb(pal, "paper")
    ro = 0.008 * s                                # rim offset: a crescent, not a band
    so = 0.020 * s                                # shadow mass offset
    lw = max(2, int(s * 0.006))                   # line weight scales with size

    def P(x: float, y: float) -> tuple[float, float]:
        return (cx + x * s, ground - y * s)

    def shift(poly, dx):
        return [(x + dx, y) for x, y in poly]

    head_c = P(0.0, 0.885)
    hrx, hry = 0.070 * s, 0.080 * s
    shoulders, waist, hips = 0.104, 0.066, 0.084

    def HP(fx: float, fy: float) -> tuple[float, float]:
        """a point on the skull: fx across its half-widths, fy up its half-heights.

        Hair and features are placed in head units rather than figure units, so
        moving the head also moves what sits on it -- which is the difference
        between a drawing and a diagram that has drifted apart.
        """
        return (head_c[0] + fx * hrx, head_c[1] - fy * hry)
    torso = [P(-shoulders, .775), P(shoulders, .775), P(.078, .62), P(waist, .565),
             P(hips, .49), P(-hips, .49), P(-waist, .565), P(-.078, .62)]

    # 0. the cast is GROUNDED: a figure that never touches the ground is a
    # sticker, and one hard ellipse of shade under the heels plants it there
    d.ellipse([cx - .105 * s, ground - .014 * s, cx + .105 * s, ground + .012 * s],
              fill=_rgb(pal, f.get("cast", "shadow")))

    # 1. the shadow mass: the same silhouette pushed away from the light, so the
    # sliver that stays visible is the shaded side (two-tone cel, no gradients)
    _blob(d, (head_c[0] + lit * so, head_c[1]), hrx, hry, shade, shade, 1)
    _shape(d, shift(torso, lit * so), shade, shade, 1)

    # 2. hair behind the skull (long/twin get a back mass, spiky gets spikes later)
    style = f.get("hair_style", "short")
    if style in ("long", "twin"):
        back = [P(-.098, .93), P(.098, .93), P(.122, .58), P(.07, .63),
                P(-.07, .63), P(-.122, .58)]
        _shape(d, back, hair, ink, lw, rim=rimc, lit=lit, roff=ro)
    if style == "twin":
        for side in (-1, 1):                      # buns above the ears, tails below
            bx, by = HP(1.02 * side, .52)         # at the temples: at eye height
            _blob(d, (bx, by), .044 * s, .050 * s, hair, ink, lw,   # they read as
                  rim=rimc, lit=lit, roff=ro)     # headphones, not a twin tail
            _shape(d, _tapered((bx, by + .045 * s),
                               (bx + .030 * s * side, by + .280 * s),
                               .022 * s, .010 * s), hair, ink, max(1, lw - 1))

    # 3. legs, shoes, then the torso over them
    for side in (-1, 1):
        hip = P(.046 * side, .50)
        knee = P(.052 * side, .27)
        ankle = P(.054 * side, .05)
        _shape(d, _tapered(hip, knee, .040 * s, .030 * s), cloth, ink, lw,
               rim=rimc, lit=lit, roff=ro)
        _shape(d, _tapered(knee, ankle, .030 * s, .022 * s), cloth, ink, lw,
               rim=rimc, lit=lit, roff=ro)
        d.ellipse([ankle[0] - .036 * s, ankle[1] - .020 * s,
                   ankle[0] + .030 * s, ankle[1] + .020 * s], fill=shade,
                  outline=ink, width=lw)
    garment = f.get("garment_style", "coat")
    if garment == "dress":
        hem = [P(-waist, .585), P(waist, .585), P(.152, .185), P(.09, .205),
               P(0, .196), P(-.09, .205), P(-.152, .185)]
        _shape(d, hem, cloth, ink, lw, rim=rimc, lit=lit, roff=ro)
        for k in (-1, 1):                         # two fold lines, skirt weight
            d.line([P(.03 * k, .56), P(.10 * k, .20)], fill=shade, width=lw)
    elif garment in ("coat", "school", "pilot", "armor"):
        hem = .30 if garment in ("coat", "pilot") else .46
        flare = .118 if garment == "coat" else .092
        skirt = [P(-waist, .575), P(waist, .575), P(flare, hem),
                 P(flare * .4, hem + .02), P(-flare * .4, hem + .02), P(-flare, hem)]
        _shape(d, skirt, cloth, ink, lw, rim=rimc, lit=lit, roff=ro)
    _shape(d, torso, cloth, ink, lw, rim=rimc, lit=lit, roff=ro)
    if garment == "coat":                         # open front + lapels
        d.line([P(0, .765), P(.012 * lit, .34)], fill=shade, width=lw + 1)
        for side in (-1, 1):
            _shape(d, [P(.03 * side, .775), P(.085 * side, .76), P(.05 * side, .66)],
                   shade, ink, lw)
    elif garment == "school":
        d.line([P(-.032, .79), P(.032, .79)], fill=ink, width=lw + 2)
        for k in range(3):
            d.ellipse([P(0, .72 - .055 * k)[0] - .008 * s,
                       P(0, .72 - .055 * k)[1] - .008 * s,
                       P(0, .72 - .055 * k)[0] + .008 * s,
                       P(0, .72 - .055 * k)[1] + .008 * s], fill=accent, outline=ink)
    elif garment == "pilot":
        d.line([P(-shoulders, .74), P(waist, .52)], fill=shade, width=lw + 2)
    elif garment == "armor":
        for side in (-1, 1):
            _blob(d, P(.112 * side, .765), .058 * s, .040 * s, accent, ink, lw,
                  rim=rimc, lit=lit, roff=ro)
        d.rectangle([P(-hips, .52)[0], P(-hips, .52)[1], P(hips, .475)[0],
                     P(hips, .475)[1]], fill=shade, outline=ink, width=lw)
        d.line([P(-.05, .70), P(.05, .70)], fill=accent, width=lw + 1)
    d.line([P(-waist, .565), P(waist, .565)], fill=shade, width=lw)   # the waist

    # 4. arms: two segments each, with a hand at the end
    pose = f.get("pose", "ready")
    wrists: dict[int, tuple[float, float]] = {}
    for side in (-1, 1):
        sh = P(.098 * side, .755)
        if pose == "raised" and side == lit:
            el, wr = P(.152 * side, .86), P(.196 * side, .985)
        elif pose == "akimbo" and side == -lit:
            el, wr = P(.168 * side, .655), P(.092 * side, .585)
        elif pose == "hold" and side == lit:
            el, wr = P(.158 * side, .70), P(.205 * side, .60)
        else:
            el, wr = P(.152 * side, .625), P(.162 * side, .485)
        _shape(d, _tapered(sh, el, .034 * s, .026 * s), cloth, ink, lw,
               rim=rimc, lit=lit, roff=ro)
        # a sleeved arm keeps its cloth to the wrist: bare forearms on every
        # figure in a period cast read as mannequins rather than as people
        fore = cloth if f.get("sleeve") else skin
        _shape(d, _tapered(el, wr, .026 * s, .020 * s), fore, ink, lw,
               rim=rimc, lit=lit, roff=ro)
        _blob(d, wr, .024 * s, .026 * s, skin, ink, lw, rim=rimc, lit=lit, roff=ro)
        wrists[side] = wr

    # 5. neck + head, then the crown and fringe over the skull, then the face
    _shape(d, _tapered(P(0, .80), P(0, .775), .024 * s, .026 * s), skin, ink, lw)
    _blob(d, head_c, hrx, hry, skin, ink, lw, rim=rimc, lit=lit, roff=ro)
    # the crown is a cap that sits ON the skull: its lower edge is a flat chord
    # across the forehead. Drawn as a band above the head it reads as a hat
    cap = [HP(1.05 * math.cos(math.pi * k / 12),
              1.05 * max(math.sin(math.pi * k / 12), 0.58)) for k in range(13)]
    _shape(d, cap, hair, ink, max(1, lw - 1))
    if style == "spiky":
        for k in range(9):
            a = math.pi * (0.04 + 0.92 * k / 8)
            bx, by = HP(math.cos(a), 0.55 + 0.45 * math.sin(a))
            tx, ty = HP(1.85 * math.cos(a) + lit * 0.08, 1.02 + 0.95 * math.sin(a))
            _shape(d, [(bx - .018 * s, by), (bx + .018 * s, by), (tx, ty)], hair,
                   ink, max(1, lw - 1))
        for side in (-1, 1):                      # two locks over the brow
            _shape(d, [HP(.06 * side, .62), HP(.55 * side, .54),
                       HP(.36 * side, .86), HP(.12 * side, .80)], hair, ink,
                   max(1, lw - 1))
    elif style == "long":
        # a centre-parted fringe and two side locks: the front of a long-haired
        # figure is a frame, not a curtain, or the face gets erased
        _shape(d, [HP(-.98, .56), HP(-.44, .50), HP(0, .74), HP(.44, .50),
                   HP(.98, .56), HP(.98, .95), HP(-.98, .95)], hair, ink,
               max(1, lw - 1))
        for side in (-1, 1):
            _shape(d, [HP(.86 * side, .56), HP(1.06 * side, .30),
                       HP(.98 * side, -.85), HP(.66 * side, -.70),
                       HP(.74 * side, .10)], hair, ink, max(1, lw - 1))
    elif style == "twin":
        _shape(d, [HP(-.96, .54), HP(-.40, .50), HP(0, .72), HP(.40, .50),
                   HP(.96, .54), HP(.96, .94), HP(-.96, .94)], hair, ink,
               max(1, lw - 1))
    else:                                         # a swept fringe, not a headband:
        # an even zigzag between two parallel lines is what a hair band looks
        # like; a fringe is one mass that runs deeper on the side it sweeps from
        _shape(d, [HP(-.99, .30), HP(-.52, .46), HP(-.08, .28), HP(.46, .52),
                   HP(.99, .36), HP(.99, .98), HP(-.99, .98)], hair, ink,
               max(1, lw - 1))
    if f.get("goggles"):                            # pushed up on the forehead
        # high enough to clear the brow: laid across the middle of the skull the
        # strap and the lens rims ate the forehead skin and crowded the eyes,
        # which is a drawing fault the cast counter then reported as a lost head
        gy = head_c[1] - hry * .80
        d.line([(head_c[0] - hrx * 1.02, gy + hry * .20),
                (head_c[0] + hrx * 1.02, gy + hry * .20)], fill=shade,
               width=lw + 1)                        # the strap, not a hair band
        for side in (-1, 1):
            gx = head_c[0] + side * hrx * .46
            _blob(d, (gx, gy), hrx * .32, hry * .24, _rgb(pal, "steel"), ink,
                  max(1, lw - 1))                   # a rim with glass in it
            d.arc([gx - hrx * .24, gy - hry * .17, gx + hrx * .24,
                   gy + hry * .17], 200, 320, fill=paper, width=1)   # a glint
        d.line([(head_c[0] - hrx * .10, gy), (head_c[0] + hrx * .10, gy)],
               fill=ink, width=lw)                  # the bridge between lenses
    if f.get("mask"):                             # a fox mask worn tipped aside:
        # plate-shaped (wide at the temples, pointed at the snout) with two eye
        # slits, a red brow marking and a cord. A rectangle over one eye reads
        # as a censor bar, which is not an object anyone could put on their face
        mx, my = HP(1.32 * lit, .20)
        k = .062 * s
        plate = [(mx - k * .86 * lit, my + k * .50), (mx - k * .30 * lit,
                 my - k * .42), (mx + k * .40 * lit, my - k * .58),
                 (mx + k * .92 * lit, my - k * .06), (mx + k * .58 * lit,
                 my + k * .74), (mx - k * .26 * lit, my + k * .82)]
        _shape(d, plate, paper, ink, max(1, lw - 1), rim=rimc, lit=lit, roff=ro)
        for side in (-1, 1):                        # two eye slits
            ex = mx + k * (.16 + .40 * side) * lit
            d.line([(ex - k * .17, my + k * .06), (ex + k * .17, my - k * .04)],
                   fill=ink, width=max(1, lw - 1))
        d.line([(mx + k * .30 * lit, my - k * .50), (mx + k * .74 * lit,
                my - k * .18)], fill=_rgb(pal, "seal"), width=lw)   # brow mark
        d.polygon([(mx + k * .10 * lit, my + k * .44), (mx + k * .38 * lit,
                   my + k * .40), (mx + k * .22 * lit, my + k * .70)],
                  fill=_rgb(pal, "seal"))           # the snout tip
        d.line([(mx - k * .86 * lit, my + k * .50), (mx - k * 1.45 * lit,
                my - k * .10)], fill=ink, width=1)  # the cord into the hair

    # 6. the face: eyes with an iris and a highlight, brows and a mouth that
    # carry the expression, since a cast that all looks the same is a diagram
    expr = f.get("expression", "smile")
    eye_y = head_c[1] + hry * .06
    for side in (-1, 1):
        c = (head_c[0] + side * hrx * .44 + lit * hrx * .06, eye_y)
        rx, ry = .019 * s, .026 * s
        d.ellipse([c[0] - rx, c[1] - ry, c[0] + rx, c[1] + ry], fill=paper)
        d.ellipse([c[0] - rx * .62, c[1] - ry * .68, c[0] + rx * .62,
                   c[1] + ry * .78], fill=ink)
        d.ellipse([c[0] - rx * .2, c[1] - ry * .5, c[0] + rx * .34,
                   c[1] - ry * .06], fill=paper)
        d.line([(c[0] - rx * 1.15, c[1] - ry * 1.05), (c[0] + rx * 1.15,
                c[1] - ry * .85)], fill=ink, width=lw + 1)   # lash line
        brow = (c[0], c[1] - ry * 1.55)   # below the fringe chord, so it still shows
        tilt = .010 * s if expr == "hot" else .004 * s
        d.line([(brow[0] - rx * 1.2, brow[1] + (tilt if side == lit else -tilt)),
                (brow[0] + rx * 1.2, brow[1] - (tilt if side == lit else -tilt))],
               fill=hair, width=lw + 1)
    mouth = {
        "hot": [(P(-.022, .828), P(.022, .828), P(0, .800))],
        "smile": [(P(-.020, .828), P(.020, .828), P(0, .812))],
        "calm": [(P(-.014, .822), P(.014, .822), P(.014, .822))],
        "grin": [(P(-.028, .830), P(.028, .830), P(0, .806))],
    }[expr]
    for p0, p1, p2 in mouth:
        if expr in ("hot", "grin"):
            d.polygon([p0, p1, p2], fill=_rgb(pal, "accent_shade"), outline=ink,
                      width=lw)
        else:
            d.line([p0, p2, p1], fill=ink, width=lw)
    if expr == "smile":
        for side in (-1, 1):
            _blob(d, P(side * .052, .845), .014 * s, .008 * s, _rgb(pal, "flame"),
                  _rgb(pal, "flame"), 1)

    # 7. props are HELD: each one is anchored to a wrist from the arm pass, since
    # a lantern parked in mid-air reads as a layout fault, not as a lit object
    for acc in f.get("accessory", []):
        if acc == "sword":
            grip = wrists[-lit]
            p0 = (grip[0] - lit * .012 * s, grip[1] + .055 * s)
            p1 = (grip[0] + lit * .075 * s, grip[1] - .330 * s)
            _shape(d, _tapered(p0, p1, .016 * s, .008 * s), _rgb(pal, "steel"), ink, lw)
            d.line([(grip[0] - lit * .045 * s, grip[1] + .020 * s),
                    (grip[0] + lit * .045 * s, grip[1] - .005 * s)], fill=ink,
                   width=lw + 2)
        elif acc == "flame":
            c = (wrists[lit][0], wrists[lit][1] - .020 * s)   # it LICKS the knuckles
            # a triangle is a diagram of fire. Fire is a mass with a warded edge
            # that narrows to a point, leans with the hand, and is brightest
            # where the fuel is -- so: outline, inner core, then three sparks
            lean = lit * .012 * s
            body = [(c[0] - .030 * s, c[1] + .014 * s), (c[0] - .038 * s,
                    c[1] - .026 * s), (c[0] - .010 * s, c[1] - .040 * s),
                    (c[0] - .022 * s, c[1] - .072 * s), (c[0] + .002 * s,
                    c[1] - .056 * s), (c[0] + .010 * s + lean, c[1] - .104 * s),
                    (c[0] + .026 * s, c[1] - .052 * s), (c[0] + .040 * s,
                    c[1] - .020 * s), (c[0] + .028 * s, c[1] + .016 * s)]
            _shape(d, body, _rgb(pal, "flame"), ink, max(1, lw - 1))
            _shape(d, [(c[0] - .015 * s, c[1] + .006 * s), (c[0] + .017 * s,
                       c[1] + .006 * s), (c[0] + lean, c[1] - .050 * s)],
                   _rgb(pal, "light"), _rgb(pal, "light"), 1)
            for k in range(3):                      # sparks, thrown off the hand
                sx = c[0] + lit * (.05 + .03 * k) * s
                sy = c[1] - (.11 + .05 * k) * s
                d.polygon([(sx, sy), (sx + .010 * s, sy - .014 * s),
                           (sx - .006 * s, sy - .016 * s)], fill=_rgb(pal, "flame"))
        elif acc == "lantern":
            top = wrists[-lit]
            c = (top[0] - lit * .010 * s, top[1] + .105 * s)
            rg, rr = .040 * s, .064 * s
            d.line([(top[0], top[1]), (c[0], c[1] - rr - .016 * s)], fill=ink,
                   width=lw)
            # a lantern is a caged cylinder: caps top and bottom, a bulged body,
            # two ribs, a warm core. One filled disc reads as a coin
            _blob(d, c, rg * 1.30, rr * 1.22, _rgb(pal, "flame"),
                  _rgb(pal, "flame"), 1)            # the glow it throws
            _blob(d, c, rg, rr, _rgb(pal, "light"), ink, max(1, lw - 1))
            for yy in (-.62, .62):                  # the two wooden caps
                d.rectangle([c[0] - rg * .52, c[1] + rr * yy - .006 * s,
                             c[0] + rg * .52, c[1] + rr * yy + .006 * s],
                            fill=_rgb(pal, "seal"), outline=ink, width=1)
            for k in (-1, 1):                       # ribs that bow with the cage
                d.arc([c[0] + k * rg * .9 - rg * .34, c[1] - rr,
                       c[0] + k * rg * .9 + rg * .34, c[1] + rr],
                      300 if k < 0 else 240, 60 if k < 0 else 120, fill=ink,
                      width=1)
            d.line([(c[0] - rg * .96, c[1]), (c[0] + rg * .96, c[1])],
                   fill=_rgb(pal, "flame"), width=1)
            for k in range(3):                      # tassels under the base cap
                tx = c[0] + (k - 1) * rg * .30
                d.line([(tx, c[1] + rr * .62 + .006 * s),
                        (tx + lit * rg * .08, c[1] + rr * .62 + .036 * s)],
                       fill=_rgb(pal, "seal"), width=1)
    if f.get("companion"):                        # a small winged cat, far shoulder
        c = P(-.155 * lit, .795)
        r = .048 * s
        body = _rgb(pal, "cloth_white") if "cloth_white" in pal else paper
        for k in (-1, 1):                         # wings first, behind the body
            d.polygon([(c[0] - k * r * .3, c[1] - r * .2),
                       (c[0] - k * r * 1.45, c[1] - r * 1.05),
                       (c[0] - k * r * .95, c[1] + r * .35),
                       (c[0] - k * r * .4, c[1] + r * .1)], fill=body, outline=ink,
                      width=max(1, lw - 1))
        _blob(d, c, r, r * .74, body, ink, max(1, lw - 1))
        _blob(d, (c[0] + r * .52, c[1] - r * .92), r * .58, r * .54, body, ink,
              max(1, lw - 1))
        for k in (-1, 1):                         # ears, narrow and set on top
            d.polygon([(c[0] + r * .52 + k * r * .34, c[1] - r * 1.30),
                       (c[0] + r * .52 + k * r * .52, c[1] - r * 1.82),
                       (c[0] + r * .52 + k * r * .04, c[1] - r * 1.40)],
                      fill=body, outline=ink, width=1)
        d.point((c[0] + r * .38, c[1] - r * .92), fill=ink)
        d.point((c[0] + r * .70, c[1] - r * .92), fill=ink)
        d.line([(c[0] + r * .52, c[1] - r * .62), (c[0] + r * .52, c[1] - r * .46)],
               fill=ink, width=1)                 # muzzle
        d.line([(c[0] - r, c[1] + r * .2), (c[0] - r * 1.8, c[1] - r * .75)],
               fill=ink, width=lw)                # tail, curved up


# --- 7-8: tone, frame, emblem -------------------------------------------------

def _screentone(arr: np.ndarray, regions: list, pal: dict, w: int, h: int,
                 pitch: int, dot: float) -> np.ndarray:
    """A staggered dot screen whose radius follows a density field.

    Vectorised: every pixel knows its cell, its cell centre (odd rows offset by
    half a pitch, which is how a tone sheet actually looks) and the local
    density, so a dot appears wherever the distance to the centre falls under
    the density-scaled radius.
    """
    ys, xs = np.mgrid[0:h, 0:w]
    cell_y = ys // pitch
    stagger = (cell_y % 2) * pitch // 2
    cx = ((xs + stagger) // pitch) * pitch - stagger + pitch / 2
    cy = cell_y * pitch + pitch / 2
    dist = np.hypot(xs - cx, ys - cy)
    density = np.zeros((h, w), dtype=float)
    for reg in regions:
        x0, y0 = w * float(reg["at"][0]), h * float(reg["at"][1])
        rad = float(reg.get("radius", 0.3)) * max(w, h)
        fall = np.clip(1.0 - np.hypot(xs - x0, ys - y0) / rad, 0.0, 1.0) ** 2
        density = np.maximum(density, float(reg.get("level", 0.6)) * fall)
    radius = dot * pitch * np.sqrt(density)
    mask = (radius > 0.4) & (dist <= radius)
    arr[mask] = np.array(_rgb(pal, "tone"), dtype=float)
    return mask


def _title(d, w: int, h: int, spec: dict, pal: dict, fonts: list) -> None:
    band = float(spec["frame"].get("logo_band", 0.14)) * h
    ink = _rgb(pal, "ink")
    d.rectangle([0, 0, w, band], fill=_rgb(pal, "paper"))
    d.line([(0, band), (w, band)], fill=ink, width=max(2, int(h * 0.004)))
    size = int(band * float(spec["frame"].get("title_size", 0.42)))
    fnt = _font(fonts, size)
    text = str(spec["title_text"])
    box = d.textbbox((0, 0), text, font=fnt)
    tw, th = box[2] - box[0], box[3] - box[1]
    emblem = float(spec["frame"].get("emblem", 0.0))
    gap = band * 0.10
    total = tw + (band * emblem + gap if emblem else 0)
    x = int((w - total) / 2) - box[0]
    y = int(band * 0.46 - th / 2) - box[1]
    if emblem:                                    # an original mark, drawn not quoted
        _emblem(d, x + band * emblem * .5, band * .46, band * emblem * .5, pal, ink)
        x += int(band * emblem + gap)
    off = max(2, int(size * 0.03))
    d.text((x + off, y + off), text, font=fnt, fill=_rgb(pal, "accent_shade"))
    d.text((x, y), text, font=fnt, fill=ink)
    if spec["frame"].get("subtitle"):
        ssize = max(11, int(size * 0.30))
        sfnt = _font(fonts, ssize)
        b2 = d.textbbox((0, 0), str(spec["frame"]["subtitle"]), font=sfnt)
        d.text((int((w - (b2[2] - b2[0])) / 2) - b2[0], int(band * 0.80) - b2[3]),
               str(spec["frame"]["subtitle"]), font=sfnt, fill=_rgb(pal, "tone"))


def _emblem(d, cx: float, cy: float, r: float, pal: dict, ink) -> None:
    """A ring with a flame inside it: the guild's own mark, geometry only."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ink, width=max(2, int(r * .12)))
    d.polygon([(cx - r * .38, cy + r * .35), (cx + r * .38, cy + r * .35),
               (cx + r * .12, cy - r * .30), (cx + r * .30, cy - r * .10),
               (cx - r * .10, cy - r * .72)], fill=_rgb(pal, "flame"), outline=ink,
              width=max(1, int(r * .08)))


def _font(fonts: list, size: int):
    for path in fonts:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    raise IllusError("no declared font resolved; a title in a substitute face "
                     "would not be the artifact the spec asked for")


# --- measurement -------------------------------------------------------------

def _dither_free_edges(lum: np.ndarray) -> np.ndarray:
    """Local luma change with the ordered dither removed and the edges kept.

    5x5 median, then the same 1-pixel forward difference the rest of the
    measurement uses. A Bayer 4x4 screen alternates inside the window, so the
    median lands on whichever of the two palette colours holds the neighbourhood's
    middle -- the alternation cancels and a gradient becomes flat. A drawn edge is
    a step function: the median shifts it by at most two pixels and keeps its
    height, so it still produces one large difference.
    """
    m = ndimage.median_filter(lum, size=5, mode="nearest")
    gx = np.abs(np.diff(m, axis=1, prepend=m[:, :1]))
    gy = np.abs(np.diff(m, axis=0, prepend=m[:1]))
    return gx + gy


def _measure(arr: np.ndarray, spec: dict, pal: dict, tone_mask: np.ndarray,
             declared: list) -> dict:
    h, w, _ = arr.shape
    flat = arr.reshape(-1, 3)
    present = {tuple(c) for c in np.unique(flat, axis=0)}
    exact = np.isin(flat, np.array(declared)).all(axis=1)
    lum = arr @ np.array([0.2126, 0.7152, 0.0722])
    gx = np.abs(np.diff(lum, axis=1, prepend=lum[:, :1]))
    gy = np.abs(np.diff(lum, axis=0, prepend=lum[:1]))
    edges = float(((gx + gy) > 24).mean() * 100)
    # the cast is counted by FACE, not by silhouette: overlapping bodies merge
    # into one blob, and the speed lines are ink everywhere, so a silhouette
    # count would measure spacing and linework noise rather than a cast
    band = int(float(spec["frame"].get("logo_band", 0.14)) * h)
    zone = np.zeros((h, w), dtype=bool)
    zone[int(h * 0.20):int(h * 0.62), :] = True
    skin_rgb = np.array(_rgb(pal, "skin"), dtype=float)
    faces = (np.abs(arr - skin_rgb).sum(axis=-1) < 30) & zone
    lbl, n = ndimage.label(ndimage.binary_dilation(faces, iterations=2))
    # a head is a COMPACT skin mass that contains a PAPER-WHITE SPOT well inside
    # its own outline. In this grammar the only white anything draws on skin is
    # the eye: the sclera and its highlight, inside an iris, inside a face. A hand
    # has no white in it, a sleeve has no white in it, and a bent arm that closes
    # a gap at the hip gets cloth there, not paper. Every earlier variant of this
    # counter was measuring something else: an area threshold scored 17 for a cast
    # of 5 (hands), an erosion test scored 14 (arm rings, because fill_holes hands
    # them the cloth behind), an enclosed-hole test scored 2 (an eye sits against
    # the cheek line, so it is not enclosed), and a fixed erosion radius erased the
    # small back-row heads outright -- so the strip scales with the mass
    paper_rgb = np.array(_rgb(pal, "paper"), dtype=float)
    white = np.abs(arr - paper_rgb).sum(axis=-1) < 30
    figures = 0
    if n:
        objects = ndimage.find_objects(lbl)
        for ids, size in enumerate(ndimage.sum(np.ones_like(lbl), lbl,
                                               range(1, n + 1)), start=1):
            if size < 0.00012 * w * h:      # floor is head-scale, not hand-scale:
                continue                    # a distant skull is smaller than a
                                            # near hand, and must still be counted
            sl = objects[ids - 1]
            tall = sl[0].stop - sl[0].start
            wide = max(1, sl[1].stop - sl[1].start)
            if tall > 1.5 * wide:
                continue                          # a limb is elongated, a skull is not
            core = ndimage.binary_erosion(
                ndimage.binary_fill_holes(lbl[sl] == ids),
                iterations=max(2, int(round(0.10 * min(tall, wide)))))
            if int((core & white[sl]).sum()) >= 2:
                figures += 1
    # negative space is the share of the sky band that carries NO mark, which is
    # a statement about the composition. Percentile-relative-to-itself was a
    # tautology: pick the 55th percentile of a band and count what sits above it
    # and the answer is ~45% for every sheet ever drawn, green and hollow.
    #
    # The straight luma gradient was worse than tautological: it measured the
    # quantiser. The sheet is Bayer-dithered before the nearest-colour snap, so a
    # smooth sky ramp alternates between two palette colours every few pixels and
    # reads as busy, while a big flat cloud bank suppresses the alternation and
    # reads as empty. Measured on the dusk sheet -- two enormous clouds took the
    # number 45.9 -> 75.6 (drawing into the sky made it "emptier"), and deleting
    # every cloud and the sun took it 45.9 -> 44.7. A rule whose value goes UP when
    # you paint over it cannot be a ceiling on emptiness.
    #
    # So busyness is judged on a median-filtered luma: a 5x5 median is the
    # textbook removal for a 4x4 alternating pattern and it preserves hard edges,
    # which is the whole difference between a dither and a mark.
    busy = ndimage.maximum_filter(_dither_free_edges(lum) > 24, size=13).astype(np.uint8)
    negative = float((busy[band: int(h * 0.42)] == 0).mean() * 100)
    title_ink = float((lum[:band] < 120).mean() * 100)
    spread = float(np.percentile(lum, 97) - np.percentile(lum, 3))
    return {
        "width": w, "height": h,
        "palette_distinct_colors": len(present),
        "palette_undeclared_colors": len(present - {tuple(c) for c in declared}),
        "palette_declared_colors": len(declared),
        "palette_exact_pct": float(exact.mean() * 100),
        "screentone_dot_pct": float(tone_mask.mean() * 100),
        "edge_density_pct": edges,
        "figure_count": figures,
        "sky_negative_pct": negative,
        "title_ink_pct": title_ink,
        "luma_spread": spread,
    }


# --- the route ---------------------------------------------------------------

def _refuse(spec: dict) -> None:
    pal = spec.get("palette") or {}
    need = ("paper", "ink", "tone", "rim", "light", "shadow", "accent_shade",
            "steel", "flame", "seal", "skin", "wall", "structure")
    missing = [k for k in need if k not in pal]
    if missing:
        raise IllusError(f"palette is missing colours the chain needs: "
                         f"{', '.join(missing)}")
    seen: dict[tuple, str] = {}
    for k, v in pal.items():
        rgb = tuple(spec_mod.parse_hex(v))
        if rgb in seen:
            # raised text stays ASCII: cp1252 consoles would turn the reason for
            # the refusal into a UnicodeEncodeError
            raise IllusError(
                f"palette colours must be distinct: '{k}' and '{seen[rgb]}' are "
                f"both {rgb} - the palette gates count pixels per colour, so a "
                f"collapsed palette measures nothing")
        seen[rgb] = k
    if not spec.get("figures"):
        raise IllusError("figures is empty: an ensemble portrait with no "
                         "ensemble has a figure_count of zero by construction")
    for i, f in enumerate(spec["figures"]):
        for key in ("hair", "garment"):
            if key not in f:
                raise IllusError(f"figures[{i}] has no '{key}' palette key")
            if f[key] not in pal:
                raise IllusError(f"figures[{i}].{key}={f[key]!r} is not a palette "
                                 f"colour (it is a colour key, not a style)")
    if int(spec.get("tone", {}).get("pitch", 7)) < 3:
        raise IllusError(f"tone.pitch must be >= 3 px: at "
                         f"{spec['tone']['pitch']} the dot screen is below one "
                         f"pixel and the screentone gate would measure noise")
    if not str(spec.get("title_text", "")).strip():
        raise IllusError("title_text is empty: the logo band would be unprintable "
                         "and title_ink_pct would measure the border only")


def render(spec: dict, out_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Paint the stack and return (quantised uint8 array, tone dot mask)."""
    w, h = int(spec["width"]), int(spec["height"])
    pal = spec["palette"]
    arr = np.zeros((h, w, 3), dtype=float)
    _sky(arr, spec["backdrop"]["stops"], pal)
    # the sheet is opened FROM the gradient rather than drawn on before it: PIL
    # does not alias the array it wraps, so strokes made on an image built from
    # a black buffer would be discarded when the array is re-read (audit F5)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)

    bd = spec["backdrop"]
    # the energy lines go down FIRST, so the ridges, the floor and the set
    # dressings mask their lower halves: lines that survive only in the sky read
    # as momentum, lines that cross the whole sheet read as a printing fault
    sp = spec.get("speed_lines")
    if sp:
        _speed_lines(d, w, h, sp["focus"], sp["count"], pal, int(spec["seed"]) + 7,
                     float(sp.get("skip", 0.12)), sp.get("wedge"))
    for cl in bd.get("clouds", []):
        _cloud(d, w * float(cl["at"][0]), h * float(cl["at"][1]),
               float(cl["scale"]) * h, [tuple(l) for l in cl["lobes"]],
               _rgb(pal, cl.get("shade", "shadow")), _rgb(pal, cl.get("lit", "paper")),
               _rgb(pal, cl["edge"]) if cl.get("edge") else None,
               _rgb(pal, cl["mid"]) if cl.get("mid") else None,
               cl.get("band", "bottom"))
    sun = bd.get("sun")
    if sun:
        r = float(sun["radius"]) * h
        sx, sy = w * float(sun["at"][0]), h * float(sun["at"][1])
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=_rgb(pal, sun["color"]))
    for ridge in bd.get("ridges", []):
        _ridge(d, w, h, float(ridge["at"]), float(ridge["amp"]),
               float(ridge["freq"]), _rgb(pal, ridge["color"]),
               int(spec["seed"]) + int(ridge.get("salt", 0)),
               float(ridge.get("phase", 0.0)))
    _floor(d, w, h, pal, spec)
    for item in spec.get("set", []):
        _set_item(d, w, h, item, pal)
    for f in sorted(spec["figures"], key=lambda x: float(x.get("depth", 0.5)),
                    reverse=True):
        _figure(d, f, pal, w, h)
    _title(d, w, h, spec, pal, spec["_fonts"])
    fr = float(spec["frame"].get("border", 0.012)) * min(w, h)
    d.rectangle([0, 0, w - 1, h - 1], outline=_rgb(pal, "ink"), width=max(2, int(fr)))
    d.rectangle([fr, fr, w - 1 - fr, h - 1 - fr], outline=_rgb(pal, "paper"),
                width=max(2, int(fr * .6)))

    arr = np.asarray(img, dtype=float)
    tone_mask = _screentone(arr, spec["tone"]["regions"], pal, w, h,
                            int(spec["tone"]["pitch"]), float(spec["tone"]["dot"]))
    # 9: snap onto the declared palette with an ordered dither, so a gradient
    # survives as a screen of two colours instead of dying as ten muddy steps
    declared = [tuple(spec_mod.parse_hex(pal[k])) for k in spec["palette_order"]]
    lut = np.array(declared, dtype=float)
    noise = (_bayer_noise(w, h) - 0.5) * float(spec["tone"].get("dither", 26))
    idx = _nearest(arr + noise[..., None], lut)
    return lut[idx].astype(np.uint8), tone_mask


def _bayer_noise(w: int, h: int) -> np.ndarray:
    return np.tile(_BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w]


def _nearest(q: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Nearest palette index per pixel, chunked so the distance cube stays small."""
    flat = q.reshape(-1, 3)
    out = np.empty(flat.shape[0], dtype=np.int32)
    for lo in range(0, flat.shape[0], 65536):
        chunk = flat[lo:lo + 65536]
        out[lo:lo + chunk.shape[0]] = (((chunk[:, None, :] - lut[None, :, :])
                                        ** 2).sum(axis=-1)).argmin(axis=1)
    return out.reshape(q.shape[:2])


def run(spec_path: Path | str, out_dir: Path | str, keep: bool = False) -> dict:
    spec = spec_mod.load_raw(spec_path)
    _refuse(spec)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pal = spec["palette"]
    declared = [tuple(spec_mod.parse_hex(pal[k])) for k in spec["palette_order"]]
    spec["_fonts"] = _resolve_fonts(spec)

    art, tone_mask = render(spec, out_dir)
    # determinism: the same spec rendered twice must agree bit for bit
    art2, _ = render(spec, out_dir)
    deterministic = bool(np.array_equal(art, art2))

    m = _measure(art, spec, pal, tone_mask, declared)
    m["deterministic"] = deterministic
    report = validate.run_acceptance(spec["acceptance"], m)
    report["measured"] = m
    report["palette"] = {k: pal[k] for k in spec["palette_order"]}
    cli.write_report(out_dir, report)

    png = out_dir / "print.png"
    Image.fromarray(art).save(png)

    extra = {"fonts": [{"path": str(p), "sha256": provenance.sha256_file(p),
                        "licence": str((spec.get("font") or {}).get("licence",
                                                                    "unverified"))}
                       for p in spec["_fonts"]]}
    manifest = provenance.build_record(
        spec_path=str(spec_path),
        spec_dict={k: v for k, v in spec.items() if k != "_fonts"},
        content_hash=provenance.sha256_bytes(art.tobytes()),
        artifact_hashes={"print.png": provenance.sha256_file(png)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["print.png", "report.json", "manifest.json"],
        notes=spec.get("assumptions", []), pipeline="vcac-illustration/0.1",
        extra=extra)
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def _resolve_fonts(spec: dict) -> list:
    got = [Path(p) for p in (spec.get("font") or {}).get("paths", [])
           if Path(p).is_file()]
    if not got:
        raise IllusError("title font not found: install Noto Sans SC or fetch the "
                         "OFL script face (declared: "
                         f"{(spec.get('font') or {}).get('paths')})")
    return got


def main(argv=None) -> int:
    a = cli.parse_args("vcac illustration route (群像插画)", argv)
    spec = spec_mod.load_raw(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec["id"]))
    m = r["report"]["measured"]
    return cli.finish("illustration", r, summaries=[
        f"{spec['id']} -> {r['out_dir']}",
        f"{m['width']}x{m['height']} colours={m['palette_distinct_colors']}/"
        f"{m['palette_declared_colors']} tone={m['screentone_dot_pct']:.2f}% "
        f"edges={m['edge_density_pct']:.1f}% figures={m['figure_count']} "
        f"sky={m['sky_negative_pct']:.0f}% title={m['title_ink_pct']:.1f}% "
        f"spread={m['luma_spread']:.0f}"])


if __name__ == "__main__":
    raise SystemExit(main())
