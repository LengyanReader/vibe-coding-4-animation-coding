// board-mirror.js — render the mirror position and its beat states.
//
// The mirror is a *model*, not a game to win: stones are drawn in ink-wash
// language (warm paper, ink stones, paper-white stones with an ink rim), and
// chains at one liberty pulse in seal-red — the visible signature of "两块棋
// 同时告急". All colors come from the ink palette; no scores anywhere.

import { emptyPosition, play, BLACK, WHITE, groupAt, key, parse, hashPosition, bestCaptureMove } from "./rules.js";

export const PALETTE = {
  paper: "#F5F1E6",
  paperDeep: "#EFE9DC",
  ink: "#26221D",
  inkSoft: "#5C554D",
  inkFaint: "#B7AEA1",
  blackStone: "#211D19",
  whiteStone: "#F1EDE3",
  sealRed: "#B03A2E",
  breath: "#7B736B",
};

export function positionFromSpec(boardSpec, beatName) {
  const pos = emptyPosition(boardSpec.size);
  for (const [r, c] of boardSpec.stones.black) {
    const res = play(pos, key(r, c), BLACK);
    if (!res.ok) throw new Error(`mirror: illegal setup stone ${r},${c} (${res.reason})`);
    pos.stones = res.pos.stones;
  }
  for (const [r, c] of boardSpec.stones.white) {
    const res = play(pos, key(r, c), WHITE);
    if (!res.ok) throw new Error(`mirror: illegal setup stone ${r},${c} (${res.reason})`);
    pos.stones = res.pos.stones;
  }
  const beat = boardSpec.beats[beatName];
  if (!beat) throw new Error(`mirror: unknown beat "${beatName}"`);
  const seq = [];
  for (const m of beat.moves ?? []) {
    // {engine: true} = the "算力手": the move is COMPUTED at runtime by the
    // tiny deterministic calculator — the case's theme lives in the mechanics
    if (m.engine) {
      const best = bestCaptureMove(pos, m.color === "black" ? BLACK : WHITE);
      if (!best) throw new Error(`mirror: beat "${beatName}" engine found no legal move`);
      seq.push({ color: m.color, at: best.at, computed: best });
    } else {
      seq.push(m);
    }
  }
  if (beat.reply) seq.push(beat.reply);
  for (const m of seq) {                // a beat may be setup-only (assertions, no moves)
    if (m.at === null) continue; // 虚着
    const res = play(pos, key(...m.at), m.color === "black" ? BLACK : WHITE);
    if (!res.ok) throw new Error(`mirror: beat "${beatName}" scripted move illegal (${res.reason})`);
    pos.stones = res.pos.stones;
    pos.koPoint = res.pos.koPoint;
  }
  return pos;
}

export function chainsAt(pos) {
  // [{color, stones, liberties, atari}] — one entry per chain
  const seen = new Set();
  const chains = [];
  for (const [k, v] of pos.stones) {
    if (seen.has(k)) continue;
    const g = groupAt(pos, k);
    for (const s of g.stones) seen.add(s);
    chains.push({
      color: v,
      stones: [...g.stones],
      liberties: g.liberties.size,
      libertyPoints: [...g.liberties],
      atari: g.liberties.size === 1,
    });
  }
  return chains;
}

export function drawBoard(canvas, pos, opts = {}) {
  const ctx = canvas.getContext("2d");
  const size = pos.size;
  const pad = canvas.width * 0.09;
  const cell = (canvas.width - pad * 2) / (size - 1);
  const px = (r, c) => [pad + (c - 1) * cell, pad + (r - 1) * cell];

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  // paper
  ctx.fillStyle = PALETTE.paper;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  // grid
  ctx.strokeStyle = PALETTE.inkFaint;
  ctx.lineWidth = 1;
  for (let i = 1; i <= size; i++) {
    const [x1, y1] = px(i, 1);
    const [x2, y2] = px(i, size);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    const [x3, y3] = px(1, i);
    const [x4, y4] = px(size, i);
    ctx.beginPath(); ctx.moveTo(x3, y3); ctx.lineTo(x4, y4); ctx.stroke();
  }

  const chains = chainsAt(pos);
  const atariChains = chains.filter((c) => c.atari);

  // highlight pulse (only when motion allowed): a breath ring around atari chains
  if (opts.highlightPulse && !opts.reducedMotion) {
    const t = opts.time ?? 0;
    const a = 0.35 + 0.25 * Math.sin(t / 500);
    for (const c of atariChains) {
      ctx.strokeStyle = PALETTE.sealRed;
      ctx.globalAlpha = a;
      ctx.lineWidth = 2;
      for (const s of c.stones) {
        const [x, y] = px(...parse(s));
        ctx.beginPath();
        ctx.arc(x, y, cell * 0.72, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
  }

  // stones with a slight ink-bleed edge (水墨语汇)
  const r = cell * 0.44;
  for (const [k, v] of pos.stones) {
    const [x, y] = px(...parse(k));
    ctx.beginPath();
    ctx.arc(x + 0.8, y + 1.1, r * 1.04, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(38,34,29,0.16)"; // bleed
    ctx.fill();
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    if (v === BLACK) {
      ctx.fillStyle = PALETTE.blackStone;
      ctx.fill();
    } else {
      ctx.fillStyle = PALETTE.whiteStone;
      ctx.fill();
      ctx.strokeStyle = PALETTE.inkSoft;
      ctx.lineWidth = 1.4;
      ctx.stroke();
    }
  }

  // liberty ticks: tiny breath marks on empty liberties of every chain
  if (opts.showLiberties) {
    ctx.strokeStyle = PALETTE.breath;
    ctx.lineWidth = 1.2;
    for (const c of chains) {
      for (const l of c.libertyPoints) {
        const [x, y] = px(...parse(l));
        ctx.beginPath();
        ctx.arc(x, y, cell * 0.09, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  }
  return { atariCount: atariChains.length, chainCount: chains.length };
}
