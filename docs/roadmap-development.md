# Development Roadmap — from proven routes to production directions

> Companion to `docs/tools.md` (the tool survey) and README §11 (milestones).
> This document answers: *given the routes that now actually run, where do we
> develop next, and how?* It is a plan, not a record of work done — nothing here
> has been built or installed unless §0 says it is proven.

---

## 0. What is proven today (the base we build on)

Five routes run end-to-end with **zero installs** (Pillow + NumPy + FFmpeg only),
each following the same invariant pipeline
`spec → render → measure → validate → manifest`, each with a determinism gate,
and each locked by a golden content hash in `tests/e2e/test_routes.py` (17 tests green):

| Route | Entry point | Medium | Gates | Golden content hash (prefix) |
|-------|-------------|--------|-------|------------------------------|
| Video | `vcac.firstloop` | 6s orbiting-cubes mp4 | duration, resolution, black-run, determinism | `d27999e7…` |
| Image | `vcac.image_sample` | value-noise poster png | resolution, unique-colors, entropy, determinism | `d538c350…` |
| Audio | `vcac.audio_sample` | R128 pad+arp wav | duration, sample-rate, LUFS, peak, silence, clip, DC, determinism | `2f9351c5…` |
| Film | `vcac.film_sample` | mux(video,audio) mp4 | duration, has-video, has-audio, A/V sync | (input-hash pinned) |
| Game | `vcac.game_sample` | headless dodge sim + playtest mp4 | moved, score, hp, terminated, determinism | `c67acbf8…` |

Shared, reusable primitives now in `src/vcac/`: `media.py` (numpy↔PIL↔WAV +
exact image/audio metrics), `audio.py` (deterministic additive synth), `ffmpeg.py`
(encode/probe/loudnorm/mux, argv-only), `validate.py` (measurement-driven rule
engine), `provenance.py` (content-hash + manifest). These are the levers every
direction below pulls on.

---

## 1. Design principles carried forward

1. **Code makes the media** — the LLM writes the *program*; deterministic tools
   render the output. No multimodal generation models in the render path.
2. **Registry-gated tools** — a planner may only select tools `scripts/doctor.py`
   reports AVAILABLE. New tools enter via the registry, never by assumption.
3. **Determinism + provenance** — same (spec, code, tools, seed) ⇒ same content
   hash. Manifests record code/tool hashes so any artifact is traceable/remakable.
4. **Acceptance-as-code, skipped ≠ passed** — prose rules map to coded checks;
   an unmeasured rule is reported `skipped` with a reason, never silently green.
5. **Composability** — media are DAG nodes. The film route proved two independent
   artifacts join on one clock; that is the template for everything larger.
6. **Zero-install first, pro tools as *alternative renderers*** — adopting
   music21/Blender/pygame replaces a renderer behind the same validate/manifest
   contract; it never rewrites the pipeline.

---

## 2. Route-by-route development directions

Each subsection: **now** → **next tier** → **tools to adopt** → **new acceptance
checks** → **the concrete sample to build next**.

### 2.1 Image

- **Now:** seeded fractal value-noise → palette-mapped, dithered poster; metrics
  for colour richness (unique colours), information (entropy), fidelity (ΔE).
- **Next tier of outputs:**
  - *Data-driven graphics*: charts, infographics, animated-data stills — a chart
    is just a deterministic mapping of a dataset through the palette.
  - *Generative families*: flow fields, reaction–diffusion, L-systems, truchet
    tiles, wave interference — each is a `render_image()` variant sharing media.py.
  - *Typography & layout*: title cards, posters, social cards (Pillow text + fonts).
  - *Vector export*: emit SVG from code for crisp logos/icons (then rasterise).
  - *Pixel/limited-palette art*: quantise to N colours → sprite sheets and textures
    that **feed the Game route** (image is upstream of game art).
- **Tools to adopt:** `matplotlib` (plots; deterministic with fixed seed/backend),
  optionally `cairosvg` (svg→png). Pillow already covers drawing + text.
- **New acceptance checks:** palette ΔE ceiling (already coded), WCAG contrast
  ratio, print DPI / bleed, ink coverage, "no unintended aliasing" (edge entropy).
