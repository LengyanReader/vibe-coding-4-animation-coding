# Development Roadmap — from proven routes to production directions

> Companion to `docs/tools.md` (the tool survey) and README §11 (milestones).
> This document answers: *given the routes that now actually run, where do we
> develop next, and how?* It is a plan, not a record of work done — nothing here
> has been built or installed unless §0 says it is proven.

---

## 0. What is proven today (the base we build on)

Ten routes run end-to-end with **no system installs** (Pillow + NumPy + SciPy +
FFmpeg, plus three sha256-locked assets fetched into `assets/` by
`scripts/fetch_assets.py` for the ink/piano routes),
each following the same invariant pipeline
`spec → render → measure → validate → manifest`, each with a determinism gate,
and each locked by a golden content hash in `tests/e2e/` (the
suite has since grown to 108 tests across routes + pipeline + simulation tiers):

| Route | Entry point | Medium | Gates | Golden content hash (prefix) |
|-------|-------------|--------|-------|------------------------------|
| Video | `vcac.firstloop` | 6s orbiting-cubes mp4 | duration, resolution, black-run, determinism | `d27999e7…` |
| Image | `vcac.image_sample` | value-noise poster png | resolution, unique-colors, entropy, determinism | `d538c350…` |
| Audio | `vcac.audio_sample` | R128 pad+arp wav | duration, sample-rate, LUFS, peak, silence, clip, DC, determinism | `2f9351c5…` |
| Audio (sampled) | `vcac.audio_sample` (`engine: fluidsynth`) | felt-piano study: score.mid + master/raw wav | duration, sample-rate, channels, LUFS, peak, silence, clip, DC, determinism | `b5bf04fd…` |
| Film | `vcac.film_sample` | mux(video,audio) mp4 | duration, has-video, has-audio, A/V sync | (input-hash pinned) |
| Game | `vcac.game_sample` | headless dodge sim + playtest mp4 | moved, score, hp, terminated, determinism | `c67acbf8…` |
| Layout | `vcac.layout_sample` | Swiss-grid poster png + pdf | resolution, grid-left, baseline, palette ceiling/floor, overflow, font resolution, determinism | `ce95c593…` |
| Type | `vcac.type_sample` | variable-weight glyph ramp mp4 | axis range, ink monotonic, resolution, duration, determinism | `3796ddf4…` |
| Spectrum | `vcac.spectrum_sample` | spectrogram of a known tone | sample-rate, duration, peak dBFS, silence, resolution, pitch, harmonics, PSNR, determinism | `e3591c8c…` |
| Ink | `vcac.ink_landscape` | nine-step 水墨山水 png | resolution, palette ceiling/floor, value bands, 留白, mist, entropy, seal, determinism | `7b767025…` |
| Anime | `vcac.anime_sample` | 2D cel shot mp4 on the frame contract | duration, resolution, scene cuts, black-run, determinism | `c05722c8…` |

Shared, reusable primitives now in `src/vcac/`: `media.py` (numpy↔PIL↔WAV +
exact image/audio metrics), `audio.py` (deterministic additive synth), `ffmpeg.py`
(encode/probe/loudnorm/mux, argv-only), `validate.py` (measurement-driven rule
engine), `provenance.py` (content-hash + manifest). These are the levers every
direction below pulls on.

**Loop #1 of §4 is built (2026-11-04): the pipeline skeleton.** `registry.py`
holds the probes `scripts/doctor.py` prints (now a thin CLI over it; output
byte-identical), plus `require()` — a node asks the registry before it runs,
and a missing capability is a loud `CapabilityError`, never a silent pass.
`pipeline.py` is a DAG executor with content-hash caching over the routes as
they are, proven by the three-node bundle `specs/examples/media-bundle.yaml`
(video + audio → film) in `tests/e2e/test_pipeline_bundle.py`: the executor's
node hashes equal the single-route goldens, a second pass is fully cached, a
tampered artifact is re-executed, and mutating one spec re-runs exactly the
affected sub-graph (54 tests green under Python 3.13.5). Honest scope: node
granularity = one whole route `run()`; the cache key mixes the spec dict,
upstream *payload* content hashes, the **whole-package** code hash and tool
versions — so any code edit invalidates every node (coarse but honest); the
remaining §3 items (spec schema, codegen, CLI beyond `run`/`doctor`) stay open.

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
  **Plus a sampled-acoustic engine**: `engine: fluidsynth` behind the same event
  contract (`specs/examples/kern-piano.yaml`) — the composed score is authored data
  (`audio.piano_events`), serialised to a real MIDI file, rendered by the vendored
  FluidSynth 2.6.2 + FluidR3_GM, then the same R128 master and the same eight gates.
  Golden `b5bf04fd…`; the MIDI is in the artifact list and the transient render wav
  is deleted (16.7 MB → 11.16 MB per run).
