"""Probe 5: showspectrumpic geometry + can ffmpeg's ssim/libvmaf run on stills?

The spectrogram route only means something if row -> Hz is a fact we measured,
not an assumption lifted from a man page that describes a different mode.
"""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

# evidence lands under outputs/ (gitignored), never in the source tree
d = Path(__file__).resolve().parents[2] / "outputs" / "_probe"
d.mkdir(parents=True, exist_ok=True)
SR = 48000
for f0 in (440.0, 1500.0):
    n = int(SR * 1.0)
    t = np.arange(n) / SR
    a = 0.4 * np.sin(2 * np.pi * f0 * t)
    pcm = (np.clip(a, -1, 1) * 32767).astype("<i2")
    import wave
    p = d / f"sine{int(f0)}.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    out = d / f"spec{int(f0)}.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p),
                    "-lavfi", "showspectrumpic=s=512x256:mode=combined:scale=lin:legend=0",
                    str(out)], check=True)
    g = np.asarray(Image.open(out).convert("L"), dtype=np.float64)
    row = g.mean(axis=1)
    peak = int(np.argmax(row))
    h = g.shape[0]
    # hypothesis A: row 0 = Nyquist, row h-1 = 0 Hz
    est = (SR / 2) * (1 - peak / (h - 1))
    print(f"f0={f0:7.1f} png={out.name} {g.shape} peak_row={peak} est_lin={est:.1f}")
    # FFT ground truth
    sp = np.abs(np.fft.rfft(a * np.hanning(n)))
    fr = np.fft.rfftfreq(n, 1 / SR)
    print(f"           fft peak={fr[np.argmax(sp)]:.1f} Hz")

# --- ssim / libvmaf on stills
for a, b in [("spec440.png", "spec1500.png"), ("spec440.png", "spec440.png")]:
    r = subprocess.run(["ffmpeg", "-loglevel", "info", "-i", str(d / a), "-i", str(d / b),
                        "-lavfi", "ssim", "-f", "null", "-"], capture_output=True, text=True)
    line = [l for l in r.stderr.splitlines() if "SSIM" in l and "P_" not in l]
    print(f"ssim {a} vs {b}: {line[-1].strip() if line else 'NO LINE'}")
r = subprocess.run(["ffmpeg", "-loglevel", "info", "-i", str(d / "spec440.png"),
                    "-i", str(d / "spec1500.png"), "-lavfi", "libvmaf", "-f", "null", "-"],
                   capture_output=True, text=True)
print("libvmaf on stills:", [l.strip() for l in r.stderr.splitlines() if "VMAF score" in l] or "no score")
