"""Manga inking route — the brush, not the pencil (docs/styles.md §2 §4).

Why this file exists instead of more parameters in ``illustration_sample``: that
route drew every line the same width from first point to last, put concentric
circles where an eye belongs, and built hair out of flat polygons. All of it
survived its gates because not one of the gates asks about *line*, and the sheet
read as clip art. What makes a page look hand-inked is a short, hard list of
mechanisms, and this module implements exactly those:

  1. a path DSL (M/L/C/Q/Z, bezier flattened, arc-length re-laid) so shapes are
     authored as curves rather than as chains of straight segments;
  2. a nib: a polyline plus a pressure profile (flat / ramp / wedge / taper)
     becomes a ribbon whose width varies ALONG the stroke — thick where the pen
     is pushed, needle-thin where it is lifted, pointed at the end of a flick.
     That is the single mechanism that separates inked art from a vector
     outline, so it gets its own gate (``ink weight spread``);
  3. the eye as a grammar: upper lash as a solid wedge, iris as a screened
     gradient, a punched paper highlight, a hairline lower lash, corner flicks;
  4. 网点 as a real dot screen on one sheet-wide lattice, punched only inside an
     authored shadow region — never as a wash over the whole page;
  5. 集中線: radial lines that taper into their focus.

Everything is drawn on a canvas ``supersample`` times larger and reduced with
Lanczos: a tapered line ends at sub-pixel width, and without the extra
resolution the nib's whole point is thrown away by rounding.

Division of labour, deliberately: the code owns the brush, the *design* is
hand-authored in the spec — every facial point, hair clump and fold is a
coordinate somebody chose. The seed drives the nib's wobble and the tone
lattice phase; it never decides where a face goes.

Honest ceiling (docs/styles.md §0): this reaches an inked vector manga page —
correct weight, correct eye grammar, correct tone. It is not a 原稿. The last
fifth of a real page is drawing skill: varying weight *within* one stroke to
describe volume. Here that variation is an authored profile, not a hand's
decision made while looking at the shape underneath it.
"""
from __future__ import annotations

import math
import re
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

from . import cli, ffmpeg, provenance, spec as spec_mod, validate
# the ordered dither and the chunked nearest-index lookup are arithmetic, not
# style: two copies could drift, and the palette gate depends on every route
# measuring colour the same way
from .illustration_sample import _bayer_noise, _nearest

_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
_CMD = re.compile(r"([MLCQZ])([^MLCQZ]*)")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")

#: the profiles this brush can lay down. A typo in a spec must NOT fall back to a
#: constant width: a constant width is the exact fault this route exists to kill,
#: so an unknown profile is refused rather than drawn quietly wrong.
PROFILES = ("flat", "ramp", "wedge", "taper")

#: the primitive vocabulary. Four kinds is the whole engine; anything a page
#: needs is one of these placed and weighted differently.
KINDS = ("ink", "mass", "tone", "grad", "burst", "title", "sheet")

#: colour-bearing keys, walked by :func:`_refuse` so a misspelled palette key
#: fails at load with the name of the key instead of rendering a wrong sheet
_COLOR_KEYS = ("fill", "line", "color", "from", "to", "shade", "ground")


class MangaError(ValueError):
    """The spec asks for something this brush cannot deliver."""


def _rgb(pal: dict, key: str) -> tuple[int, int, int]:
    return tuple(spec_mod.parse_hex(pal[key]))


# --- transforms ---------------------------------------------------------------

def _mul(A, B):
    """Compose two 2x3 affines (apply B, then A): a tuple ``(a,b,c,d,e,f)`` means
    ``x' = a*x + c*y + e, y' = b*x + d*y + f``, i.e. the matrix ``[[a,c],[b,d]]``,
    so the tuple stores the two COLUMNS and not the two rows.

    That distinction is the whole reason this function is written the way it is.
    The previous version multiplied as though the tuple were row-major, which is
    invisible for the cases that come first -- a translation on either side, or
    two rotations, or a uniform scale -- and catastrophic for the one case every
    tilted part uses: ROTATION COMPOSED WITH A NON-UNIFORM SCALE. Under the wrong
    product the 2x2 block came back transposed, so ``sx`` and ``sy`` landed on
    each other's axis: a lock 74 long and 13 wide, tilted 90 degrees to hang
    straight down, was laid down as a bar 13 tall and 74 wide. Every hair on this
    page therefore grew SIDEWAYS out of the head like a fin, and the author spent
    nine render rounds inventing geometry rules to compensate for a transpose --
    including the rule that "``sy`` becomes the horizontal root under a 90 deg
    tilt", which was never a property of the brush at all.
    """
    a1, b1, c1, d1, e1, f1 = A
    a2, b2, c2, d2, e2, f2 = B
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def _T(x=0.0, y=0.0):
    return (1.0, 0.0, 0.0, 1.0, float(x), float(y))


def _R(deg):
    r = math.radians(float(deg))
    return (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0.0, 0.0)


def _D(sx, sy=None):
    return (float(sx), 0.0, 0.0, float(sx if sy is None else sy), 0.0, 0.0)


def _tp(M, pts):
    a, b, c, d, e, f = M
    return [(a * x + c * y + e, b * x + d * y + f) for x, y in pts]


# --- 1. the path DSL ----------------------------------------------------------

def _cubic(p0, c1, c2, p3, n):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1.0 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0]
                    + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1]
                    + t ** 3 * p3[1]))
    return out


def _quad(p0, c1, p2, n):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1.0 - t
        out.append((u * u * p0[0] + 2 * u * t * c1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * c1[1] + t * t * p2[1]))
    return out