- **Next tier of outputs:**
  - *Real notation*: music21 → score → LilyPond → PDF/PNG (readable sheet music,
    not just sound). The symbolic layer becomes an inspectable artifact.
  - ~~*Acoustic timbres*~~: **done for piano** — FluidSynth + SoundFont behind the audio
    route (`engine` switch, `registry` capability `fluidsynth` recorded as `via: repo-tool`).
    Strings/brass/kit remain open: same engine, different note data + different gate set.
  - *Rhythm & electronic*: kick/snare/hat synthesis, sidechain, filters (SciPy is
    already installed — biquads, FFT, resampling).
  - *Sound design / SFX*: noise bursts, sweeps, impacts — **consumed by Game & Film**.
  - *Adaptive/branching music*: stems + vertical layering for games (a music DAG).
  - *Voice-over*: optional TTS for explainer films.
- **Tools to adopt:** `fluidsynth` + a SoundFont — **done, and without a system install**
  (fetched into `assets/`, sha256-locked, gitignored). Still to adopt: `music21`, `lilypond`.
  (SciPy present.)
- **New acceptance checks:** per-platform loudness (−14 LUFS streaming vs −16 here),
  true-peak (inter-sample, distinct from the sample-peak we measure), loudness
  range (LRA), tempo-grid alignment, stem loop continuity (seam energy).
- **Next sample:** *notated loop* — music21 writes 4 bars → LilyPond png (score) +
  FluidSynth wav (render); gate on score-file present + LUFS + note-count == spec.
  The FluidSynth half of this already exists; the engraving half does not.

### 2.3 Video

- **Now:** orthographic 3D cubes in Pillow → H.264; duration/resolution/black/determinism.
  **And a second renderer over the same frame contract**: `medium: anime`
  (`src/vcac/anime_sample.py`, `specs/examples/anime-eave.yaml`) — a 2D cel shot with
  keyframe interpolation on twos, camera drift, and a real edit. Not a new schema: same
  `format/style/render/timeline` keys, so one spec vocabulary covers both animators.
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
- **New acceptance checks:** ~~shot count / scene boundaries~~ **done** — `at least N scene
  cuts` is measured as the isolated peak of frame-to-frame luma-histogram total variation
  (a fade's per-frame shift is *larger* than a cut's, so amplitude alone cannot name an edit;
  the classifier separates hard cuts from ramps and the report carries the measured margin,
  4.2× on the shipped clip); transition duration, subtitle coverage %, colour primaries
  (bt709) via ffprobe, optical flow sanity — still open.
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

### 2.5 Style / painterly route (opened by `docs/styles.md`)

A **sixth medium class**, not a new tool: "what style can be formalised into code".
`docs/styles.md` is the map; the render path stays the proven image route.

- **Now:** **ink chain built** — `src/vcac/ink_landscape.py` + `specs/examples/ink-landscape.yaml`,
  nine-step 山水 renderer (纸本→地形→勾→皴→染→积墨→云气留白→题款钤印→量化), 9 measured gates,
  golden `7b767025…`, 6 mutants/refusals in `tests/e2e/test_ink_piano_anime_routes.py`. The OFL
  colophon face is a fetched asset (`assets/fonts/`, sha256-locked, not in git) and is hashed into
  the manifest. What is still survey-only: hand-drawn/2D-animation families beyond the cel route
  below, painterly styles, feature-3D and anime stacks — registered in `docs/tools.md` §5–§7 with
  licence + headless columns.
- **Highest-leverage first tier (zero install, all deterministic):**
  - ~~*Ink-wash landscape chain*~~ — **done** (`ink_landscape.py`; styles.md §1.2 nine-step chain:
    paper base → fBm+domain-warp terrain → contour "勾" → texture-primitive "皴" → wash → accumulated
    ink → negative-space mist → seal + colophon → acceptance). 画理 becomes constraints, not a filter.
    One measured lesson worth keeping: the chain must write each layer's strokes back into the float
    buffer, or every layer but the nearest paints into an image that is thrown away — a spec knob with
    no artifact and no gate able to notice it absent.
  - *Woodcut / ukiyo-e as layered DAG* — one block = one channel = one mask; the multi-block
    full-colour print is literally our `alpha_composite` chain (styles.md §2).
  - *XDoG / OpenCV sketch / halftone* — already installed (cv2 5.0.0, SciPy); pure filtering.
  - *Riso* — spot-ink separation + per-layer offset (misregistration) + multiply overprint.
