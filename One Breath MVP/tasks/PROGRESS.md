# PROGRESS — One Breath MVP · Chapter 0

**Updated:** 2026-11-11 · Append-only; corrections are new rows.

## Session log

- 2026-11-11T07:20:36+00:00 — harness generated (`harness-factory` 0.1.0). No work yet.
- 2026-11-11 — **baseline observed, not assumed**: `node --test` → 24/24 pass; `python tools/verify.py` → all 7 mirror beats hold; `tools/build.py` present.
- 2026-11-11 — **R0–R5 refinement**; user confirmed 4/4 recommended: new case 同气, 觉悟人生 as third stage ending in 行, Elevated interactive scope, Chapter 0 placement.
- 2026-11-11 — **harness concretized and checked**: `tasks/PLAN.md`, `.harness/gates.md`, working set 9 active / 14 evicted; self-check and factory check OK.
- 2026-11-11 — **S0 geometry measured** (temporary probe, deleted after recording):
  - a search over 5×5 positions found **no** two-chain / two-liberty-each / one-shared-liberty shape within the tested space;
  - the two-eye corner group works: one chain, 10 liberties, eyes at `(2,2)` and `(3,3)`, no legal white move inside;
  - capture and suicide setups verified; the four-point corridor yields a true zugzwang (first mover loses).
  - Consequence: the plan's `shared_liberties == 1` was **replaced** by `libs(you) == libs(them) == corridor` (4 points) + "every first move loses" (8 branches). Recorded in `.harness/decisions.md` #8.
- 2026-11-11 — **S0–S3 implemented**:
  - `specs/board-shared-breath.yaml` (10 beats + roles + same_as + lesson_checks), `specs/lessons.yaml` (7 steps, 4 core), `specs/vignettes/shared-breath.yaml` (11 nodes, 5 responses);
  - `app/teaching.js` runtime; `rules.js` gained `eyesFor` / `allLegalMoves` / `capturedPoints`; `board-mirror.js` gained hit-test, ghosts, role chops, breath marks; `main.js` gained lesson / compare / sit screens; `build.py` emits lessons and strips multi-line imports;
  - `tools/verify.py` re-derives the two-eye and corridor claims independently; `tests/teaching.test.js` adds 16 gates.
- 2026-11-11 — **classical Chinese visual pass**: rice-paper palette, vermilion seal stamps, hairline rules, single delicate board frame, vertical chapter chop, softer corridor breath marks; the four role labels are small vermilion chops.
- 2026-11-11 — **gates re-run after the visual pass**:
  - `node --test` → **40/40 pass**, 0 fail;
  - `python tools/verify.py` → 11 beats + 2 lesson checks, all hold under the independent Python rules;
  - `python tools/build.py` twice → **same sha256** `1ad1e73c95d4006e4fabbc84fe22c84a0f42ac41e5d4f7a7f69a0995984539df`;
  - `python tools/smoke.py` → title 3 cards, lesson canvas non-empty, 4 liberties counted, compare corridor found, sit canvas non-empty, 5 ending seals, existing case still renders, **0 page errors**;
  - `.harness/check.py` and factory `check --dir` → OK.
- 2026-11-11 — **bilingual record extended**: `docs/corroboration-record.md` §5 records five meaning-unit back-translations (author, weak evidence) and marks the native-reader pass as **pending (you)**.

## Hard gates · observed evidence

| Gate | Result |
|---|---|
| G1 build reproducible | PASS — two builds, identical sha256 |
| G2 node suite | PASS — 40/40 |
| G3 independent verifier | PASS — 11 beats + 2 lesson checks |
| G4–G7 legality / liberty set / capture / refusal | PASS — `tests/teaching.test.js` |
| G8 zugzwang (first mover loses) | PASS — 8 branches, JS + Python |
| G9 corridor identity | PASS — four points, both liberty sets equal it |
| G10–G12 same_as / roles / determinism | PASS |
| G13–G14 bilingual / no score | PASS |
| G15 harness checks | PASS |
| G16 browser smoke | PASS — 0 page errors |

## Soft gates · still false

- **S1 comprehension** — no first-time player observed yet.
- **S2 non-moralization** — no interview yet.
- **S3 6–10 minutes** — not timed with a first-time player.
- **Native-reader pass** on the Chinese — this is you (see `docs/corroboration-record.md` §5.2).

## Handoff (latest)

- **Goal:** Chapter 0 — 学 → 照 → 觉 → 行, carried by 同气 / The Shared Corridor; bilingual, deterministic, no scoring, no AI.
- **Done:** full playable chapter, classical Chinese visual pass, 40 tests, independent verifier, reproducible build, browser smoke, bilingual record.
- **Blocked:** nothing. Human gates and the native-reader pass are pending by design.
- **Next:** S4 — three first-time players (comprehension, non-moralization, duration), then a mentor walkthrough; optionally refine the ink pictograms if the human look asks for it.
- **Sources:** `docs/MVP-BUILD-PLAN.md`; `docs/_extract_mvp.md`; `docs/corroboration-record.md`; `app/rules.js`; `app/teaching.js`; `tools/verify.py`; `tools/build.py`; observed command output 2026-11-11.