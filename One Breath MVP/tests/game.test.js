// game.test.js — the guided mini-game's gates.
//
// The curated record (specs/game-record.yaml) is BOARD-TRUE by contract: every
// `expect` claim on every move is re-derived here from the SAME JS engine the
// browser runs (tools/verify.py re-derives them again with the independent
// Python brain). The runtime walk (teaching.js kind:"game") is driven through
// its real entry points: clickPoint / pressPass — including the redirect on an
// off-script click, the refusal on an illegal one, and the closing double pass.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  GameState, teachingReply, eyesFor, allLegalMoves, play, key, groupAt,
  hashPosition, BLACK, WHITE, emptyPosition,
} from "../app/rules.js";
import { newLessonWalk, currentStep, clickPoint, pressPass, resetStep, advanceStep, moveCursor } from "../app/teaching.js";

const content = JSON.parse(
  readFileSync(new URL("../dist/content.json", import.meta.url), "utf-8"));
const rec = content.games["guided-game"];
const lesson = content.lessons["shared-breath"];
const board = content.boards["board-shared-breath"];

// --- GameState unit behaviour -------------------------------------------------

test("GameState: setup, alternation, capture accounting, two-pass end", () => {
  // white (1,2) sits between black (1,1),(1,3) with one breath left;
  // black (2,2) takes it
  const gs = new GameState(5, { black: [[1, 1], [1, 3]], white: [[1, 2]] });
  assert.equal(gs.toPlay, BLACK);
  const res = gs.gameMove([2, 2]);
  assert.equal(res.ok, true);
  assert.equal(res.capturedCount, 1);
  assert.equal(gs.captures.black, 1);
  assert.equal(gs.toPlay, WHITE);
  assert.equal(gs.pos.stones.has(key(1, 2)), false, "the captured stone left");
  gs.gamePass();
  assert.equal(gs.done, false, "one pass is not the end");
  gs.gamePass();
  assert.equal(gs.done, true, "two passes end the game");
});

test("GameState: a refused move changes nothing and keeps the turn", () => {
  // white surrounds the corner point (1,1) — black playing there is suicide
  const gs = new GameState(5, { white: [[1, 2], [2, 1]] });
  const h0 = hashPosition(gs.pos);
  const res = gs.gameMove([1, 1]);
  assert.equal(res.ok, false);
  assert.equal(res.reason, "suicide");
  assert.equal(hashPosition(gs.pos), h0, "a refused move leaves the position");
  assert.equal(gs.toPlay, BLACK, "and it is still black's turn");
  const occupied = gs.gameMove([1, 2]);
  assert.equal(occupied.ok, false);
  assert.equal(occupied.reason, "occupied");
  assert.equal(hashPosition(gs.pos), h0);
});

test("GameState: Chinese area scoring counts stones plus one-bordered regions", () => {
  // black walls off the top-left 2x2 corner; white's lone stone sits in the
  // unclaimed rest, which borders both colours and stays uncounted
  const gs = new GameState(5, {
    black: [[1, 3], [2, 3], [3, 3], [3, 2], [3, 1]],
    white: [[5, 5]],
  });
  const s = gs.score();
  // black stones 5 + enclosed empty (1,1),(1,2),(2,1),(2,2) = 4 territory
  assert.equal(s.black, 9);
  assert.equal(s.white, 1);
  assert.equal(s.neutral, 15, "the contested rest is uncounted");
  assert.equal(s.black + s.white + s.neutral, 25);
});

// --- the curated record is board-true -------------------------------------------

test("record shape: 21 entries, colours alternate, learner moves are 8+1 pass", () => {
  assert.equal(rec.moves.length, 21);
  for (const m of rec.moves) {
    assert.equal((m.color === "black") === (m.num % 2 === 1), true,
      `M${m.num}: colour must alternate black-first`);
    assert.ok(m.teach?.zh?.trim() && m.teach?.en?.trim(), `M${m.num}: teach must be bilingual`);
    assert.ok(m.phase, `M${m.num}: phase tag`);
    assert.equal(m.learner === true || m.auto === true, true,
      `M${m.num}: every move belongs to someone`);
  }
  const learner = rec.moves.filter((m) => m.learner);
  assert.equal(learner.filter((m) => m.at !== null).length, 8,
    "the learner finds eight points themselves");
  assert.deepEqual(learner.filter((m) => m.at === null).map((m) => m.num), [21],
    "the game ends on the learner's own pass");
});

