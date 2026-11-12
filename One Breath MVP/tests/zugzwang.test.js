// zugzwang.test.js — the corridor race, exhaustively.
//
// Claim: in the four-point corridor, if the first mover keeps attacking after
// the first exchange, its own chain is captured — for EVERY first point, EVERY
// white reply, and EVERY second attack. This is stronger than the policy test
// in teaching.test.js (which uses the authored "farthest reply"): here every
// branch is played out and the capture is asserted, not logged.
//
// The mutation test at the end proves the check can fail: removing one black
// wall stone gives the first mover a private liberty, and firstMoverLoses()
// must then return ok:false. A gate that cannot be made red is not a gate.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { emptyPosition, play, key, groupAt, BLACK, WHITE } from "../app/rules.js";
import { firstMoverLoses } from "../app/teaching.js";

const content = JSON.parse(
  readFileSync(new URL("../dist/content.json", import.meta.url), "utf-8"));
const board = content.boards["board-shared-breath"];
const CHK = board.lesson_checks.corridor;
const CORRIDOR = CHK.corridor.map((p) => key(...p));
const YOU = key(...CHK.you);
const THEM = key(...CHK.them);

function buildSetup(chk = CHK) {
  const pos = emptyPosition(board.size);
  for (const [r, c] of chk.setup.black) {
    const res = play(pos, key(r, c), BLACK);
    if (!res.ok) throw new Error(`setup illegal: ${r},${c} (${res.reason})`);
    pos.stones = res.pos.stones;
  }
  for (const [r, c] of chk.setup.white) {
    const res = play(pos, key(r, c), WHITE);
    if (!res.ok) throw new Error(`setup illegal: ${r},${c} (${res.reason})`);
    pos.stones = res.pos.stones;
  }
  return pos;
}

test("corridor identity: you and them breathe through exactly the same four points", () => {
  const pos = buildSetup();
  const you = groupAt(pos, YOU);
  const them = groupAt(pos, THEM);
  const want = CORRIDOR.slice().sort();
  assert.deepEqual([...you.liberties].sort(), want, "your liberty set IS the corridor");
  assert.deepEqual([...them.liberties].sort(), want, "their liberty set IS the corridor");
});

test("exhaustive race: every first move × every reply × every second attack captures the first mover", () => {
  const pos0 = buildSetup();
  let branches = 0;
  for (const first of CORRIDOR) {
    const p1 = play(pos0, first, BLACK);
    assert.equal(p1.ok, true, `first ${first} must be legal`);
    const afterFirst = CORRIDOR.filter((k) => k !== first && !p1.pos.stones.has(k));
    for (const reply of afterFirst) {
      const p2 = play(p1.pos, reply, WHITE);
      assert.equal(p2.ok, true, `white reply ${reply} after ${first} must be legal`);
      assert.equal(groupAt(p2.pos, YOU).liberties.size, 2,
        `after ${first}/${reply}: your chain has exactly two breaths`);
      assert.equal(groupAt(p2.pos, THEM).liberties.size, 2,
        `after ${first}/${reply}: their chain has exactly two breaths`);

      const afterReply = CORRIDOR.filter((k) => !p2.pos.stones.has(k));
      for (const second of afterReply) {
        const p3 = play(p2.pos, second, BLACK);
        assert.equal(p3.ok, true, `second attack ${second} after ${first}/${reply} must be legal`);
        const last = CORRIDOR.filter((k) => !p3.pos.stones.has(k));
        assert.equal(last.length, 1, "exactly one corridor point remains");

        const p4 = play(p3.pos, last[0], WHITE);
        assert.equal(p4.ok, true, `last reply ${last[0]} must capture, not be refused`);
        assert.equal(p4.pos.stones.has(YOU), false,
          `first mover ${first} must be captured after reply ${reply} / attack ${second}`);
        branches++;
      }
    }
  }
  assert.equal(branches, 24, "4 first moves × 3 replies × 2 second attacks");
});

test("the authored policy re-derives the same verdict (8 branches, no capture survives)", () => {
  const check = firstMoverLoses(board);
  assert.equal(check.ok, true, check.why);
  assert.equal(check.branches, 8);
});

test("mutation red: a private liberty for the first mover breaks the zugzwang claim", () => {
  const tampered = structuredClone(board);
  tampered.lesson_checks.corridor.setup.black =
    tampered.lesson_checks.corridor.setup.black.filter(([r, c]) => !(r === 2 && c === 5));
  const check = firstMoverLoses(tampered);
  assert.equal(check.ok, false, "the check must notice a surviving first mover");
});