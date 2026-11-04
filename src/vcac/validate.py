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
# Each rule maps prose -> a coded check that declares the measured keys it needs.
# If a route did not measure those keys the rule is reported `skipped` with a
# reason, never silently passed (M0.2). `NUM` matches -?d+.d+.
_NUM = r"-?\d+(?:\.\d+)?"
_PATTERNS = [
    (re.compile(rf"duration between ({_NUM})\s*s? and ({_NUM})\s*s?", re.I),
     "duration_range", ("duration",)),
    (re.compile(r"resolution exactly (\d+)\s*x\s*(\d+)", re.I),
     "resolution_exact", ("width", "height")),
    (re.compile(rf"no black frame longer than ({_NUM})\s*s", re.I),
     "max_black_run", ("max_black_run_seconds",)),
    # MOST-SPECIFIC-FIRST: "distinct colors at most N" sits lexically inside the
    # unique-colors pattern's reach; if the generic floor rule matched first, a
    # ceiling would be evaluated as a floor (wrong rule, green verdict). The
    # ceiling pattern (palette optional in the wording) therefore sits ABOVE the
    # generic color-floor pattern.
    (re.compile(rf"(?:distinct|usable)\s+(?:palette\s+)?colou?rs?\s+at most\s+(\d+)", re.I),
     "palette_max", ("palette_distinct_colors",)),
    (re.compile(rf"(?:unique colors|distinct colors)[^0-9]*(?:>=|at least|>|more than)?\s*(\d+)", re.I),
     "unique_colors_min", ("unique_colors",)),
    (re.compile(rf"entropy\s*(?:>|above)\s*({_NUM})", re.I), "entropy_min", ("entropy_bits",)),
    (re.compile(rf"(?:palette|\u0394e|delta ?e)[^0-9<]*<\s*({_NUM})", re.I),
     "delta_e_max", ("palette_delta_e",)),
    (re.compile(r"sample rate exactly (\d+)", re.I), "sample_rate_exact", ("sample_rate",)),
    (re.compile(rf"channels? exactly (\d+)", re.I), "channels_exact", ("channels",)),
    (re.compile(rf"peak below ({_NUM})\s*dbfs", re.I), "peak_max_dbfs", ("peak_dbfs",)),
    (re.compile(rf"(?:lufs|loudness)[^0-9-]*({_NUM})\s*lufs?", re.I),
     "lufs_target", ("lufs_i",)),
    (re.compile(r"not silent", re.I), "not_silent", ("rms_dbfs",)),
    (re.compile(rf"clipping[^0-9]*<\s*({_NUM})\s*%", re.I), "clipping_max_pct", ("clipping_pct",)),
    # --- layout / grid route (styles.md §10: a movement is a verifiable 4-tuple) ---
    (re.compile(rf"left edges? within ({_NUM})\s*px of the column grid", re.I),
     "grid_left_max", ("left_edge_max_offset_px",)),
    (re.compile(rf"tops? within ({_NUM})\s*px of the baseline grid", re.I),
     "grid_baseline_max", ("baseline_max_offset_px",)),
    (re.compile(r"no text overflows the canvas", re.I),
     "no_overflow", ("overflow_elements",)),
    (re.compile(rf"at least ({_NUM})\s*% of pixels are exact palette colors", re.I),
     "palette_exact_pct_min", ("palette_exact_pct",)),
    (re.compile(r"every declared font family resolves \(no silent fallback\)", re.I),
     "font_resolved", ("fonts_unresolved",)),
    # --- variable-font route: the axis must be *visible in the pixels* ---
    (re.compile(r"ink increases monotonically with the weight axis", re.I),
     "ink_monotonic", ("ink_monotonic",)),
    (re.compile(rf"weight axis spans ({_NUM}) to ({_NUM})", re.I),
     "axis_range", ("axis_from", "axis_to")),
    # --- spectrogram route: read the sound back OUT of the picture ---
    (re.compile(rf"measured pitch within ({_NUM})\s*Hz of ({_NUM})", re.I),
     "pitch_within", ("pitch_hz",)),
    (re.compile(rf"at least (\d+) harmoni[cz]s? (?:are )?visible", re.I),
     "harmonics_min", ("harmonics",)),
    # --- perceptual quality gates (libvmaf / ssim / psnr via ffmpeg) ---
    (re.compile(rf"(?:vmaf)[^0-9]*>=\s*({_NUM})", re.I), "vmaf_min", ("vmaf",)),
    (re.compile(rf"(?:ssim)[^0-9]*>=\s*({_NUM})", re.I), "ssim_min", ("ssim",)),
    (re.compile(rf"(?:degraded control|negative control)[^0-9]*<\s*({_NUM})", re.I),
     "ssim_control_max", ("ssim_degraded",)),
    (re.compile(rf"(?:psnr)[^0-9]*>=\s*({_NUM})", re.I), "psnr_min", ("psnr",)),
    (re.compile(rf"dc[^0-9]*<\s*({_NUM})", re.I), "dc_max", ("dc_offset",)),
    (re.compile(r"has video stream", re.I), "has_video", ("has_video",)),
    (re.compile(r"has audio stream", re.I), "has_audio", ("has_audio",)),
    (re.compile(rf"a/v sync within ({_NUM})\s*s", re.I), "av_sync", ("av_delta_seconds",)),
    (re.compile(r"player moved", re.I), "moved", ("moved",)),
    (re.compile(rf"score at least (\d+)", re.I), "score_min", ("score",)),
    (re.compile(r"hp decreased", re.I), "hp_decreased", ("hp", "start_hp")),
    (re.compile(r"session terminated", re.I), "terminated", ("terminated",)),
    (re.compile(r"audio", re.I), "audio_generic", ()),
]


