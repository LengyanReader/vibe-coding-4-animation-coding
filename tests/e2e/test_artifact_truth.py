"""Gates must measure the *artifact*, not the spec's claim about it.

README §12.3: "格式与尺寸 Format/Size — 与 spec 完全一致". Reading the declared
width/height back out of the spec and comparing them to the spec is a tautology:
a wrong or quoted value can never fail. These mutants pin the honest semantics —
each one declares dimensions (or a sample rate) that differ from what the route
actually produces, and the gate must go red. Under the pre-fix code every one of
these passed, which is exactly why the fix is a bug fix and not a refactor.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from vcac import (audio_sample, game_sample, image_sample, layout_sample,
                  spectrum_sample, spec as spec_mod, type_sample)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="routes need ffmpeg on PATH")

SPEC = Path("specs/examples")


def _mutated(name: str, tmp_path: Path, edit) -> Path:
    raw = spec_mod.load_raw(SPEC / name)
    edit(raw)
    p = tmp_path / f"mut-{name}"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return p


def _resolution_rule(w: int, h: int) -> str:
    return f"resolution exactly {w}x{h}"


# --- the resolution gate reads pixels, not promises ----------------------------

def test_image_resolution_gate_catches_a_wrong_declaration(tmp_path):
    raw = spec_mod.load_raw(SPEC / "poster-noise.yaml")
    raw["acceptance"] = [_resolution_rule(999, 999), "entropy > 5.0"]
    p = tmp_path / "wrong-res.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    r = image_sample.run(p, tmp_path / "i")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids[_resolution_rule(999, 999)]["status"] == "fail"
    assert ids[_resolution_rule(999, 999)]["actual"] == "1024x1024"


def test_game_resolution_gate_catches_a_wrong_declaration(tmp_path):
    def wrong(raw):
        raw["acceptance"] = [_resolution_rule(123, 456),
                             "player moved", "score at least 1",
                             "hp decreased", "session terminated"]

    p = _mutated("dodge-headless.yaml", tmp_path, wrong)
    r = game_sample.run(p, tmp_path / "g")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids[_resolution_rule(123, 456)]["status"] == "fail"
    assert ids[_resolution_rule(123, 456)]["actual"] != "123x456"


def test_type_resolution_gate_catches_a_wrong_declaration(tmp_path):
    pytest.importorskip("fontTools", reason="variable-font route needs fontTools")

    def wrong(raw):
        raw["acceptance"] = [_resolution_rule(999, 176),
                             "weight axis spans 100 to 900",
                             "ink increases monotonically with the weight axis",
                             "duration between 0.9 and 1.1"]

    p = _mutated("variable-weight.yaml", tmp_path, wrong)
    r = type_sample.run(p, tmp_path / "t")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids[_resolution_rule(999, 176)]["status"] == "fail"
    assert ids[_resolution_rule(999, 176)]["actual"] == "640x176"


def test_spectrum_resolution_gate_catches_a_wrong_declaration(tmp_path):
    def wrong(raw):
        raw["size"] = {"width": 512, "height": 768}   # rendered size (unchanged)
        raw["acceptance"] = [r for r in raw["acceptance"]
                             if not r.startswith("resolution")] \
            + [_resolution_rule(999, 768)]

    p = _mutated("spectrogram-truth.yaml", tmp_path, wrong)
    r = spectrum_sample.run(p, tmp_path / "s")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids[_resolution_rule(999, 768)]["status"] == "fail"
    assert ids[_resolution_rule(999, 768)]["actual"] == "512x768"


def test_layout_resolution_gate_catches_a_wrong_declaration(tmp_path):
    pytest.importorskip("playwright", reason="browser rasterizer needs playwright")

    def wrong(raw):
        raw["acceptance"] = [_resolution_rule(999, 960)] + [
            r for r in raw["acceptance"] if not r.startswith("resolution")]

    p = _mutated("swiss-poster.yaml", tmp_path, wrong)
    r = layout_sample.run(p, tmp_path / "l")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids[_resolution_rule(999, 960)]["status"] == "fail"
    assert ids[_resolution_rule(999, 960)]["actual"] == "720x960"


# --- a declared sample rate must survive mastering ------------------------------

def test_audio_route_respects_a_declared_44k1_rate(tmp_path):
    """loudnorm's apply pass force-resamples to 48 kHz, so a 44.1 kHz spec could
    never pass its own 'sample rate exactly 44100' rule. The target rate is the
    spec's, not a module constant."""
    raw = spec_mod.load_raw(SPEC / "synth-pad.yaml")
    raw["sample_rate"] = 44100
    raw["duration"] = "1.2s"
    raw["bars"] = 1
    raw["acceptance"] = ["duration between 1.0 and 1.5",
                         "sample rate exactly 44100",
                         "peak below -1 dBFS", "not silent"]
    p = tmp_path / "audio44k1.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    r = audio_sample.run(p, tmp_path / "a")
    assert r["report"]["passed"], r["report"]["checks"]
    assert r["report"]["measured"]["sample_rate"] == 44100


def test_image_route_accepts_quoted_dimensions(tmp_path):
    """image route fed the raw spec value into the measured dict, so YAML
    ``width: "1024"`` (quoted = str) false-failed against the int rule even
    though the artifact is exactly 1024 wide. The artifact decides."""
    raw = spec_mod.load_raw(SPEC / "poster-noise.yaml")
    raw["width"] = "1024"
    raw["height"] = "1024"
    p = tmp_path / "quoted.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    r = image_sample.run(p, tmp_path / "i")
    assert r["report"]["passed"], r["report"]["checks"]
    assert r["report"]["measured"]["width"] == 1024
