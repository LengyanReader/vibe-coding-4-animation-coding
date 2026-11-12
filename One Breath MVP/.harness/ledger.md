# Ledger (append-only)

> Memory depth: **durable**. Never overwrite history; corrections are new rows.

| time | actor | action | basis | result |
|---|---|---|---|---|
| 2026-11-11T07:20:36+00:00 | harness-factory | init | task intake | scaffold generated |
| 2026-11-11 | agent | baseline observed | `node --test`; `python tools/verify.py` | 24/24 node tests pass; all 7 mirror beats hold under the independent Python rules |
| 2026-11-11 | agent | R0–R5 refinement | `reference/requirement-refinement.md` | ask restated; two readings surfaced; 4 decisions confirmed by the user (Elevated, new case, third stage, Chapter 0) |
| 2026-11-11 | agent | harness concretized | `tasks/PLAN.md`; `.harness/gates.md`; `working-set.json` | 15 hard gates + 4 soft gates; 9 capabilities active, 14 evicted with receipts |
| 2026-11-11 | agent | artifact feature corrected | `.harness/manifest.json` features; `PROVENANCE.md` | `document → code` override recorded with reason |
| 2026-11-11 | agent | harness check run | `python .harness/check.py .`; `harness_factory check --dir "One Breath MVP"` | both OK (observed) |
| 2026-11-11 | agent | no code written | `decisions.md` #7 | design/plan only; first move awaits the "start S0" nod |
| 2026-11-11 | agent | S0 geometry measured | temporary 5×5 search; `tools/verify.py` | no 2-lib/2-lib/1-shared seki found; two eyes hold; 4-point corridor is a zugzwang |
| 2026-11-11 | agent | S0–S3 implemented | `specs/board-shared-breath.yaml`; `specs/lessons.yaml`; `specs/vignettes/shared-breath.yaml`; `app/teaching.js`; `tests/teaching.test.js` | 7-step ladder, compare, sit, 5 responses |
| 2026-11-11 | agent | classical Chinese visual pass | `app/styles.css`; `app/main.js`; `app/board-mirror.js` | rice paper, vermilion seal, hairline rules, single board frame, role chops |
| 2026-11-11 | agent | gates re-run | `node --test`; `tools/verify.py`; `build.py` ×2; `tools/smoke.py` | 40/40; 11 beats + 2 lesson checks; identical sha256 `1ad1e73c…`; 0 page errors |
| 2026-11-11 | agent | bilingual record extended | `docs/corroboration-record.md` §5 | author back-translation of 5 units; native reader pending |
| 2026-11-11 | agent | harness checks re-run | `.harness/check.py`; factory `check --dir` | both OK |
| 2026-11-11 | agent | code written, no commit | `decisions.md` #11 | local and reversible; a commit waits for an explicit request |
| 2026-11-12 | user | four commits after Round 1 | `e9e5e43`, `f1a3b3c`, `741083c`, `5b9e4c4` | guided game, tactical steps, fuzz, smoke matrix, brush overhaul |
| 2026-11-12 | agent | Round 2 review | `node --test` 63/63; `verify.py`; `fuzz_reference.py`; `smoke.py`; `shoot_game.py`; build ×2 | all green; `5fd98610…`; findings P0-1…P0-5 recorded in `tasks/PLAN.md` §Round 2 |
| 2026-11-12 | agent | no product code changed | `tasks/PLAN.md` Round 2; `tasks/PROGRESS.md` | plan only; score/time decisions await the user |
| 2026-11-12 | user | decisions A–D confirmed | question answers | land-only; per-step skip; 100% fuzz; brush/progress |
| 2026-11-12 | agent | P0 gates fixed | `tests/zugzwang.test.js`; `tests/differential-fuzz.test.js`; `tests/vignette.test.js` | 24-branch + mutation; 100% + mutation; score boundary |
| 2026-11-12 | agent | core path + visuals | `app/teaching.js`; `app/main.js`; `app/board-mirror.js`; `app/styles.css` | skipStep, compact progress, stone texture, hint contrast |
| 2026-11-12 | agent | concurrent revert restored | HEAD versions + re-applied | 4 files restored; 67/67; sha `3e3ecbda…` |
| 2026-11-12 | agent | final gates | node --test; verify; fuzz; smoke; shoot; build ×2; harness | 67/67; 0 divergence; 0 errors; reproducible || 2026-11-12 | agent | simulated personas | `tools/human_sim.py`; 6 personas | 0 errors; 5 seals; mobile overflow found |
| 2026-11-12 | agent | mobile fix | `app/styles.css` | 444→390; tap 44; seal 56; contrast |
| 2026-11-12 | agent | accessibility gap recorded | `#lesson-board` tabIndex -1 | keyboard-only blocked; P1 open |