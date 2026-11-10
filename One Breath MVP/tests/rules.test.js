// rules.test.js — the Go-rules red cases. A rule nobody has watched refuse is
// not a rule: capture MUST clear, suicide MUST refuse, simple ko MUST refuse.
// Plus the mirror position's two provable properties (attack → two chains in
// atari; calm → everyone keeps two liberties) — the two facts the story points at.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { emptyPosition, play, groupAt, key, BLACK, WHITE, hashPosition } from "../app/rules.js";
import { positionFromSpec, chainsAt } from "../app/board-mirror.js";

const content = JSON.parse(readFileSync(new URL("../dist/content.json", import.meta.url), "utf-8"));
const boardSpec = content.boards["board-two-sides"];

test("capture: last liberty filled -> stone removed", () => {
  let pos = emptyPosition(5);
  pos.stones.set(key(1, 1), WHITE);
  pos.stones.set(key(2, 1), BLACK);   // one white liberty left: (1,2)
  const res = play(pos, key(1, 2), BLACK);
  assert.equal(res.ok, true);
  assert.equal(res.pos.stones.has(key(1, 1)), false, "captured stone must be gone");
  assert.equal(res.capturedCount, 1);
});

test("suicide: a move leaving one's own chain with no liberties is refused", () => {
  // white surrounds the centre point (3,3) on all four sides; black playing
  // there has zero liberties and captures nothing -> refused
  let pos = emptyPosition(5);
  pos.stones.set(key(2, 3), WHITE);
  pos.stones.set(key(3, 2), WHITE);
  pos.stones.set(key(3, 4), WHITE);
  pos.stones.set(key(4, 3), WHITE);
  const res = play(pos, key(3, 3), BLACK);
  assert.equal(res.ok, false);
  assert.equal(res.reason, "suicide");
});

test("suicide that captures first is legal (the exception)", () => {
  let pos = emptyPosition(5);
  // white (1,1) with liberties (1,2),(2,1); black wall elsewhere such that
  // black plays (1,2): white (1,1) captured -> (1,2) has liberties via capture
  pos.stones.set(key(1, 1), WHITE);
  pos.stones.set(key(2, 1), BLACK);
  pos.stones.set(key(2, 2), BLACK);
  pos.stones.set(key(1, 3), BLACK);
  const res = play(pos, key(1, 2), BLACK);
  assert.equal(res.ok, true, "capturing move is not suicide");
  assert.equal(res.pos.stones.has(key(1, 1)), false);
});

test("simple ko: immediate recapture is refused", () => {
  // classic ko shape on the top-left corner
  let pos = emptyPosition(5);
  const B = [[1, 3], [2, 1], [2, 2], [2, 3]];
  const W = [[1, 2], [3, 1], [3, 2]];
  for (const [r, c] of B) pos.stones.set(key(r, c), BLACK);
  for (const [r, c] of W) pos.stones.set(key(r, c), WHITE);
  // white stone (1,2) has liberties: (1,1) only
  const res1 = play(pos, key(1, 1), BLACK); // black captures the white stone
  assert.equal(res1.ok, true);
  assert.equal(res1.pos.stones.has(key(1, 2)), false, "white ko stone captured");
  assert.equal(res1.pos.koPoint, key(1, 2), "ko point recorded");
  // immediate white recapture at the ko point must be refused
  const res2 = play(res1.pos, key(1, 2), WHITE);
  assert.equal(res2.ok, false);
  assert.equal(res2.reason, "ko");
});

test("occupied points are refused", () => {
  let pos = emptyPosition(5);
  pos.stones.set(key(3, 3), BLACK);
  const res = play(pos, key(3, 3), WHITE);
  assert.equal(res.ok, false);
  assert.equal(res.reason, "occupied");
});

// --- the mirror position's two provable properties ---------------------------

test("mirror setup: five interlocking chains, every chain at exactly two liberties", () => {
  const pos = positionFromSpec(boardSpec, "initial");
  const chains = chainsAt(pos);
  assert.equal(chains.length, 5, "B W B W B: three of yours, two of his");
  for (const c of chains) assert.equal(c.liberties, 2, c.stones.join("|"));
  assert.equal(chains.filter((c) => c.color === BLACK).length, 3);
  assert.equal(chains.filter((c) => c.color === WHITE).length, 2);
});

test("attack beat: two chains — one his, one yours — simultaneously at one liberty", () => {
  const pos = positionFromSpec(boardSpec, "attack");
  const chains = chainsAt(pos);
  const atari = chains.filter((c) => c.atari);
  assert.equal(atari.length, 2, "动两块: the attack woke two chains");
  assert.equal(atari.filter((c) => c.color === BLACK).length, 1, "one of yours");
  assert.equal(atari.filter((c) => c.color === WHITE).length, 1, "one of his");
});

test("calm beat: nobody loses a liberty — coexistence holds", () => {
  const pos = positionFromSpec(boardSpec, "calm");
  for (const c of chainsAt(pos)) {
    assert.ok(c.liberties >= 2, `chain ${c.stones[0]} keeps >=2 liberties`);
  }
  assert.equal(chainsAt(pos).some((c) => c.atari), false);
});

test("pass beat: nothing changes", () => {
  const pos0 = positionFromSpec(boardSpec, "initial");
  const pos1 = positionFromSpec(boardSpec, "pass");
  assert.equal(hashPosition(pos0), hashPosition(pos1));
});

test("determinism: same position -> same hash, always", () => {
  const a = positionFromSpec(boardSpec, "attack");
  const b = positionFromSpec(boardSpec, "attack");
  assert.equal(hashPosition(a), hashPosition(b));
});