def _match_rule(rule: str):
    for pat, kind, needs in _PATTERNS:
        m = pat.search(rule)
        if m:
            return kind, m, needs
    return None, None, ()


def _evaluate(kind, m, measured):
    """Return (ok, expected, actual) for a matched rule."""
    if kind == "duration_range":
        lo, hi = float(m.group(1)), float(m.group(2))
        v = measured["duration"]
        return lo <= v <= hi, f"{lo}..{hi}", round(v, 3)
    if kind == "resolution_exact":
        w, h = int(m.group(1)), int(m.group(2))
        return measured["width"] == w and measured["height"] == h, f"{w}x{h}", f'{measured["width"]}x{measured["height"]}'
    if kind == "max_black_run":
        lim = float(m.group(1)); v = measured["max_black_run_seconds"]
        return v <= lim, f"<={lim}", round(v, 3)
    if kind == "unique_colors_min":
        n = int(m.group(1)); v = measured["unique_colors"]
        return v >= n, f">={n}", v
    if kind == "entropy_min":
        x = float(m.group(1)); v = measured["entropy_bits"]
        return v > x, f">{x}", round(v, 3)
    if kind == "delta_e_max":
        x = float(m.group(1)); v = measured["palette_delta_e"]
        return v < x, f"<{x}", round(v, 3)
    if kind == "grid_left_max":
        x = float(m.group(1)); v = measured["left_edge_max_offset_px"]
        return v <= x, f"<={x}", round(v, 3)
    if kind == "grid_baseline_max":
        x = float(m.group(1)); v = measured["baseline_max_offset_px"]
        return v <= x, f"<={x}", round(v, 3)
    if kind == "palette_max":
        n = int(m.group(1)); v = measured["palette_distinct_colors"]
        return v <= n, f"<={n}", v
    if kind == "no_overflow":
        v = int(measured["overflow_elements"])
        return v == 0, "0 elements outside canvas", v
    if kind == "palette_exact_pct_min":
        x = float(m.group(1)); v = measured["palette_exact_pct"]
        return v >= x, f">={x}", round(v, 3)
    if kind == "font_resolved":
        v = list(measured["fonts_unresolved"])
        return not v, "all resolve", ("all resolve" if not v else f"fell back: {v}")
    if kind == "pitch_within":
        tol, target = float(m.group(1)), float(m.group(2))
        v = measured["pitch_hz"]
        if v is None:
            # "the estimator found nothing" is a legitimate measurement outcome;
            # the rule fails with evidence instead of raising inside the gate
            return False, f"{target}\u00b1{tol}", "unmeasurable"
        return abs(float(v) - target) <= tol, f"{target}\u00b1{tol}", round(float(v), 2)
    if kind == "harmonics_min":
        n = int(m.group(1)); v = measured["harmonics"]
        if v is None:
            return False, f">={n}", "unmeasurable"
        return int(v) >= n, f">={n}", int(v)
    if kind == "ink_monotonic":
        v = bool(measured["ink_monotonic"])
        return v, "strictly increasing", "increasing" if v else "not monotonic"
    if kind == "axis_range":
        lo, hi = float(m.group(1)), float(m.group(2))
        return (float(measured["axis_from"]) == lo and float(measured["axis_to"]) == hi,
                f"{lo}..{hi}", f'{measured["axis_from"]}..{measured["axis_to"]}')
    if kind == "vmaf_min":
        x = float(m.group(1)); v = measured["vmaf"]
        return v >= x, f">={x}", round(v, 2)
    if kind == "ssim_min":
        x = float(m.group(1)); v = measured["ssim"]
        return v >= x, f">={x}", round(v, 4)
    if kind == "ssim_control_max":
        x = float(m.group(1)); v = measured["ssim_degraded"]
        return v < x, f"<{x}", round(v, 4)
    if kind == "psnr_min":
        x = float(m.group(1)); v = measured["psnr"]
        return v >= x, f">={x}", round(v, 2)
    if kind == "sample_rate_exact":
        n = int(m.group(1)); v = measured["sample_rate"]
        return v == n, n, v
    if kind == "channels_exact":
        n = int(m.group(1)); v = measured["channels"]
        return v == n, n, v
    if kind == "peak_max_dbfs":
        x = float(m.group(1)); v = measured["peak_dbfs"]
        return v <= x, f"<={x}", round(v, 2)
    if kind == "lufs_target":
        target = float(m.group(1)); tol = 1.0
        v = measured["lufs_i"]
        return abs(v - target) <= tol, f"{target}\u00b1{tol}", round(v, 2)
    if kind == "not_silent":
        v = measured["rms_dbfs"]
        return v > -60.0, "> -60 dBFS", round(v, 2)
    if kind == "clipping_max_pct":
        x = float(m.group(1)); v = measured["clipping_pct"]
        return v < x, f"<{x}", round(v, 4)
    if kind == "dc_max":
        x = float(m.group(1)); v = measured["dc_offset"]
        return abs(v) < x, f"|DC|<{x}", round(v, 5)
    if kind == "has_video":
        v = bool(measured["has_video"])
        return v, "present", "present" if v else "missing"
    if kind == "has_audio":
        v = bool(measured["has_audio"])
        return v, "present", "present" if v else "missing"
    if kind == "av_sync":
        lim = float(m.group(1)); v = measured["av_delta_seconds"]
        return v <= lim, f"<={lim}", round(v, 4)
    if kind == "moved":
        v = bool(measured["moved"])
        return v, "nonzero", "moved" if v else "static"
    if kind == "score_min":
        n = int(m.group(1)); v = measured["score"]
        return v >= n, f">={n}", v
    if kind == "hp_decreased":
        return measured["hp"] < measured["start_hp"], f"< {measured['start_hp']}", measured["hp"]
    if kind == "terminated":
        v = bool(measured["terminated"])
        return v, "reached end", "ended" if v else "running"
    return None, None, None


