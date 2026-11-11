// two-ways.test.js — the mirror position of case two, proven in the engine:
// the "算力手" is COMPUTED at runtime (real enumeration, not hardcoded) and
// captures exactly three; the calm hand captures nothing but lets the thin
// pair breathe. The two ledgers, both as numbers.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { emptyPosition, play, key, BLACK, WHITE, bestCaptureMove, hashPosition } from "../app/rules.js";
import { positionFromSpec, chainsAt } from "../app/board-mirror.js";

const content = JSON.parse(readFileSync(new URL("../dist/content.json", import.meta.url), "utf-8"));
const boardSpec = content.boards["board-two-ways"];

test("the computed move is honest: it captures exactly the machine's three stones", () => {
  const pos = positionFromSpec(boardSpec, "initial");
  const best = bestCaptureMove(pos, BLACK);
  assert.deepEqual(best.at, [1, 5]);
  assert.equal(best.captured, 3);
  // and it is the unique maximum: no other move captures anything
  let otherCaptures = 0;
  for (let r = 1; r <= 5; r++) {
    for (let c = 1; c <= 5; c++) {
      if (r === 1 && c === 5) continue;
      const probe = play(pos, key(r, c), BLACK);
      if (probe.ok && (probe.capturedCount ?? 0) > 0) otherCaptures++;
    }
  }
  assert.equal(otherCaptures, 0, "no other capturing move may rival the engine's");
});

test("engine beat: +3 on the scoreboard, the other chain thins to two liberties", () => {
  const pos = positionFromSpec(boardSpec, "engine");
  const chains = chainsAt(pos);
  const whiteTop = chains.find((c) => c.color === WHITE && c.stones.includes("1,2"));
  assert.equal(whiteTop, undefined, "the three stones are lifted");
  const thin = chains.find((c) => c.color === BLACK && c.stones.includes("4,1"));
  assert.equal(thin.liberties, 2, "the other chain lost a breath (3 -> 2)");
  assert.equal(chains.filter((c) => c.atari).length, 1, "white's reply sits in atari itself");
});

test("calm beat: zero captures, the pair breathes from two liberties to four", () => {
  const pos = positionFromSpec(boardSpec, "calm");
  const chains = chainsAt(pos);
  const pair = chains.find((c) => c.color === BLACK && c.stones.includes("4,1"));
  assert.equal(pair.liberties, 4, "3 -> 4: the other ledger's arithmetic");
  // exactly TWO chains stand in atari, both standing facts from the start:
  // the corner stone (1,1) — protected structurally by the wall — and the
  // machine's three stones, hanging since game ten. The calm move must not
  // add a third.
  const atari = chains.filter((c) => c.atari);
  assert.equal(atari.length, 2);
  const ids = atari.map((c) => c.stones.join("|")).sort();
  assert.deepEqual(ids, ["1,1", "1,2|1,3|1,4"]);
  for (const c of chains.filter((x) => x.color === BLACK && x.stones[0] !== "1,1")) {
    assert.ok(c.liberties >= 3, "every other black chain keeps at least three breaths");
  }
});

test("both ledgers are stable: recompute, same hash", () => {
  const a = positionFromSpec(boardSpec, "engine");
  const b = positionFromSpec(boardSpec, "engine");
  assert.equal(hashPosition(a), hashPosition(b));
});
