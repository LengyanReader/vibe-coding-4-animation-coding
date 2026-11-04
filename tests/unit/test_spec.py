"""Unit tests for the spec + parse layer (fast, no subprocess)."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from vcac import spec as spec_mod
from vcac.spec import SpecError


def test_parse_duration_variants():
    assert spec_mod.parse_duration("6s") == 6.0
    assert spec_mod.parse_duration(6) == 6.0
    assert spec_mod.parse_duration("6.5") == 6.5
    assert spec_mod.parse_duration("90 sec") == 90.0
    with pytest.raises(SpecError):
        spec_mod.parse_duration("abc")


def test_parse_hex():
    assert spec_mod.parse_hex("#0B1020") == (11, 16, 32)
    assert spec_mod.parse_hex("fff") == (255, 255, 255)
    with pytest.raises(SpecError):
        spec_mod.parse_hex("#12")


def test_load_raw_requires_acceptance(tmp_path: Path):
    p = tmp_path / "s.yaml"
    p.write_text(textwrap.dedent("""
        id: x
        medium: image
    """), encoding="utf-8")
    with pytest.raises(SpecError):
        spec_mod.load_raw(p)


def test_load_raw_ok(tmp_path: Path):
    p = tmp_path / "s.yaml"
    p.write_text(textwrap.dedent("""
        id: x
        medium: image
        acceptance:
          - resolution exactly 2x2
    """), encoding="utf-8")
    d = spec_mod.load_raw(p)
    assert d["id"] == "x" and d["acceptance"]


def test_load_rejects_non_video(tmp_path: Path):
    p = tmp_path / "s.yaml"
    p.write_text(textwrap.dedent("""
        id: x
        medium: audio
        format: {width: 4, height: 4, fps: 30, duration: 1s}
        style: {palette: ["#000000", "#ffffff"]}
        acceptance: [duration between 0 and 2]
    """), encoding="utf-8")
    with pytest.raises(SpecError):
        spec_mod.load(p)
