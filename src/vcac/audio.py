"""Symbolic-to-wave additive synthesiser (pure NumPy, deterministic).

The audio route's zero-install renderer: it turns a tiny note-event list into a
float waveform. This is *not* a fake of music21/FluidSynth — it is the same
"code makes the media" idea one level down: the timbres are explicit harmonic
sums, so the output is bit-reproducible from (events, sr, seed) with no SoundFont
or GPU. When music21/FluidSynth are adopted (docs/roadmap-development.md) they
become *alternative* renderers behind the capability registry, not a rewrite.
"""
from __future__ import annotations

from pathlib import Path

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
    # felt piano: strong fundamental, weak low partials, negligible top —
    # the additive answer to a soft hammered string; per-partial decay below
    "felt-piano": [(1, 1.0), (2, 0.20), (3, 0.08), (4, 0.035), (5, 0.015)],
}


def _partial(freq: float, n: int, sr: int, phase: float) -> np.ndarray:
    t = (np.arange(n) / sr) + phase
    return np.sin(2 * np.pi * freq * t)


def render(events, sr: int, total_dur: float, seed: int = 0) -> np.ndarray:
    """events: [{at, dur, notes:[names], timbre, gain}] -> mono float array.

    Envelope selection is per timbre (audit B note): the shared ADSR is right
    for sustained pads/winds, but a struck string must *decay* — and higher
    partials decay faster. ``felt-piano`` therefore gets its own per-partial
    exponential envelope applied inside the harmonic loop; every other timbre
    keeps the ADSR. Both paths are bit-reproducible from (events, sr, seed).

    The ADSR branch keeps its historical order — **normalise, then shape**.
    Swapping the two rescales each event against its own envelope peak rather
    than its raw peak, which silently rewrites the recorded golden payload of
    every existing audio route (``2f9351c5…``). That is provenance, not taste."""
    total_n = int(round(total_dur * sr))
    out = np.zeros(total_n)
    rng = np.random.default_rng(seed)
    for ev in events:
        at = int(round(float(ev.get("at", 0)) * sr))
        dur = float(ev.get("dur", 0.25))
        n = min(int(round(dur * sr)), total_n - at)
        if n <= 0:
            continue
        timbre_name = ev.get("timbre", "sine")
        timbre = _TIMBRES.get(timbre_name, _TIMBRES["sine"])
        gain = float(ev.get("gain", 0.5))
        seg = np.zeros(n)
        if timbre_name == "felt-piano":
            t = np.arange(n) / sr
            attack = np.clip(t / 0.008, 0, 1)
            for note in ev.get("notes", []):
                f0 = note_to_freq(note)
                tau0 = max(0.30, dur * 0.55)
                for mult, amp in timbre:
                    detune = 1.0 + rng.normal(0, 0.0008)
                    tau = tau0 / (1.0 + 0.45 * (mult - 1))
                    seg += amp * attack * np.exp(-t / tau) \
                        * _partial(f0 * mult * detune, n, sr, phase=0.0)
            seg = seg / max(1e-6, np.max(np.abs(seg)))  # decay is already inside
        else:
            env = _adsr(n, sr, r=min(0.1, dur * 0.3))
            for note in ev.get("notes", []):
                f0 = note_to_freq(note)
                for mult, amp in timbre:
                    # slight per-note detune from seeded rng -> stable across reruns
                    detune = 1.0 + rng.normal(0, 0.0008)
                    seg += amp * _partial(f0 * mult * detune, n, sr, phase=0.0)
            seg = seg / max(1e-6, np.max(np.abs(seg)))  # normalise per event
        if timbre_name == "felt-piano":
            out[at:at + n] += gain * seg
        else:
            # the accumulation is spelled `(gain * env) * seg` by association,
            # exactly as it was before the felt-piano branch existed. Factoring
            # it as gain * (env * seg) is the same real number and a different
            # float64: ULP shifts survive the float32 payload cast and move the
            # content hash (measured: 2f9351c5 -> 5da9a9e0). Bit-reproducibility
            # of a committed route is a stronger contract than DRY here.
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


