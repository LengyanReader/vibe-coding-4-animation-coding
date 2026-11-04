"""Unit tests for the acceptance rule engine (the verify-before-done core)."""
from __future__ import annotations

from pathlib import Path

from vcac import spec as spec_mod
from vcac import validate

SPEC = Path("specs/examples")


def test_max_black_run_seconds():
    # 30 fps; frames 0..2 dark (luma < 8), rest bright -> 3/30 = 0.1s run
    luma = [1.0, 2.0, 3.0] + [120.0] * 27
    assert abs(validate.max_black_run_seconds(luma, 30) - 0.1) < 1e-9
    assert validate.max_black_run_seconds([120.0] * 30, 30) == 0.0


def test_duration_rule_pass_and_fail():
    ok = validate.run_acceptance(["duration between 5.8 and 6.2"], {"duration": 6.0})
    assert ok["passed"] and ok["checks"][0]["status"] == "pass"
    bad = validate.run_acceptance(["duration between 5.8 and 6.2"], {"duration": 7.0})
    assert not bad["passed"] and bad["checks"][0]["status"] == "fail"


def test_missing_metric_is_skipped_not_passed():
    # a black-frame rule with no black measurement must NOT silently pass (M0.2)
    r = validate.run_acceptance(["no black frame longer than 0.5s"], {"duration": 6.0})
    assert r["checks"][0]["status"] == "skipped"
    assert r["passed"]  # nothing failed


def test_unknown_rule_skipped():
    r = validate.run_acceptance(["make it pop"], {"duration": 6.0})
    assert r["checks"][0]["status"] == "skipped"


def test_determinism_gate_appended():
    r = validate.run_acceptance(["duration between 1 and 10"],
                                {"duration": 5.0, "deterministic": False})
    assert not r["passed"]
    assert any("determinism" in c["id"] and c["status"] == "fail" for c in r["checks"])


def test_audio_lufs_and_peak_rules():
    m = {"sample_rate": 48000, "duration": 9.6, "lufs_i": -16.0,
         "peak_dbfs": -4.2, "rms_dbfs": -15.0, "clipping_pct": 0.0,
         "dc_offset": 1e-5, "channels": 1}
    rules = ["loudness -16 LUFS", "peak below -1 dBFS", "not silent",
             "clipping < 0.01%", "dc offset < 0.001", "sample rate exactly 48000"]
    r = validate.run_acceptance(rules, m)
    assert r["passed"], r["checks"]


def test_game_rules():
    m = {"moved": True, "score": 5, "hp": 0, "start_hp": 6, "terminated": True}
    r = validate.run_acceptance(
        ["player moved", "score at least 1", "hp decreased", "session terminated"], m)
    assert r["passed"], r["checks"]


# --- the small-case routes' rules: green once, and demonstrably red on demand ---

LAYOUT_RULES = [
    "left edges within 1 px of the column grid",
    "tops within 0.5 px of the baseline grid",
    "distinct palette colors at most 3",
    "at least 90% of pixels are exact palette colors",
    "no text overflows the canvas",
    "every declared font family resolves (no silent fallback)",
]


def test_layout_rules_green():
    m = {"left_edge_max_offset_px": 0.0, "baseline_max_offset_px": 0.3,
         "palette_distinct_colors": 3, "palette_exact_pct": 98.1,
         "overflow_elements": 0, "fonts_unresolved": []}
    r = validate.run_acceptance(LAYOUT_RULES, m)
    assert r["passed"] and r["skipped_n"] == 0, r["checks"]


def test_layout_rules_all_can_fail():
    """Every layout gate needs a red case. A rule that has only ever been seen green
    has not been shown to measure anything."""
    m = {"left_edge_max_offset_px": 7.0, "baseline_max_offset_px": 9.0,
         "palette_distinct_colors": 4, "palette_exact_pct": 12.0,
         "overflow_elements": 2, "fonts_unresolved": ["Noto Sans"]}
    r = validate.run_acceptance(LAYOUT_RULES, m)
    assert not r["passed"] and r["failed_n"] == 6, r["checks"]


def test_type_axis_rules():
    ok = validate.run_acceptance(
        ["weight axis spans 100 to 900",
         "ink increases monotonically with the weight axis"],
        {"axis_from": 100.0, "axis_to": 900.0, "ink_monotonic": True})
    assert ok["passed"], ok["checks"]
    bad = validate.run_acceptance(
        ["weight axis spans 100 to 900",
         "ink increases monotonically with the weight axis"],
        {"axis_from": 400.0, "axis_to": 400.0, "ink_monotonic": False})
    assert bad["failed_n"] == 2, bad["checks"]