- **Next sample:** *data-viz poster* — a seeded dataset → bar/line chart → PNG,
  gated on resolution + ΔE + contrast + determinism. Reuses the image harness 1:1.

### 2.2 Audio

- **Now:** additive synthesis (pad/arp/bass/marimba timbres as harmonic sums),
  two-pass EBU R128 mastering; metrics for LUFS/peak/RMS/DC/clipping/duration.
- **Next tier of outputs:**
  - *Real notation*: music21 → score → LilyPond → PDF/PNG (readable sheet music,
    not just sound). The symbolic layer becomes an inspectable artifact.
  - *Acoustic timbres*: FluidSynth + SoundFont for piano/strings/brass/kit.
  - *Rhythm & electronic*: kick/snare/hat synthesis, sidechain, filters (SciPy is
    already installed — biquads, FFT, resampling).
  - *Sound design / SFX*: noise bursts, sweeps, impacts — **consumed by Game & Film**.
  - *Adaptive/branching music*: stems + vertical layering for games (a music DAG).
  - *Voice-over*: optional TTS for explainer films.
- **Tools to adopt:** `music21`, `lilypond`, `fluidsynth` + a SoundFont. (SciPy present.)
- **New acceptance checks:** per-platform loudness (−14 LUFS streaming vs −16 here),
  true-peak (inter-sample, distinct from the sample-peak we measure), loudness
  range (LRA), tempo-grid alignment, stem loop continuity (seam energy).
- **Next sample:** *notated loop* — music21 writes 4 bars → LilyPond png (score) +
  FluidSynth wav (render); gate on score-file present + LUFS + note-count == spec.

### 2.3 Video

- **Now:** orthographic 3D cubes in Pillow → H.264; duration/resolution/black/determinism.
- **Next tier of outputs:**
  - *Transitions & titles*: crossfade/dissolve, lower-thirds, end-cards (FFmpeg filters).
  - *Subtitles / captions*: SRT/ASS burn-in; opens the door to localised deliverables.
  - *Multi-shot assembly*: a **timeline DAG** — brief → N scenes → per-scene render →
    concat. This is the film route generalised from 2 nodes to N.
  - *Math/explainer animation*: Manim (adopt) for formula-driven motion.
  - *Data-driven motion*: animate the Image route's charts frame-by-frame.
  - *Real 3D*: headless Blender for product shots (cubes → shaded/beauty renders).
  - *Colour pipeline*: LUTs, bt709 tagging, HDR→SDR tone-map.
- **Tools to adopt:** `manim` (community), later headless `blender` (heavier).
- **New acceptance checks:** shot count / scene boundaries, transition duration,
  subtitle coverage %, colour primaries (bt709) via ffprobe, optical flow sanity.
- **Next sample:** *scored, captioned explainer* — title card + animated chart +
  VO + burned captions, assembled from a timeline DAG (composes 2.1 + 2.2 + here).

### 2.4 Game

- **Now:** pure-Python fixed-timestep sim + scripted input + state assertions +
  3× replay determinism + rendered playtest mp4. The *harness* is the asset.
- **Next tier of outputs:**
  - *Real runtime*: pygame-ce (arcade, pip) / Godot (headless export) / Phaser (web).
    The sim becomes the reference model the real build is tested against.
  - *Richer mechanics*: physics (`pymunk`/SciPy), state machines, level data (Tiled).
  - *Asset pipeline*: sprites from the Image route + SFX/music from Audio route →
    the game **consumes other routes' artifacts** (cross-route DAG).
  - *Playtest hardening*: property-based invariants (no NaN/out-of-bounds), fuzzed
    input seeds, explicit win/lose-path coverage, perf (ticks/sec budget).
  - *Interactive narrative*: Ren'Py (adopt) — generated script → visual-novel build.
- **Tools to adopt:** `pygame-ce` first (pip, light), then `godot` / `renpy`.
- **New acceptance checks:** win & lose reachability, invariant safety, frame-budget,
  required-asset presence, save/load round-trip equality.
- **Next sample:** *30s pygame-ce microgame* — same scripted-input harness pointed at
  a pygame headless loop; assert identical final-state hash vs the pure sim.

