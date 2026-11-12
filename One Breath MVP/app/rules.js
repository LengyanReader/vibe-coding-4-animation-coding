// rules.js — Go rules as pure functions for the mirror board.
//
// Scope is deliberately small: this is NOT a Go engine. The mirror layer needs
// exactly enough rules to make the scripted beats provable — placement, capture,
// suicide refusal, simple-ko refusal, group/liberty queries. Every function is
// pure: (position, action) -> position | refusal. The tests watch each rule go
// red (an illegal move must be refused, a capture must clear), which is the
// repo doctrine: a gate nobody has seen fail is not a gate.
//
// A position is an object {size, stones: Map "r,c" -> 1|2, koPoint: "r,c"|null}
// where 1 = black (the player's side of the metaphor), 2 = white (the other).

export const BLACK = 1;
export const WHITE = 2;

export const key = (r, c) => `${r},${c}`;
export const parse = (k) => k.split(",").map(Number);

export function emptyPosition(size) {
  return { size, stones: new Map(), koPoint: null };
}

function neighbors(size, r, c) {
  const out = [];
  if (r > 1) out.push(key(r - 1, c));
  if (r < size) out.push(key(r + 1, c));
  if (c > 1) out.push(key(r, c - 1));
  if (c < size) out.push(key(r, c + 1));
  return out;
}

export function groupAt(pos, k) {
  // flood-fill the chain containing k; returns {stones: Set, liberties: Set}
  const color = pos.stones.get(k);
  const stones = new Set([k]);
  const liberties = new Set();
  const stack = [k];
  while (stack.length) {
    const cur = stack.pop();
    const [r, c] = parse(cur);
    for (const n of neighbors(pos.size, r, c)) {
      const v = pos.stones.get(n);
      if (v === undefined) liberties.add(n);
      else if (v === color && !stones.has(n)) {
        stones.add(n);
        stack.push(n);
      }
    }
  }
  return { stones, liberties };
}

export function libertiesAt(pos, k) {
  return groupAt(pos, k).liberties.size;
}

// A play attempt returns {ok: true, pos} or {ok: false, reason}.
// reasons: "occupied" | "suicide" | "ko" — each refusal is observable in tests.
export function play(pos, k, color) {
  if (pos.stones.has(k)) return { ok: false, reason: "occupied" };
  if (pos.koPoint && pos.koPoint === k) return { ok: false, reason: "ko" };

  const next = { size: pos.size, stones: new Map(pos.stones), koPoint: null };
  next.stones.set(k, color);

  // capture every adjacent enemy chain left without liberties
  const [r, c] = parse(k);
  const enemy = color === BLACK ? WHITE : BLACK;
  const captured = [];
  const handled = new Set();
  for (const n of neighbors(next.size, r, c)) {
    if (next.stones.get(n) === enemy && !handled.has(n)) {
      const g = groupAt(next, n);
      for (const s of g.stones) handled.add(s);
      if (g.liberties.size === 0) captured.push(g);
    }
  }
  let koPoint = null;
  const seen = new Set();
  for (const g of captured) {
    for (const s of g.stones) {
      seen.add(s);
      next.stones.delete(s);
    }
    // simple ko: a single stone captured by the single placed stone
    if (g.stones.size === 1 && captured.length === 1) {
      koPoint = [...g.stones][0];
    }
  }

  // suicide check AFTER captures: own chain must have liberties now
  const own = groupAt(next, k);
  if (own.liberties.size === 0) return { ok: false, reason: "suicide" };

  next.koPoint = koPoint;
  return { ok: true, pos: next, capturedCount: seen.size, capturedPoints: [...seen] };
}

// eyesFor — the empty points enclosed by one chain (each neighbour is one of
// its stones). Used by the two-eye lesson; it is a query, not a rule.
export function eyesFor(pos, anchorKey) {
  const g = groupAt(pos, anchorKey);
  if (!g.stones.size) return [];
  const out = [];
  for (const lib of g.liberties) {
    const [r, c] = parse(lib);
    if (neighbors(pos.size, r, c).every((n) => g.stones.has(n))) out.push(lib);
  }
  return out;
}

// allLegalMoves — enumerate every point `color` may legally play. The teaching
// claim "no white move exists inside the eyes" and the corridor check both use
// this; the Python verifier re-derives the same enumeration independently.
export function allLegalMoves(pos, color) {
  const out = [];
  for (let r = 1; r <= pos.size; r++) {
    for (let c = 1; c <= pos.size; c++) {
      const k = key(r, c);
      if (pos.stones.has(k)) continue;
      const res = play(pos, k, color);
      if (res.ok) out.push({ at: [r, c], key: k, captured: res.capturedCount ?? 0 });
    }
  }
  return out;
}

