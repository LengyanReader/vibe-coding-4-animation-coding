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
