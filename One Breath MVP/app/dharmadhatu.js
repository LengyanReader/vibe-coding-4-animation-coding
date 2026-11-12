// dharmadhatu.js — the "坐观" act: four widening views of the final position,
// staged after the Huayan four-dharmadhatu contemplation (事 → 理 → 理事无碍 →
// 事事无碍). This is a DESIGN INTERPRETATION of the ladder — a viewing order,
// not a doctrinal claim (the proposal's rule: label interpretations as
// hypotheses, keep sources distinct).
//
// The views are computed from the real final position + the initial position:
//   观一 事     stones as stones: each with its place; nothing dissolves.
//   观二 理     stones fade; the breath network remains — every chain's
//               liberties drawn as one connected web of the same ink.
//   观三 理事   stones return AND the lifted stones appear as ghost outlines:
//               the capture is still in the position. Each chain draws its
//               liberties — principle visible inside the phenomena.
//   观四 事事   Indra's net: a line from every stone to every other stone,
//               and each stone carries a tiny reflected board (recursive
//               miniature) — one stone contains the whole game.
//
// Everything is pure rendering of (finalPos, initialPos, viewIndex): no
// randomness, so the contemplation is as reproducible as the game.

import { PALETTE } from "./board-mirror.js";
import { DHARMA as DHARMA_T, WARM as WARM_T, STONE as STONE_T, PAPER as PAPER_T } from "./tokens.js";
import { key, parse, groupAt } from "./rules.js";

const DHARMA = { ...WARM_T, ...DHARMA_T };  // warm reading; tokens override where defined

// square canvas: the contemplation canvas is drawn square (S x S)
function pt(r, c, size, pad, cell) {
  return [pad + (c - 1) * cell, pad + (r - 1) * cell];
}

function grid(ctx, size, S, C) {
  const pad = S * 0.09;
  const cell = (S - pad * 2) / (size - 1);
  for (let i = 1; i <= size; i++) {
    const [x1, y1] = pt(i, 1, size, pad, cell);
    const [x2, y2] = pt(i, size, size, pad, cell);
    const [x3, y3] = pt(1, i, size, pad, cell);
    const [x4, y4] = pt(size, i, size, pad, cell);
    ctx.strokeStyle = (i === 1 || i === size) ? "rgba(62,56,49,0.5)" : "rgba(62,56,49,0.3)";
    ctx.lineWidth = (i === 1 || i === size) ? Math.max(1, cell * 0.045) : Math.max(0.7, cell * 0.03);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x3, y3); ctx.lineTo(x4, y4); ctx.stroke();
  }
  return { pad, cell };
}

