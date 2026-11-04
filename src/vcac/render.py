"""Pillow frame-by-frame renderer for the first closed loop.

Renders the ``orbiting-cubes`` scene: several 3D cubes (painted with a
flat-shaded painter's algorithm in pure Python matrices) orbiting a centre
and spinning about their own axes, over a dark background from the spec's
palette. Everything is a pure function of (frame_index, spec, seed):

  * deterministic — no wall-clock, no global RNG; per-cube phases come from a
    ``random.Random(seed)`` so changing the seed changes the layout (the
    determinism gate is therefore non-trivial: same seed -> identical bytes).
  * timeline-aware — fade-in / fade-out brightness and ease-in-out motion are
    read from the spec's ``timeline`` events, not hard-coded.

This is deliberately simple, readable creative code (README §6.3): the code is
the editable medium, so it is commented and self-contained rather than
abstracted across files. ``renderers/image/pillow`` + ``renderers/video/*``
split out when a second renderer needs the same interface.
"""
from __future__ import annotations

import math
import random
from typing import Iterable

from PIL import Image, ImageDraw

from .spec import Spec

# --- unit cube geometry -----------------------------------------------------
_VERTS = [
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
]
# (vertex indices, local outward normal)
_FACES = [
    ((0, 1, 2, 3), (0, 0, -1)),   # back
    ((5, 4, 7, 6), (0, 0, 1)),    # front
    ((4, 0, 3, 7), (-1, 0, 0)),   # left
    ((1, 5, 6, 2), (1, 0, 0)),    # right
    ((4, 5, 1, 0), (0, -1, 0)),   # bottom
    ((3, 2, 6, 7), (0, 1, 0)),    # top
]


def _norm(v):
    x, y, z = v
    m = math.sqrt(x * x + y * y + z * z) or 1.0
    return (x / m, y / m, z / m)


_LIGHT = _norm((0.4, 0.7, 0.6))


def _rot_xyz(ax: float, ay: float, az: float):
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    # combined R = Rz @ Ry @ Rx as a flat 3x3
    return [
        [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
        [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
        [-sy, cy * sx, cy * cx],
    ]


def _mul(m, v):
    return tuple(m[r][0] * v[0] + m[r][1] * v[1] + m[r][2] * v[2] for r in range(3))


def smoothstep(x: float) -> float:
    """ease-in-out on [0,1] (clamped)."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _shade(rgb, k: float):
    return tuple(max(0, min(255, int(round(c * k)))) for c in rgb)


def _mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


class Cube:
    def __init__(self, rng: random.Random, palette, index: int, n_accents: int):
        self.orbit_r = rng.uniform(0.16, 0.34)          # fraction of min-dimension
        self.orbit_phase = rng.uniform(0, math.tau)
        self.orbit_speed = rng.choice([1, 1, 2]) * rng.choice([1, -1])
        self.spin_phase = rng.uniform(0, math.tau)
        self.spin_speed = rng.uniform(1.5, 3.0) * rng.choice([1, -1])
        self.size = rng.uniform(0.05, 0.10)             # fraction of min-dimension
        self.tilt = rng.uniform(0.2, 0.6)
        # accent colour, cycling the palette (index 0 is the background)
        self.color = palette[1 + (index % n_accents)]

    def draw(self, d: ImageDraw.ImageDraw, w: int, h: int, scene: float, bg):
        min_dim = min(w, h)
        cx, cy = w / 2, h / 2
        ang = self.orbit_phase + self.orbit_speed * scene * math.tau
        ox = cx + math.cos(ang) * self.orbit_r * min_dim
        oy = cy + math.sin(ang) * self.orbit_r * min_dim * 0.55  # ellipse = perspective
        depth = (math.sin(ang) + 1) / 2                          # 0 far .. 1 near
        spin = self.spin_phase + self.spin_speed * scene * math.tau
        size = self.size * min_dim * (0.7 + 0.5 * depth)         # nearer = bigger
        scale = size / math.sqrt(3)

        m = _rot_xyz(self.tilt, spin, spin * 0.37)
        pts, face_data = [], []
        for v in _VERTS:
            rv = _mul(m, v)
            pts.append((ox + rv[0] * scale, oy - rv[1] * scale, rv[2]))
        for idx, nrm in _FACES:
            wn = _mul(m, nrm)
            shade_k = 0.45 + 0.55 * max(0.0, _dot(wn, _LIGHT))
            zavg = sum(pts[i][2] for i in idx) / len(idx)
            face_data.append((zavg, idx, shade_k))
        # painter's algorithm: far faces first
        face_data.sort(key=lambda f: f[0])
        depth_dim = 0.65 + 0.35 * depth                          # far cubes darker
        for _z, idx, shade_k in face_data:
            poly = [(pts[i][0], pts[i][1]) for i in idx]
            col = _shade(_mix(bg, self.color, 0.15 + 0.85 * depth_dim), shade_k)
            d.polygon(poly, fill=col)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _make_cubes(spec: Spec):
    rng = random.Random(spec.seed)
    accents = max(1, len(spec.palette) - 1)
    n = int(spec.raw.get("render", {}).get("cubes", 6))
    return [Cube(rng, spec.palette, i, accents) for i in range(n)], accents


def _fade_envelope(spec: Spec) -> list[tuple[float, float, bool]]:
    """[(start_s, dur_s, is_in)] from declared timeline fade events."""
    fades = []
    for ev in spec.timeline:
        act = str(ev.get("action", ""))
        if act in ("fade-in", "fade-out"):
            start = spec.seconds_at(ev.get("at", "0s"))
            dur = spec.seconds_at(ev.get("duration", "1s"))
            fades.append((start, dur, act == "fade-in"))
    return fades


def frame_image(spec: Spec, cubes, t: int) -> Image.Image:
    w, h, fps = spec.width, spec.height, spec.fps
    n = spec.n_frames
    img = Image.new("RGB", (w, h), spec.background)
    d = ImageDraw.Draw(img)

    raw_p = t / max(1, n - 1)
    eased = spec.raw.get("timeline", {}) and any(
        "ease" in str(e) for e in spec.timeline
    )
    scene = smoothstep(raw_p) if eased else raw_p

    for c in cubes:
        c.draw(d, w, h, scene, spec.background)

    # brightness / fade: blend whole frame toward the dark background colour
    b = 1.0
    for start, dur, is_in in _fade_envelope(spec):
        s = t / fps
        if start <= s <= start + dur:
            local = (s - start) / dur
            b = min(b, smoothstep(local) if is_in else smoothstep(1 - local))
    if b < 1.0:
        img = Image.blend(Image.new("RGB", (w, h), spec.background), img, b)
    return img


def render_frames(spec: Spec) -> Iterable[bytes]:
    """Yield raw RGB bytes for every frame (pure function of spec + seed)."""
    cubes, _ = _make_cubes(spec)
    for t in range(spec.n_frames):
        yield frame_image(spec, cubes, t).tobytes()

