// teaching.js — the Chapter 0 lesson runtime.
//
// It interprets lesson data (specs/lessons.yaml) over real 5x5 positions from
// the board spec. The engine confirms or refuses; there is no score, no
// "correct path" flag, and no hidden randomness. Every success is a structural
// fact (the clicked set equals the liberty set, the capture count matches, the
// refusal reason is the authored one, or the pass leaves the hash unchanged).
//
// The comparison and contemplation acts live in main.js; this module only owns
// the ladder (show -> try -> confirm/refuse) and the checks tests reuse.

import { emptyPosition, play, groupAt, key, parse, hashPosition, BLACK, WHITE, GameState } from "./rules.js";

const COLOR = (name) => (name === "black" ? BLACK : WHITE);

export function buildPosition(size, setup) {
  const pos = emptyPosition(size);
  for (const [r, c] of setup.black ?? []) {
    const res = play(pos, key(r, c), BLACK);
    if (!res.ok) throw new Error(`lesson: illegal black setup ${r},${c} (${res.reason})`);
    pos.stones = res.pos.stones;
    pos.koPoint = res.pos.koPoint;
  }
  for (const [r, c] of setup.white ?? []) {
    const res = play(pos, key(r, c), WHITE);
    if (!res.ok) throw new Error(`lesson: illegal white setup ${r},${c} (${res.reason})`);
    pos.stones = res.pos.stones;
    pos.koPoint = res.pos.koPoint;
  }
  return pos;
}

export function positionForStep(step, boardSpec) {
  // a game step's board is built by the game runtime (GameState replays the
  // record's authored opening), not from a beat setup
  if (step.kind === "game") return emptyPosition(boardSpec.size);
  const beat = boardSpec.beats[step.beat];
  if (!beat) throw new Error(`lesson: unknown beat "${step.beat}"`);
  // SETUP only — the player's click IS the move. The beat.moves field is
  // reserved for verify.py assertions (which replay independently).
  return buildPosition(boardSpec.size, beat.setup ?? boardSpec.stones);
}

export function newLessonWalk(lesson, boardSpec, games = {}) {
  const first = lesson.steps[0];
  const walk = {
    lesson, boardSpec, games,
    stepIndex: 0,
    phase: 0,
    pos: positionForStep(first, boardSpec),
    clicked: [],
    refused: [],
    ghosts: [],
    lastMove: null,
    done: false,
    message: null,
    trail: [],
  };
  return first.kind === "game" ? initGameStep(walk) : walk;
}

// --- the guided mini-game (kind: "game") ---------------------------------------
//
// A curated full game against grandpa. The learner plays the authored black
// points; each wrong legal click gets a gentle redirect (and, after that, a
// soft hint ring); illegal clicks get the engine's own refusal reason. Grandpa
// replies instantly with the authored white move. The record's `expect`
// claims are board-true — verify.py and tests/game.test.js re-derive them;
// this runtime only replays and teaches.

export function initGameStep(walk) {
  const record = walk.games[walk.lesson.steps[walk.stepIndex].game];
  if (!record) throw new Error(`game "${walk.lesson.steps[walk.stepIndex].game}" is not in the build`);
  const w = {
    ...walk,
    record,
    gs: new GameState(record.size, null),
    gameIdx: 0,
    gameBubble: null,
    gameResult: null,
    hint: false,
    awaitingPass: false,
  };
  // replay the authored opening instantly; grandpa's replies (and the white
  // pass) fire from autoReplies as each learner move lands
  return autoReplies(w).walk;
}