def test_spectrogram_and_perceptual_rules():
    ok = validate.run_acceptance(
        ["measured pitch within 10 Hz of 440", "at least 5 harmonics visible",
         "psnr >= 45", "ssim >= 0.99", "degraded control < 0.9", "vmaf >= 93"],
        {"pitch_hz": 438.1, "harmonics": 5, "psnr": 48.3, "ssim": 0.9977,
         "ssim_degraded": 0.77, "vmaf": 99.7})
    assert ok["passed"] and ok["skipped_n"] == 0, ok["checks"]
    # the real SSIM numbers from the flat-artwork audit: pass, but the control does
    # not separate, so the route refuses to gate on it
    weak = validate.run_acceptance(
        ["measured pitch within 10 Hz of 440", "at least 5 harmonics visible",
         "psnr >= 45", "degraded control < 0.9"],
        {"pitch_hz": 500.2, "harmonics": 2, "psnr": 39.5, "ssim_degraded": 0.987})
    assert weak["failed_n"] == 4, weak["checks"]


def test_pitch_rule_does_not_collide_with_colour_rules():
    """Several patterns share the shape "... word ... number", so pin that a pitch
    sentence is read as a pitch rule and not as a colour or delta-E claim."""
    r = validate.run_acceptance(["measured pitch within 10 Hz of 440"],
                                {"pitch_hz": 441.0})
    assert r["checks"][0]["status"] == "pass"
    assert r["checks"][0]["expected"] == "440.0\u00b110.0"

# --- honesty of the rule engine itself ----------------------------------------

def test_unmeasurable_pitch_fails_instead_of_crashing():
    """`pitch_hz: None` is a legitimate "the estimator found nothing" — the rule
    must fail with evidence, not raise TypeError inside the validator."""
    r = validate.run_acceptance(["measured pitch within 10 Hz of 440"],
                                {"pitch_hz": None})
    assert r["checks"][0]["status"] == "fail"
    assert r["checks"][0]["actual"] == "unmeasurable"
    r2 = validate.run_acceptance(["at least 5 harmonics visible"], {"harmonics": None})
    assert r2["checks"][0]["status"] == "fail"
    assert r2["checks"][0]["actual"] == "unmeasurable"


def test_palette_ceiling_is_not_read_as_the_color_floor():
    """"distinct colors at most 3" sits lexically inside the unique-colors
    pattern's reach. If the floor rule wins, a 4-colour poster with a rich
    gradient passes a *ceiling* it must fail — wrong rule, green verdict."""
    r = validate.run_acceptance(["distinct colors at most 3"],
                                {"palette_distinct_colors": 4, "unique_colors": 9000})
    assert r["checks"][0]["status"] == "fail"
    assert r["checks"][0]["expected"] == "<=3"
    assert r["checks"][0]["actual"] == 4


# --- regression pin: the rule->kind mapping of every shipped spec -------------
# Re-ordering _PATTERNS or rewording a pattern is a semantic change to every
# gate; here it shows up as a reviewable diff instead of a silent shift.

KIND_SNAPSHOT = {
    "dodge-headless.yaml": ["moved", "score_min", "hp_decreased", "terminated"],
    "film-mux.yaml": ["duration_range", "has_video", "has_audio", "av_sync"],
    "orbiting-cubes.yaml": ["duration_range", "resolution_exact", "max_black_run"],
    "poster-noise.yaml": ["resolution_exact", "unique_colors_min", "entropy_min"],
    "spectrogram-truth.yaml": ["sample_rate_exact", "duration_range", "peak_max_dbfs",
                               "not_silent", "resolution_exact", "pitch_within",
                               "harmonics_min", "psnr_min"],
    "swiss-poster.yaml": ["resolution_exact", "grid_left_max", "grid_baseline_max",
                          "palette_max", "palette_exact_pct_min", "no_overflow",
                          "font_resolved"],
    "synth-pad.yaml": ["duration_range", "sample_rate_exact", "lufs_target",
                       "peak_max_dbfs", "not_silent", "clipping_max_pct", "dc_max"],
    "variable-weight.yaml": ["axis_range", "ink_monotonic", "resolution_exact",
                             "duration_range"],
}


def test_rule_kind_snapshot_over_shipped_specs():
    for name, kinds in KIND_SNAPSHOT.items():
        raw = spec_mod.load_raw(SPEC / name)
        assert len(raw["acceptance"]) == len(kinds), name
        for rule, kind in zip(raw["acceptance"], kinds):
            assert validate._match_rule(rule)[0] == kind, (name, rule)
