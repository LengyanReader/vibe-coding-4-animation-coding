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
## Round 2 · review (2026-11-12)

- **Observed state:** HEAD `5b9e4c4`; four commits after the Round 1 plan (`e9e5e43`, `f1a3b3c`, `741083c`, `5b9e4c4`); working tree clean except the untracked `dist/` build.
- **Gates observed:** `node --test` 63/63; `verify.py` 11 beats + 2 lesson checks + 21 game moves (final 12-4); `fuzz_reference.py` 10 sequences / 250 moves / 9 refusals / 47 captured; `smoke.py` 3 vignettes × 2 languages × 2 word modes + full chapter + 4 sit views + 5 endings, 0 errors; `shoot_game.py` 9 screenshots; `build.py` twice, same sha256 `5fd98610…`; `.harness/check.py` OK.
- **Added by the round:** guided 21-move game with dual verification, three tactical steps (ko / capture-before-suicide / atari escape), differential fuzz, panels structure gate, smoke matrix, brush visual overhaul (robed figures, gradient stones); `.harness/decisions.md` #12–#13.
- **Findings:** P0-1 `tests/zugzwang.test.js` overclaims (empty branches, a tautology at `:117`, no capture assertion; the real proof is `firstMoverLoses`); P0-2 `tests/differential-fuzz.test.js` allows 95% and logs divergences while titled "every step"; P0-3 the no-score gate does not cover the game's area count, and the wording "决定胜负" contradicts "不数输赢"; P0-4 "七手"/6-min text vs 11 steps + game, optional steps not skippable; P0-5 stale PLAN/AGENTS/PROGRESS and a fused decisions row.
- **P1:** `rules.js` header says "NOT a Go engine" but holds `GameState`/`score()`/`teachingReply`; `teachingReply` is unused in the product; the game → corridor transition has no bridge line.
- **P2:** 11 step dots clutter; stones read as digital marbles; hint/corridor marks are low contrast; the "Start here" seal reads slightly digital. S1–S3 and the native-reader pass remain open.
- **No product code was changed by the review itself.** The A–D implementation follows below.

## Round 2 · implementation (2026-11-12)

- **Decisions A–D confirmed:** land-only, per-step skip + core path, 100% differential fuzz, brush stones + compact progress + hint contrast.
- **P0-1 fixed** — `tests/zugzwang.test.js` now enumerates 24 branches (4 first × 3 replies × 2 second attacks), asserts the first mover's chain is captured, checks exact set identity, keeps the 8-branch `firstMoverLoses` policy, and includes a **mutation-red** (a private liberty makes it `ok:false`).
- **P0-2 fixed** — `tests/differential-fuzz.test.js` now fails on any divergence or hash mismatch; 10 seeds × 25 moves are clean; a one-step mutation was observed red and restored.
- **P0-3 fixed** — the game's count is land only; `count_note` no longer says "决定胜负"; `tests/vignette.test.js` rejects a score/result on respond/ending and winner/loser wording.
- **P0-4 fixed** — `skipStep` + `lesson_step_skip` let the player skip any `core:false` step; the game is core; the 11 dots became a compact progress rule; the card says core 8–10 min; n2's "十手" is the 10 rule moves plus the game.
- **D fixed** — deterministic ink-wash stone texture, stronger hint/corridor marks, paper rule strip; the screenshot review confirms the hint ring and the land-count framing.
- **Product bug found and fixed** — after a concurrent edit, `app/main.js` had lost the `games` binding; the lesson/game screen would have thrown in the browser. Restored the committed HEAD file and re-applied the A–D changes.
- **Concurrent-edit note** — four files (`app/main.js`, `app/teaching.js`, `app/board-mirror.js`, `tests/teaching.test.js`) were reverted mid-round. I restored the committed HEAD versions and re-applied the uncommitted changes. If another session is still editing, reconcile before the next commit.
- **Evidence:** `node --test` 67/67; `verify.py` 11 beats + 2 lesson checks + 21 game moves; `fuzz_reference.py` 10 × 25 moves, 0 divergence; `smoke.py` matrix 0 errors; `shoot_game.py` 9 screenshots (hint included); `build.py` twice identical sha256 `d70481136e8bf164a63c8f28f24043aeb681eab802ba703003350e291ba3dd3d` (final, after the mobile/visual fix); `.harness/check.py` OK.

## Round 2 · simulated-persona walkthrough (2026-11-12)

- **Method:** `tools/human_sim.py` drives six scripted personas through the real UI — not human subjects. beginner zh (core, deliberate wrong clicks), beginner en (words), Go-literate zh (full 11 steps), mentor (skips the lesson), mobile 390×844, reduced motion. **0 page errors** in all six; 5 seals; land count; hint ring; corridor 2 → 4; 0 overflow.
- **Found and fixed:** the mobile lesson overflowed (`scrollWidth 444` vs `innerWidth 390`; offenders `lesson-stage`, `lesson-board`, `lesson-side`). CSS at 860/520 now yields **390/390, 0 offenders**; top navigation targets 30 → 44 px; the ending seal strip is 56 px; prompt/caption/footer contrast raised.
- **Open (P1):** keyboard accessibility — `#lesson-board` and `#compare-board` are `<canvas>` with `tabIndex -1` and no `tabindex` attribute, so a keyboard-only player cannot complete Chapter 0. This needs an arrow-key grid / point-list fallback, not a CSS patch.
- **Timing model (heuristic, not a stopwatch):** core ~5.9–6.8 min zh / 4.8–5.4 en; full ~7.7–8.9 / 6.4–7.3; mentor ~2.6–3.1 / 2.0–2.3. The card's 8–10 min is conservative for the core path.
- **Not proven:** S1 comprehension, S2 non-moralization, S3 real duration, the native-reader pass.
- **Artifacts:** `outputs/human-sim/REPORT.md`, `results.json`, and per-persona screenshots.

## Handoff (latest)

- **Goal:** Chapter 0 — 学 → 照 → 觉 → 行, carried by 同气 / The Shared Corridor; bilingual, deterministic, no score of the player, no AI.
- **Done:** full chapter + guided game; A–D implemented; 67 tests; independent verifier; strict fuzz; smoke matrix; classical visual pass; six simulated personas; mobile overflow fixed; reproducible build.
- **Blocked:** keyboard accessibility (P1), S1–S3, and the native-reader pass.
- **Next:** keyboard grid for the lesson/compare boards; then real S4 (three first-time players + mentor + native reader); then P1 (`GameState`/`teachingReply` out of `rules.js`, use/remove `teachingReply`, game → corridor bridge).
- **Sources:** observed command output 2026-11-12; `tasks/PLAN.md` Round 2; `.harness/decisions.md` #14–#17; `outputs/human-sim/REPORT.md`.