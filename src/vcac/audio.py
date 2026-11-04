"""Symbolic-to-wave additive synthesiser (pure NumPy, deterministic).

The audio route's zero-install renderer: it turns a tiny note-event list into a
float waveform. This is *not* a fake of music21/FluidSynth — it is the same
"code makes the media" idea one level down: the timbres are explicit harmonic
sums, so the output is bit-reproducible from (events, sr, seed) with no SoundFont
or GPU. When music21/FluidSynth are adopted (docs/roadmap-development.md) they
become *alternative* renderers behind the capability registry, not a rewrite.
"""
from __future__ import annotations

import numpy as np

_SEMITONE = {
    "C": -9, "C#": -8, "Db": -8, "D": -7, "D#": -6, "Eb": -6, "E": -5, "F": -4,
    "F#": -3, "Gb": -3, "G": -2, "G#": -1, "Ab": -1, "A": 0, "A#": 1, "Bb": 1, "B": 2,
}


def note_to_freq(name: str) -> float:
    """'A4'->440.0, 'F#3'->184.997... MIDI-number based (A4 = key 69)."""
    i = 1
    while i < len(name) and name[i] in "#b":
        i += 1
    letter, _accidental, octave = name[:1] + name[1:i], name[i:], int(name[i:])
    if letter not in _SEMITONE:
        raise ValueError(f"bad note: {name!r}")
    midi = 69 + (octave - 4) * 12 + _SEMITONE[letter]
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def _adsr(n: int, sr: int, a=0.01, d=0.05, s=0.7, r=0.08) -> np.ndarray:
    env = np.ones(n)
    na, nd, nr = int(a * sr), int(d * sr), int(r * sr)
    if na > 0:
        env[:na] = np.linspace(0, 1, na)
    if nd > 0:
        env[na:na + nd] = np.linspace(1, s, nd)
    if na + nd < n - nr:
        env[na + nd:n - nr] = s
    if nr > 0:
        env[n - nr:] = np.linspace(s, 0, nr)
    return np.clip(env, 0, 1)


# timbre -> list of (harmonic_multiple, relative_amplitude)
_TIMBRES = {
    "sine": [(1, 1.0)],
    "pad": [(1, 1.0), (2, 0.35), (3, 0.18), (4, 0.09)],
    "marimba": [(1, 1.0), (4, 0.25), (10, 0.08)],
    "bass-synth": [(1, 1.0), (2, 0.5), (3, 0.33), (4, 0.25), (5, 0.2)],
    "arp": [(1, 1.0), (3, 0.3), (5, 0.15)],
}


def _partial(freq: float, n: int, sr: int, phase: float) -> np.ndarray:
    t = (np.arange(n) / sr) + phase
    return np.sin(2 * np.pi * freq * t)


def render(events, sr: int, total_dur: float, seed: int = 0) -> np.ndarray:
    """events: [{at, dur, notes:[names], timbre, gain}] -> mono float array."""
    total_n = int(round(total_dur * sr))
    out = np.zeros(total_n)
    rng = np.random.default_rng(seed)
    for ev in events:
        at = int(round(float(ev.get("at", 0)) * sr))
        dur = float(ev.get("dur", 0.25))
        n = min(int(round(dur * sr)), total_n - at)
        if n <= 0:
            continue
        timbre = _TIMBRES.get(ev.get("timbre", "sine"), _TIMBRES["sine"])
        gain = float(ev.get("gain", 0.5))
        env = _adsr(n, sr, r=min(0.1, dur * 0.3))
        seg = np.zeros(n)
        for note in ev.get("notes", []):
            f0 = note_to_freq(note)
            for mult, amp in timbre:
                # slight per-note detune from seeded rng -> stable across reruns
                detune = 1.0 + rng.normal(0, 0.0008)
                seg += amp * _partial(f0 * mult * detune, n, sr, phase=0.0)
        seg = seg / max(1e-6, np.max(np.abs(seg)))  # normalise per event
        out[at:at + n] += gain * env * seg
    peak = np.max(np.abs(out)) or 1.0
    return out / peak * 0.9  # headroom; loudnorm pass sets final LUFS


def chord_events(tempo: float, key_root: str, bars: int, sr: int) -> list:
    """A tiny deterministic progression: pad chords + arpeggio on the beat."""
    root = note_to_freq(key_root)
    # natural-minor-ish triads relative to root semitone offsets
    triads = [[0, 3, 7], [5, 8, 12], [3, 7, 10], [7, 10, 14]]
    beat = 60.0 / tempo
    events = []
    for b in range(bars):
        chord = triads[b % len(triads)]
        start = b * 4 * beat
        notes = [_name_from_freq(root * 2 ** (semi / 12.0)) for semi in chord]
        events.append({"at": start, "dur": 4 * beat, "notes": notes,
                       "timbre": "pad", "gain": 0.5})
        for s in range(8):  # eighth-note arpeggio
            n = notes[s % len(notes)]
            events.append({"at": start + s * beat / 2, "dur": beat / 2,
                           "notes": [n], "timbre": "arp", "gain": 0.35})
    return events


def _name_from_freq(freq: float) -> str:
    midi = int(round(69 + 12 * np.log2(freq / 440.0)))
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi // 12) - 1
    return names[midi % 12] + str(octave)
