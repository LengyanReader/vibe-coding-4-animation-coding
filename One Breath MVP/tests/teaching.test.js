// teaching.test.js — Chapter 0's gates.
//
// The lesson is only "done" when a structural fact holds: the clicked set is
// the liberty set, the capture count is exact, the refusal reason is the
// authored one, or the pass leaves the position hash unchanged. The corridor
// claim is re-derived here and independently in tools/verify.py.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  newLessonWalk, currentStep, clickPoint, pressPass, resetStep, advanceStep, skipStep,
  firstMoverLoses, sameAsCheck, rolesCheck, positionForStep, sharedCorridor,
  buildPosition,
} from "../app/teaching.js";
import { positionFromSpec, chainsAt } from "../app/board-mirror.js";
import {
  eyesFor, allLegalMoves, groupAt, key, hashPosition, play, BLACK, WHITE,
} from "../app/rules.js";
import { reachability } from "../app/vignette.js";

const content = JSON.parse(readFileSync(new URL("../dist/content.json", import.meta.url), "utf-8"));
const lesson = content.lessons["shared-breath"];
const board = content.boards["board-shared-breath"];

function clickAll(w, points) {
  for (const p of points) {
    const pt = Array.isArray(p) ? p : p.split(",").map(Number);
    w = clickPoint(w, pt).walk;
  }
  return w;
}

function liberties(w, step) {
  return [...groupAt(w.pos, key(...step.chain)).liberties];
}

function solveCurrent(w) {
  const step = currentStep(w);
  if (step.kind === "liberties") return clickAll(w, liberties(w, step));
  if (step.kind === "play") return clickPoint(w, step.solution).walk;
  if (step.kind === "refuse") return clickAll(w, step.points ?? [step.point]);
  if (step.kind === "mutual") {
    let out = clickPoint(w, step.corridor[0]).walk;
    return pressPass(out).walk;
  }
  if (step.kind === "pass") return pressPass(w).walk;
  if (step.kind === "game") {
    // the golden path: every authored learner point, then the closing pass
    while (!w.done && w.gameIdx < w.record.moves.length) {
      const m = w.record.moves[w.gameIdx];
      if (!m.learner) break; // auto replies fire inside clickPoint
      if (m.at === null) return pressPass(w).walk;
      w = clickPoint(w, m.at).walk;
    }
    return w;
  }
  return w;
}

function walkTo(index) {
  let w = newLessonWalk(lesson, board, content.games);
  for (let i = 0; i < index; i++) w = advanceStep(solveCurrent(w)).walk;
  return w;
}

test("lesson data: eleven steps, five on the core path, every rule and prompt bilingual", () => {
  assert.equal(lesson.steps.length, 11);
  assert.equal(lesson.steps.filter((s) => s.core).length, 5);
  for (const s of lesson.steps) {
    for (const field of ["rule", "prompt"]) {
      assert.ok(s[field]?.zh?.trim(), `${s.id}: missing zh ${field}`);
      assert.ok(s[field]?.en?.trim(), `${s.id}: missing en ${field}`);
    }
  }
  // the payoff step is the curated game and the build carries its record
  const game = lesson.steps.find((s) => s.kind === "game");
  assert.ok(game, "the ladder ends with a guided game");
  assert.ok(content.games[game.game], `record "${game.game}" is in the build`);
});

test("every lesson step starts from a legal position", () => {
  for (const step of lesson.steps) {
    const pos = positionForStep(step, board);
    assert.equal(pos.size, 5);
    assert.ok(pos.stones.size >= 0);
  }
});

test("气: clicking every liberty completes the step; six-liberty chain shares one breath", () => {
  let w = newLessonWalk(lesson, board);
  const l1 = currentStep(w);
  assert.deepEqual(liberties(w, l1).sort(), ["2,3", "3,2", "3,4", "4,3"].sort());
  w = clickAll(w, liberties(w, l1));
  assert.equal(w.done, true);
  assert.equal(w.message.key, "lesson.msg.counted");
  w = advanceStep(w).walk;
  const l2 = currentStep(w);
  assert.equal(l2.id, "l2_chain");
  assert.equal(liberties(w, l2).length, 6);
  const chains = chainsAt(w.pos);
  assert.equal(chains.length, 1, "two connected stones are one chain");
});