def _note_midi(name: str) -> int:
    i = 1
    while i < len(name) and name[i] in "#b":
        i += 1
    letter, _accidental, octave = name[:1] + name[1:i], name[i:], int(name[i:])
    if letter not in _SEMITONE:
        raise ValueError(f"bad note: {name!r}")
    return 69 + (octave - 4) * 12 + _SEMITONE[letter]


# --- the kern-piano composer: a reviewable score, not improvisation ----------

# LH broken-chord pattern per bar: (scale-degree index, beat, dur_beats).
# chords are (root, third, fifth) names; pattern = root2, fifth3, tenth4, fifth3.
_LH_PATTERN = [(0, 0.0, 1.0), (2, 1.0, 1.0), (1, 2.0, 1.0), (2, 3.0, 1.0),
               (0, 4.0, 1.0), (2, 5.0, 1.0), (1, 6.0, 1.0), (2, 7.0, 1.0)]

# RH melody, form A–A′–B–A″ over 8 bars: (bar, beat, dur_beats, note, gain).
_MELODY = [
    (0, 0.0, 1.0, "E5", 0.60), (0, 1.0, 1.0, "G5", 0.55), (0, 2.0, 2.0, "C6", 0.62),
    (1, 0.0, 1.0, "A5", 0.58), (1, 1.0, 1.0, "G5", 0.54), (1, 2.0, 2.0, "E5", 0.58),
    (2, 0.0, 1.0, "G5", 0.56), (2, 1.0, 1.0, "E5", 0.52),
    (2, 2.0, 1.0, "D5", 0.52), (2, 3.0, 1.0, "C5", 0.50),
    (3, 0.0, 1.0, "D5", 0.54), (3, 1.0, 1.0, "E5", 0.56), (3, 2.0, 2.0, "G5", 0.60),
    (4, 0.0, 1.0, "C6", 0.62), (4, 1.0, 1.0, "A5", 0.56),
    (4, 2.0, 1.0, "G5", 0.54), (4, 3.0, 1.0, "E5", 0.52),
    (5, 0.0, 1.0, "G5", 0.55), (5, 1.0, 1.0, "A5", 0.56), (5, 2.0, 2.0, "C6", 0.60),
    (6, 0.0, 1.0, "A5", 0.56), (6, 1.0, 1.0, "G5", 0.52),
    (6, 2.0, 1.0, "E5", 0.52), (6, 3.0, 1.0, "D5", 0.50),
    (7, 0.0, 3.0, "C5", 0.52),
]

# one soft pad bed per two bars, an octave-below triad + added 9th colour
_PAD_EVERY = 2


