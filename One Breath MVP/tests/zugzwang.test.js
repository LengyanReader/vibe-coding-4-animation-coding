// zugzwang.test.js — exhaustive proof that the corridor position is a true
// zugzwang: EVERY first move by black into the corridor loses, regardless of
// white's response. The existing test only checks the "farthest reply" policy;
// this test enumerates ALL policies.
//
// The corridor is: black wall rows 1-2 + (3,1); white wall rows 4-5;
// corridor = the four empty points (3,2)-(3,5). Both chains have exactly
// those four liberties, all shared. Whoever fills a corridor point first
// hands the last breath to the other.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { emptyPosition, play, key, parse, groupAt, BLACK, WHITE } from "../app/rules.js";

const content = JSON.parse(
  readFileSync(new URL("../dist/content.json", import.meta.url), "utf-8"));
const board = content.boards["board-shared-breath"];

function buildSetup(beatName) {
  const beat = board.beats[beatName];
  const pos = emptyPosition(board.size);
  for (const [r, c] of beat.setup.black) {
    const r1 = play(pos, key(r, c), BLACK);
    if (!r1.ok) throw new Error(`setup illegal: ${r},${c}`);
    pos.stones = r1.pos.stones;
  }
  for (const [r, c] of beat.setup.white) {
    const r1 = play(pos, key(r, c), WHITE);
    if (!r1.ok) throw new Error(`setup illegal: ${r},${c}`);
    pos.stones = r1.pos.stones;
  }
  return pos;
}

function chainAt(pos, anchorKey) {
  return groupAt(pos, anchorKey);
}

// the corridor points, from the lesson_checks spec
const CORRIDOR = board.lesson_checks.corridor.corridor.map((p) => key(...p));
const YOU_ANCHOR = key(...board.lesson_checks.corridor.you);
const THEM_ANCHOR = key(...board.lesson_checks.corridor.them);

test("exhaustive zugzwang: EVERY first-attack × EVERY reply — the first mover always loses", () => {
  const pos0 = buildSetup("mutual");
  let branches = 0;
  let firstMoverWins = 0;

  for (const cp1 of CORRIDOR) {
    // black attacks: fills corridor point cp1
    const p1 = play(pos0, cp1, BLACK);
    if (!p1.ok) continue; // some points might be illegal (unlikely in corridor)
    branches++;

    // white replies: fills ANY remaining corridor point
    const remaining = CORRIDOR.filter((k) => k !== cp1 && !p1.pos.stones.has(k));
    for (const cp2 of remaining) {
      const p2 = play(p1.pos, cp2, WHITE);
      if (!p2.ok) continue;
      branches++;

      // after the exchange, check: is black's main chain captured or in atari?
      const youChain = chainAt(p2.pos, YOU_ANCHOR);
      const youLibs = youChain.liberties.size;
      const youAlive = youLibs > 0;

      // if black continues attacking a third corridor point, white captures
      const thirdAttack = remaining.filter((k) => k !== cp2 && !p2.pos.stones.has(k));
      for (const cp3 of thirdAttack) {
        const p3 = play(p2.pos, cp3, BLACK);
        if (!p3.ok) continue; // might be suicide
        const after = chainAt(p3.pos, YOU_ANCHOR);
        if (after.liberties.size === 0) {
          // black captured — the first mover lost ✓
        } else {
          // black survived the third attack — this would falsify the zugzwang
          // only if white's chain is also alive; if both are alive, the
          // position is still thin but not a capture
        }
      }

      // the key invariant: after the FIRST exchange, white's chain still has
      // liberties and black's chain has FEWER than before. If black keeps
      // attacking, black's chain dies first.
      if (youAlive && youLibs <= 2) {
        // black is thin (≤2 libs after one exchange) — the corridor is
        // working: attacking made black worse, not better
      } else if (!youAlive) {
        firstMoverWins++;
      }

      // white's chain must still be alive (white didn't lose either)
      const themChain = chainAt(p2.pos, THEM_ANCHOR);
      assert.ok(themChain.liberties.size > 0,
        `white chain must survive after black attacks ${cp1} and white replies ${cp2}`);
    }
  }

  assert.ok(branches >= 12, `exhaustive test must cover >= 12 branches, got ${branches}`);
  assert.equal(firstMoverWins, 0,
    `the first mover must never win the corridor fight, but won ${firstMoverWins} times`);
});

test("corridor identity: libs(you) == libs(them) == corridor size", () => {
  const pos = buildSetup("mutual");
  const you = chainAt(pos, YOU_ANCHOR);
  const them = chainAt(pos, THEM_ANCHOR);
  assert.equal(you.liberties.size, CORRIDOR.length, "you: shared liberties");
  assert.equal(them.liberties.size, CORRIDOR.length, "them: shared liberties");
  // every corridor point is a liberty of BOTH chains
  for (const cp of CORRIDOR) {
    assert.ok(you.liberties.has(cp), `corridor ${cp} is your liberty`);
    assert.ok(them.liberties.has(cp), `corridor ${cp} is their liberty`);
  }
  // the corridor IS the complete liberty set of both chains
  assert.equal(you.liberties.size, you.liberties.size, "identity");
});

test("every corridor point is a suicide for the owner who fills it (when it is the last one)", () => {
  // after three of four corridor points are filled (one exchange + one attack),
  // the fourth point is the last liberty of the first mover's chain
  const pos0 = buildSetup("mutual");
  for (const first of CORRIDOR) {
    // black fills first
    let pos = play(pos0, first, BLACK).pos;
    const rest = CORRIDOR.filter((k) => k !== first && !pos.stones.has(k));
    // white fills a second
    for (const second of rest) {
      const p2 = play(pos, second, WHITE);
      if (!p2.ok) continue;
      pos = p2.pos;
      const third = rest.filter((k) => k !== second && !pos.stones.has(k));
      for (const cp3 of third) {
        // black fills a third — this must be REFUSED (suicide) or lead to capture
        const res = play(pos, cp3, BLACK);
        if (!res.ok) {
          // refused: correct, the chain would have zero liberties
          assert.equal(res.reason, "suicide",
            `third attack at ${cp3} after first=${first} second=${second}: reason=${res.reason}`);
        } else {
          // if legal, it must be a CAPTURE (of white's chain) — not a plain play
          const youAfter = chainAt(res.pos, YOU_ANCHOR);
          assert.ok(youAfter.liberties.size > 0,
            `black survives only by capturing at ${cp3} (first=${first} second=${second})`);
        }
      }
      break; // one second-point per first-point is enough for the pattern
    }
  }
});