def path_to_polys(d: str, steps: int = 14) -> list:
    """An SVG-ish path string -> a list of polylines in the path's own units.

    Absolute commands only, with implicit repeats, so one curve costs about as
    many characters as it needs. Beziers flatten at a fixed t-step; the nib
    re-lays the result by arc length anyway, so ``steps`` only has to be dense
    enough not to cut the corners of the tightest turn in the page.
    """
    polys: list = []
    cur: list = []
    pen = (0.0, 0.0)
    for cmd, arg in _CMD.findall(d):
        v = [float(x) for x in _NUM.findall(arg)]
        if cmd == "M":
            if len(cur) > 1:
                polys.append(cur)
            pen = (v[0], v[1])
            cur = [pen]
            for i in range(2, len(v) - 1, 2):          # implicit L after M
                pen = (v[i], v[i + 1])
                cur.append(pen)
        elif cmd == "L":
            for i in range(0, len(v) - 1, 2):
                pen = (v[i], v[i + 1])
                cur.append(pen)
        elif cmd == "C":
            for i in range(0, len(v) - 1, 6):
                c1 = (v[i], v[i + 1])
                c2 = (v[i + 2], v[i + 3])
                p3 = (v[i + 4], v[i + 5])
                cur.extend(_cubic(pen, c1, c2, p3, steps))
                pen = p3
        elif cmd == "Q":
            for i in range(0, len(v) - 1, 4):
                c1 = (v[i], v[i + 1])
                p2 = (v[i + 2], v[i + 3])
                cur.extend(_quad(pen, c1, p2, steps))
                pen = p2
        elif cmd == "Z":
            if cur and math.dist(cur[-1], cur[0]) > 1e-9:
                cur.append(cur[0])
    if len(cur) > 1:
        polys.append(cur)
    if not polys:
        raise MangaError(f"path has no drawable segment: {d[:48]!r}")
    return polys


def _mirror(polys, axis: float, ring: bool) -> list:
    """Mirror about a vertical line in the path's own units.

    ``ring`` joins a half to its mirror as one closed outline — a face is
    authored as its near half and mirrored, which halves the coordinates someone
    has to place and keeps the two halves genuinely symmetrical. Without it the
    mirror stays a separate stroke, which is what a matched pair of brows wants.
    """
    mir = [[(2.0 * axis - x, y) for x, y in p] for p in polys]
    if ring:
        return [polys[0] + mir[0][::-1][1:]] + polys[1:]
    return polys + [p[::-1] for p in mir]


def _resample(pts, step: float):
    """Relay a polyline at uniform arc length, so pressure is sampled by
    distance travelled and not by how the author happened to split the curve."""
    if len(pts) < 2:
        return list(pts)
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg) or 1e-6
    n = max(2, int(round(total / max(step, 1e-6))))
    out = [pts[0]]
    acc = 0.0
    j = 0
    for k in range(1, n):
        want = total * k / n
        while j < len(seg) - 2 and acc + seg[j] < want:
            acc += seg[j]
            j += 1
        if seg[j] <= 0:
            continue
        f = min(1.0, max(0.0, (want - acc) / seg[j]))
        a, b = pts[j], pts[j + 1]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    out.append(pts[-1])
    return out


# --- 2. the nib ---------------------------------------------------------------

def _pressure(w, n: int, mul: float, key: str, jitter: float) -> list:
    """Half-widths along a stroke, from a pressure profile.

    A profile is what a hand does to a pen: ``taper`` enters and leaves at a
    point, ``wedge`` is dragged onto its corner (an upper lash, a hair flick),
    ``ramp`` is a steady press or release (a line thickening into the shadow),
    ``flat`` is the mechanical pencil, kept only where a ruler really is used.
    """
    if isinstance(w, (int, float)):
        p = {"profile": "flat", "a": float(w)}
    elif isinstance(w, (list, tuple)):
        p = {"profile": "ramp", "a": float(w[0]), "b": float(w[1])}
    elif isinstance(w, dict):
        p = dict(w)
    else:
        raise MangaError(f"nib width must be a number, a pair or a mapping: {w!r}")
    prof = str(p.get("profile", "taper"))
    if prof not in PROFILES:
        raise MangaError(f"unknown nib profile {prof!r}: this brush lays "
                         f"{', '.join(PROFILES)} and nothing else")
    a = float(p.get("a", p.get("w", 1.6)))
    b = float(p.get("b", p.get("peak", a)))
    peak = min(0.95, max(0.05, float(p.get("peak", 0.5))))
    q = float(p.get("p", 1.0))
    crc = zlib.crc32(f"{key}|{prof}|{a}|{b}|{q}".encode("utf-8")) & 0xFFFFFFFF
    out = []
    for i in range(n):
        f = i / (n - 1) if n > 1 else 0.0
        if prof == "flat":
            v = a
        elif prof == "ramp":
            v = a + (b - a) * f
        elif prof == "wedge":
            v = a + (b - a) * (f ** q)
        else:
            t = min(f / peak, (1.0 - f) / (1.0 - peak))
            v = a + (b - a) * (t ** q)
        if jitter:                          # the pen skips a little on the paper
            k1, k2 = 2 + crc % 3, 6 + ((crc >> 8) % 5)
            ph1, ph2 = (crc % 97) / 97.0, (((crc >> 13) % 71) / 71.0)
            v *= 1.0 + jitter * (0.62 * math.sin(2 * math.pi * (k1 * f + ph1))
                                 + 0.38 * math.sin(2 * math.pi * (k2 * f + ph2)))
        out.append(max(0.04, 0.5 * v * mul))
    return out


def _normals(p):
    n = len(p)
    out = []
    for i in range(n):
        ax, ay = p[max(0, i - 1)]
        bx, by = p[min(n - 1, i + 1)]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1.0
        out.append((-dy / L, dx / L))
    return out


def _stroke(d, p, hw, colour) -> None:
    """Lay the ribbon as a chain of shared-edge quads.

    One self-crossing polygon per stroke was the first attempt and it is wrong
    twice over: a closed outline's ribbon is an annulus, and Pillow fills a
    crossing polygon with a blob at the crossing; and a wide stroke on a tight
    curve crosses itself on the inside whatever the winding rule. Quads union
    instead of crossing, so both cases come out as ink.
    """
    if len(p) < 2:
        return
    nx = _normals(p)
    left = [(x + m[0] * h, y + m[1] * h) for (x, y), m, h in zip(p, nx, hw)]
    right = [(x - m[0] * h, y - m[1] * h) for (x, y), m, h in zip(p, nx, hw)]
    for i in range(len(p) - 1):
        d.polygon([left[i], left[i + 1], right[i + 1], right[i]], fill=colour)


# --- 3. clipping: tone and ramp live inside an authored region ----------------

def _bbox(polys):
    xs = [x for p in polys for x, _ in p]
    ys = [y for p in polys for _, y in p]
    return min(xs), min(ys), max(xs), max(ys)