function replayRecord() {
  const gs = new GameState(rec.size, null);
  const caps = { black: 0, white: 0 };
  const ghostsAfter = {};
  for (const m of rec.moves) {
    let captured = 0;
    let points = [];
    if (m.at !== null) {
      const res = gs.gameMove(m.at);
      assert.equal(res.ok, true, `M${m.num}: ${m.color} ${m.at} must be legal (${res.reason})`);
      captured = res.capturedCount ?? 0;
      points = res.capturedPoints ?? [];
      caps[m.color] += captured;
    } else {
      gs.gamePass();
    }
    // expect: captures
    if (m.expect?.captures !== undefined) {
      assert.equal(captured, m.expect.captures, `M${m.num}: captured ${captured}`);
    }
    // expect: libs — chain liberties at each anchor
    for (const chk of m.expect?.libs ?? []) {
      const p = key(...chk.at);
      assert.ok(gs.pos.stones.has(p), `M${m.num}: anchor ${p} must be on board`);
      assert.equal(groupAt(gs.pos, p).liberties.size, chk.count,
        `M${m.num}: libs at ${p}`);
    }
    // expect: eyes — eyesFor(anchor) equals exactly the authored set
    if (m.expect?.eyes) {
      const got = eyesFor(gs.pos, key(...m.expect.eyes.at))
        .map((k) => k.split(",").map(Number)).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      const want = [...m.expect.eyes.eyes].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      assert.deepEqual(got, want, `M${m.num}: eyes ${JSON.stringify(got)}`);
    }
    // expect: score — the final Chinese count
    if (m.expect?.score) {
      const s = gs.score();
      assert.equal(s.black, m.expect.score.black, `M${m.num}: black area`);
      assert.equal(s.white, m.expect.score.white, `M${m.num}: white area`);
    }
    ghostsAfter[m.num] = points;
  }
  return { gs, caps, ghostsAfter };
}

test("record replay: every move is legal and every expect claim holds (JS brain)", () => {
  const { gs, caps, ghostsAfter } = replayRecord();
  assert.equal(gs.done, true, "the double pass ends the game");
  assert.equal(caps.black, 5, "black captured 1 + 4");
  assert.equal(caps.white, 0, "grandpa never captures — this is a first game");
  assert.deepEqual(ghostsAfter[5].map((k) => k.split(",").map(Number)), [[1, 2]],
    "the first prize is the squeezing stone");
  assert.equal(ghostsAfter[13].length, 4, "the chase ends with four lifted stones");
  const s = gs.score();
  assert.deepEqual([s.black, s.white], [12, 4]);
});

test("the two eyes are real: white has no legal move inside them, ever", () => {
  const { gs } = replayRecord();
  // replay to just after M17 (before the endgame): pass through the remaining
  const mid = new GameState(rec.size, null);
  for (const m of rec.moves.filter((x) => x.num <= 17)) {
    if (m.at === null) mid.gamePass();
    else mid.gameMove(m.at);
  }
  const eyes = eyesFor(mid.pos, key(2, 2)).map((k) => k.split(",").map(Number));
  assert.deepEqual(eyes, [[3, 1], [5, 1]], "exactly the two doors");
  for (const eye of eyes) {
    const res = play(mid.pos, key(...eye), WHITE);
    assert.equal(res.ok, false, `white cannot enter the eye ${eye}`);
    assert.equal(res.reason, "suicide");
  }
  assert.equal(allLegalMoves(mid.pos, WHITE).some((m) =>
    m.at[0] === 3 && m.at[1] === 1), false, "and the enumeration agrees");
});

// --- the runtime walk (teaching.js kind:"game") -----------------------------------