function autoReplies(w) {
  // auto moves (grandpa's authored replies, the white pass) fire immediately;
  // stop when the next authored move belongs to the learner
  while (w.gameIdx < w.record.moves.length) {
    const m = w.record.moves[w.gameIdx];
    if (m.learner) break;
    if (m.at === null) {
      w.gs.gamePass();
      w.lastMove = null;
    } else {
      const res = w.gs.gameMove(m.at);
      if (!res.ok) throw new Error(`game: authored move ${m.num} illegal (${res.reason})`);
      w.lastMove = key(...m.at);
      // grandpa's own captures replace the ghosts; a quiet reply keeps the
      // learner's just-lifted stones visible (the capture's proof)
      if (res.capturedPoints?.length) w.ghosts = res.capturedPoints;
    }
    w.gameBubble = { main: m.teach, prev: w.gameBubble?.main ?? null, captures: { ...w.gs.captures } };
    w.gameIdx += 1;
  }
  w.pos = w.gs.pos;
  const next = w.record.moves[w.gameIdx];
  w.awaitingPass = Boolean(next && next.learner && next.at === null);
  if (!next) w.done = true; // record exhausted without the closing pass
  return { walk: w, event: "reply" };
}

function gameClick(w, k) {
  const m = w.record.moves[w.gameIdx];
  if (w.done || !m) return { walk: w, event: "noop" };
  if (m.at === null) {
    w.message = { key: "lesson.msg.game_use_pass" };
    return { walk: w, event: "wrong" };
  }
  if (!m.learner) {
    w.message = { key: "lesson.msg.game_your_turn" };
    return { walk: w, event: "wrong" };
  }
  // probe first: a legal but off-script click must NOT reach the board
  const probe = play(w.gs.pos, k, BLACK);
  if (!probe.ok) {
    w.message = { key: "lesson.msg.refused_reason", vars: { reason: probe.reason } };
    return { walk: w, event: "refused", reason: probe.reason };
  }
  if (k !== key(...m.at)) {
    w.hint = true;
    w.message = { key: "lesson.msg.game_redirect" };
    return { walk: w, event: "wrong" };
  }
  const res = w.gs.gameMove(parse(k));
  w.hint = false;
  w.lastMove = k;
  w.ghosts = res.capturedPoints ?? [];
  w.gameBubble = { main: m.teach, prev: null, captures: { ...w.gs.captures } };
  w.gameIdx += 1;
  return autoReplies(w);
}

function gamePassPress(w) {
  if (!w.awaitingPass) {
    w.message = { key: "lesson.msg.game_your_turn" };
    return { walk: w, event: "noop" };
  }
  w.gs.gamePass();
  w.gameIdx += 1;
  w.awaitingPass = false;
  w.done = true;
  w.pos = w.gs.pos;
  const s = w.gs.score();
  w.gameResult = {
    black: s.black, white: s.white,
    captures: { ...w.gs.captures },
    note: w.record.count_note,
  };
  const closing = w.record.moves[w.gameIdx - 1];
  w.gameBubble = { main: closing.teach, prev: null, captures: { ...w.gs.captures } };
  w.message = { key: "lesson.msg.game_result", vars: { b: s.black, w: s.white } };
  return { walk: w, event: "game-over" };
}

export function currentStep(walk) {
  return walk.lesson.steps[walk.stepIndex];
}

export function isDone(walk) {
  return walk.done;
}

export function roleAnchor(boardSpec, role) {
  const raw = boardSpec.roles?.[role];
  if (!raw || !raw.includes("@")) return null;
  return raw.split("@")[1];
}

function chainLiberties(pos, anchorKey) {
  return groupAt(pos, anchorKey).liberties;
}

function sharedLibertyCount(pos, youKey, themKey) {
  const a = chainLiberties(pos, youKey);
  const b = chainLiberties(pos, themKey);
  let n = 0;
  for (const k of a) if (b.has(k)) n++;
  return n;
}

export function sharedCorridor(boardSpec, beatName = "mutual") {
  const you = roleAnchor(boardSpec, "you");
  const them = roleAnchor(boardSpec, "them");
  const pos = positionForStep({ beat: beatName }, boardSpec);
  const a = chainLiberties(pos, you);
  const b = chainLiberties(pos, them);
  return [...a].filter((k) => b.has(k));
}

