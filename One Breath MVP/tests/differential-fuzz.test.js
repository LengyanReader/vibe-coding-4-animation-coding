// differential-fuzz.test.js — the two brains must agree.
//
// tools/fuzz_reference.py generates deterministic random Go sequences using
// an independent Python Rules implementation. This test replays the SAME
// sequences through the JS engine (app/rules.js) and compares, step by step:
//   * ok/refused match
//   * captured count matches
//   * refusal reason matches
//   * final position hash matches
//
// Any divergence is a bug in one of the two brains. 10 seeds × 25 moves =
// 250 steps covering captures, ko attempts, suicides, and ordinary plays —
// far beyond the authored setups.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { emptyPosition, play, key, BLACK, WHITE, hashPosition } from "../app/rules.js";

const fuzz = JSON.parse(
  readFileSync(new URL("../dist/fuzz-seqs.json", import.meta.url), "utf-8"));

const COLOR = (name) => name === "black" ? BLACK : WHITE;

test("differential fuzz: JS engine agrees with Python reference on every step", () => {
  let totalSteps = 0, totalCaptured = 0, totalRefused = 0;
  const hashDiffs = [], divergences = [];
  for (const seq of fuzz.sequences) {
    const pos = emptyPosition(seq.size);
    for (const step of seq.steps) {
      const k = key(...step.at);
      const res = play(pos, k, COLOR(step.color));
      // both brains must agree on ok/refused
      if (res.ok !== step.ok) {
        divergences.push({seed: seq.seed, step: step.step, kind: "ok",
          js: res.ok, py: step.ok, reason: res.reason ?? step.reason});
        pos.stones = step.after ? new Map(Object.entries(step.after).map(([k,v]) => [k, +v]))
          : pos.stones;
        continue;
      }
      if (!res.ok) {
        if (res.reason !== step.reason) {
          divergences.push({seed: seq.seed, step: step.step, kind: "reason",
            js: res.reason, py: step.reason});
        } else { totalRefused++; }
      } else {
        if ((res.capturedCount ?? 0) !== step.captured) {
          divergences.push({seed: seq.seed, step: step.step, kind: "captured",
            js: res.capturedCount ?? 0, py: step.captured});
        } else { totalCaptured += res.capturedCount ?? 0; }
        // position hash: informational check — hash formatting differences
        // between the two brains may cause false positives, but the CAPTURED
        // count and REFUSAL REASON are the substantive agreement
        const jsHash = hashPosition(res.pos);
        if (jsHash !== step.hash) {
          hashDiffs.push({seed: seq.seed, step: step.step, js: jsHash, py: step.hash});
        }
        pos.stones = res.pos.stones;
        pos.koPoint = res.pos.koPoint;
      }
      totalSteps++;
    }
  }
  // the fuzz must actually exercise the interesting paths (not all passes)
  assert.ok(totalRefused > 0, "fuzz must include refusals");
  assert.ok(totalCaptured > 0, "fuzz must include captures");
  assert.ok(totalSteps >= fuzz.sequences.length * 10, "enough steps exercised");
  // The hash is the state. A formatting difference between the brains is a
  // defect in the harness, not permission to ignore the state; and a captured/
  // reason divergence is a rule bug. Both must be zero. (A gate that can pass
  // with a known divergence is not a gate.)
  assert.deepEqual(hashDiffs, [],
    `position hash mismatches: ${JSON.stringify(hashDiffs.slice(0, 5))}`);
  assert.deepEqual(divergences, [],
    `engine divergences: ${JSON.stringify(divergences.slice(0, 5))}`);
});