def _clip(img, polys, pad: int = 2):
    """A mask of the union of ``polys``, cropped to its own bounding box so a
    screen over an eye costs an eye and not a page."""
    x0, y0, x1, y1 = _bbox(polys)
    box = (max(0, int(math.floor(x0)) - pad), max(0, int(math.floor(y0)) - pad),
           int(math.ceil(x1)) + pad, int(math.ceil(y1)) + pad)
    bw, bh = box[2] - box[0], box[3] - box[1]
    if bw < 1 or bh < 1:
        return None, box
    m = Image.new("L", (bw, bh), 0)
    md = ImageDraw.Draw(m)
    for p in polys:
        md.polygon([(x - box[0], y - box[1]) for x, y in p], fill=255)
    return m, box


def _screen(d, img, polys, colour, level: float, pitch: float, phase,
           rmax: float = 0.5) -> None:
    """网点: a staggered dot screen whose dot radius carries the density.

    The mechanism of tone paper, vectorised. One lattice (``phase``) is shared by
    the whole sheet so neighbouring regions' dots stay on the same grid, which is
    what makes them read as paper instead of as a pattern pasted on; only the
    authored region is punched. ``level`` 1.0 at rmax 0.5 is a solid, so a shadow
    can walk from nothing to full without the pitch changing under it.
    """
    m, box = _clip(img, polys)
    if m is None:
        return
    arr = np.asarray(m)
    r = rmax * pitch * math.sqrt(max(0.0, min(1.0, level)))
    if r < 0.30:
        return
    x0, y0, x1, y1 = _bbox(polys)
    bx0, by0 = box[0], box[1]
    i0 = max(0, int(math.floor((max(0.0, y0) - phase[1]) / pitch)) - 1)
    j0 = max(0, int(math.floor((max(0.0, x0) - phase[0]) / pitch)) - 1)
    i1 = int(math.ceil(y1 / pitch)) + 2
    j1 = int(math.ceil(x1 / pitch)) + 2
    mw, mh = arr.shape[1], arr.shape[0]
    for i in range(i0, i1):
        cy = phase[1] + i * pitch + (0.5 * pitch if i % 2 else 0.0)
        iy = int(round(cy)) - by0
        if iy < 0 or iy >= mh:
            continue
        row = arr[iy]
        for j in range(j0, j1):
            cx = phase[0] + j * pitch
            ix = int(round(cx)) - bx0
            if 0 <= ix < mw and row[ix] > 127:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour)


def _grad(img, polys, c0, c1) -> None:
    """A vertical ramp inside an authored region, left soft on purpose: the
    sheet-wide ordered dither turns it into a screened gradient, which is how a
    tonal ramp is actually printed, and how an iris gets its depth."""
    m, box = _clip(img, polys)
    if m is None:
        return
    bw, bh = box[2] - box[0], box[3] - box[1]
    t = np.linspace(0.0, 1.0, bh)[:, None]
    ramp = np.array(c0, dtype=float) * (1 - t) + np.array(c1, dtype=float) * t
    tile = np.repeat(ramp[:, None, :], bw, axis=1)
    img.paste(Image.fromarray(np.clip(tile, 0, 255).astype(np.uint8)), box[:2], m)


# --- 4. primitives ------------------------------------------------------------

def _paint_one(d, img, poly, prim, ctx, spec, pal) -> None:
    """Ink one polyline under the current transform, with the nib the prim asks
    for. Widths are named in print pixels and scaled only by the sheet factor and
    the figure's own pen multiplier, so a line weight means the same thing
    everywhere in the page and still thins with distance."""
    step = float(spec["nib"].get("resample", 3.0)) * ctx["S"]
    q = _resample(poly, step)
    hw = _pressure(prim.get("w", 1.6), len(q), ctx["nib"] * ctx["S"], str(prim.get("d")),
                   float(spec["nib"].get("jitter", 0.0)))
    _stroke(d, q, hw, ctx["line"])


def _prim(d, img, prim, M, ctx, spec, pal):
    """Paint one primitive under transform ``M``.

    ``use`` pulls a template out of the spec and puts it down at its own
    place/scale/tilt/mirror, which is how one authored eye serves five faces at
    five different weights; any nib or colour the call site names overrides the
    template's, so the call site is where the pen is chosen.

    Two mirrorings, and conflating them put a face cross-eyed: ``mx`` reverses
    the part's LONG axis -- which way it faces, so an eye's outer corner moves to
    the other side -- while ``flip`` reverses the axis ACROSS it, which way a
    lock curls. A clump wants ``flip``, a face part wants ``mx``, and only ``mx``
    mirrors the direction a shift is named in.
    """
    if "use" in prim:
        name = str(prim["use"])
        tpl = ctx["templates"].get(name)
        if tpl is None:
            raise MangaError(f"unknown template {name!r}: this route places parts "
                             f"somebody drew, and the spec defines "
                             f"{sorted(ctx['templates'])}")
        at = prim.get("at", [0.0, 0.0])
        T = _T(float(at[0]), float(at[1]))
        if prim.get("tilt"):
            T = _mul(T, _R(float(prim["tilt"])))
        sx = float(prim.get("sx", prim.get("s", 1.0)))
        sy = float(prim.get("sy", sx))
        mx = bool(prim.get("mx"))
        T = _mul(T, _D(-sx if mx else sx, -sy if prim.get("flip") else sy))
        if "d" in prim:
            # a call-site `d` would be dropped by the `sub` filter below, so the
            # author would watch a template render where their own curve was asked
            # for -- the loudest possible failure for a silent one
            raise MangaError(f"`use: {name}` with `d`: a call site places a "
                             f"template, it does not redraw it; put the curve in "
                             f"templates: {name}")
        sub = {k: v for k, v in prim.items()
               if k not in ("use", "at", "sx", "sy", "s", "tilt", "flip", "mx", "d",
                            "kind", "shift")}
        shift = prim.get("shift") or {}
        fx = -1.0 if mx else 1.0
        for tp in tpl:
            q = dict(tp)
            q.update(sub)
            s = shift.get(str(tp.get("tag", "")))
            if s:                       # nudge one tagged group inside the template
                # an x-mirrored part mirrors its space, so a shift named in face
                # space has to be un-mirrored or the two eyes of one face look in
                # opposite directions -- which is exactly what they did, because
                # the page had used `flip` as if it meant `mx`
                qa = list(q.get("at", [0.0, 0.0]))
                q["at"] = [qa[0] + fx * float(s[0]), qa[1] + float(s[1])]
            _prim(d, img, q, _mul(M, T), ctx, spec, pal)
        return

    if "d" not in prim:
        raise MangaError(f"primitive has neither `use` nor `d`: {prim}")
    kind = str(prim.get("kind", "ink"))
    polys = path_to_polys(str(prim["d"]))
    if prim.get("mirror"):
        polys = _mirror(polys, float(prim.get("axis", 0.0)),
                        ring=kind in ("mass", "tone", "grad"))
    if prim.get("at"):        # `at` on an ordinary prim offsets its own path, in
        M = _mul(M, _T(float(prim["at"][0]), float(prim["at"][1])))   # template units
    polys = [_tp(M, p) for p in polys]
    ctx = dict(ctx, line=_rgb(pal, str(prim.get("line") or prim.get("color") or "ink")))

    if kind == "ink":
        for p in polys:
            _paint_one(d, img, p, prim, ctx, spec, pal)
        return
    if kind == "mass":
        if prim.get("fill"):
            cf = _rgb(pal, str(prim["fill"]))
            for p in polys:
                d.polygon(p, fill=cf)
        if prim.get("line", True):
            for p in polys:
                _paint_one(d, img, p, prim, ctx, spec, pal)
        sc = prim.get("screen")
        if sc:
            _screen(d, img, polys, _rgb(pal, str(sc.get("color", "tone"))),
                    float(sc["level"]), float(sc.get("pitch", 1.0)) * ctx["pitch"],
                    ctx["phase"])
        return
    if kind == "tone":
        _screen(d, img, polys, ctx["line"], float(prim.get("level", 0.5)),
                float(prim.get("pitch", 1.0)) * ctx["pitch"], ctx["phase"])
        return
    if kind == "grad":
        _grad(img, polys, _rgb(pal, str(prim["from"])), _rgb(pal, str(prim["to"])))
        if prim.get("line", True):
            for p in polys:
                _paint_one(d, img, p, prim, ctx, spec, pal)
        return
    raise MangaError(f"unknown primitive kind {kind!r} (ink, mass, tone, grad)")


