"""Unit tests for the acceptance rule engine (the verify-before-done core)."""
from __future__ import annotations

from vcac import validate


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