def run_acceptance(acceptance, measured: dict) -> dict:
    checks, passed = [], 0
    failed = skipped = 0
    for rule in acceptance:
        kind, m, needs = _match_rule(rule)
        if kind is None:
            checks.append({"id": rule, "status": "skipped", "reason": "no coded check yet"})
            skipped += 1
            continue
        if kind == "audio_generic":
            checks.append({"id": rule, "status": "skipped", "reason": "generic audio rule; see specific checks"})
            skipped += 1
            continue
        missing = [k for k in needs if k not in measured]
        if missing:
            checks.append({"id": rule, "status": "skipped",
                           "reason": f"route did not measure {missing}"})
            skipped += 1
            continue
        ok, expected, actual = _evaluate(kind, m, measured)
        checks.append({"id": rule, "status": "pass" if ok else "fail",
                       "expected": expected, "actual": actual})
        passed += int(ok); failed += int(not ok)

    if "deterministic" in measured:
        det = measured["deterministic"]
        checks.append({"id": "determinism: same seed -> identical content hash",
                       "status": "pass" if det else "fail", "expected": "equal",
                       "actual": "equal" if det else "differ"})
        passed += int(det); failed += int(not det)

    return {"passed": failed == 0, "checks_total": len(checks), "passed_n": passed,
            "failed_n": failed, "skipped_n": skipped, "checks": checks}