function stoneAt(ctx, x, y, r, color, C, alpha = 1) {
  ctx.globalAlpha = alpha;
  // the shadow beneath
  ctx.beginPath();
  ctx.ellipse(x + r * 0.16, y + r * 0.3, r * 1.02, r * 0.6, 0, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(58,50,38,0.18)";
  ctx.fill();
  // the dome: radial gradient — slate heart for black, shell sheen for white
  const g = ctx.createRadialGradient(x - r * 0.36, y - r * 0.4, r * 0.14, x, y, r * 1.1);
  if (color === 1) {
    g.addColorStop(0, STONE_T.blackHi);
    g.addColorStop(0.55, C.stone);
    g.addColorStop(1, STONE_T.blackLo);
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = g; ctx.fill();
  } else {
    g.addColorStop(0, STONE_T.whiteHi);
    g.addColorStop(0.55, C.whiteStone);
    g.addColorStop(1, STONE_T.whiteLo);
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = g; ctx.fill();
    ctx.strokeStyle = C.inkSoft; ctx.lineWidth = 1.2; ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

export function drawDharmadhatuView(canvas, viewIndex, finalPos, initialPos,
                                    { time = 0, reducedMotion = false } = {}) {
  const C = DHARMA;
  const ctx = canvas.getContext("2d");
  const S = canvas.width;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const paper = ctx.createRadialGradient(S * 0.5, S * 0.42, S * 0.12, S * 0.5, S * 0.5, S * 0.72);
  paper.addColorStop(0, C.paper);
  paper.addColorStop(1, PAPER_T.deep);
  ctx.fillStyle = paper;
  ctx.fillRect(0, 0, S, canvas.height);

  const size = finalPos.size;
  const pad = S * 0.09;
  const cell = (S - pad * 2) / (size - 1);
  grid(ctx, size, S, C);
  const r = cell * 0.44;

  // ghosts: stones present at the start but lifted by the game — 理事无碍's proof
  const ghosts = [];
  for (const [k, v] of initialPos.stones) {
    if (!finalPos.stones.has(k)) ghosts.push({ k, color: v });
  }

  const chains = [];
  const seen = new Set();
  for (const [k, v] of finalPos.stones) {
    if (seen.has(k)) continue;
    const g = groupAt(finalPos, k);
    for (const s of g.stones) seen.add(s);
    chains.push({ color: v, stones: [...g.stones], libs: [...g.liberties] });
  }

  const breathe = reducedMotion ? 0 : Math.sin(time / 900) * 0.5 + 0.5;

  if (viewIndex === 0) {
    // 观一 事: the position as it stands — stones full, honest, distinct
    for (const [k, v] of finalPos.stones) {
      const [rr, cc] = parse(k);
      const [x, y] = pt(rr, cc, size, pad, cell);
      stoneAt(ctx, x, y, r, v, C);
    }
  }

  if (viewIndex === 1) {
    // 观二 理: stones fade to ghosts of themselves; the breath web remains
    for (const [k, v] of finalPos.stones) {
      const [rr, cc] = parse(k);
      const [x, y] = pt(rr, cc, size, pad, cell);
      stoneAt(ctx, x, y, r, v, C, 0.18);
    }
    ctx.strokeStyle = C.sage;
    ctx.lineWidth = 1.6;
    ctx.globalAlpha = 0.55 + 0.2 * breathe;
    for (const ch of chains) {
      for (const lib of ch.libs) {
        const [lr, lc] = parse(lib);
        const [sx, sy] = pt(lr, lc, size, pad, cell);
        // each liberty of the chain links back to every stone of the chain
        for (const s of ch.stones) {
          const [sr, sc] = parse(s);
          const [tx, ty] = pt(sr, sc, size, pad, cell);
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.quadraticCurveTo((sx + tx) / 2 + 6, (sy + ty) / 2 - 6, tx, ty);
          ctx.stroke();
        }
      }
    }
    ctx.globalAlpha = 1;
  }

  if (viewIndex === 2) {
    // 观三 理事无碍: stones full + the lifted ones as ghost outlines — the
    // capture is still in the position; principle and phenomena hold together
    for (const g of ghosts) {
      const [rr, cc] = parse(g.k);
      const [x, y] = pt(rr, cc, size, pad, cell);
      ctx.globalAlpha = 0.5;
      ctx.strokeStyle = C.sealRed;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }
    for (const [k, v] of finalPos.stones) {
      const [rr, cc] = parse(k);
      const [x, y] = pt(rr, cc, size, pad, cell);
      stoneAt(ctx, x, y, r, v, C);
    }
    // each chain shows its own liberties — the whole visible in the part
    ctx.strokeStyle = C.sage;
    ctx.lineWidth = 1.4;
    ctx.globalAlpha = 0.6;
    for (const ch of chains) {
      for (const lib of ch.libs) {
        const [lr, lc] = parse(lib);
        const [x, y] = pt(lr, lc, size, pad, cell);
        ctx.beginPath(); ctx.arc(x, y, 3.2, 0, Math.PI * 2); ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  if (viewIndex === 3) {
    // 观四 事事无碍: Indra's net — every stone to every stone, and inside each
    // stone a tiny reflected board (one contains the whole)
    ctx.strokeStyle = C.amber;
    ctx.lineWidth = 0.8;
    ctx.globalAlpha = 0.35 + 0.25 * breathe;
    const all = [...finalPos.stones.keys()].map(parse);
    for (let i = 0; i < all.length; i++) {
      for (let j = i + 1; j < all.length; j++) {
        const [x1, y1] = pt(all[i][0], all[i][1], size, pad, cell);
        const [x2, y2] = pt(all[j][0], all[j][1], size, pad, cell);
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
    // ghosts still in the net (they are part of what reflects)
    for (const g of ghosts) {
      const [rr, cc] = parse(g.k);
      const [x, y] = pt(rr, cc, size, pad, cell);
      ctx.strokeStyle = C.inkFaint;
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
    }
    // stones, each carrying a miniature of the whole position
    const mini = Math.max(6, cell * 0.34);
    for (const [k, v] of finalPos.stones) {
      const [rr, cc] = parse(k);
      const [x, y] = pt(rr, cc, size, pad, cell);
      stoneAt(ctx, x, y, r, v, C);
      // tiny reflected board inside the stone
      ctx.save();
      ctx.translate(x, y);
      ctx.scale(mini / S, mini / S);
      ctx.globalAlpha = 0.85;
      ctx.strokeStyle = v === 1 ? C.whiteStone : C.inkSoft;
      ctx.lineWidth = 1.2 / (mini / S) * (mini / S); // keep 1.2px in stone space
      ctx.lineWidth = 1.2;
      const m = mini * 0.62;
      ctx.strokeRect(-m / 2, -m / 2, m, m);
      ctx.beginPath(); ctx.moveTo(-m / 2, 0); ctx.lineTo(m / 2, 0); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, -m / 2); ctx.lineTo(0, m / 2); ctx.stroke();
      ctx.beginPath();
      ctx.arc(-m / 4, -m / 4, m * 0.09, 0, Math.PI * 2);
      ctx.fillStyle = v === 1 ? C.whiteStone : C.stone;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(m / 4, m / 4, m * 0.09, 0, Math.PI * 2);
      ctx.fillStyle = v === 1 ? C.stone : C.whiteStone;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.restore();
    }
  }

}

// ghost stones of a given game: initial whites/blacks absent from the final
export function computeGhosts(initialPos, finalPos) {
  const out = [];
  for (const [k, v] of initialPos.stones) {
    if (!finalPos.stones.has(k)) out.push({ at: k, color: v });
  }
  return out;
}

export const VIEW_COUNT = 4;
