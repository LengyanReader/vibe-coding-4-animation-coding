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
  sage: "#8A9B8E",
};

export function positionFromSpec(boardSpec, beatName) {
  const beat = boardSpec.beats[beatName];
  if (!beat) throw new Error(`mirror: unknown beat "${beatName}"`);
  // a beat may carry its own setup (teaching positions do); the base stones
  // are the default for the two case boards.
  const setup = beat.setup ?? boardSpec.stones;
  const pos = emptyPosition(boardSpec.size);
  for (const [r, c] of setup.black) {
    const res = play(pos, key(r, c), BLACK);
    if (!res.ok) throw new Error(`mirror: illegal setup stone ${r},${c} (${res.reason})`);
    pos.stones = res.pos.stones;
  }
  for (const [r, c] of setup.white) {
    const res = play(pos, key(r, c), WHITE);
    if (!res.ok) throw new Error(`mirror: illegal setup stone ${r},${c} (${res.reason})`);
    pos.stones = res.pos.stones;
  }
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
  const W = canvas.width, H = canvas.height;
  const pad = W * 0.105;   // room for the edge stones' domes and shadows
  const cell = (W - pad * 2) / (size - 1);
  const px = (r, c) => [pad + (c - 1) * cell, pad + (r - 1) * cell];

  ctx.clearRect(0, 0, W, H);
  // the board is a wooden wash, not a flat fill: warm heart, cooler rim
  const paper = ctx.createRadialGradient(W * 0.5, H * 0.42, H * 0.12, W * 0.5, H * 0.5, Math.max(W, H) * 0.72);
  paper.addColorStop(0, "#FBF4E4");
  paper.addColorStop(1, "#EFE3C8");
  ctx.fillStyle = paper;
  ctx.fillRect(0, 0, W, H);
  // a fine double frame, like the board's own edge
  ctx.strokeStyle = "rgba(92,84,73,0.5)";
  ctx.lineWidth = Math.max(1, H * 0.004);
  ctx.strokeRect(W * 0.03, H * 0.03, W * 0.94, H * 0.94);
  // grid: hairline ink, slightly heavier on the outer lines (棋盘线)
  for (let i = 1; i <= size; i++) {
    const [x1, y1] = px(i, 1);
    const [x2, y2] = px(i, size);
    const [x3, y3] = px(1, i);
    const [x4, y4] = px(size, i);
    ctx.strokeStyle = (i === 1 || i === size) ? "rgba(62,56,49,0.55)" : "rgba(62,56,49,0.34)";
    ctx.lineWidth = (i === 1 || i === size) ? Math.max(1.1, cell * 0.05) : Math.max(0.7, cell * 0.032);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
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

  // stones: radial-gradient domes with a soft shadow — slate and clamshell,
  // not flat circles
  const r = cell * 0.44;
  for (const [k, v] of pos.stones) {
    const [x, y] = px(...parse(k));
    // the shadow beneath
    ctx.beginPath();
    ctx.ellipse(x + r * 0.18, y + r * 0.3, r * 1.02, r * 0.62, 0, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(58,50,38,0.2)";
    ctx.fill();
    const g = ctx.createRadialGradient(x - r * 0.38, y - r * 0.42, r * 0.12, x, y, r * 1.12);
    if (v === BLACK) {
      g.addColorStop(0, "#5D564C");
      g.addColorStop(0.5, PALETTE.blackStone);
      g.addColorStop(1, "#29251F");
    } else {
      g.addColorStop(0, "#FFFDF4");
      g.addColorStop(0.55, PALETTE.whiteStone);
      g.addColorStop(1, "#E2D8BE");
    }
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = g;
    ctx.fill();
    ctx.strokeStyle = v === BLACK ? "rgba(30,26,21,0.5)" : "rgba(118,108,88,0.55)";
    ctx.lineWidth = Math.max(0.8, r * 0.07);
    ctx.stroke();
  }

// liberty ticks: tiny breath marks on empty liberties of every chain
  if (opts.showLiberties) {
    ctx.strokeStyle = PALETTE.breath;
    ctx.lineWidth = 1.2;
    for (const c of chains) {
      for (const l of c.libertyPoints) {
        const [x, y] = px(...parse(l));
        ctx.beginPath(); ctx.arc(x, y, cell * 0.09, 0, Math.PI * 2); ctx.stroke();
      }
    }
  }

  // one chain's breath (teaching: only the chain being taught)
  if (opts.libertiesFor) {
    const c = chains.find((ch) => ch.stones.includes(opts.libertiesFor));
    if (c) {
      ctx.strokeStyle = PALETTE.sage ?? PALETTE.breath;
      ctx.lineWidth = 2;
      for (const l of c.libertyPoints) {
        const [x, y] = px(...parse(l));
        ctx.beginPath(); ctx.arc(x, y, cell * 0.13, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.strokeStyle = PALETTE.breath;
      ctx.lineWidth = 1.4;
      for (const s of c.stones) {
        const [x, y] = px(...parse(s));
        ctx.beginPath(); ctx.arc(x, y, cell * 0.56, 0, Math.PI * 2); ctx.stroke();
      }
    }
  }

  // markers: corridor (faint), refused (seal-red cross), last move (small dot)
  for (const m of opts.markers ?? []) {
    const [x, y] = px(...parse(m.at));
    if (m.kind === "corridor") {
      // a quiet breath mark, not a dashed UI ring
      ctx.strokeStyle = PALETTE.sage;
      ctx.globalAlpha = 0.55;
      ctx.lineWidth = 1.1;
      ctx.beginPath(); ctx.arc(x, y, cell * 0.17, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = PALETTE.sage;
      ctx.globalAlpha = 0.22;
      ctx.beginPath(); ctx.arc(x, y, cell * 0.06, 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = 1;
    } else if (m.kind === "refused") {
      ctx.strokeStyle = PALETTE.sealRed;
      ctx.lineWidth = 2.4;
      const d = cell * 0.18;
      ctx.beginPath();
      ctx.moveTo(x - d, y - d); ctx.lineTo(x + d, y + d);
      ctx.moveTo(x + d, y - d); ctx.lineTo(x - d, y + d);
      ctx.stroke();
    } else if (m.kind === "clicked") {
      ctx.strokeStyle = PALETTE.sage;
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(x, y, cell * 0.2, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = PALETTE.sage;
      ctx.beginPath(); ctx.arc(x, y, cell * 0.08, 0, Math.PI * 2); ctx.fill();
    } else if (m.kind === "last") {
      ctx.fillStyle = PALETTE.sealRed;
      ctx.beginPath(); ctx.arc(x, y, cell * 0.09, 0, Math.PI * 2); ctx.fill();
    } else if (m.kind === "hint") {
      // the guided game's gentle nudge: a soft ring on the point grandpa means
      ctx.strokeStyle = PALETTE.sage;
      ctx.globalAlpha = 0.8;
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(x, y, cell * 0.3, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 0.2;
      ctx.fillStyle = PALETTE.sage;
      ctx.beginPath(); ctx.arc(x, y, cell * 0.3, 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = 1;
    }
  }

  // ghosts: stones lifted earlier — dashed outlines (理事无碍's proof)
  for (const g of opts.ghostPoints ?? []) {
    const [x, y] = px(...parse(g));
    ctx.strokeStyle = PALETTE.sealRed;
    ctx.globalAlpha = 0.6;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
  }

  // role labels: a small vermilion chop beside the anchor stone
  for (const [role, anchor] of Object.entries(opts.roles ?? {})) {
    const [x, y] = px(...parse(anchor));
    const label = role === "you" ? "你" : "他";
    const s = cell * 0.44;
    const bx = x + cell * 0.46;
    const by = y - cell * 0.6;
    ctx.fillStyle = PALETTE.sealRed;
    ctx.fillRect(bx - s / 2, by - s / 2, s, s);
    ctx.fillStyle = PALETTE.paper;
    ctx.font = `${Math.max(11, cell * 0.32)}px "Noto Serif SC", serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, bx, by + 0.5);
  }

  return { atariCount: atariChains.length, chainCount: chains.length };
}

// nearest intersection for a pointer event; returns [r,c] or null
export function hitTest(canvas, clientX, clientY, size) {
  const rect = canvas.getBoundingClientRect();
  if (!rect.width || !rect.height) return null;
  const x = (clientX - rect.left) * (canvas.width / rect.width);
  const y = (clientY - rect.top) * (canvas.height / rect.height);
  const pad = canvas.width * 0.105;  // must match drawBoard's pad exactly
  const cell = (canvas.width - pad * 2) / (size - 1);
  const c = Math.round((x - pad) / cell) + 1;
  const r = Math.round((y - pad) / cell) + 1;
  if (r < 1 || r > size || c < 1 || c > size) return null;
  const sx = pad + (c - 1) * cell;
  const sy = pad + (r - 1) * cell;
  if (Math.hypot(x - sx, y - sy) > cell * 0.55) return null;
  return [r, c];
}