// deterministic reply: the farthest remaining corridor point (ties: lowest key)
export function farthestReply(corridor, pos, playerKey) {
  const [pr, pc] = parse(playerKey);
  const rest = corridor.filter((k) => !pos.stones.has(k));
  if (!rest.length) return null;
  return rest
    .map((k) => {
      const [r, c] = parse(k);
      return { k, d: Math.abs(r - pr) + Math.abs(c - pc) };
    })
    .sort((x, y) => (y.d - x.d) || x.k.localeCompare(y.k, "en"))[0].k;
}

// --- the ladder ---------------------------------------------------------------

export function clickPoint(walk, point) {
  const step = currentStep(walk);
  const k = key(...point);
  const w = { ...walk, message: null };

  if (step.kind === "liberties") {
    const libs = chainLiberties(w.pos, key(...step.chain));
    if (!libs.has(k)) {
      w.message = { key: "lesson.msg.not_liberty" };
      return { walk: w, event: "not-liberty" };
    }
    const clicked = new Set(w.clicked);
    if (clicked.has(k)) clicked.delete(k);
    else clicked.add(k);
    w.clicked = [...clicked];
    if (clicked.size === libs.size) {
      w.done = true;
      w.message = { key: "lesson.msg.counted", vars: { n: libs.size } };
    }
    return { walk: w, event: "liberty" };
  }

  if (step.kind === "play") {
    const res = play(w.pos, k, COLOR(step.color));
    if (!res.ok) {
      w.message = { key: "lesson.msg.refused_reason", vars: { reason: res.reason } };
      return { walk: w, event: "refused", reason: res.reason };
    }
    w.pos = res.pos;
    w.lastMove = k;
    w.trail = [...w.trail, { step: step.id, color: step.color, at: k }];
    if ((res.capturedCount ?? 0) >= (step.expect_captured ?? 1)) {
      w.done = true;
      w.ghosts = [...(res.capturedPoints ?? [])];
      w.message = { key: "lesson.msg.captured", vars: { n: res.capturedCount } };
    } else {
      w.message = { key: "lesson.msg.no_capture" };
    }
    return { walk: w, event: res.capturedCount ? "capture" : "placed" };
  }

  if (step.kind === "refuse") {
    const authored = (step.points ?? [step.point]).map(([r, c]) => key(r, c));
    if (!authored.includes(k)) {
      w.message = { key: "lesson.msg.wrong_point" };
      return { walk: w, event: "wrong" };
    }
    const res = play(w.pos, k, COLOR(step.color));
    if (res.ok) {
      w.message = { key: "lesson.msg.surprisingly_legal" };
      return { walk: w, event: "wrong" };
    }
    if (res.reason !== step.reason) {
      w.message = { key: "lesson.msg.refused_reason", vars: { reason: res.reason } };
      return { walk: w, event: "refused", reason: res.reason };
    }
    const refused = new Set(w.refused);
    refused.add(k);
    w.refused = [...refused];
    w.trail = [...w.trail, { step: step.id, color: step.color, at: k, refused: res.reason }];
    if (refused.size >= (step.count ?? 1)) {
      w.done = true;
      w.message = { key: (step.count ?? 1) > 1 ? "lesson.msg.both_eyes" : "lesson.msg.refused_suicide" };
    } else {
      w.message = { key: "lesson.msg.one_eye" };
    }
    return { walk: w, event: "refused", reason: res.reason };
  }

  if (step.kind === "mutual") return mutualClick(w, step, k);
  if (step.kind === "game") return gameClick(w, k);

  return { walk: w, event: "noop" };
}

