"""Small-case routes: layout (browser), type (variable font), spectrum (sound->picture).

Two duties per case, not one.

  * the happy path is pinned to a human-confirmed **golden content hash**, and the
    hash was recorded by a different process than the one asserting it, so an
    ordinary pass here doubles as a cross-process reproducibility proof;
  * every gate ships with a **mutant that must fail it**. A gate nobody has seen
    go red is indistinguishable from a gate that cannot go red, and "the check
    passed" with an uncalibrated check is exactly the failure mode M0.2 forbids.

Optional-dependency routes skip instead of lying: playwright and fontTools are
installed in one interpreter on this machine and absent from the conda env the
older golden manifests came from (docs/coverage-audit.md §0). A skip with a reason
is the honest output of a capability registry; a green is not.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from vcac import layout_sample, spectrum_sample, spec as spec_mod, type_sample, validate

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="routes need ffmpeg on PATH")

SPEC = Path("specs/examples")

# human-confirmed golden content hashes (raw payload digests, cross-process)
GOLDEN = {
    "layout": "sha256:ce95c59301b6ac63c264041cf59d941fe1eb75ef75c686311951fe1086b5bbf3",
    "type": "sha256:3796ddf4ef392c3b7dc72e35f784c000ebc86c152a2016d1f34d276c3307ab1f",
    "spectrum": "sha256:e3591c8c740866e4a577d40aaed38248464ea2ff7c5a66efff4d80610ec54890",
}


def _mutated(spec_path: Path, tmp_path: Path, name: str, edit) -> Path:
    raw = spec_mod.load_raw(spec_path)
    edit(raw)
    p = tmp_path / f"{name}.yaml"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return p


# --- A. layout: a design movement as a measurable 4-tuple ----------------------

def test_layout_route(tmp_path):
    pytest.importorskip("playwright", reason="browser rasterizer needs playwright")

    r = layout_sample.run(SPEC / "swiss-poster.yaml", tmp_path / "l")
    rep, m = r["report"], r["report"]["measured"]
    assert rep["passed"], rep["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN["layout"]
    # the grid error is not "small", it is nil: positions come from the spec's own
    # arithmetic and the browser agrees to the last decimal
    assert m["left_edge_max_offset_px"] == 0.0
    assert m["baseline_max_offset_px"] == 0.0
    assert m["palette_distinct_colors"] == 3
    # raster and vector surfaces from one spec
    assert (tmp_path / "l" / "poster.png").stat().st_size < 60_000
    assert (tmp_path / "l" / "poster.pdf").stat().st_size > 1000


def test_layout_grid_gate_catches_a_nudge(tmp_path):
    """7 px off the column field must turn the gate red, not 'close enough'."""
    pytest.importorskip("playwright", reason="browser rasterizer needs playwright")

    def push(raw):
        raw["blocks"][0]["nudge_px"] = {"dx": 7}

    p = _mutated(SPEC / "swiss-poster.yaml", tmp_path, "offgrid", push)
    r = layout_sample.run(p, tmp_path / "l")
    bad = [c for c in r["report"]["checks"] if c["status"] == "fail"]
    assert [c["id"] for c in bad] == ["left edges within 1 px of the column grid"]
    assert bad[0]["actual"] == pytest.approx(7.0, abs=0.01)


def test_layout_palette_gate_catches_a_fourth_colour(tmp_path):
    pytest.importorskip("playwright", reason="browser rasterizer needs playwright")

    def add_colour(raw):
        raw["palette"]["extra"] = "#00FF00"
        raw["blocks"][3]["color"] = "extra"

    p = _mutated(SPEC / "swiss-poster.yaml", tmp_path, "fourcol", add_colour)
    r = layout_sample.run(p, tmp_path / "l")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["distinct palette colors at most 3"]["status"] == "fail"
    assert ids["distinct palette colors at most 3"]["actual"] == 4


def test_layout_font_gate_catches_a_silent_fallback(tmp_path):
    """``Noto Sans`` (no SC) is not installed here, and the shaper substitutes it
    with the serif default. document.fonts.check() calls that a success; the
    advance-width fingerprint does not."""
    pytest.importorskip("playwright", reason="browser rasterizer needs playwright")

    def fake_family(raw):
        raw["type"]["display"]["family"] = "Noto Sans"

    p = _mutated(SPEC / "swiss-poster.yaml", tmp_path, "fallback", fake_family)
    r = layout_sample.run(p, tmp_path / "l")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["every declared font family resolves (no silent fallback)"]["status"] == "fail"
    assert "Noto Sans" in ids["every declared font family resolves (no silent fallback)"]["actual"]


def test_layout_overflow_gate_catches_overlong_copy(tmp_path):
    pytest.importorskip("playwright", reason="browser rasterizer needs playwright")

    def ram_it(raw):
        raw["blocks"][3]["text"] = "Schrift und Raster bilden eine Einheit, die man messen kann"
        raw["blocks"][3]["span"] = 1

    p = _mutated(SPEC / "swiss-poster.yaml", tmp_path, "overflow", ram_it)
    r = layout_sample.run(p, tmp_path / "l")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["no text overflows the canvas"]["status"] == "fail"


def test_layout_refuses_a_grid_that_does_not_divide(tmp_path):
    """Rounding a column width down would quietly put every block a fraction off,
    so the route refuses the spec instead of rendering a poster it cannot verify."""
    pytest.importorskip("playwright", reason="browser rasterizer needs playwright")

    def ugly(raw):
        raw["grid"]["columns"] = 7

    p = _mutated(SPEC / "swiss-poster.yaml", tmp_path, "ugly", ugly)
    with pytest.raises(layout_sample.LayoutError):
        layout_sample.run(p, tmp_path / "l")


# --- B. type: the axis has to be visible, because the name table will lie ------

def test_type_route(tmp_path):
    pytest.importorskip("fontTools", reason="variable-font route needs fontTools")
    r = type_sample.run(SPEC / "variable-weight.yaml", tmp_path / "t")
    rep = r["report"]
    assert rep["passed"], rep["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN["type"]
    # 10.6 MB source face -> one in-memory subset, reused for every frame
    assert rep["font"]["subset_bytes"] < 20_000
    assert not (tmp_path / "t" / "frames").exists()
    # the metadata says "Thin" at every weight; only the pixels know the truth
    assert all(n[1] == "Thin" for n in rep["font"]["name_table_says"])
    assert rep["ink"]["ascending_run"][0] < rep["ink"]["ascending_run"][-1]
    # fonts are a licensed third-party input, so they belong in the record (styles.md §17)
    fonts = r["manifest"]["fonts"]
    assert fonts[0]["licence"] == "OFL-1.1"
    assert fonts[0]["source_sha256"].startswith("sha256:")
    assert fonts[0]["axes"]["wght"] == [100.0, 900.0]


def test_type_gate_catches_a_fake_ramp(tmp_path):
    """Pin lo == hi and the 'animation' is seventeen copies of one weight. The ink
    gate has to say so."""
    pytest.importorskip("fontTools", reason="variable-font route needs fontTools")
    import numpy as np

    spec_dict = spec_mod.load_raw(SPEC / "variable-weight.yaml")
    face, _ = type_sample.subset_face(
        type_sample.find_font(spec_dict), spec_dict["text"])
    masks = type_sample.render_masks(spec_dict, face, 400.0, 400.0)
    ink = [int(np.count_nonzero(np.asarray(m["mask"]))) for m in masks]
    half = len(ink) // 2
    assert not all(a < b for a, b in zip(ink[:half], ink[:half][1:]))


def test_type_refuses_a_canvas_it_would_clip(tmp_path):
    """Clipping the heaviest instance would *lower* its ink count and could be
    mistaken for a rendering defect, so the route refuses before it measures."""
    pytest.importorskip("fontTools", reason="variable-font route needs fontTools")

    def shrink(raw):
        raw["width"] = 120
        raw["height"] = 80

    p = _mutated(SPEC / "variable-weight.yaml", tmp_path, "tiny", shrink)
    with pytest.raises(type_sample.FontCapabilityError, match="canvas too small"):
        type_sample.run(p, tmp_path / "t")


def test_type_refuses_a_missing_face(tmp_path):
    """Absent font must be an error, never a fallback to whatever is handy."""
    pytest.importorskip("fontTools", reason="variable-font route needs fontTools")

    def absent(raw):
        raw["font"]["paths"] = ["C:/nope/NotoSansSC-VF.ttf"]

    p = _mutated(SPEC / "variable-weight.yaml", tmp_path, "absent", absent)
    with pytest.raises(type_sample.FontCapabilityError, match="none of the declared"):
        type_sample.run(p, tmp_path / "t")


# --- C. spectrum: read the sound back out of the picture -----------------------

def test_spectrum_route(tmp_path):
    r = spectrum_sample.run(SPEC / "spectrogram-truth.yaml", tmp_path / "s")
    rep = r["report"]
    assert rep["passed"], rep["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN["spectrum"]
    # two independent methods must agree far inside the row grid (31.29 Hz)
    cc = rep["cross_check"]
    assert cc["agreement_delta_hz"] < cc["row_resolution_hz"] / 4
    assert (tmp_path / "s" / "spectrum.png").stat().st_size < 40_000


def test_spectrum_metric_audit_is_pinned(tmp_path):
    """The delivery gate is PSNR because SSIM was measured to be too flat here.
    Pinning the measurement, not just the code path: if a future build changes the
    encoder or the metric, this test says the premise moved."""
    r = spectrum_sample.run(SPEC / "spectrogram-truth.yaml", tmp_path / "s")
    ma = r["report"]["metric_audit"]
    assert ma["gate_used"] == "psnr"
    assert ma["margins"]["ssim"] < ma["criterion"]["ssim_gap_needed"]
    assert ma["criterion"]["ssim_gate_stable"] is False
    assert ma["margins"]["psnr_db"] >= 5.0
    assert not (tmp_path / "s" / "_control.webp").exists()


def test_spectrum_gate_catches_a_detuned_tone(tmp_path):
    def detune(raw):
        raw["fundamental_hz"] = 500.0        # acceptance still demands 440 +-10

    p = _mutated(SPEC / "spectrogram-truth.yaml", tmp_path, "detune", detune)
    r = spectrum_sample.run(p, tmp_path / "s")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["measured pitch within 10 Hz of 440"]["status"] == "fail"
    assert ids["measured pitch within 10 Hz of 440"]["actual"] == pytest.approx(500.0, abs=2)


def test_spectrum_gate_catches_a_missing_partial(tmp_path):
    """Two played partials cannot satisfy 'five visible': the harmonic detector has
    to be reading lines that are really in the picture."""
    def thin(raw):
        raw["harmonics_to_play"] = 2

    p = _mutated(SPEC / "spectrogram-truth.yaml", tmp_path, "thin", thin)
    r = spectrum_sample.run(p, tmp_path / "s")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["at least 5 harmonics visible"]["status"] == "fail"
    assert ids["at least 5 harmonics visible"]["actual"] == 2


# --- the route table itself ----------------------------------------------------

def test_medium_names_are_declared_per_route():
    """Each small case is a distinct medium in the README table; a spec that lies
    about its medium would route to the wrong renderer."""
    for name, medium in [("swiss-poster.yaml", "layout"),
                         ("variable-weight.yaml", "type"),
                         ("spectrogram-truth.yaml", "spectrum")]:
        assert spec_mod.load_raw(SPEC / name)["medium"] == medium


def test_validator_reports_an_unmeasured_rule_as_skipped():
    """A rule the route never measured must be ``skipped`` with a reason. Silent
    absence is how a green pipeline hides an unverified claim."""
    out = validate.run_acceptance(["vmaf >= 93"], {"ssim": 0.99})
    assert out["checks"][0]["status"] == "skipped"
    assert "vmaf" in out["checks"][0]["reason"]
    # nothing failed, so the run is still "passed" -- which is precisely why a
    # report has to show the skip count next to the green, not hide it
    assert out["passed"] is True and out["skipped_n"] == 1