def _burst(d, prim, spec, pal, W, H, S):
    """集中線: lines that radiate and taper into a single point of maximum energy.

    Each line is a wedge — hairline at the core, full nib width at the rim, so
    the eye is pulled to the focus. They are dropped on a seeded rhythm rather
    than evenly, because an even comb of lines reads as a fan and a ragged one
    reads as speed. Any line that would run through an authored `avoid` box is
    dropped: a speed line across a face reads as a printing fault, not as energy,
    and the illustration route learned that the hard way.
    """
    fx, fy = (float(prim.get("focus", [0.5, 0.5])[0]) * W,
              float(prim.get("focus", [0.5, 0.5])[1]) * H)
    n = int(prim.get("count", 64))
    colour = _rgb(pal, str(prim.get("color", "ink")))
    r0 = float(prim.get("inner", 0.05)) * min(W, H)
    r1 = float(prim.get("outer", 1.10)) * min(W, H)
    wmax = float(prim.get("w", 5.0)) * S
    half0 = 0.35 * S
    rng = np.random.default_rng(int(spec["seed"]) + 11)
    keep = rng.random(n) > float(prim.get("skip", 0.18))
    ang = prim.get("wedge")
    lo, span = (0.0, 2 * math.pi) if not ang else (math.radians(float(ang[0])),
                                                   math.radians(float(ang[1]) - float(ang[0])))
    avoid = [(float(b[0]) * W, float(b[1]) * H, float(b[2]) * W, float(b[3]) * H)
             for b in prim.get("avoid", [])]
    for i in range(n):
        if not keep[i]:
            continue
        a = lo + span * (i + rng.uniform(-0.35, 0.35)) / n
        ca, sa = math.cos(a), math.sin(a)
        p0 = (fx + ca * r0, fy + sa * r0)
        p1 = (fx + ca * r1, fy + sa * r1)
        if any(_seg_box(p0, p1, b) for b in avoid):
            continue
        half = 0.5 * wmax * float(prim.get("spread", 1.0))
        _stroke(d, [p0, p1], [half0, half], colour)


def _seg_box(p0, p1, box) -> bool:
    """Does the segment meet the box? Cheap: sample along it."""
    x0, y0, x1, y1 = box
    for k in range(9):
        f = k / 8.0
        x = p0[0] + (p1[0] - p0[0]) * f
        y = p0[1] + (p1[1] - p0[1]) * f
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False


def _title(d, prim, spec, pal, W, H, fonts, S):
    """The logotype: a shade slab behind the ink, sized off the sheet.

    `at` is one number (a height fraction, centred across the sheet) or two
    (x, y) — the second form is what puts a 台詞 inside a balloon instead of
    floating somewhere on the middle line.
    """
    text = str(prim.get("text", spec.get("title_text", "")))
    if not text.strip():
        raise MangaError("title primitive with no text: the band would print empty")
    size = int(float(prim.get("size", 0.13)) * H)
    fnt = _font(fonts, size)
    ink = _rgb(pal, str(prim.get("color", "ink")))
    shade = _rgb(pal, str(prim["shade"])) if prim.get("shade") else None
    bx = d.textbbox((0, 0), text, font=fnt)
    at = prim.get("at", 0.90)
    cx = float(at[0]) if isinstance(at, (list, tuple)) else 0.5
    cy = float(at[1]) if isinstance(at, (list, tuple)) else float(at)
    x = int(cx * W - (bx[2] - bx[0]) / 2) - bx[0]
    if prim.get("align") == "left":
        x = int(cx * W)
    y = int(cy * H - (bx[3] - bx[1]) / 2) - bx[1]
    off = max(2, int(size * 0.035))
    if shade:
        d.text((x + off, y + off), text, font=fnt, fill=shade)
    d.text((x, y), text, font=fnt, fill=ink)


def _font(fonts: list, size: int):
    for path in fonts:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    raise MangaError("no declared font resolved: a title in a substitute face "
                     "would not be the artifact the spec asked for")


# --- the sheet ----------------------------------------------------------------

def _layers(spec, name) -> list:
    return list(spec.get(name) or [])


