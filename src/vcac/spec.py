"""Spec layer — the contract between human intent and the generator.

Loads a YAML creative spec, validates the *required* fields for the first
closed loop, and exposes parsed helpers. This is the seed of ``src/vcac/spec.py``
described in README §4/§6.1. The full JSON Schema + pydantic model land when a
second medium needs the same contract — for now a focused, honest validation is
enough to make the loop runnable and mis-specs fail loud (M0.3).

Intent vs hard constraints (README §6.1):
  * hard  -> format.{width,height,fps,duration}, render.seed, acceptance
  * intent -> style.{palette,mood}
Ambiguities are recorded as explicit ``assumptions`` rather than silently guessed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SpecError(ValueError):
    """Raised when a spec is missing or contradicts a required field."""


def parse_duration(value: Any) -> float:
    """Parse '6s' / 6 / '6.0' / 6.0 into seconds (float)."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(s|sec|secs|seconds)?", s)
    if not m:
        raise SpecError(f"cannot parse duration: {value!r}")
    return float(m.group(1))


def parse_hex(color: str) -> tuple[int, int, int]:
    """'#0B1020' -> (11, 16, 32)."""
    s = color.strip().lstrip("#")
    if len(s) not in (3, 6) or not re.fullmatch(r"[0-9a-fA-F]+", s):
        raise SpecError(f"bad hex color: {color!r}")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


@dataclass
class Spec:
    raw: dict
    id: str
    title: str
    medium: str
    width: int
    height: int
    fps: int
    duration: float
    palette: list[tuple[int, int, int]]
    seed: int
    timeline: list[dict] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    @property
    def n_frames(self) -> int:
        return round(self.duration * self.fps)

    @property
    def background(self) -> tuple[int, int, int]:
        return self.palette[0]

    def seconds_at(self, at: str) -> float:
        return parse_duration(at)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "medium": self.medium,
            "format": {
                "width": self.width,
                "height": self.height,
                "fps": self.fps,
                "duration": self.duration,
            },
            "palette": ["#%02X%02X%02X" % c for c in self.palette],
            "seed": self.seed,
            "timeline": self.timeline,
            "acceptance": self.acceptance,
            "assumptions": self.assumptions,
        }


def _require(d: dict, path: str) -> Any:
    cur: Any = d
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            raise SpecError(f"spec missing required field: {path!r}")
        cur = cur[key]
    return cur


def _acceptance_list(value, where: str = "acceptance") -> list[str]:
    """Acceptance must be a *list of strings*. A bare string would list()-ify
    into characters: every char-rule is then skipped, ``failed`` stays 0 and
    ``passed`` reports true — the quietest fake-green there is (M0.3)."""
    if isinstance(value, str) or not isinstance(value, list) \
            or not all(isinstance(r, str) for r in value):
        raise SpecError(f"{where} must be a list of rule strings (verify-before-done, M0.3)")
    return list(value)


# Existence-only required keys per medium — schema-lite, *not* the README §3
# JSON Schema (still open). Catches the typo class that used to crash deep
# inside a render with a bare KeyError (audit A: late failure) at load time,
# with the field named. Nested keys stay the route's business.
REQUIRED_KEYS = {
    "image": ("width", "height", "palette"),
    "audio": ("duration",),
    "film": ("inputs",),
    "game": ("width", "height", "fps", "duration", "palette"),
    "layout": ("canvas", "grid", "palette", "type", "blocks"),
    "type": ("font", "text", "width", "height", "frames", "palette"),
    "spectrum": ("sample_rate", "duration", "fundamental_hz", "size"),
    "ink": ("width", "height", "palette", "font"),
    # a still ensemble portrait is authored, not parsed by the frame contract:
    # the figures ARE the substance, so an empty cast is a schema error
    "illustration": ("width", "height", "palette", "palette_order", "font",
                     "backdrop", "figures", "tone", "frame", "title_text"),
    # an inked page is authored as paths: the nib block is the pen, the tone block
    # is the lattice, and a page with no cast has no line to measure
    "manga": ("width", "height", "palette", "palette_order", "figures", "tone",
              "nib", "frame"),
    # anime speaks the frame contract (see VIDEO_CONTRACT_MEDIA below); its cut
    # is the gate, so a spec without a timeline is not an anime shot
    "anime": ("format", "style", "timeline"),
    # a book is authored: its identity (metadata) and its chapters ARE the
    # deliverable, so either missing is a schema error before pandoc runs
    "ebook": ("metadata", "chapters"),
}

