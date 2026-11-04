"""Unit tests for the media primitives (exact numpy/PIL/WAV metrics)."""
from __future__ import annotations

import json

import numpy as np

from vcac import media


def test_silence_measures_are_finite_json():
    """A digital-silence peak/RMS is -inf dBFS, and json.dumps writes that as
    ``-Infinity`` — which strict JSON parsers (and any downstream report
    consumer) reject. Silence gets a documented sentinel instead."""
    z = np.zeros(100, dtype=np.float32)
    assert media.peak_dbfs(z) == -120.0
    assert media.rms_dbfs(z) == -120.0
    roundtrip = json.loads(json.dumps({"p": media.peak_dbfs(z), "r": media.rms_dbfs(z)}))
    assert roundtrip == {"p": -120.0, "r": -120.0}


def test_non_silence_measures_unchanged():
    """The sentinel must not move real measurements: a full-scale sine sits at
    ~0 dBFS peak; 0.5 amplitude at ~-6 dB."""
    t = np.arange(480, dtype=np.float64) / 48000
    full = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    assert media.peak_dbfs(full) == media.peak_dbfs(full)  # finite
    assert abs(media.peak_dbfs(full) - 0.0) < 0.01
    half = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    assert abs(media.peak_dbfs(half) - (-6.0206)) < 0.01