export function hashPosition(pos) {
  // deterministic payload hash for the determinism gate
  const entries = [...pos.stones.entries()].sort(([a], [b]) =>
    a.localeCompare(b, "en"));
  const body = entries.map(([k, v]) => `${k}:${v}`).join(";") +
    `|ko:${pos.koPoint ?? "-"}`;
  // FNV-1a 32-bit — small, stable, not cryptographic (positions are public data)
  let h = 0x811c9dc5;
  for (let i = 0; i < body.length; i++) {
    h ^= body.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return ("00000000" + h.toString(16)).slice(-8);
}

// bestCaptureMove — the "算力手": a tiny deterministic calculator that
// enumerates every legal move for `color` and returns the one maximizing
// (captured stones, then resulting liberties of the placed chain, then
// lowest coordinate for stability). This IS the case-two opponent's brain:
// real computation, no LLM, no hardcoding — and honestly small.
export function bestCaptureMove(pos, color) {
  let best = null;
  for (let r = 1; r <= pos.size; r++) {
    for (let c = 1; c <= pos.size; c++) {
      const k = key(r, c);
      if (pos.stones.has(k)) continue;
      const res = play(pos, k, color);
      if (!res.ok) continue;
      const chain = groupAt(res.pos, k);
      const score = [res.capturedCount ?? 0, chain.liberties.size, -r, -c];
      if (!best || score > best.score) {
        best = { at: [r, c], captured: res.capturedCount ?? 0, libs: chain.liberties.size, score };
      }
    }
  }
  return best;
}

// --- GameState: a thin game-state wrapper for guided mini-games ---------------
//
// rules.js deliberately does NOT implement a Go engine (header, lines 1-11).
// GameState is the minimum wrapper needed to run a curated mini-game:
// alternating turns, pass tracking, two-pass end, and Chinese area scoring.
// It is NOT a full engine — no handicap, no move history/undo, no AI beyond
// the calling code's choice of reply policy.

export class GameState {
  constructor(size, setup) {
    this.size = size;
    const base = emptyPosition(size);
    if (setup) {
      for (const [r, c] of setup.black ?? []) {
        const res = play(base, key(r, c), BLACK);
        if (!res.ok) throw new Error(`GameState: illegal setup ${r},${c} (${res.reason})`);
        base.stones = res.pos.stones;
      }
      for (const [r, c] of setup.white ?? []) {
        const res = play(base, key(r, c), WHITE);
        if (!res.ok) throw new Error(`GameState: illegal setup ${r},${c} (${res.reason})`);
        base.stones = res.pos.stones;
      }
    }
    this.pos = base;
    this.toPlay = BLACK;
    this.passes = 0;
    this.moveCount = 0;
    this.done = false;
    this.captures = { black: 0, white: 0 }; // stones captured BY each side
  }

  gameMove(at) {
    if (this.done) return { ok: false, reason: "game-over" };
    const color = this.toPlay;
    const res = play(this.pos, key(...at), color);
    if (!res.ok) return res;
    this.pos = res.pos;
    if (color === BLACK) this.captures.black += res.capturedCount ?? 0;
    else this.captures.white += res.capturedCount ?? 0;
    this.toPlay = color === BLACK ? WHITE : BLACK;
    this.passes = 0;
    this.moveCount++;
    return { ...res, ok: true };
  }

  gamePass() {
    if (this.done) return;
    this.passes++;
    this.toPlay = this.toPlay === BLACK ? WHITE : BLACK;
    if (this.passes >= 2) this.done = true;
  }

  /** Chinese area scoring: stones on board + empty regions bordered by only
      one colour. Returns {black, white, neutral}. */
  score() {
    const size = this.size;
    const visited = new Set();
    const scores = { black: 0, white: 0, neutral: 0 };
    for (const [k, v] of this.pos.stones) {
      if (v === BLACK) scores.black++;
      else scores.white++;
    }
    for (let r = 1; r <= size; r++) {
      for (let c = 1; c <= size; c++) {
        const k = key(r, c);
        if (this.pos.stones.has(k) || visited.has(k)) continue;
        // flood-fill empty region
        const region = new Set([k]);
        const stack = [k];
        const borders = new Set();
        while (stack.length) {
          const cur = stack.pop();
          visited.add(cur);
          const [cr, cc] = parse(cur);
          for (const n of neighbors(size, cr, cc)) {
            const v = this.pos.stones.get(n);
            if (v === undefined) {
              if (!region.has(n)) { region.add(n); stack.push(n); }
            } else borders.add(v);
          }
        }
        const area = region.size;
        if (borders.size === 1) {
          if (borders.has(BLACK)) scores.black += area;
          else scores.white += area;
        } else scores.neutral += area;
      }
    }
    return scores;
  }
}

// --- a teaching-strength opponent (deterministic, no AI) ----------------------
// Priority: extend own atari > capture > any legal move (farthest from last
// enemy move for variety). This is NOT a Go engine — just enough to give the
// learner a responsive opponent for a guided mini-game.

export function teachingReply(gs, lastEnemyMove) {
  const legal = [];
  for (let r = 1; r <= gs.size; r++) {
    for (let c = 1; c <= gs.size; c++) {
      const k = key(r, c);
      if (gs.pos.stones.has(k)) continue;
      const res = play(gs.pos, k, WHITE);
      if (res.ok) legal.push({ at: [r, c], captured: res.capturedCount ?? 0, libs: groupAt(res.pos, k).liberties.size });
    }
  }
  if (!legal.length) return null;
  // 1. capture: max captured
  const caps = legal.filter((m) => m.captured > 0);
  if (caps.length) return caps.sort((a, b) => b.captured - a.captured)[0].at;
  // 2. extend own atari: find own chains with 1 lib, play their liberty —
  // but ONLY if that liberty is actually legal (filling your own last
  // liberty can be suicide, and the differential gate would catch it)
  const ownChains = [];
  const seen = new Set();
  for (const [k, v] of gs.pos.stones) {
    if (v !== WHITE || seen.has(k)) continue;
    const g = groupAt(gs.pos, k);
    for (const s of g.stones) seen.add(s);
    if (g.liberties.size === 1) {
      ownChains.push([...g.liberties][0]);
    }
  }
  const saves = ownChains.filter((k) => play(gs.pos, k, WHITE).ok);
  if (saves.length) return saves[0].split(",").map(Number);
  // 3. any legal move farthest from last enemy move
  if (lastEnemyMove) {
    const [er, ec] = lastEnemyMove;
    legal.sort((a, b) => {
      const da = Math.abs(a.at[0] - er) + Math.abs(a.at[1] - ec);
      const db = Math.abs(b.at[0] - er) + Math.abs(b.at[1] - ec);
      return db - da;
    });
    return legal[0].at;
  }
  return legal[0].at;
}