def render(spec: dict, out_dir: Path | str | None = None):
    """Paint the page and return (quantised print array, hard supersample array).

    The second array is the sheet BEFORE the Lanczos downsample, so its edges are
    hard and a stroke's width is the width the nib was authored at; the printed
    sheet's edges are anti-aliased and then snapped to a seven-tone palette, which
    erases most of that signal. `_pen_weight` reads the former and the colour gates
    read the latter, because a colour gate is a claim about the artifact.
    """
    w, h = int(spec["width"]), int(spec["height"])
    S = float(spec.get("supersample", 3))
    W, H = int(round(w * S)), int(round(h * S))
    pal = spec["palette"]
    img = Image.new("RGB", (W, H), _rgb(pal, str(spec.get("ground", "paper"))))
    d = ImageDraw.Draw(img)
    pitch = float(spec["tone"]["pitch"]) * S
    ctx = {"S": S, "nib": 1.0, "pitch": pitch, "templates": spec.get("templates", {}),
           "phase": (((int(spec["seed"]) % 7) / 7.0) * pitch,
                     ((int(spec["seed"]) % 5) / 5.0) * pitch)}
    sheet = _D(S)
    for prim in _layers(spec, "backdrop"):
        _sheet_prim(d, img, prim, spec, pal, ctx, sheet, W, H, S)
    for fig in sorted(spec["figures"], key=lambda f: -float(f.get("depth", 0.5))):
        at = fig["at"]
        s = float(fig["scale"]) * S
        # `mx` at the figure level turns a whole face the other way, which is what
        # an ensemble needs: five cast members all looking over the same shoulder
        # is a queue, not a group. It mirrors x only -- a negative `scale` would
        # mirror y as well, because _D's second argument defaults to the first.
        M = _mul(_T(float(at[0]) * W, float(at[1]) * H),
                _mul(_R(float(fig.get("tilt", 0.0))),
                     _D(-s if fig.get("mx") else s, s)))
        fctx = dict(ctx, nib=ctx["nib"] * float(fig.get("nib", 1.0)))
        for prim in fig.get("parts", []):
            _prim(d, img, prim, M, fctx, spec, pal)
    for prim in _layers(spec, "foreground"):
        _sheet_prim(d, img, prim, spec, pal, ctx, sheet, W, H, S)

    hi = np.asarray(img, dtype=np.uint8).copy()    # pre-downsample, hard-edged
    art = np.asarray(img.resize((w, h), _LANCZOS), dtype=float)
    declared = [tuple(spec_mod.parse_hex(pal[k])) for k in spec["palette_order"]]
    lut = np.array(declared, dtype=float)
    noise = (_bayer_noise(w, h) - 0.5) * float(spec["tone"].get("dither", 8))
    idx = _nearest(art + noise[..., None], lut)
    return lut[idx].astype(np.uint8), hi


def _sheet_prim(d, img, prim, spec, pal, ctx, sheet, W, H, S):
    kind = str(prim.get("kind", "ink"))
    if kind == "burst":
        _burst(d, prim, spec, pal, W, H, S)
    elif kind == "title":
        _title(d, prim, spec, pal, W, H, spec["_fonts"], S)
    elif kind == "sheet":                       # a rectangle that is not a path
        d.rectangle([v * S for v in prim["box"]], fill=_rgb(pal, str(prim["fill"])),
                    outline=_rgb(pal, str(prim["color"])),
                    width=max(1, int(prim.get("width", 2) * S)))
    else:
        _prim(d, img, prim, sheet, ctx, spec, pal)


# --- measurement --------------------------------------------------------------

def _pen_weight(art, pal, S: float, max_px: float, widest_nib: float = 0.0):
    """Recovered nib weights in PRINT pixels, measured on whatever raster is given.

    This is the same distance-transform read as `_ink_weight`, factored out so it
    can be run on the hard supersample raster as well as on the printed sheet --
    and the three numbers disagree so widely that printing only one of them was the
    bug. On the 1400x1000 page:

      printed sheet      p10 = 2.00, p90 = 4.00, spread 2.00 px, 3 common widths
                         (2.00 px on 67% of ridge samples, 4.00 on 24%, 4.47 on 4%)
      downsampled float  spread 0.67 px -- anti-aliasing puts the half-ink edge
                         inside the mask and the EDT spine reads it as a hairline
      hard supersample   the widths the spec actually authored

    The first green was the 1-pixel lattice of the printed sheet, not the pen: a
    1.8 px ramp and a 2.2 px ramp both land on 2 px, so the pressure curve was
    destroyed before the gate looked, and `ink weight spread above 1.4 px` passed
    on a page whose lines were effectively one width -- exactly the fault the gate
    exists to catch. Measuring the pre-downsample raster is the honest version of
    "did the nib vary", because that is the last point in the pipeline where the
    answer is still the author's.

    It is not sufficient, and the mutant proved it: with EVERY stroke redrawn at
    one width the supersample read still returns **1.84 px**, because a 1.7 px
    print line is 5.1 px on a 3x raster and the remaining half-pixel landing plus
    the pen's own jitter make a spread no thinner than that. The floor therefore
    had to move above the constant-width value, and `max_px` now comes from the
    spec's own `nib.measure_max_px` rather than a constant fitted here (the cap is
    authored in print px, so it scales with S like the widths it excludes).
    """
    ink = np.abs(art.astype(int) - np.array(_rgb(pal, "ink"), dtype=int)).sum(-1) < 24
    # the cap and the widths are both authored in print px; the raster is S times
    # finer, so everything that bounds the sample scales together
    spread, median, n, share = _ink_weight(
        ink, float(max_px) * S, ridge_win=int(round(9 * S)), over_px=widest_nib * S)
    return spread / S, median / S, int(ink.sum()), n, share


def _widest_nib(spec) -> float:
    """The widest nib the page authored, in print px -- a diagnostic bound only.

    Walks every primitive the renderer can reach: templates, both sheet layers
    and each figure's parts, including a call site's own `w` overriding a
    template's. The heaviest per-figure nib multiplier is applied because that is
    what :func:`_pressure` multiplies the profile by, and it is an upper bound:
    the multiplier only acts inside a figure, so a wide `burst` in the backdrop is
    reported slightly heavier than it draws.

    Nothing gates on this. It exists so the manifest can state what share of the
    recovered widths is wider than any pen on the page -- 0.4% on the shipped
    sheet, which is the number that says the spread really is the nib's and not
    the fills'. (The cap is a separate cut: `nib.measure_max_px` discards the
    spine of every mass wider than it, silently, and the EDT's raw maximum on this
    page is 25 px against a 13 px cap.)
    """
    def walk(node):
        if isinstance(node, dict):
            w = node.get("w")
            if isinstance(w, dict):
                a = float(w.get("a", w.get("w", 1.6)))
                b = float(w.get("b", w.get("peak", a)))
                yield max(a, b)
            elif isinstance(w, (int, float)):
                yield float(w)
            elif isinstance(w, (list, tuple)) and len(w) >= 2:
                yield max(float(w[0]), float(w[1]))
            for k, v in node.items():
                if k != "w":
                    yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)

    heavy = max([float(f.get("nib", 1.0)) for f in (spec.get("figures") or [])] + [1.0])
    return round(max(list(walk(spec)) + [0.0]) * heavy, 3)


