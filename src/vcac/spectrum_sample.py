"""Spectrogram route sample — the picture is checked by reading the sound back out of it.

Turning audio into an image is a *translation*, and a translation can lie: a wrong
axis scale, a clipped window, a filter that quietly normalises everything all still
produce a plausible-looking picture. So this route does not stop at "a PNG came
out". It measures the PNG, converts the brightest row back to hertz, and demands
that the answer agree with an independent FFT of the samples the synthesiser was
told to play. Two methods, two code paths, one number.

The second half of the case is an audit *of the measuring instrument*. Shipping a
re-encoded image normally gets an SSIM threshold, and on this kind of flat graphic
output SSIM turns out to be a poor gate: a faithful quality-80 WebP scores 0.9977
and a mangling quality-3 one scores 0.9870, so the whole usable distance between
"good" and "broken" is about 0.011 -- thinner than the 0.01 step any three-decimal
threshold would be set on. PSNR spreads the same two encodes by ~8.8 dB, which
leaves real room for a cut. The route therefore gates on PSNR and reports the SSIM
numbers as evidence, because a gate whose pass and fail cases sit one rounding
apart is not a gate (M0.2). The measured margins are written into report.json so
the reader can disagree with that judgement on the same data.

Run:
    $env:PYTHONPATH="src"; python -m vcac.spectrum_sample specs/examples/spectrogram-truth.yaml
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import ffmpeg, media, provenance, spec as spec_mod, validate


def synth(spec_dict: dict) -> np.ndarray:
    """Deterministic harmonic stack: f0 plus ``harmonics_to_play`` partials at 1/k
    amplitude, shaped by a raised-cosine attack/release so the tone has a steady
    middle for the row profile to be averaged over."""
    sr = int(spec_dict["sample_rate"])
    dur = float(spec_dict["duration"])
    f0 = float(spec_dict["fundamental_hz"])
    n_harm = int(spec_dict.get("harmonics_to_play", 5))
    seed = int(spec_dict.get("seed", 42))
    rng = np.random.default_rng(seed)

    n = int(round(sr * dur))
    t = np.arange(n) / sr
    a = np.zeros(n)
    for k in range(1, n_harm + 1):
        # a plain 1/k stack: the quietest of five partials then sits 14 dB under the
        # fundamental, which is inside the picture's display range -- so the harmonic
        # gate can demand all five without being handed them by a louder mix
        amp = 1.0 / k
        phase = float(rng.uniform(0, 2 * np.pi))
        a += amp * np.sin(2 * np.pi * f0 * k * t + phase)
    a /= np.max(np.abs(a)) if np.max(np.abs(a)) else 1.0

    env = np.ones(n)
    edge = int(sr * float(spec_dict.get("envelope_s", 0.02)))
    if edge > 0:
        ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, edge))
        env[:edge] = ramp
        env[-edge:] = ramp[::-1]
    return a * env * float(spec_dict.get("level", 0.4))


def row_to_hz(row: int, height: int, sr: int) -> float:
    """Only valid for ``scale=lin``: FFmpeg puts 0 Hz on the bottom row and Nyquist
    on the top, so the mapping is a straight line we can invert."""
    return (height - 1 - row) * (sr / 2.0) / (height - 1)


def read_pitch(gray: np.ndarray, sr: int) -> dict:
    """Recover the pitch from the *pixels*. The peak row alone resolves about 31 Hz,
    which would force a loose gate, so the estimate is the energy-weighted centroid
    over the rows around the peak -- sub-row precision, measured to hold to within a
    few hertz on the calibration tones in tests/e2e/test_routes.py."""
    prof = gray.mean(axis=1)
    h = prof.shape[0]
    peak = int(np.argmax(prof))
    lo, hi = max(0, peak - 3), min(h, peak + 4)
    w = prof[lo:hi] ** 2
    rows = np.arange(lo, hi)
    if w.sum() <= 0:
        return {"peak_row": peak, "pitch_hz": None, "profile": prof}
    cent_hz = float((w * np.array([row_to_hz(r, h, sr) for r in rows])).sum() / w.sum())
    return {"peak_row": peak, "pitch_hz": cent_hz, "profile": prof}


def count_harmonics(prof: np.ndarray, sr: int, f0: float, want: int) -> int:
    """Count partials the picture actually shows, from k=1 upward, stopping at the
    first miss -- so '5 harmonics' means five *contiguous* lines, not five somewhere."""
    h = prof.shape[0]
    span = max(2.0, (sr / 2.0) / (h - 1) * 1.5)
    ref = float(prof.max()) or 1.0
    got = 0
    for k in range(1, want + 1):
        target = f0 * k
        rows = [r for r in range(h) if abs(row_to_hz(r, h, sr) - target) <= span]
        if not rows:
            break
        best = max(rows, key=lambda r: prof[r])
        is_local_max = (best == 0 or prof[best] >= prof[best - 1]) and \
                       (best == h - 1 or prof[best] >= prof[best + 1])
        if prof[best] >= 0.05 * ref and is_local_max:
            got += 1
        else:
            break
    return got


def fft_pitch(samples: np.ndarray, sr: int) -> float:
    """The independent reading: same signal, different method, no image involved."""
    n = samples.shape[0]
    sp = np.abs(np.fft.rfft(samples * np.hanning(n)))
    i = int(np.argmax(sp))
    if 0 < i < len(sp) - 1:                       # parabolic interpolation, sub-bin
        d = (sp[i - 1] - sp[i + 1]) / (2 * (sp[i - 1] - 2 * sp[i] + sp[i + 1]))
        i += d
    return float(i * sr / n)


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    sr = int(spec_dict["sample_rate"])
    w_px, h_px = int(spec_dict["size"]["width"]), int(spec_dict["size"]["height"])

    samples = synth(spec_dict)
    wav = media.write_wav(out_dir / "tone.wav", samples, sr)

    png = ffmpeg.spectrogram_png(wav, out_dir / "spectrum.png", w_px, h_px)
    gray = np.asarray(Image.open(png).convert("L"), dtype=np.float64)

    got = read_pitch(gray, sr)
    pitch_hz = got["pitch_hz"]
    truth_hz = fft_pitch(samples, sr)
    harmonics = count_harmonics(got["profile"], sr, float(spec_dict["fundamental_hz"]),
                               int(spec_dict.get("harmonics_to_play", 5)))

    # --- delivery surface + metric audit: which number is allowed to gate us?
    q_ok = int(spec_dict.get("delivery_quality", 80))
    q_bad = int(spec_dict.get("control_quality", 3))
    good = ffmpeg.encode_webp(png, out_dir / "spectrum.webp", q_ok)
    ctl = ffmpeg.encode_webp(png, out_dir / "_control.webp", q_bad)
    ssim_ok, ssim_ok_line = ffmpeg.ssim_all(png, good)
    ssim_bad, _ = ffmpeg.ssim_all(png, ctl)
    psnr_ok, _ = ffmpeg.psnr_avg(png, good)
    psnr_bad, _ = ffmpeg.psnr_avg(png, ctl)
    ctl.unlink()                                  # the control is a measurement, not a deliverable

    rerender = ffmpeg.spectrogram_png(wav, out_dir / "_rerender.png", w_px, h_px)
    deterministic = (provenance.sha256_file(png) == provenance.sha256_file(rerender)
                     and provenance.sha256_bytes(np.asarray(samples, dtype=np.float32).tobytes())
                     == provenance.sha256_bytes(np.asarray(synth(spec_dict), dtype=np.float32).tobytes()))
    rerender.unlink()

    measured = {
        "width": w_px, "height": h_px,
        "sample_rate": sr,
        "duration": media.duration_s(samples, sr),
        "peak_dbfs": media.peak_dbfs(samples),
        "rms_dbfs": media.rms_dbfs(samples),
        "dc_offset": media.dc_offset(samples),
        "clipping_pct": media.clipping_pct(samples),
        "pitch_hz": pitch_hz,
        "target_hz": float(spec_dict["fundamental_hz"]),
        "harmonics": harmonics,
        "ssim": ssim_ok,
        "psnr": psnr_ok,
        "deterministic": deterministic,
    }
    report = validate.run_acceptance(spec_dict["acceptance"], measured)
    report["measured"] = measured
    report["cross_check"] = {
        "pitch_from_pixels_hz": None if pitch_hz is None else round(pitch_hz, 3),
        "pitch_from_fft_hz": round(truth_hz, 3),
        "spec_declared_hz": float(spec_dict["fundamental_hz"]),
        "agreement_delta_hz": None if pitch_hz is None else round(abs(pitch_hz - truth_hz), 3),
        "peak_row": got["peak_row"],
        "row_resolution_hz": round((sr / 2.0) / (h_px - 1), 3),
    }
    report["metric_audit"] = {
        "delivery": {"quality": q_ok, "bytes": good.stat().st_size,
                     "ssim": ssim_ok, "psnr": psnr_ok, "ssim_line": ssim_ok_line},
        "control": {"quality": q_bad, "ssim": ssim_bad, "psnr": psnr_bad},
        # How far apart the faithful and the mangling encode actually land.
        "margins": {"ssim": None if None in (ssim_ok, ssim_bad)
                    else round(ssim_ok - ssim_bad, 5),
                    "psnr_db": None if None in (psnr_ok, psnr_bad)
                    else round(psnr_ok - psnr_bad, 2)},
        # A threshold is only stable if it can sit between pass and fail with one
        # full quantum of its own metric on each side. Three-decimal SSIM is read
        # and set in steps of 0.01, so it needs a gap of at least 0.02 to be usable.
        "criterion": {"ssim_quantum": 0.01, "ssim_gap_needed": 0.02,
                      "ssim_gate_stable": None if None in (ssim_ok, ssim_bad)
                      else (ssim_ok - ssim_bad) >= 0.02},
        "gate_used": "psnr",
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # The payload of this route is a *pair*: what was played and what the picture
    # says was played. Both halves go into one digest, so the reproducibility claim
    # covers the translation and not just the source.
    chash = provenance.sha256_bytes(
        np.asarray(samples, dtype=np.float32).tobytes()
        + gray.astype(np.uint8).tobytes())
    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict, content_hash=chash,
        artifact_hashes={"tone.wav": provenance.sha256_file(wav),
                         "spectrum.png": provenance.sha256_file(png),
                         "spectrum.webp": provenance.sha256_file(good)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["tone.wav", "spectrum.png", "spectrum.webp", "report.json",
                   "manifest.json"],
        notes=list(spec_dict.get("assumptions", [])) + [
            "scale=lin is load-bearing: the row->Hz inversion is only true for a "
            "linear frequency axis",
            f"SSIM is reported but does not gate delivery: the faithful encode scored "
            f"{ssim_ok} and the quality-{q_bad} control {ssim_bad}, a gap of "
            f"{report['metric_audit']['margins']['ssim']} against a 0.01 threshold "
            f"quantum; PSNR put the same pair {report['metric_audit']['margins']['psnr_db']} dB apart",
        ],
        pipeline="vcac-spectrum/0.1")
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="vcac sound->picture route sample")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    spec_dict = spec_mod.load_raw(a.spec)
    out_dir = a.out or (Path("outputs") / spec_dict["id"])
    r = run(a.spec, out_dir)
    rep, m = r["report"], r["report"]["measured"]
    cc, ma = rep["cross_check"], rep["metric_audit"]

    def num(v, nd=5):
        return "n/a" if v is None else f"{v:.{nd}f}"

    print(f"[vcac:spectrum] {spec_dict['id']} -> {r['out_dir']}")
    print(f"[vcac:spectrum] picture says {num(cc['pitch_from_pixels_hz'], 2)}Hz, fft says "
          f"{num(cc['pitch_from_fft_hz'], 2)}Hz (declared {cc['spec_declared_hz']}Hz, "
          f"delta {num(cc['agreement_delta_hz'], 3)}Hz, row grid {cc['row_resolution_hz']}Hz)")
    print(f"[vcac:spectrum] harmonics visible {m['harmonics']}  "
          f"ssim {num(ma['delivery']['ssim'])}/{num(ma['control']['ssim'])} "
          f"margin={ma['margins']['ssim']} (stable gate={ma['criterion']['ssim_gate_stable']})  "
          f"psnr {num(ma['delivery']['psnr'], 1)}/{num(ma['control']['psnr'], 1)} dB "
          f"margin={ma['margins']['psnr_db']}dB")
    for c in rep["checks"]:
        extra = (f"  (exp {c.get('expected')}, act {c.get('actual')})"
                 if c["status"] in ("pass", "fail") else f"  ({c.get('reason','')})")
        print(f"  [{c['status'].upper():7}] {c['id']}{extra}")
    print(f"[vcac:spectrum] run_id={r['manifest']['run_id']}")
    print(f"[vcac:spectrum] ACCEPTANCE {'PASSED' if rep['passed'] else 'FAILED'}")
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