test("提子: filling the last liberty removes two stones and leaves exactly those ghosts", () => {
  const w = walkTo(2);
  const step = currentStep(w);
  assert.equal(step.id, "l3_capture");
  const res = play(w.pos, key(3, 1), BLACK);
  assert.equal(res.ok, true);
  assert.equal(res.capturedCount, 2);
  assert.deepEqual([...res.capturedPoints].sort(), ["3,2", "3,3"]);
  const after = clickPoint(w, [3, 1]).walk;
  assert.equal(after.done, true);
  assert.deepEqual(after.ghosts.sort(), ["3,2", "3,3"]);
  assert.equal(after.pos.stones.has(key(3, 2)), false);
});

test("禁入点: the surrounded point is refused with reason suicide, and no stone is placed", () => {
  const w = walkTo(3);
  const step = currentStep(w);
  assert.equal(step.id, "l4_suicide");
  const r = clickPoint(w, [2, 2]);
  assert.equal(r.event, "refused");
  assert.equal(r.reason, "suicide");
  assert.equal(r.walk.pos.stones.has(key(2, 2)), false);
  assert.equal(r.walk.done, true);
  assert.equal(r.walk.message.key, "lesson.msg.refused_suicide");
});

test("两眼: both eyes are real and no white move exists inside them", () => {
  const w = walkTo(4);
  const step = currentStep(w);
  assert.equal(step.id, "l5_eyes");
  const eyes = eyesFor(w.pos, key(1, 1)).sort();
  assert.deepEqual(eyes, ["2,2", "3,3"]);
  const inside = allLegalMoves(w.pos, WHITE).filter((m) => m.at[0] === 2 || m.at[0] === 3);
  assert.equal(inside.some((m) => m.at[0] === 2 && m.at[1] === 2), false);
  assert.equal(inside.some((m) => m.at[0] === 3 && m.at[1] === 3), false);
  const after = clickAll(w, [[2, 2], [3, 3]]);
  assert.equal(after.done, true);
  assert.equal(after.message.key, "lesson.msg.both_eyes");
});

test("双活: the corridor is four shared liberties and both chains have exactly those four", () => {
  const w = walkTo(5);
  const step = currentStep(w);
  assert.equal(step.id, "l6_mutual");
  const corridor = sharedCorridor(board).sort();
  assert.equal(corridor.length, 4);
  const chains = chainsAt(w.pos);
  const you = chains.find((c) => c.stones.includes("1,1"));
  const them = chains.find((c) => c.stones.includes("4,1"));
  assert.equal(you.liberties, 4);
  assert.equal(them.liberties, 4);
  assert.deepEqual([...you.libertyPoints].sort(), corridor);
  assert.deepEqual([...them.libertyPoints].sort(), corridor);
});

test("双活 is a zugzwang: every first move loses the first mover's chain (computed invariant)", () => {
  const check = firstMoverLoses(board);
  assert.equal(check.ok, true, check.why);
  assert.equal(check.branches, 8, "four first moves x two second moves");
});

test("双活: one exchange leaves 2-2; a second attack is captured; a pass keeps the position", () => {
  const w = walkTo(5);
  const step = currentStep(w);
  const first = clickPoint(w, step.corridor[0]).walk;
  const chains = chainsAt(first.pos);
  assert.equal(chains.find((c) => c.stones.includes("1,1")).liberties, 2);
  assert.equal(chains.find((c) => c.stones.includes("4,1")).liberties, 2);
  const second = clickPoint(first, step.corridor[1]).walk;
  assert.equal(second.phase, 2);
  assert.equal(second.message.key, "lesson.msg.mutual_lost");
  assert.equal(second.pos.stones.has(key(1, 1)), false, "the first mover's chain is gone");
  const reset = resetStep(w);
  const hash0 = hashPosition(reset.pos);
  const passed = pressPass(reset).walk;
  assert.equal(passed.done, true);
  assert.equal(hashPosition(passed.pos), hash0, "a pass changes nothing");
});