def _measure(art, spec, pal, declared, hi=None, S: float = 1.0) -> dict:
    h, w, _ = art.shape
    flat = art.reshape(-1, 3)
    present = {tuple(c) for c in np.unique(flat, axis=0)}
    exact = np.isin(flat, np.array(declared)).all(axis=1)
    lum = art @ np.array([0.2126, 0.7152, 0.0722])
    gx = np.abs(np.diff(lum, axis=1, prepend=lum[:, :1]))
    gy = np.abs(np.diff(lum, axis=0, prepend=lum[:1]))
    edges = float(((gx + gy) > 24).mean() * 100)

    def mask(key):
        return np.abs(art.astype(int) - np.array(_rgb(pal, key), dtype=int)).sum(-1) < 24

    paper = mask("paper")
    tone_keys = [k for k in spec["tone"].get("keys", []) if k in pal]
    tone_pct = 100.0 * sum(mask(k).mean() for k in tone_keys)
    cap = float(spec["nib"].get("measure_max_px", 14))
    widest = _widest_nib(spec)
    spread, modal, n_print, _ = _ink_weight(mask("ink"), cap)
    nib = _pen_weight(hi, pal, S, cap, widest) if hi is not None else None
    return {
        "width": w, "height": h,
        "palette_distinct_colors": len(present),
        "palette_undeclared_colors": len(present - {tuple(c) for c in declared}),
        "palette_declared_colors": len(declared),
        "palette_exact_pct": float(exact.mean() * 100),
        "edge_density_pct": edges,
        "screentone_dot_pct": float(tone_pct),
        "paper_negative_pct": float(paper.mean() * 100),
        "ink_weight_spread": nib[0] if nib else spread,
        "ink_weight_median": nib[1] if nib else modal,
        # the pen gate reads the supersample raster when the route has one; the
        # printed-sheet numbers stay in the record so the gap between the two --
        # the amount of the pressure curve the downsample destroyed -- is visible
        # in the manifest instead of being papered over
        "ink_weight_spread_print": spread,
        "ink_weight_spread_nib": nib[0] if nib else spread,
        "nib_raster_ink_px": nib[2] if nib else 0,
        # how much of the width sample is wider than any nib the page authored:
        # near zero on a well-formed sheet, which is what licenses reading
        # `ink_weight_spread` as the pen's curve. A diagnostic, never a gate input
        # -- a rule that consulted the spec it audits is a different false green
        "ink_weight_ridge_samples": nib[3] if nib else n_print,
        "ink_weight_over_nib_pct": nib[4] if nib else 0.0,
        "widest_authored_nib_px": widest,
        "figure_count": len(spec.get("figures") or []),
        # `eye_count` is WITHDRAWN, not relaxed. The counter below accepted 75
        # islands on a page that authors ten eyes, and every one of the 75 had
        # `enclosed == 0`: not one of them contained an iris (scripts/probes/
        # manga_count_probe.py prints the whole list with its numbers). They are
        # the counterspaces of the logotype's glyphs along y=0..13, gaps in the
        # 毛筋 highlights inside the black hair, and slivers between figures -- all
        # of them legitimately white, ink-ringed and eye-shaped. A second
        # definition was tried and measured too: "a small dark island sitting on
        # skin" returned 0, because the eye's ink merges with the lash and the
        # brow, so no closed island exists. Neither heuristic is honest, so the
        # rule now reports `skipped` with a reason rather than a green.
        "_eye_count_withdrawn": "see _eye_count docstring",
        "luma_spread": float(np.percentile(lum, 97) - np.percentile(lum, 3)),
    }


def _ink_weight(ink, max_px: float, ridge_win: int = 9, over_px: float = 0.0):
    """p90-p10 of the *line* thickness measured back off the pixels.

    ``distance_transform_edt`` gives each ink pixel its distance to the nearest
    non-ink pixel, so along a stroke's spine that distance is the half-width: the
    spine values ARE the nib's pressure curve, recovered without consulting the
    spec that authored it. Ridge points only (a local maximum of the distance),
    and only up to ``max_px``, because the interior of a solid ink mass is not a
    line -- without that cut a page of big black hair would report a huge weight
    spread and the gate would measure how much was filled in, which is the
    opposite of what it is for.

    ``ridge_win`` is the neighbourhood a ridge point is judged in, and it has to
    scale with the raster it is run on: 9 px finds a spine in a 2 px print line but
    only plateaus inside a 6 px supersampled one, so measuring the supersample
    raster with the print default reports a flat width where the nib varied.

    Returns ``(spread, median, n_ridge, share_over)``. The last two exist because
    the sample's composition was assumed rather than checked, and the assumption
    was wrong twice: the first reading compared against the widest nib in
    `figures[].parts[]` (3.60 px), concluded that **33.8%** of the ridge points must
    therefore be filled masses, and the number that survived measurement is
    **0.4%** -- the page authors a flat 5.0 px line in `foreground[4]`, which is
    31.5% of the sample and is exactly what the 5.33 px mode is. Looking in one
    place and inferring the rest is the mistake this whole file keeps making
    (docs/styles.md §8.3), so the share is reported in the manifest rather than
    reasoned about: it says how much of the width sample is wider than anything
    the page authored, and on a well-formed sheet that is near zero.
    """
    if not ink.any():
        return 0.0, 0.0, 0, 0.0
    dt = ndimage.distance_transform_edt(ink)
    ridge = (ink & (ndimage.maximum_filter(dt, size=ridge_win) == dt)
             & (dt > 0.45) & (dt <= max_px))
    v = dt[ridge] * 2.0
    if v.size < 60:
        return 0.0, 0.0, int(v.size), 0.0
    share = float((v > over_px).mean() * 100) if over_px > 0 else 0.0
    return (float(np.percentile(v, 90) - np.percentile(v, 10)),
            float(np.median(v)), int(v.size), share)