function mutualClick(w, step, k) {
  const corridor = step.corridor.map(([r, c]) => key(r, c));
  if (!corridor.includes(k)) {
    w.message = { key: "lesson.msg.wrong_point" };
    return { walk: w, event: "wrong" };
  }
  if (w.phase === 2) {
    w.message = { key: "lesson.msg.pass_lost" };
    return { walk: w, event: "lost" };
  }
  if (w.pos.stones.has(k)) {
    w.message = { key: "lesson.msg.occupied" };
    return { walk: w, event: "occupied" };
  }
  const mine = play(w.pos, k, COLOR(step.color));
  if (!mine.ok) {
    w.message = { key: "lesson.msg.refused_reason", vars: { reason: mine.reason } };
    return { walk: w, event: "refused", reason: mine.reason };
  }
  w.pos = mine.pos;
  w.lastMove = k;
  w.trail = [...w.trail, { step: step.id, color: step.color, at: k }];

  const reply = farthestReply(corridor, w.pos, k);
  if (reply) {
    const theirs = play(w.pos, reply, step.color === "black" ? WHITE : BLACK);
    if (theirs.ok) {
      w.pos = theirs.pos;
      w.trail = [...w.trail, { step: step.id, color: "white", at: reply }];
    }
  }
  w.phase += 1;

  const you = roleAnchor(w.boardSpec, "you");
  const them = roleAnchor(w.boardSpec, "them");
  if (!w.pos.stones.has(you)) {
    w.phase = 2;
    w.message = { key: "lesson.msg.mutual_lost" };
    return { walk: w, event: "captured" };
  }
  const n = sharedLibertyCount(w.pos, you, them);
  w.message = { key: "lesson.msg.mutual_reply", vars: { n } };
  return { walk: w, event: "reply" };
}

export function pressPass(walk) {
  const step = currentStep(walk);
  const w = { ...walk, message: null };
  if (step.kind === "game") return gamePassPress(w);
  if (step.kind === "pass") {
    w.trail = [...w.trail, { step: step.id, action: "pass" }];
    w.done = true;
    w.message = { key: "lesson.msg.pass_kept" };
    return { walk: w, event: "pass" };
  }
  if (step.kind === "mutual") {
    if (w.phase === 2) {
      w.message = { key: "lesson.msg.pass_lost" };
      return { walk: w, event: "lost" };
    }
    w.trail = [...w.trail, { step: step.id, action: "pass" }];
    w.done = true;
    w.message = { key: "lesson.msg.pass_kept" };
    return { walk: w, event: "pass" };
  }
  return { walk: w, event: "noop" };
}

export function resetStep(walk) {
  const step = currentStep(walk);
  const base = {
    ...walk,
    phase: 0,
    clicked: [],
    refused: [],
    ghosts: [],
    lastMove: null,
    done: false,
    message: { key: "lesson.msg.reset" },
  };
  if (step.kind === "game") {
    return { ...initGameStep(base), message: { key: "lesson.msg.reset" } };
  }
  return {
    ...base,
    pos: positionForStep(step, walk.boardSpec),
  };
}

export function advanceStep(walk) {
  if (!walk.done) return { walk, event: "not-done" };
  if (walk.stepIndex + 1 >= walk.lesson.steps.length) {
    return { walk: { ...walk, done: true }, event: "lesson-done" };
  }
  const nextIndex = walk.stepIndex + 1;
  const next = walk.lesson.steps[nextIndex];
  const w = {
    ...walk,
    stepIndex: nextIndex,
    phase: 0,
    clicked: [],
    refused: [],
    ghosts: [],
    lastMove: null,
    done: false,
    message: null,
  };
  return {
    walk: next.kind === "game" ? initGameStep(w) : { ...w, pos: positionForStep(next, walk.boardSpec) },
    event: "step",
  };
}