def piano_events(spec_dict: dict) -> list:
    """Kevin Kern-style neoclassical study (quiet felt piano, warm harmony).

    The piece is **authored data** — every note of the melody and the
    left-hand pattern is written out here, so the score is reviewable note by
    note and nothing depends on improvisation. ``key_root`` transposes the
    whole thing; the seed is unused by the composer itself (rendering detune
    handles the humanisation) because a composition is not a random variable.
    Form over 8 bars: A – A′ – B – A″, C-major ballad harmony, LH broken
    chords in eighths, RH melody with phrase-shaped gains, a soft pad bed
    under every two bars."""
    tempo = float(spec_dict.get("tempo", 72))
    bars = int(spec_dict.get("bars", 8))
    beat = 60.0 / tempo
    root_name = spec_dict.get("key_root", "C4")
    # transpose everything by (key_root - C4) semitones
    shift = _note_midi(root_name) - _note_midi("C4")

    def _t(name: str) -> str:
        midi = _note_midi(name) + shift
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[midi % 12] + str(midi // 12 - 1)

    _CHORDS = [
        ["C3", "E3", "G3"],   # C
        ["A2", "C3", "E3"],   # Am
        ["F2", "A2", "C3"],   # F
        ["G2", "B2", "D3"],   # G
    ]
    _BAR_CHORD = [0, 1, 2, 3, 0, 1, 2, 3]   # C Am F G C Am F G
    events = []
    for b in range(bars):
        chord = [_t(n) for n in _CHORDS[_BAR_CHORD[b % len(_BAR_CHORD)]]]
        start = b * 4 * beat
        # pad bed every _PAD_EVERY bars
        if b % _PAD_EVERY == 0:
            events.append({
                "at": start, "dur": _PAD_EVERY * 4 * beat,
                "notes": chord, "timbre": "pad", "gain": 0.16})
        # LH broken chords (felt-piano, low register)
        for idx, off, dur in _LH_PATTERN:
            events.append({"at": start + off * beat / 2, "dur": min(1.6, dur * beat * 1.8),
                           "notes": [chord[idx % len(chord)]],
                           "timbre": "felt-piano", "gain": 0.30})
        # RH melody
        for m_bar, m_off, m_dur, note, g in _MELODY:
            if m_bar == b:
                events.append({"at": start + m_off * beat, "dur": m_dur * beat * 1.05,
                               "notes": [_t(note)], "timbre": "felt-piano", "gain": g})
    return events


def apply_room(samples: np.ndarray, sr: int, reverb: dict | None) -> np.ndarray:
    """Deterministic synthetic room for an already-rendered (n, ch) array:
    FFT convolution with a fixed exponential-decay-noise IR. Lives in
    numpy/scipy (not an ffmpeg filter) so the audio path stays
    bit-reproducible; the IR seed is a constant, so the room never changes."""
    if not reverb:
        return samples
    from scipy.signal import fftconvolve  # deferred: pure-numpy imports stay cheap
    seconds = float(reverb.get("seconds", 1.6))
    wet = float(reverb.get("wet", 0.22))
    n = int(sr * seconds)
    t = np.arange(n) / sr
    rng = np.random.default_rng(1234)      # fixed IR seed: the room never changes
    ir = rng.normal(0, 1, n) * np.exp(-t / max(0.2, seconds * 0.3))
    fade = int(0.005 * sr)
    ir[:fade] *= np.linspace(0, 1, fade)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet_sig = np.stack([fftconvolve(samples[:, ch], ir)[: len(samples)]
                        for ch in range(samples.shape[1])], axis=1)
    out = samples * (1 - wet) + wet_sig * wet
    peak = np.max(np.abs(out)) or 1.0
    return out / peak * 0.9


def render_stereo(events, sr: int, total_dur: float, seed: int = 0,
                  reverb: dict | None = None) -> np.ndarray:
    """Two decorrelated mono renders (left/right detune streams) -> stereo,
    then the optional room of :func:`apply_room`."""
    left = render(events, sr, total_dur, seed=seed)
    right = render(events, sr, total_dur, seed=seed + 977)
    return apply_room(np.stack([left, right], axis=1), sr, reverb)


def _vlq(value: int) -> bytes:
    out = bytearray([value & 0x7F])
    value >>= 7
    while value:
        out.insert(0, 0x80 | (value & 0x7F))
        value >>= 7
    return bytes(out)


def write_midi(events, path, tempo: float, tpq: int = 480) -> Path:
    """Minimal Standard MIDI File writer (format 0, one track, zero deps).

    FluidSynth's CLI consumes MIDI, not event lists, so the composed score is
    serialised here. Deterministic: events sorted by tick with note-offs
    before note-ons at equal ticks; velocity maps linearly from the event
    gain. Program 0 = Acoustic Grand."""
    ticks_per_sec = tempo / 60.0 * tpq
    evs = []
    for ev in events:
        for note in ev.get("notes", []):
            t0 = int(round(float(ev.get("at", 0)) * ticks_per_sec))
            t1 = t0 + max(1, int(round(float(ev.get("dur", 0.25)) * ticks_per_sec)))
            vel = max(1, min(127, int(round(float(ev.get("gain", 0.5)) * 160))))
            evs.append((t0, 1, 0x90, _note_midi(note), vel))
            evs.append((t1, 0, 0x80, _note_midi(note), 0))
    evs.sort(key=lambda e: (e[0], e[1]))

    track = bytearray()
    track += _vlq(0) + b"\xFF\x51\x03" + int(round(60_000_000 / tempo)).to_bytes(3, "big")
    track += _vlq(0) + b"\xC0\x00"
    last = 0
    for tick, _kind, status, note, vel in evs:
        track += _vlq(tick - last) + bytes([status, note, vel])
        last = tick
    track += _vlq(0) + b"\xFF\x2F\x00"

    header = (b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big")
              + (1).to_bytes(2, "big") + tpq.to_bytes(2, "big"))
    blob = header + b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(blob)
    return p