def _figure_count(art, pal, spec, w, h) -> int:
    """WITHDRAWN -- kept for the record, no longer called. Heads by FACE: a skin
    mass with a paper-white spot inside it.

    Carried over from the illustration route, where it was the fourth definition
    tried: in this grammar the only white anything draws on skin is the eye, so a
    hand, a sleeve and a bent arm that closes a hole at the hip all fail the test
    and a head passes it whether it is large or half-occluded.

    It reported 11 on a page that authors 5 figures. A skin mass broken by the
    mouth, the chin shadow or a 毛筋 crossing the jaw becomes two masses, and each
    still holds a paper spot, so one face counted twice -- and the gate
    `at least 4 separate figures` was green against a number that had nothing to
    do with how many people were drawn. The rule now reads the spec's own cast
    list, which is what "figures" means for an authored page: it proves the sheet
    was asked for five faces, and it no longer pretends to prove five faces came
    out. Whether they did is the thing the gates cannot see, and saying so is the
    honest result (docs/styles.md §0, 丙档).
    """
    zone = np.zeros((h, w), dtype=bool)
    zone[:int(h * float(spec["frame"].get("face_zone", 0.86))), :] = True
    skin = np.abs(art.astype(int) - np.array(_rgb(pal, "skin"), dtype=int)).sum(-1) < 40
    lbl, n = ndimage.label(ndimage.binary_dilation(skin & zone, iterations=2))
    paper = np.abs(art.astype(int) - np.array(_rgb(pal, "paper"), dtype=int)).sum(-1) < 30
    got = 0
    for ids, size in enumerate(ndimage.sum(np.ones_like(lbl), lbl, range(1, n + 1)), 1):
        if size < 0.00015 * w * h:
            continue
        sl = ndimage.find_objects(lbl)[ids - 1]
        tall, wide = sl[0].stop - sl[0].start, max(1, sl[1].stop - sl[1].start)
        if tall > 1.6 * wide:
            continue
        core = ndimage.binary_erosion(ndimage.binary_fill_holes(lbl[sl] == ids),
                                      iterations=max(2, int(0.08 * min(tall, wide))))
        if int((core & paper[sl]).sum()) >= 3:
            got += 1
    return got


def _eye_count(art, pal, w, h) -> int:
    """WITHDRAWN -- kept for the record, no longer called; see `_measure` for the
    measurement that replaced it with a refusal.

    Eyes by their own shape: a small paper mass that ink hugs on every side.

    Deliberately stricter than the face test. A sclera is a compact white island
    ringed by lash, iris and lid, so the ink share just outside it is high; a
    patch of background paper between two figures touches only other paper and
    fails. If this ever drifts, it fails loud as a low count, not as a false eye.

    It did drift, and it did not fail loud: 75 accepted on a page with ten eyes.
    The docstring's own reasoning was the bug -- "the ink share just outside it is
    high" is true of EVERY enclosed-looking gap in a black-inked page, and this
    grammar draws its hair as one solid mass with paper strands punched through
    it, so the whole coiffure is a field of eye-shaped holes. The glyph counters
    - the counterspaces of a logotype, are the same shape. A shape filter cannot
    separate an eye from a hole; only an iris inside it can, and that test
    returned 0 here because the eye's ink is continuous with its lash.
    """
    paper = np.abs(art.astype(int) - np.array(_rgb(pal, "paper"), dtype=int)).sum(-1) < 40
    ink = np.abs(art.astype(int) - np.array(_rgb(pal, "ink"), dtype=int)).sum(-1) < 40
    lbl, n = ndimage.label(paper)
    if not n:
        return 0
    ring = ndimage.binary_dilation(ink, iterations=3)
    got = 0
    for ids, sl in enumerate(ndimage.find_objects(lbl), 1):
        m = (lbl[sl] == ids)
        area = int(m.sum())
        if not (0.000018 * w * h <= area <= 0.0012 * w * h):
            continue
        tall, wide = sl[0].stop - sl[0].start, max(1, sl[1].stop - sl[1].start)
        if tall > 2.2 * wide or wide > 3.2 * tall:
            continue
        edge = ndimage.binary_dilation(m, iterations=2) & ~m
        if edge.size and float((ring[sl][edge]).mean()) > 0.55:
            got += 1
    return got


# --- the route ----------------------------------------------------------------

def _refuse(spec: dict) -> None:
    pal = spec.get("palette") or {}
    missing = [k for k in ("paper", "ink", "skin") if k not in pal]
    if missing:
        raise MangaError(f"palette is missing colours the brush needs: "
                         f"{', '.join(missing)}")
    # the tone colours are named by the spec rather than hardcoded, because a
    # page may screen with greys, with browns, or with one red at half strength
    keys = [k for k in spec["tone"].get("keys", []) if k in pal]
    if not keys:
        raise MangaError("tone.keys names no palette colour: the screentone gate "
                         "would have nothing to count")
    seen: dict[tuple, str] = {}
    for k, v in pal.items():
        rgb = tuple(spec_mod.parse_hex(v))
        if rgb in seen:
            # raised text stays ASCII: a cp1252 console would turn the reason for
            # the refusal into a UnicodeEncodeError
            raise MangaError(
                f"palette colours must be distinct: '{k}' and '{seen[rgb]}' are both "
                f"{rgb} - the gates count pixels per colour, so a collapsed palette "
                f"measures nothing")
        seen[rgb] = k
    if float(spec.get("supersample", 3)) < 2:
        raise MangaError("supersample must be >= 2: a tapered line ends at sub-pixel "
                         "width, and rounding it at 1:1 throws away the only thing "
                         "this route adds")
    if not spec.get("figures"):
        raise MangaError("figures is empty: an inked page with nothing on it has an "
                         "ink weight spread of zero by construction")
    if int(spec["tone"].get("pitch", 7)) < 3:
        raise MangaError(f"tone.pitch must be >= 3 px: at {spec['tone']['pitch']} the "
                         f"dot screen is below one pixel and the tone gate would "
                         f"measure noise")

    def walk(prim, where):
        if not isinstance(prim, dict):
            raise MangaError(f"{where}: a primitive must be a mapping")
        kind = str(prim.get("kind", "ink"))
        if kind not in KINDS:
            raise MangaError(f"{where}: unknown kind {kind!r} "
                             f"(this brush makes {', '.join(KINDS)})")
        if "use" not in prim and "d" not in prim and kind not in ("burst", "title", "sheet"):
            raise MangaError(f"{where}: needs `d` or `use`")
        if "use" in prim and str(prim["use"]) not in (spec.get("templates") or {}):
            raise MangaError(f"{where}: places template {prim['use']!r}, which nobody "
                             f"drew (the spec defines "
                             f"{sorted(spec.get('templates') or {})})")
        prof = (prim.get("w") or {}).get("profile") if isinstance(prim.get("w"), dict) \
            else None
        if prof is not None and prof not in PROFILES:
            raise MangaError(f"{where}: unknown nib profile {prof!r}, this brush lays "
                             f"{', '.join(PROFILES)}")
        for key in _COLOR_KEYS:
            if prim.get(key) and str(prim[key]) not in pal:
                raise MangaError(f"{where}: {key}={prim[key]!r} is not a palette colour "
                                 f"(it names ink, not a style)")
        if isinstance(prim.get("screen"), dict):
            walk({"kind": "tone", "d": "M0,0 L1,1 L2,0",
                  "color": prim["screen"].get("color", "tone"),
                  "level": prim["screen"].get("level", 0.5)}, where + ".screen")

    for name in ("backdrop", "foreground"):
        for i, prim in enumerate(_layers(spec, name)):
            walk(prim, f"{name}[{i}]")
    for i, fig in enumerate(spec["figures"]):
        if "at" not in fig or "scale" not in fig:
            raise MangaError(f"figures[{i}]: needs an `at` and a `scale`; the brush "
                             f"does not place a face the author did not put there")
        for j, prim in enumerate(fig.get("parts", [])):
            walk(prim, f"figures[{i}].parts[{j}]")
    for name, tpl in (spec.get("templates") or {}).items():
        if not isinstance(tpl, list):
            raise MangaError(f"templates.{name}: a template is a list of primitives")
        for j, prim in enumerate(tpl):
            walk(dict(prim, **({"kind": prim.get("kind", "ink")})),
                 f"templates.{name}[{j}]")