// core/deep path: an optional step can be stepped over without completing it.
// The skipped step is recorded in the trail (determinism), and the next step
// (including the guided game) is initialised exactly as advanceStep would.
export function skipStep(walk) {
  const step = currentStep(walk);
  if (step.core) return { walk, event: "not-optional" };
  const trail = [...walk.trail, { step: step.id, action: "skip" }];
  const nextIndex = walk.stepIndex + 1;
  if (nextIndex >= walk.lesson.steps.length) {
    return { walk: { ...walk, done: true, trail }, event: "lesson-done" };
  }
  const next = walk.lesson.steps[nextIndex];
  const w = {
    ...walk,
    stepIndex: nextIndex,
    phase: 0,
    clicked: [],
    refused: [],
    ghosts: [],
    lastMove: null,
    done: false,
    message: null,
    trail,
  };
  return {
    walk: next.kind === "game" ? initGameStep(w) : { ...w, pos: positionForStep(next, walk.boardSpec) },
    event: "step",
  };
}

// --- checks reused by the tests and verify.py --------------------------------

// The corridor is a four-point zugzwang: fill one and the reply takes the
// farthest remaining; after the first exchange both chains hold exactly two
// liberties, and a second attack by the first mover loses its chain.
export function firstMoverLoses(boardSpec) {
  const chk = boardSpec.lesson_checks?.corridor;
  if (!chk) return { ok: false, why: "no corridor check in the board spec" };
  const corridor = chk.corridor.map(([r, c]) => key(r, c));
  const you = key(...chk.you);
  const them = key(...chk.them);
  const details = [];
  for (const first of corridor) {
    let pos = buildPosition(boardSpec.size, chk.setup);
    const a = play(pos, first, BLACK);
    if (!a.ok) return { ok: false, why: `first move illegal: ${first}` };
    pos = a.pos;
    const r = farthestReply(corridor, pos, first);
    const b = play(pos, r, WHITE);
    if (!b.ok) return { ok: false, why: `reply illegal: ${r}` };
    pos = b.pos;
    if (sharedLibertyCount(pos, you, them) !== 2) {
      return { ok: false, why: `first exchange did not leave 2-2 (${first})` };
    }
    const remain = corridor.filter((k) => !pos.stones.has(k));
    for (const second of remain) {
      const c = play(pos, second, BLACK);
      if (!c.ok) continue;
      let after = c.pos;
      const last = corridor.filter((k) => !after.stones.has(k));
      if (last.length !== 1) return { ok: false, why: `corridor count after ${second}` };
      const d = play(after, last[0], WHITE);
      if (!d.ok) return { ok: false, why: `final reply illegal: ${last[0]}` };
      if (d.pos.stones.has(you)) {
        return { ok: false, why: `first mover survived: ${first} / ${second}` };
      }
      details.push({ first, second, capturedBy: last[0] });
    }
  }
  return { ok: true, branches: details.length, details };
}

// referential integrity: the case's compare node must point at this board+beat
export function sameAsCheck(vignettes, boards) {
  const board = Object.values(boards).find((b) => b.same_as);
  if (!board) return { ok: false, why: "no board declares same_as" };
  const v = vignettes[board.same_as.vignette];
  if (!v) return { ok: false, why: "same_as names an unknown vignette" };
  const node = Object.values(v.nodes).find((n) => n.compare);
  if (!node) return { ok: false, why: "the named vignette has no compare node" };
  return {
    ok: node.compare.board === board.id && node.compare.beat === board.same_as.beat,
    board: board.id,
    beat: board.same_as.beat,
    node: node.compare,
  };
}

export function rolesCheck(boardSpec) {
  const you = roleAnchor(boardSpec, "you");
  const them = roleAnchor(boardSpec, "them");
  if (!you || !them) return { ok: false, why: "missing role anchor" };
  const pos = positionForStep({ beat: "mutual" }, boardSpec);
  const a = pos.stones.get(you);
  const b = pos.stones.get(them);
  if (!a || !b) return { ok: false, why: "role anchor is not a stone in the beat" };
  if (a === b) return { ok: false, why: "roles share a colour" };
  const ga = groupAt(pos, you).stones;
  const gb = groupAt(pos, them).stones;
  return { ok: ![...ga].some((s) => gb.has(s)), you, them, youColor: a, themColor: b };
}

export function positionHash(walk) {
  return hashPosition(walk.pos);
}