function gameWalk() {
  const w = newLessonWalk(lesson, board, content.games);
  // walk the ladder to the game step
  let out = w;
  for (let i = 0; i < lesson.steps.length - 1; i++) {
    const step = currentStep(out);
    if (step.kind === "game") break;
    out = advanceStep(solve(out)).walk;
  }
  return out;
}

function solve(w) {
  const step = currentStep(w);
  if (step.kind === "liberties") {
    const libs = [...groupAt(w.pos, key(...step.chain)).liberties]
      .map((k) => k.split(",").map(Number));
    for (const p of libs) w = clickPoint(w, p).walk;
    return w;
  }
  if (step.kind === "play") return clickPoint(w, step.solution).walk;
  if (step.kind === "refuse") {
    for (const p of step.points ?? [step.point]) w = clickPoint(w, p).walk;
    return w;
  }
  if (step.kind === "mutual") {
    w = clickPoint(w, step.corridor[0]).walk;
    return pressPass(w).walk;
  }
  if (step.kind === "pass") return pressPass(w).walk;
  return w;
}

test("game runtime: the authored opening replays before the learner's first click", () => {
  const w = gameWalk();
  const step = currentStep(w);
  assert.equal(step.kind, "game");
  assert.equal(w.gameIdx, 4, "M1-M4 replayed instantly");
  assert.equal(w.record.moves[w.gameIdx].num, 5, "the learner's first task is M5");
  assert.equal(w.gs.pos.stones.size, 4, "four opening stones on the board");
  assert.ok(w.gameBubble?.main?.zh, "grandpa's recap bubble is present");
});

test("game runtime: an off-script legal click redirects without touching the board", () => {
  let w = gameWalk();
  const h0 = hashPosition(w.gs.pos);
  const r = clickPoint(w, [3, 3]); // legal, but not the authored point
  w = r.walk;
  assert.equal(r.event, "wrong");
  assert.equal(w.message.key, "lesson.msg.game_redirect");
  assert.equal(hashPosition(w.gs.pos), h0, "the board did not change");
  assert.equal(w.hint, true, "and the gentle hint ring appears");
  assert.equal(w.gameIdx, 4, "still the learner's move");
});

test("game runtime: an illegal click reports the engine's own refusal", () => {
  let w = gameWalk();
  const r = clickPoint(w, [1, 1]); // occupied (the authored opening stone)
  w = r.walk;
  assert.equal(r.event, "refused");
  assert.equal(r.reason, "occupied");
  assert.equal(w.gameIdx, 4);
});

test("game runtime: the golden walk ends 12-4 with five captures and no white capture", () => {
  let w = gameWalk();
  let guard = 0;
  while (!w.done && guard++ < 30) {
    if (w.awaitingPass) { w = pressPass(w).walk; break; }
    const m = w.record.moves[w.gameIdx];
    w = clickPoint(w, m.at).walk;
  }
  assert.equal(w.done, true, "the closing pass ends the game");
  assert.equal(w.gs.done, true);
  assert.deepEqual([w.gameResult.black, w.gameResult.white], [12, 4]);
  assert.deepEqual([w.gameResult.captures.black, w.gameResult.captures.white], [5, 0]);
  assert.ok(w.gameResult.note?.zh, "the count note is present");
  assert.equal(w.message.key, "lesson.msg.game_result");
  // and the walk advances out of the lesson
  const r = advanceStep(w);
  assert.equal(r.event, "lesson-done", "the game is the ladder's last step");
});

test("game runtime: reset replays the authored opening from scratch", () => {
  let w = gameWalk();
  w = clickPoint(w, [2, 2]).walk; // play M5
  assert.equal(w.gameIdx, 6, "M5 played, M6 replied");
  // the lifted stone stays visible even after grandpa's quiet reply
  assert.deepEqual(w.ghosts, [key(1, 2)], "the first capture's ghost persists");
  const r = resetStep(w);
  assert.equal(r.gameIdx, 4, "back to the learner's first task");
  assert.equal(r.gs.moveCount, 4, "four opening stones replayed");
  assert.equal(r.hint, false);
  assert.equal(r.done, false);
});