- **Next tier:** Curtis 1997 watercolor reimplementation; `vsketch`/`vpype` pen-plotter
  line art (SVG is a reusable vector asset downstream); OFL Chinese calligraphy fonts for
  colophon/seal (manifest needs a `fonts` field — see styles.md §6).
- **Deferred, gated:** Blender as an *alternative renderer* for 2.5D (toon shader + Freestyle
  + Grease Pencil + composited painted backgrounds). Feature-3D tooling is not the bottleneck —
  art labour is (see §6).
- **New acceptance checks:** five-band value histogram (墨分五色) ✓, negative-space ratio
  (留白, with both a floor and a ceiling) ✓, seal-red presence and count as connected
  components ✓, licence check on every font ✓ — palette ΔE against a fixed ink/mineral set
  ✗ (superseded for this route: the artifact is *quantised onto* the declared gamut, so exact
  occupancy is a stronger claim than distance).
- **Next sample:** ~~`ink-landscape`~~ **delivered**; the open one in this class is now
  *woodcut/ukiyo-e as a layered DAG* and *Riso separation*. *(no install)*

### 2.6 Layout & document media (the zero-install blind spot we just found)

An exhaustiveness audit (`docs/coverage-audit.md`) found the biggest omission was **not**
exotic art tools — it was media classes that **this machine already runs**: `pandoc 3.8.2`
and `MiKTeX` are installed and measured, and FFmpeg ships `libass`. Nothing had been routed.