#: Media authored against the *frame contract* that :func:`load` parses: a
#: ``format`` block (width/height/fps/duration), ``style.palette``,
#: ``render.seed`` and a ``timeline``. ``anime`` is a second renderer over the
#: same contract -- a new look is not a new schema -- so it is listed here rather
#: than given a duplicate loader that could drift from the first.
VIDEO_CONTRACT_MEDIA = ("video", "anime")


def load_raw(path: str | Path) -> dict:
    """Light loader for the per-route sample specs (image / audio / game).

    Unlike :func:`load` (which is the video ``Spec`` contract), this only enforces
    the two invariants every route shares — an ``id`` to name outputs under and a
    non-empty ``acceptance`` list (verify-before-done, M0.3). Each sample reads
    its own medium-specific keys from the returned dict, so new media don't force
    a schema rewrite before a second medium needs the shared ``Spec`` model.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SpecError(f"spec root must be a mapping: {path}")
    if not raw.get("id"):
        raise SpecError("spec missing required field: 'id'")
    if not raw.get("acceptance"):
        raise SpecError("spec must declare acceptance rules (verify-before-done, M0.3)")
    medium = raw.get("medium")
    for key in REQUIRED_KEYS.get(medium, ()):
        if key not in raw:
            raise SpecError(f"spec missing required field: '{key}' (medium: {medium})")
    raw["acceptance"] = _acceptance_list(raw["acceptance"])
    return raw


def load(path: str | Path) -> Spec:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SpecError(f"spec root must be a mapping: {path}")

    assumptions: list[str] = []

    medium = _require(raw, "medium")
    if medium not in VIDEO_CONTRACT_MEDIA:
        raise SpecError(
            f"spec.load parses the frame contract {VIDEO_CONTRACT_MEDIA}, "
            f"got medium={medium!r}")

    fmt = _require(raw, "format")
    width = int(_require(fmt, "width"))
    height = int(_require(fmt, "height"))
    fps = int(_require(fmt, "fps"))
    duration = parse_duration(_require(fmt, "duration"))

    # yuv420p needs even dimensions; record the constraint as an assumption if adjusted.
    if width % 2 or height % 2:
        assumptions.append(
            f"width/height forced even for yuv420p: {width}x{height} -> "
            f"{width - width % 2}x{height - height % 2}"
        )
        width -= width % 2
        height -= height % 2

    style = raw.get("style", {})
    palette_hex = style.get("palette")
    if not palette_hex or len(palette_hex) < 2:
        raise SpecError("style.palette needs >= 2 colors (background + at least one accent)")
    palette = [parse_hex(c) for c in palette_hex]

    render = raw.get("render", {})
    seed = int(render.get("seed", 42))
    if "seed" not in render:
        assumptions.append("render.seed defaulted to 42")

    acceptance = raw.get("acceptance") or []
    if not acceptance:
        raise SpecError("spec must declare acceptance rules (verify-before-done, M0.3)")

    return Spec(
        raw=raw,
        id=str(_require(raw, "id")),
        title=str(raw.get("title", _require(raw, "id"))),
        medium=medium,
        width=width,
        height=height,
        fps=fps,
        duration=duration,
        palette=palette,
        seed=seed,
        timeline=raw.get("timeline", []),
        acceptance=_acceptance_list(acceptance),
        assumptions=assumptions,
    )
