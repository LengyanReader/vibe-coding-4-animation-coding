"""Validate — objective probes + acceptance rules (README §5.2-7 / §12.5).

"No output is done without test evidence." The spec's ``acceptance`` list is
prose; here a tiny rule engine maps each supported prose rule to a coded check
against *measured* values, and returns a machine-readable report. Rules we do
not yet enforce are reported as ``skipped`` with a reason rather than silently
passing (M0.2 — never present an unverified claim as fact).

Determinism (README §12.3) is checked by the caller comparing two content
hashes; the result is folded into the report here.
"""
from __future__ import annotations

import re


def max_black_run_seconds(luma_by_frame, fps: int, black_below: float = 8.0):
    """Longest consecutive run of near-black frames, in seconds."""
    longest = cur = 0
    for luma in luma_by_frame:
        if luma < black_below:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return longest / fps if fps else 0.0


# --- rule engine -------------------------------------------------------------
_PATTERNS = [
    (re.compile(r"duration between ([\d.]+)\s*s? and ([\d.]+)\s*s?", re.I), "duration_range"),
    (re.compile(r"resolution exactly (\d+)\s*x\s*(\d+)", re.I), "resolution_exact"),
    (re.compile(r"no black frame longer than ([\d.]+)\s*s", re.I), "max_black_run"),
    (re.compile(r"not silent|audio", re.I), "audio"),  # out of scope: silent film
]


def _match_rule(rule: str):
    for pat, kind in _PATTERNS:
        m = pat.search(rule)
        if m:
            return kind, m
    return None, None


def run_acceptance(acceptance, measured: dict) -> dict:
    """measured keys: duration, width, height, max_black_run_seconds, deterministic."""
    checks = []
    passed = failed = skipped = 0
    for rule in acceptance:
        kind, m = _match_rule(rule)
        if kind == "duration_range":
            lo, hi = float(m.group(1)), float(m.group(2))
            ok = lo <= measured["duration"] <= hi
            val = measured["duration"]
        elif kind == "resolution_exact":
            w, h = int(m.group(1)), int(m.group(2))
            ok = measured["width"] == w and measured["height"] == h
            val = f'{measured["width"]}x{measured["height"]}'
            lo, hi = f"{w}x{h}", f"{w}x{h}"
        elif kind == "max_black_run":
            limit = float(m.group(1))
            ok = measured["max_black_run_seconds"] <= limit
            val = measured["max_black_run_seconds"]
            lo, hi = 0, limit
        elif kind == "audio":
            checks.append({"id": rule, "status": "skipped",
                           "reason": "silent film — audio rules not enforced in loop #1"})
            skipped += 1
            continue
        else:
            checks.append({"id": rule, "status": "skipped",
                           "reason": "no coded check for this rule yet"})
            skipped += 1
            continue
        checks.append({"id": rule, "status": "pass" if ok else "fail",
                       "expected": f"{lo}..{hi}" if kind != "resolution_exact" else f"{w}x{h}",
                       "actual": val})
        passed += int(ok)
        failed += int(not ok)

    # determinism is a standing gate regardless of prose rules
    det_ok = measured.get("deterministic", False)
    checks.append({"id": "determinism: same seed -> identical frame content hash",
                   "status": "pass" if det_ok else "fail",
                   "expected": "equal", "actual": "equal" if det_ok else "differ"})
    passed += int(det_ok)
    failed += int(not det_ok)

    return {
        "passed": failed == 0,
        "checks_total": len(checks),
        "passed_n": passed,
        "failed_n": failed,
        "skipped_n": skipped,
        "checks": checks,
    }