- **Now:** routes 3 (browser-layout), 6 (Swiss poster), 7 (variable-font) and the
  sound→picture spectrum route from this section are **built and golden-locked**
  (see §0 loop-#1 note and docs/audit-2026-11-05.md); the **document route** below is
  still open. A **second**
  zero-install medium was found on the follow-up machine audit: the **browser** (`playwright 1.58.0`
  + Chromium `145.0.7632.6`, proven by a real screenshot) — HTML/CSS/SVG/Canvas as rasterizer and
  layout engine, which also removes the "needs Chromium" objection for Marp/Slidev/Mermaid. Caveat:
  these live only on the 3.13.5 interpreter, not on `hy_py312` where the golden manifests were made.
- **Route candidates (in cost order):**
  1. *Document route* — markdown/YAML front-matter → `pandoc --pdf-engine=xelatex` → PDF
     (report, zine, spec sheet). Verification: page count, paper size, embedded-font list,
     PDF version, no missing-figure warnings.
  2. *Caption route* — timings → **ASS** (a real styling language: `\pos`, `\t`, `\clip`, `\k`)
     → `ffmpeg -vf ass=` burn-in. Verification: coverage %, safe-area, font availability,
     A/V sync (already implemented).
  3. *Diagram route* — D2/Vega-Lite/Graphviz → SVG → PNG. Verification: node/edge counts
     from the source text vs rendered bounding box, ΔE against the palette, no clipped labels.
  4. *Browser-layout route* — HTML/CSS (or a generated deck) → `page.screenshot()` PNG / `page.pdf()`.
     Verification: viewport + `deviceScaleFactor` pinned in spec, browser build recorded in manifest,
     `--disable-gpu`/headless_shell for cross-hardware determinism, grid metrics (column alignment,
     baseline divisibility) measured off the pixels. Unblocks posters, decks, infographics,
     kinetic type, and shader-art screenshots (WebGL) in one medium.
  5. *Variable-font route* — `fonttools varLib`/`setvar` on the local `NotoSansSC-VF` (`wght 100–900`)
     → per-frame weight axis animation. Verification: instance named-axes match spec, glyph outline
     hash, licence recorded (OFL-1.1 clean).
- **New tools (see `docs/tools.md` §8):** pandoc+LaTeX ✅ installed, libass ✅ installed,
  playwright+Chromium ✅ installed (3.13.5), fonttools ✅ installed (3.13.5), matplotlib ✅ installed
  (3.11.0); still to add: `vl-convert-python`, D2, Mermaid CLI, QGIS, Ghostscript, Marp.
- **Why it matters:** these are *symbolic-rule* generators (audit axis A3) — the most
deterministic, most auditable, easiest-to-verify class we can add, and they make the
explainer film route complete (poster + chart + captions + PDF handout from one brief).

### 2.7 Cross-media / product line (highest leverage)

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

1. ~~**Pipeline skeleton** — registry + DAG + content-hash cache.~~ **Done
   2026-11-04** — `src/vcac/registry.py` + `src/vcac/pipeline.py`, gated by
   `tests/e2e/test_pipeline_bundle.py` (see §0). Turns samples into cached,
   composable builds. *(no install)*
2. **Document route** — `pandoc + MiKTeX` → spec → PDF report/handout. **Cheapest new medium
   on this machine** (both already installed and measured). *(no install)*
3. ~~**Browser-layout route**~~ — **done** (`src/vcac/layout_sample.py` + `browser.py`,
   golden + 4 mutants, PNG+PDF from one spec).
4. **Caption route** — timings → ASS → `ffmpeg` burn-in on the loop1 video. *(no install)*
5. ~~**`ink-landscape` style loop**~~ — **done 2026-11-05** (`src/vcac/ink_landscape.py`, golden
   `7b767025…`, 9 gates, 6 mutants/refusals): the nine-step 山水 chain from `docs/styles.md` §1.2
   as a spec. Proves style can be a *spec*, not a filter. XDoG/sketch and Riso separations are
   still open items inside this loop. *(no install)*
   - ~~**2D cel animation loop**~~ — **done 2026-11-05** (`src/vcac/anime_sample.py`,
     `medium: anime`, golden `c05722c8…`): keyframes on twos + camera drift + a measured scene
     cut, over the existing frame contract rather than a new schema. *(no install)*
   - ~~**Sampled-instrument audio loop**~~ — **done 2026-11-05** (`engine: fluidsynth` in
     `audio_sample.py`, `specs/examples/kern-piano.yaml`, golden `b5bf04fd…`): authored note
     data → MIDI → vendored FluidSynth → R128 master → eight gates. *(no system install: the
     binary and the SoundFont are fetched into `assets/`)*
6. **Graphic-design-movement loop** — one movement = a 4-tuple `{palette, grid, type-pair, motif}` in
   `spec.yaml` → poster via loop 3 (Swiss grid first: `styles.md` §10, `swiss-grid-generator` MIT as the
   reference implementation of the grid maths). Acceptance = alignment ratio, baseline divisibility,
   palette size, type-scale ratio — **hard rules, no taste judgement**. *(no install)*
7. ~~**Variable-font type-animation loop**~~ — **done** (`src/vcac/type_sample.py`,
   ink-monotonic gate reads the pixels; fonts + licences in the manifest).
8. **Style-animation loop** — cellular automata / reaction–diffusion as a **frame sequence**
   (styles.md §11): the image route wrapped in a loop = a new animation medium for free. *(no install)*
9. **Timing-as-style loop** — easing curves + on-ones/on-twos quantisation applied to the
   existing orbiting-cubes render (styles.md §15). *(no install)*
10. **Data-viz image loop** — matplotlib/`vl-convert` chart → poster with ΔE/contrast gates.
    ⚠ Measured correction: `matplotlib 3.11.0` **is already installed** (no install needed), but
    `plt.xkcd()` **degrades** because Humor Sans / Comic Neue are absent (72 `findfont` warnings, no error) —
    so the hand-drawn *line* is free, the hand-drawn *glyph* is not. Either add the font or write the
    jitter ourselves (the honest, code-first answer). *(+1 install only for `vl-convert-python`)*
11. **Notation audio loop** — music21 → LilyPond (score png/pdf) + FluidSynth (wav).
    FluidSynth half delivered 2026-11-05 (see the sub-item under 5); the engraving half still
    *(installs)*.
12. **30s pygame-ce microgame** — headless playtest reusing the game harness. *(+1 install)*
13. **Multi-shot explainer film** — timeline DAG: title + chart + gameplay + VO + captions +
    PDF handout. *(composes 1–10)*
14. **(later, needs approval) 2.5D anime shot** — Blender toon render + painted background from
    loop 5 → first frame from the feature-3D/anime column, as an *alternative renderer*. The
    zero-install version (cel shading in Pillow, real edit measured off the frames) shipped
    first under item 5; this item is now specifically the *Blender* renderer behind the same
    spec. *(heavy install)*

Every loop is gated by `tests/e2e` + a new golden content hash before it is called done.

---

## 5. Install / adoption queue (requires explicit consent)

All entries are pip/winget and reversible; none is taken without a go-ahead.

| Package | Purpose | Install | Weight |
|---------|---------|---------|--------|
| **pandoc + MiKTeX + libass** | **document & caption routes — already installed** | **none** | — |
| **playwright 1.58.0 + Chromium 145.0.7632.6** | **browser-layout route — installed and proven this session** (browsers already downloaded) | **none** (on the 3.13.5 interpreter) | — |
| **fonttools 4.63.0 + local VF fonts** | variable-font type animation, subsetting (Noto Sans/Serif SC VF, **OFL-1.1**) | **none** (3.13.5); `pip install fonttools` into hy_py312 | — |
| matplotlib | data-viz images | **already installed (3.11.0) on 3.13.5**; missing in hy_py312 | — |
| Humor Sans / Comic Neue (or self-written jitter line) | makes `xkcd()` actually look hand-drawn | font download, **or zero install** if we implement the jitter | light |
| vl-convert-python | declarative chart specs | `pip install vl-convert-python` | light |
| music21 | symbolic music / score | `pip install music21` | light |
| LilyPond | score engraving (pdf/png) | winget/choco | medium |
| FluidSynth + SoundFont | acoustic rendering | winget + SF2 file | medium |
| manim | math animation | `pip install manim` (+cairo) | medium |
| pygame-ce | real game runtime | `pip install pygame-ce` | light |
| SciPy | filters/FFT (audio, physics) | **already installed** | — |
| scikit-image | XDoG (`difference_of_gaussians`) + NPR filters | `pip install scikit-image` | light |
| vsketch / vpype | pen-plotter line art, SVG pipeline | `pip install vsketch vpype` | light |
| ~~OFL Chinese fonts~~ | ~~colophon, seal text, CJK posters~~ | **no longer needed — Noto Sans/Serif SC (OFL-1.1) already on this machine** | — |
| Met Open Access pulls | 492k CC0 artworks via REST API — composition/value statistics | network fetch, hash + licence per file | light |
| godot / renpy / blender | engines / 3D | external installers | heavy |
| Houdini 22 Apprentice/Indie | procedural FX (smoke/fire/destruction) | external installer | heavy + **licence limits (watermark / revenue cap)** |
| **decision required: which interpreter ships?** | hy_py312 (3.12.13, produced all golden manifests) vs C:\Python313 (3.13.5, has matplotlib/fonttools/playwright) | none — **yours to decide** | — |

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
- **Style/animation ceilings are unequal, and the honest ranking is** (docs/styles.md §0,
  docs/tools.md §5–§7): painterly styles (ink, woodcut, riso, pixel, sketch) **high** — the
  technique is already a layered, enumerable program; Japanese 2D/2.5D **medium-high** — the
  render/composite half scriptifies, the *drawing* half (timing, spacing, performance) stays
  human; feature-3D at Disney/DreamWorks level **medium** — the open industrial stack (USD,
  MoonRay Apache-2.0, Cycles, Houdini) is not the bottleneck, **art labour measured in
  person-years is**; we commit to procedural shots and short sequences, not feature polish.
- Generative "style transfer" models stay **out of the render path** for four documented
  reasons (docs/styles.md §8): non-determinism, unauditability, licence/case-law risk, and
  conflict with the provenance contract. They may serve offline reference only, and any AI
  material in a deliverable must be declared in the manifest.
- Two recollection errors were caught and corrected during this survey ("Weta open-sourced
  Zoo Tools" — unsupported; `shader-to-ruby` — repo not located). Recorded in
  docs/styles.md §17 rather than propagated into the adoption queue.
- **Exhaustiveness is not claimed and cannot be proved.** `docs/coverage-audit.md` states the
  six taxonomy axes, the per-cell verdict, and — importantly — the **residual gaps that code
  cannot close**: one-time physical presence (live performance, installation), taste/smell/
  touch delivery, and hand-crafted physical objects. Those are boundary conditions of the
  medium, not backlog items; any claim of "all media types covered" should be read against it.
- The audit also found that **our largest gap was a route we could already run** (pandoc +
  MiKTeX + libass are installed). Lesson: audit the machine before auditing the internet.
- **The second-round audit found the same mistake twice, one level deeper.** Probing `pip list`,
  the font directory and `ms-playwright` turned up a whole medium we had registered as "needs
  install": the **browser as a deterministic rasterizer/layout engine** (playwright + Chromium,
  proven by a real screenshot this session), plus **variable fonts already on the machine**.
  It also exposed a **governance problem no media audit would catch**: two Pythons with different
  capability sets, while *every golden manifest was produced by the one that lacks these tools*.
  Any "zero-install" claim in these docs is therefore **interpreter-qualified**, and `doctor.py`
  now prints `sys.executable`/`sys.prefix` so the claim can always be re-checked. Choosing the
  shipping interpreter is a human decision (M0: machines observe, humans decide) — see §5 last row.
- **A tool being installed is not a style being available**: `plt.xkcd()` runs but silently degrades
  to the default sans-serif because the hand-drawn *font* is absent (measured: 72 `findfont` warnings,
  zero errors). Silent degradation is worse than an exception for a validation pipeline — acceptance
  gates should assert on the *artefact*, never on the exit code alone.
