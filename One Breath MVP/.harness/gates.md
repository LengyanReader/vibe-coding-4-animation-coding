# Gates — Definition of Done

> Gate strictness: **standard** (verifiability=high, stakes=medium)
> **Last full run:** 2026-11-11 — evidence in `tasks/PROGRESS.md`.
> Every criterion starts `false`. It may be set `true` only after the required evidence is attached (M0.3).
> A gate nobody has seen fail is not a gate: every hard gate below has a named red example.

## Hard gates · 硬门 (mechanical)

### Inherited from the existing MVP (must stay green)

- [x] **Build reproducible** — `python tools/build.py` twice; `dist/build-manifest.json` sha256 identical. Red: a timestamp enters the artifact.
- [x] **Node suite green** — `node --test`; 24 existing tests plus the new ones; 0 fail. Red: any existing gate regresses.
- [x] **Bilingual completeness** — every key in `zh` and `en`, non-empty, placeholders identical. Red: one missing `en` line.
- [x] **No scoring** — static scan of `app/*.js` and `specs/*` for score/points/rating variables or keys. Red: `score` appears in `teaching.js`.
- [x] **No AI / no telemetry / no network** — static scan + the single-file build opens offline. Red: a fetch call in `app/`.
- [x] **Graph reachability** — every ending reachable, no orphan nodes, no dead branches. Red: a choice points at an unknown node.

### New for Chapter 0

- [x] **G4 Two implementations agree** — every setup stone and scripted move legal in `app/rules.js` and `tools/verify.py`. Red: one illegal setup coordinate.
- [x] **G5 Liberty-set equality** — the player's clicked liberties equal the engine's liberty set for the named chain. Red: swap one expected coordinate.
- [x] **G6 Capture and ghosts** — captured count and ghost count exact after the capture beat. Red: remove one ghost.
- [x] **G7 Refusal is observable** — the suicide / ko attempt is refused with a machine-readable reason. Red: the engine silently allows it.
- [x] **G8 The corridor is a zugzwang (computed invariant, M3.12)** — for every first move, the reply at the farthest remaining point leaves 2-2; a second attack is answered at the last point and the first mover's chain is captured. 8 branches, re-derived in Python. Red: add a fifth corridor point, or let the first mover survive one branch.
- [x] **G9 Corridor identity** — `libs(you) == libs(them) == corridor` (four points). Measured: no two-chain / two-liberty-each / one-shared-liberty shape exists on 5×5 within the tested space, so the claim was changed, not faked. Red: geometry drift removes or adds a corridor point.
- [x] **G10 Referential integrity** — the board's `same_as` points at an existing vignette + beat, and the beat's position hash matches. Red: re-point the board id.
- [x] **G11 Role mapping** — `you` and `them` anchors exist, are different colours, and belong to different chains. Red: both anchors on one chain.
- [x] **G12 Determinism** — a scripted click sequence yields the same position hash every run. Red: inject `Math.random`.
- [x] **G15 Harness self-check** — `python .harness/check.py .` and `PYTHONPATH=<HF>/src python -m harness_factory check --dir "One Breath MVP"`. Red: a listed file missing, or a double-brace template marker left in a document.

- [x] **G16 Browser smoke** — `python tools/smoke.py` (Playwright, dev-only): title → lesson → compare → sit → ending → existing case; canvases non-empty; 0 page errors. Red: any page error, a blank canvas, or a missing ending seal.

## Soft gates · 软门 (human judgment)

- [ ] **S1 Comprehension** — three first-time players can point to (a) which chain is theirs, (b) the shared liberty, (c) why the obvious attack puts both at risk. Ask open questions; do not prompt the answer.
- [ ] **S2 Non-moralization** — players do not conclude that capture is bad or passing is good. Revise if the mechanics or captions imply a single moral answer.
- [ ] **S3 Duration** — a first-time player reaches 行 in 6–10 minutes without a facilitator.
- [ ] **S4 Mentor legibility** — a supervisor can state the design proposition, the mechanic that embodies it, and the open research question after the walkthrough.

## Evidence rule · 证据规则

- Evidence is a first-class artifact: a test result, a file, a log line, a screenshot, an interview note. No evidence → no pass.
- Default-FAIL: the agent may not set a row true on intention or on "it should work".
- Build and judge are separated where possible: the evaluator reads the artifact, not the author's reasoning.
- Report the **red** that was observed for each gate at least once (mutation test), not only the green.
- A soft gate is never upgraded to a hard gate to make the table look complete; an unresolved soft gate is reported as `uncertain`, not `pass`.

## Command block · 一键复跑

```
python tools/build.py
node --test
python tools/verify.py
python tools/smoke.py
python tools/build.py
python .harness/check.py .
PYTHONPATH=C:/DA_Practice/research_foodie/research_foodie/harness_factory/src python -m harness_factory check --dir "One Breath MVP"
```

All seven must pass, and G1's two sha256 values must match, before any "done" is stated.