test("虚着: the pass step completes without touching the position", () => {
  const w = walkTo(6);
  const step = currentStep(w);
  assert.equal(step.id, "l7_pass");
  const hash0 = hashPosition(w.pos);
  const r = pressPass(w);
  assert.equal(r.event, "pass");
  assert.equal(r.walk.done, true);
  assert.equal(hashPosition(r.walk.pos), hash0);
});

test("core/deep path: an optional step can be skipped without completion", () => {
  const w = walkTo(1);              // l2_chain, core:false
  assert.equal(currentStep(w).id, "l2_chain");
  const h0 = hashPosition(w.pos);
  const r = skipStep(w);
  assert.equal(r.event, "step");
  assert.equal(currentStep(r.walk).id, "l3_capture");
  assert.notEqual(hashPosition(r.walk.pos), h0);
  assert.ok(r.walk.trail.some((t) => t.action === "skip"), "the skip is recorded");
});

test("core/deep path: a core step cannot be skipped, and the last optional step opens the game", () => {
  const core = skipStep(walkTo(0)); // l1_breath, core:true
  assert.equal(core.event, "not-optional");
  assert.equal(currentStep(core.walk).id, "l1_breath");
  const last = skipStep(walkTo(9)); // l10_escape → the guided game
  assert.equal(last.event, "step");
  assert.equal(currentStep(last.walk).kind, "game");
  assert.equal(last.walk.gameIdx, 4, "the four opening moves replayed");
  const game = skipStep(walkTo(10)); // the game itself is core
  assert.equal(game.event, "not-optional");
});

test("determinism: the same click script yields the same final hash and trail", () => {
  const run = () => {
    let w = newLessonWalk(lesson, board, content.games);
    for (let i = 0; i < lesson.steps.length; i++) w = advanceStep(solveCurrent(w)).walk;
    return { hash: hashPosition(w.pos), trail: JSON.stringify(w.trail) };
  };
  assert.deepEqual(run(), run());
});

test("same_as: the case's compare node points at this board and beat", () => {
  const check = sameAsCheck(content.vignettes, content.boards);
  assert.equal(check.ok, true);
  assert.equal(check.board, "board-shared-breath");
  assert.equal(check.beat, "mutual");
});

test("roles: 'you' and 'them' are two distinct chains with different colours", () => {
  const check = rolesCheck(board);
  assert.equal(check.ok, true, check.why);
  assert.notEqual(check.youColor, check.themColor);
});

test("the mirror board's own beat assertions hold after the capture", () => {
  const done = positionFromSpec(board, "capture_done");
  const white = [...done.stones.entries()].filter(([, c]) => c === WHITE);
  assert.equal(white.length, 0, "the two white stones left the board");
  assert.equal(chainsAt(done).length, 4, "four black chains remain in the teaching setup");
});

test("Chapter 0 graph: the lesson node is reachable and all five responses are endings", () => {
  const v = content.vignettes["shared-breath"];
  const r = reachability(v);
  assert.equal(r.orphans.length, 0, `orphans: ${r.orphans}`);
  assert.ok(r.reachable.has("n2"), "the lesson node is reachable");
  assert.equal(r.endings.length, 5);
  const compare = Object.values(v.nodes).find((n) => n.compare);
  assert.equal(compare.compare.board, board.id);
  assert.equal(compare.compare.beat, "mutual");
});

test("NO moral scoring in the teaching runtime: no score/points/rating/harmony tokens", () => {
  const src = readFileSync(new URL("../app/teaching.js", import.meta.url), "utf-8");
  for (const banned of [/\b(score|points|rating)\w*\s*[:=]/i, /harmony.?index/i]) {
    assert.equal(banned.test(src), false, `banned token ${banned} found in teaching.js`);
  }
});