### 2.5 Cross-media / product line (highest leverage)

The film mux was the first proof of **node composition**. Generalise it:

- **Timeline DAG engine**: one brief → a typed plan of image/audio/video/game nodes
  → each renders (cached) → assemble → **one manifest with sub-hashes**.
- **Deliverable bundles** (one brief, many artifacts):
  - *Explainer kit*: poster.png + voiceover + captions + 60s mp4 + landing page.
  - *Microgame*: sprites (image) + music/SFX (audio) + gameplay (game) → shippable.
  - *Visual novel*: Ren'Py script + sprites + music → narrative product.
- **Reproducible remake** (README §8): given a manifest, rebuild bit-identical by
  replaying the DAG with pinned code/tool hashes and cached node outputs.

---

## 3. From samples to the real pipeline (the P0 scaffold)

The five routes are currently sibling modules with light copy-paste orchestration.
The next **engineering** (not media) step makes them composable and cached:

- `registry.py` — merge `scripts/doctor.py` into a capability registry the planner reads.
- `pipeline.py` — a DAG executor with **content-hash caching**: a node re-runs only
  when its inputs change (so re-assembling a film reuses the cached video + audio
  instead of re-rendering). The film route is the seed of this executor.
- **Spec schema** — pydantic/JSON-Schema per medium (a superset of `spec.load_raw`).
- **Codegen stage** — for a *new* brief the LLM writes the renderer; the 5 sample
  renderers become the few-shot library it draws on. Flow: codegen → static check →
  sandboxed render → validate → repair loop (README §5).
- **CLI** — `vcac render | play | assemble | doctor` (typer; `firstloop:main` is the seed).

Do this *after* one more real route (e.g. data-viz or microgame) exists, so the
abstraction is extracted from ≥2 concrete cases rather than guessed.

---

## 4. Near-term loop queue (recommended order)

1. **Pipeline skeleton** — registry + DAG + content-hash cache. Turns samples into
   cached, composable builds. *(no install)*
2. **Data-viz image loop** — matplotlib chart → poster with ΔE/contrast gates. *(+1 install)*
3. **Notation audio loop** — music21 → LilyPond (score png/pdf) + FluidSynth (wav). *(installs)*
4. **30s pygame-ce microgame** — headless playtest reusing the game harness. *(+1 install)*
5. **Multi-shot explainer film** — timeline DAG: title + chart + gameplay + VO + captions.
   *(composes 1–4)*

Every loop is gated by `tests/e2e` + a new golden content hash before it is called done.

---

## 5. Install / adoption queue (requires explicit consent)

All entries are pip/winget and reversible; none is taken without a go-ahead.

| Package | Purpose | Install | Weight |
|---------|---------|---------|--------|
| matplotlib | data-viz images | `pip install matplotlib` | light |
| music21 | symbolic music / score | `pip install music21` | light |
| LilyPond | score engraving (pdf/png) | winget/choco | medium |
| FluidSynth + SoundFont | acoustic rendering | winget + SF2 file | medium |
| manim | math animation | `pip install manim` (+cairo) | medium |
| pygame-ce | real game runtime | `pip install pygame-ce` | light |
| SciPy | filters/FFT (audio, physics) | **already installed** | — |
| godot / renpy / blender | engines / 3D | external installers | heavy |

---

## 6. Honesty & risk notes

- The current renderers are **ours** (deterministic by construction), not yet the
  professional tools. Adopting real tools introduces version drift — already
  mitigated: `provenance.tool_versions` + `code_hashes` record everything a run used.
- **Container byte hashes are not pinned** (mp4/wav bytes can move with the encoder);
  the raw-payload content digest is the ground truth the tests lock.
- `loudnorm` reports **true-peak** (inter-sample); our numpy gate measures
  **sample-peak**. When a −1 dBTP platform target matters, add a TP measurement.
- The game sim is a **model** of a game, not a shipped engine; the durable artifact
  is the headless harness (scripted input → state assertions → determinism → render).
- Everything in §2–§5 is a **proposal**. No install or irreversible action has been
  taken; each loop in §4 starts only on your go-ahead.