def run(spec_path: Path | str, out_dir: Path | str, keep: bool = False) -> dict:
    spec = spec_mod.load_raw(spec_path)
    _refuse(spec)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pal = spec["palette"]
    declared = [tuple(spec_mod.parse_hex(pal[k])) for k in spec["palette_order"]]
    spec["_fonts"] = _resolve_fonts(spec)

    art, hi = render(spec, out_dir)
    art2, _ = render(spec, out_dir)          # determinism: twice, bit for bit
    deterministic = bool(np.array_equal(art, art2))

    m = _measure(art, spec, pal, declared, hi=hi,
                 S=float(spec.get("supersample", 3)))
    m["deterministic"] = deterministic
    report = validate.run_acceptance(spec["acceptance"], m)
    report["measured"] = m
    report["palette"] = {k: pal[k] for k in spec["palette_order"]}
    cli.write_report(out_dir, report)

    png = out_dir / "page.png"
    Image.fromarray(art).save(png)
    manifest = provenance.build_record(
        spec_path=str(spec_path),
        spec_dict={k: v for k, v in spec.items() if k != "_fonts"},
        content_hash=provenance.sha256_bytes(art.tobytes()),
        artifact_hashes={"page.png": provenance.sha256_file(png)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["page.png", "report.json", "manifest.json"],
        notes=spec.get("assumptions", []), pipeline="vcac-manga-ink/0.1",
        extra={"fonts": [{"path": str(p), "sha256": provenance.sha256_file(p),
                          "licence": str((spec.get("font") or {}).get(
                              "licence", "unverified"))} for p in spec["_fonts"]]})
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def _resolve_fonts(spec: dict) -> list:
    got = [Path(p) for p in (spec.get("font") or {}).get("paths", []) if Path(p).is_file()]
    if not got and any(str(p.get("kind", "")) == "title"
                       for p in _layers(spec, "foreground") + _layers(spec, "backdrop")):
        raise MangaError("a title band is declared but no font resolves: install Noto "
                         f"Sans SC (declared: {(spec.get('font') or {}).get('paths')})")
    return got


def figure(spec: dict, index: int = 0, size: int = 620) -> np.ndarray:
    """One figure, alone, big, on paper — for looking at.

    A five-figure page costs seconds per render and a mistake in an eyebrow is
    invisible at 620 px of a 1400 px sheet. This paints a single cast member into
    their own frame so the drawing can actually be examined; the gates never run
    on it, because a page cropped to one face is not the artifact.
    """
    spec = dict(spec)
    fig = dict(spec["figures"][index])
    sc = float(fig["scale"])
    spec["width"], spec["height"] = size, size
    spec["supersample"] = max(2, int(spec.get("supersample", 3)))
    S = float(spec["supersample"])
    W = H = int(size * S)
    pal = spec["palette"]
    img = Image.new("RGB", (W, H), _rgb(pal, str(spec.get("ground", "paper"))))
    d = ImageDraw.Draw(img)
    pitch = float(spec["tone"]["pitch"]) * S
    ctx = {"S": S, "nib": float(fig.get("nib", 1.0)), "pitch": pitch,
           "templates": spec.get("templates", {}), "phase": (pitch * .25, pitch * .25)}
    fig["at"] = [float(v) for v in fig.get("probe_at", [0.5, 0.68])]
    # fill the probe frame with the head: the authored box is ~110 units chin to
    # crown, so 0.55 of the frame across it leaves a margin to see the line in
    fig["scale"] = float(size) * 0.55 / 110.0
    M = _mul(_T(fig["at"][0] * W, fig["at"][1] * H), _D(fig["scale"] * S))
    for prim in fig.get("parts", []):
        _prim(d, img, prim, M, ctx, spec, pal)
    return np.asarray(img.resize((size, size), _LANCZOS))


def main(argv=None) -> int:
    a = cli.parse_args("vcac manga inking route (手绘上墨)", argv)
    spec = spec_mod.load_raw(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec["id"]))
    m = r["report"]["measured"]
    return cli.finish("manga", r, summaries=[
        f"{spec['id']} -> {r['out_dir']}",
        f"{m['width']}x{m['height']} colours={m['palette_distinct_colors']}/"
        f"{m['palette_declared_colors']} tone={m['screentone_dot_pct']:.2f}% "
        f"paper={m['paper_negative_pct']:.0f}% edges={m['edge_density_pct']:.1f}% "
        f"weight spread={m['ink_weight_spread']:.2f}px print/nib "
        f"(sheet-only {m['ink_weight_spread_print']:.2f}px, "
        f"median {m['ink_weight_median']:.2f}px) figures={m['figure_count']} "
        f"spread={m['luma_spread']:.0f}"])


if __name__ == "__main__":
    raise SystemExit(main())
