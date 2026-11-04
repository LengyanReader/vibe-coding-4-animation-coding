"""Media primitives shared by the sample routes (README §6 renderers/base idea).

Small, honest converters between NumPy arrays, Pillow images and PCM WAV, plus
the exact, deterministic audio measurements the validators rely on. Everything
here is pure-Python/numpy so the routes run with zero external installs; the
"real tool" versions (music21, FluidSynth, Blender, pygame) plug in later as
registry-gated alternatives, not replacements.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from PIL import Image


# --- image ------------------------------------------------------------------
def arr_to_image(a: np.ndarray) -> Image.Image:
    """uint8 (H,W,3) or (H,W) -> PIL RGB image."""
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    if a.dtype != np.uint8:
        a = np.clip(a, 0, 255).astype(np.uint8)
    return Image.fromarray(a, "RGB")


def image_mean_luma(img: Image.Image) -> float:
    g = np.asarray(img.convert("L"), dtype=np.float64)
    return float(g.mean())


def unique_colors(img: Image.Image) -> int:
    rgb = np.asarray(img.convert("RGB")).reshape(-1, 3)
    return int(len(np.unique(rgb, axis=0)))


def entropy_bits(img: Image.Image) -> float:
    g = np.asarray(img.convert("L")).ravel()
    counts = np.bincount(g, minlength=256)
    p = counts[counts > 0] / counts.sum()
    return float(-(p * np.log2(p)).sum())


def palette_delta_e(img: Image.Image, palette_rgb) -> float:
    """Mean nearest-palette-colour CIE76 ΔE over sampled pixels (README §12.3)."""
    px = np.asarray(img.convert("RGB"), dtype=np.float64).reshape(-1, 3)
    if len(px) > 20000:  # deterministic stride sample, not random
        px = px[:: max(1, len(px) // 20000)]
    pal = np.asarray(palette_rgb, dtype=np.float64)
    # rgb -> lab (D65)
    def to_lab(rgb):
        c = rgb / 255.0
        m = c > 0.04045
        c = np.where(m, ((c + 0.055) / 1.055) ** 2.4, c / 12.92) * 95.0
        x, y, z = (c @ np.array([[0.4124, 0.3576, 0.1805],
                                 [0.2126, 0.7152, 0.0722],
                                 [0.0193, 0.1192, 0.9505]]).T).T
        x /= 95.047; z /= 108.883
        f = lambda t: np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)
        fx, fy, fz = f(x), f(y), f(z)
        return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], -1)
    lab_px, lab_pal = to_lab(px), to_lab(pal)
    d = np.min(np.linalg.norm(lab_px[:, None, :] - lab_pal[None, :, :], axis=-1), axis=1)
    return float(d.mean())


# --- audio (PCM16 WAV) ------------------------------------------------------
def write_wav(path: Path, samples: np.ndarray, sr: int, channels: int = 1) -> Path:
    """float [-1,1] (n,) or (n,channels) -> 16-bit PCM WAV via stdlib wave."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    a = np.asarray(samples, dtype=np.float64)
    if a.ndim == 1:
        a = a[:, None]
    a = np.clip(a, -1.0, 1.0)
    pcm = (a * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """PCM16 WAV -> (float [-1,1] shaped (n,channels), sr)."""
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    a = data.astype(np.float64) / 32767.0
    return a.reshape(-1, ch), sr


# --- audio measurements (exact, deterministic) ------------------------------
def peak_dbfs(a: np.ndarray) -> float:
    p = float(np.max(np.abs(a))) if a.size else 0.0
    return -np.inf if p == 0 else 20 * np.log10(p)


def rms_dbfs(a: np.ndarray) -> float:
    r = float(np.sqrt(np.mean(a ** 2))) if a.size else 0.0
    return -np.inf if r == 0 else 20 * np.log10(r)


def dc_offset(a: np.ndarray) -> float:
    return float(np.mean(a)) if a.size else 0.0


def clipping_pct(a: np.ndarray, thresh: float = 0.999) -> float:
    if not a.size:
        return 0.0
    return float(np.mean(np.abs(a) >= thresh) * 100.0)


def duration_s(a: np.ndarray, sr: int) -> float:
    return float(a.shape[0]) / sr if sr else 0.0