test("teachingReply: across a long game the deterministic opponent never picks an illegal point", () => {
  // the reply brain's contract is LEGALITY, not termination: two greedy
  // policies can oscillate in endless recaptures (each capture reopens a
  // point), exactly like an unfinished real game. What must never happen is
  // an off-board or refused reply.
  const gs = new GameState(5, null);
  let last = null;
  for (let i = 0; i < 60; i++) {
    if (gs.done) break;
    let played = false;
    outer:
    for (let r = 1; r <= 5; r++) for (let c = 1; c <= 5; c++) {
      if (gs.pos.stones.has(key(r, c))) continue;
      const res = gs.gameMove([r, c]);
      if (res.ok) { played = true; last = [r, c]; break outer; }
    }
    if (!played) gs.gamePass();
    if (gs.done) break;
    const reply = teachingReply(gs, last);
    if (!reply) gs.gamePass();
    else {
      const rr = gs.gameMove(reply);
      assert.equal(rr.ok, true, `teachingReply picked an illegal point ${reply} (${rr.reason})`);
    }
  }
  // the position stays a valid 5x5 board no matter how long the fight runs
  for (const k of gs.pos.stones.keys()) {
    const [r, c] = k.split(",").map(Number);
    assert.ok(r >= 1 && r <= 5 && c >= 1 && c <= 5, `stone off board: ${k}`);
  }
});


test("the personal mirror: the walk records what 照见 and 坐观 will play on", () => {
  // the player's own game becomes act 4's board: opening snapshot, the five
  // lifted stones in order, and the final position with its two doors
  let w = gameWalk();
  let guard = 0;
  while (!w.done && guard++ < 30) {
    if (w.awaitingPass) { w = pressPass(w).walk; break; }
    const m = w.record.moves[w.gameIdx];
    w = clickPoint(w, m.at).walk;
  }
  assert.ok(w.openingPos, "the opening snapshot exists");
  assert.equal(w.openingPos.stones.size, 4, "the authored opening, four stones");
  assert.equal(w.captureLog[0], key(1, 2),
    "the squeeze stone came off first");
  assert.deepEqual([...w.captureLog].sort(),
    [key(1, 2), key(2, 1), key(3, 1), key(4, 1), key(5, 1)].sort(),
    "the log holds exactly the chase's five lifted stones");
  // the doors ARE former capture points: the land exists because of the lifts
  const eyes = eyesFor(w.gs.pos, key(2, 2)).map((k) => k.split(",").map(Number));
  assert.deepEqual(eyes, [[3, 1], [5, 1]]);
  for (const [r, c] of eyes) {
    assert.ok(w.captureLog.includes(key(r, c)),
      `the door (${r},${c}) was a capture point — 提过的子仍在棋局里`);
  }
});

test("keyboard access: the grid cursor clamps at the board edge", () => {
  const size = 5;
  let cur = { r: 3, c: 3 };
  for (let i = 0; i < 10; i++) cur = moveCursor(cur, "ArrowUp", size);
  assert.deepEqual(cur, { r: 1, c: 3 }, "the cursor never leaves the board");
  for (let i = 0; i < 10; i++) cur = moveCursor(cur, "ArrowRight", size);
  assert.deepEqual(cur, { r: 1, c: 5 });
  assert.deepEqual(moveCursor(cur, "Enter", size), cur,
    "non-arrow keys do not move the hand");
});

test("no engine randomness: the golden walk is reproducible byte for byte", () => {
  const run = () => {
    let w = gameWalk();
    let guard = 0;
    while (currentStep(w).kind === "game" && guard++ < 30) {
      if (w.awaitingPass) { w = pressPass(w).walk; break; }
      const m = w.record.moves[w.gameIdx];
      w = clickPoint(w, m.at).walk;
    }
    return {
      hash: hashPosition(w.gs.pos),
      idx: w.gameIdx,
      result: JSON.stringify(w.gameResult),
    };
  };
  assert.deepEqual(run(), run());
});
