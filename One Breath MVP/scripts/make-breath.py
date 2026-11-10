#!/usr/bin/env python3
"""Generate assets/breath-pad.wav — the One Breath audio bed.

One soft pad chord (C-E-G) breathing in and out over 8 seconds via the vcac
additive engine (deterministic: seed 7, fixed recipe). The amplitude envelope
returns to near-silence at the seam, so the file loops cleanly. Run from the
vcac repo root:  PYTHONPATH=src python "One Breath MVP/scripts/make-breath.py"
"""
import sys
from pathlib import Path

import numpy as np

VCAC_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(VCAC_SRC))
from vcac import audio, media  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "assets" / "breath-pad.wav"

sr, dur = 22050, 8.0
events = [{"at": 0, "dur": dur, "notes": ["C4", "E4", "G4"],
           "timbre": "pad", "gain": 0.5}]
a = audio.render(events, sr, dur, seed=7)
t = np.arange(len(a)) / sr
a = a * (0.3 + 0.7 * np.sin(np.pi * t / dur) ** 2)   # one breath, loop-safe
OUT.parent.mkdir(parents=True, exist_ok=True)
media.write_wav(OUT, a, sr)
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
