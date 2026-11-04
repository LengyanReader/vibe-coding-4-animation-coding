"""L3 fault injection, part 1: bad inputs (README §12.8).

坏输入必须给出「文件、原因、修复方向」齐全的错误，并且绝不产生假成功：
* a malformed spec must fail at LOAD time with the missing field named, not
  crash mid-render with a bare KeyError after output dirs were created;
* corrupted media must raise, never decode to "something".
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from vcac import media, spec as spec_mod
from vcac.spec import SpecError


def _spec(tmp_path: Path, name: str, raw: dict) -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


# --- missing required keys fail at load, with the field named ------------------

def test_image_spec_without_width_is_refused_at_load(tmp_path):
    """Pre-schema-lite this crashed as KeyError 'width' *after* out_dir was
    created — a render-side stacktrace for a spec typo."""
    raw = {"id": "x", "medium": "image", "height": 8,
           "palette": ["#000000", "#ffffff"],
           "acceptance": ["resolution exactly 8x8"]}
    p = _spec(tmp_path, "no-width.yaml", raw)
    with pytest.raises(SpecError, match="missing required field: 'width'"):
        spec_mod.load_raw(p)


def test_layout_spec_without_canvas_is_refused_at_load(tmp_path):
    raw = {"id": "x", "medium": "layout", "grid": {"columns": 2},
           "acceptance": ["resolution exactly 2x2"]}
    p = _spec(tmp_path, "no-canvas.yaml", raw)
    with pytest.raises(SpecError, match="missing required field: 'canvas'"):
        spec_mod.load_raw(p)


def test_film_spec_without_inputs_is_refused_at_load(tmp_path):
    """Used to be a bare KeyError('inputs') from the route body."""
    raw = {"id": "x", "medium": "film",
           "acceptance": ["has video stream", "has audio stream"]}
    p = _spec(tmp_path, "no-inputs.yaml", raw)
    with pytest.raises(SpecError, match="missing required field: 'inputs'"):
        spec_mod.load_raw(p)


def test_every_shipped_spec_still_passes_the_required_keys():
    """The schema-lite must not exclude a single shipped example."""
    base = Path("specs/examples")
    for p in sorted(base.glob("*.yaml")):
        if p.name == "media-bundle.yaml":      # a plan, not a media spec
            continue
        spec_mod.load_raw(p)                   # must not raise


# --- bad hex / bad duration get clear, load-time errors ------------------------

def test_bad_palette_hex_is_a_clear_error_before_any_output(tmp_path):
    """Hex validation lives in the route (parse_hex); the point is that it
    fails with a named value BEFORE any artifact is written."""
    from vcac import image_sample
    raw = {"id": "x", "medium": "image", "width": 8, "height": 8,
           "palette": ["#0000", "#ffffff"],          # 4-digit hex is invalid
           "acceptance": ["resolution exactly 8x8"]}
    p = _spec(tmp_path, "badhex.yaml", raw)
    out = tmp_path / "o"
    with pytest.raises(SpecError, match="bad hex color"):
        image_sample.run(p, out)
    assert not (out / "poster.png").exists()         # no artifact, no fake success


# --- corrupted media raise instead of decoding to "something" ------------------

def test_zero_byte_wav_raises(tmp_path):
    """wave.open refuses an empty file immediately (EOFError with an empty
    message — the refusal is the evidence, the route layer adds context)."""
    f = tmp_path / "empty.wav"
    f.write_bytes(b"")
    with pytest.raises(Exception):
        media.read_wav(f)


def test_truncated_wav_raises(tmp_path):
    """A real WAV, then chopped mid-frames: the wave reader must refuse, not
    return a short buffer that 'measures' fine."""
    import numpy as np
    f = tmp_path / "cut.wav"
    media.write_wav(f, np.zeros((4800, 1), dtype=np.float32), 48000)
    raw = f.read_bytes()
    f.write_bytes(raw[: len(raw) // 3])
    with pytest.raises(Exception):
        media.read_wav(f)


def test_garbage_png_raises(tmp_path):
    f = tmp_path / "junk.png"
    f.write_bytes(b"\x89PNG-not-really" + b"\x00" * 64)
    with pytest.raises(Exception):
        media.image_size(f.read_bytes())


def test_zero_byte_png_raises(tmp_path):
    f = tmp_path / "empty.png"
    f.write_bytes(b"")
    with pytest.raises(Exception):
        media.image_size(f.read_bytes())
