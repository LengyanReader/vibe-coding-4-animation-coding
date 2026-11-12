// panels.js — the wordless picture layer.
//
// The proposal's rule: the prototype stays wordless or minimally verbal
// (One_Breath_Mentor_MVP_Plan §3.1). This module draws every story beat as an
// ink-minimal pictogram panel on canvas — silhouettes, tables, speech bursts,
// documents — and every choice as a picture tile. No glyph carries the
// meaning; the picture does. All shapes are vector primitives so the panels
// are deterministic and zoom-clean.

import { PALETTE } from "./board-mirror.js";
import { WARM as WARM_TOKENS, INK as INK_TONES, PAPER as PAPER_T, STONE as STONE_T, AMBER as AMBER_T } from "./tokens.js";

// 清雅温馨 palette for the warm panels (case two): cream paper, soft brown
// ink, sage and amber accents — 治愈系 shape language instead of stark ink.
export const WARM = WARM_TOKENS;

let C = { ...PALETTE };   // active palette, set per draw call (ink or warm)
let INK = C.ink, SOFT = C.inkSoft, FAINT = C.inkFaint, RED = C.sealRed;

// 五级墨色: 焦浓重淡清 — the classical ink scale every primitive draws from.
const INK_SCALE = INK_TONES;

function ctxSetup(canvas, warm = false) {
  C = warm ? { ...PALETTE, ...WARM } : PALETTE;
  INK = C.ink; SOFT = C.inkSoft; FAINT = C.inkFaint; RED = C.sealRed;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  // the paper itself is a wash: warm at the heart, cooler at the edges —
  // not a flat fill. Deterministic, so the build stays reproducible.
  const g = ctx.createRadialGradient(W * 0.5, H * 0.42, H * 0.1, W * 0.5, H * 0.5, Math.max(W, H) * 0.75);
  g.addColorStop(0, C.paper);
  g.addColorStop(1, warm ? PAPER_T.warmRim : PAPER_T.deep);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  // 册页 border: a fine double frame with a heavier outer stroke
  ctx.strokeStyle = INK_SCALE.dan;
  ctx.lineWidth = Math.max(1.2, H * 0.004);
  ctx.strokeRect(W * 0.028, H * 0.032, W * 0.944, H * 0.936);
  ctx.strokeStyle = INK_SCALE.qing;
  ctx.lineWidth = Math.max(0.8, H * 0.002);
  ctx.strokeRect(W * 0.04, H * 0.044, W * 0.92, H * 0.912);
  // paper grain: three horizontal wash strokes + deterministic fibre flecks
  ctx.strokeStyle = warm ? "rgba(138,155,142,0.18)" : "rgba(183,174,161,0.2)";
  ctx.lineWidth = H * 0.012;
  for (const u of [0.24, 0.52, 0.78]) {
    ctx.beginPath();
    ctx.moveTo(W * 0.07, H * u);
    ctx.bezierCurveTo(W * 0.3, H * (u - 0.02), W * 0.7, H * (u + 0.02), W * 0.93, H * u);
    ctx.stroke();
  }
  ctx.fillStyle = warm ? "rgba(122,110,96,0.1)" : "rgba(90,83,72,0.12)";
  for (let i = 0; i < 26; i++) {
    // deterministic pseudo-scatter (no Math.random — the panels must replay)
    const t = (i * 137.508) % 360;
    const rr = (i * 83) % 97;
    const fx = W * (0.08 + ((t / 360) * 0.84));
    const fy = H * (0.1 + ((rr / 97) * 0.8));
    ctx.fillRect(fx, fy, 1.6, 1.6);
  }
  return ctx;
}

// --- the brush vocabulary -------------------------------------------------------
// Every line in a classical panel is a brush stroke: variable width, a slight
// tremble, a tapered tail. The tremble is deterministic (index-based phase),
// because the panels must replay byte-for-byte.

function brushPath(ctx, pts, w, tone) {
  // pts: [[x,y],...] polyline; w: base width; draws a tapered ink ribbon
  if (pts.length < 2) return;
  const left = [], right = [];
  for (let i = 0; i < pts.length; i++) {
    const [x, y] = pts[i];
    // width profile: full in the middle, taper at both ends (a loaded brush)
    const t = i / (pts.length - 1);
    const taper = Math.min(1, Math.min(t, 1 - t) * 4 + 0.25);
    // tremble: slow sine wiggle, phase locked to the segment index
    const tr = 1 + 0.14 * Math.sin(i * 2.1) * (i % 2 ? 1 : -1);
    const half = (w / 2) * taper * tr;
    // local normal
    const [nx, ny] = i === 0
      ? [pts[1][1] - y, -(pts[1][0] - x)]
      : i === pts.length - 1
        ? [y - pts[i - 1][1], -(x - pts[i - 1][0])]
        : [pts[i + 1][1] - pts[i - 1][1], -(pts[i + 1][0] - pts[i - 1][0])];
    const len = Math.hypot(nx, ny) || 1;
    left.push([x + (nx / len) * half, y + (ny / len) * half]);
    right.push([x - (nx / len) * half, y - (ny / len) * half]);
  }
  ctx.fillStyle = tone;
  ctx.beginPath();
  ctx.moveTo(left[0][0], left[0][1]);
  for (let i = 1; i < left.length; i++) {
    const [px, py] = left[i - 1], [cx, cy] = left[i];
    ctx.quadraticCurveTo(px, py, (px + cx) / 2, (py + cy) / 2);
  }
  ctx.lineTo(left[left.length - 1][0], left[left.length - 1][1]);
  for (let i = right.length - 1; i >= 0; i--) {
    const [cx, cy] = right[i];
    const [px, py] = right[i + 1] ?? right[i];
    ctx.quadraticCurveTo(px, py, (px + cx) / 2, (py + cy) / 2);
  }
  ctx.closePath();
  ctx.fill();
}

function brushLine(ctx, x1, y1, x2, y2, w = 3, tone = INK) {
  // subdivide so the tremble has room to breathe
  const n = Math.max(4, Math.round(Math.hypot(x2 - x1, y2 - y1) / 14));
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    pts.push([x1 + (x2 - x1) * t, y1 + (y2 - y1) * t]);
  }
  brushPath(ctx, pts, w, tone);
}

function brushArc(ctx, x, y, r, w = 3, tone = INK, a0 = 0, a1 = Math.PI * 2) {
  const n = 14;
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const a = a0 + (a1 - a0) * (i / n);
    pts.push([x + Math.cos(a) * r, y + Math.sin(a) * r]);
  }
  brushPath(ctx, pts, w, tone);
}

function inkWash(ctx, x, y, r, tone, alpha = 0.5) {
  // a dropped-ink bloom: dense heart, dissolving rim
  const g = ctx.createRadialGradient(x, y, r * 0.1, x, y, r);
  const col = tone ?? INK;
  g.addColorStop(0, hexA(col, alpha));
  g.addColorStop(0.7, hexA(col, alpha * 0.45));
  g.addColorStop(1, hexA(col, 0));
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fill();
}

function hexA(hex, a) {
  // "#RRGGBB" -> "rgba(r,g,b,a)"
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function eave(ctx, x, y, w, h, tone = INK) {
  // 飞檐: a roof line whose two tips sweep upward — the signature of a
  // classical building, drawn in one tapering stroke
  const pts = [];
  const n = 16;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    // the centre sags a touch, the tips lift
    const lift = Math.pow(Math.abs(t - 0.5) * 2, 2.2) * h * 2.2 - h * 0.12;
    pts.push([x + w * t, y + h * 0.5 - lift]);
  }
  brushPath(ctx, pts, Math.max(2.4, h * 0.24), tone);
  // the two ridge tips
  brushLine(ctx, x + w * 0.02, y + h * 0.34, x + w * 0.02, y - h * 0.5, Math.max(1.6, h * 0.14), tone);
  brushLine(ctx, x + w * 0.98, y + h * 0.34, x + w * 0.98, y - h * 0.5, Math.max(1.6, h * 0.14), tone);
}

function bamboo(ctx, x, baseY, h, tone = SOFT) {
  // 竹: stalk with joints, leaning leaves — the quietest classical accent
  const w = Math.max(2.6, h * 0.045);
  const nodes = Math.max(2, Math.round(h / (h * 0.3)));
  for (let seg = 0; seg < nodes; seg++) {
    const y1 = baseY - (h * seg) / nodes;
    const y2 = baseY - (h * (seg + 1)) / nodes;
    const lean = (seg % 2 ? 1 : -1) * h * 0.02;
    brushLine(ctx, x + lean, y1, x - lean, y2, w, tone);
    // the node ring
    ctx.strokeStyle = tone;
    ctx.lineWidth = w * 0.5;
    ctx.beginPath();
    ctx.moveTo(x - lean - w * 0.7, y2);
    ctx.lineTo(x - lean + w * 0.7, y2);
    ctx.stroke();
  }
  // leaves: three lanceolate sweeps near the top
  const top = baseY - h;
  for (const [dx, dy, len] of [[-1, -0.2, 0.28], [1, 0.05, 0.24], [-0.6, 0.12, 0.2]]) {
    const lx = x + dx * h * 0.06, ly = top + dy * h;
    const tx = lx + dx * h * len, ty = ly + (dy + 0.18) * h * len;
    brushPath(ctx, [[lx, ly], [(lx + tx) / 2 + dx * 4, (ly + ty) / 2], [tx, ty]], w * 0.85, tone);
  }
}

function panelStone(ctx, x, y, r, which = "black") {
  // a Go stone with its soft shadow — gradient, rim light, the works
  ctx.fillStyle = "rgba(60,52,40,0.18)";
  ctx.beginPath();
  ctx.ellipse(x + r * 0.15, y + r * 0.28, r * 1.05, r * 0.6, 0, 0, Math.PI * 2);
  ctx.fill();
  const base = which === "black" ? C.blackStone : C.whiteStone;
  const g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.15, x, y, r * 1.15);
  if (which === "black") {
    g.addColorStop(0, STONE_T.blackHi);
    g.addColorStop(0.55, base);
    g.addColorStop(1, STONE_T.blackLo);
  } else {
    g.addColorStop(0, STONE_T.whiteHi);
    g.addColorStop(0.6, base);
    g.addColorStop(1, STONE_T.whiteLo);
  }
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = which === "black" ? "rgba(34,29,23,0.55)" : "rgba(120,110,90,0.5)";
  ctx.lineWidth = Math.max(0.8, r * 0.08);
  ctx.stroke();
}

function sealChar(ctx, x, y, s, text = "一息") {
  // a vermilion seal: the classical signature. Deterministic, text from the
  // app's own identity — never a random decorative glyph.
  ctx.fillStyle = RED;
  ctx.fillRect(x - s * 0.5, y - s * 0.5, s, s);
  ctx.fillStyle = C.paper;
  ctx.font = `${Math.max(8, s * 0.62)}px "Noto Serif SC", serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text.slice(0, 2), x, y + s * 0.04);
}

// a person as a robed ink silhouette; pose changes the sleeves and the lean.
// Coordinate contract preserved from the old stick figure: feet at y=0,
// head centre at y=-78, so every existing scene call keeps its scale.
function figure(ctx, x, y, s, { pose = "stand", flip = false, tone = INK } = {}) {
  const f = (dx) => (flip ? -dx : dx);
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.fillStyle = tone;
  ctx.strokeStyle = tone;
  ctx.lineCap = "round";

  // head + 髻 (hair bun with its pin)
  ctx.beginPath();
  ctx.arc(f(0), -78, 13, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(f(3), -92, 5.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(f(9), -94);
  ctx.lineTo(f(15), -89);
  ctx.stroke();

  // the robe: one tapering body from shoulders to hem — the silhouette of
  // someone at rest, not a diagram of joints
  ctx.beginPath();
  ctx.moveTo(f(-9), -62);            // left shoulder
  ctx.quadraticCurveTo(f(-15), -40, f(-13), -2);   // robe falls wide
  ctx.quadraticCurveTo(f(0), 3, f(13), -2);        // hem
  ctx.quadraticCurveTo(f(15), -40, f(9), -62);     // right shoulder
  ctx.closePath();
  ctx.fill();
  // collar: a paper-coloured V, so the robe reads as clothing
  ctx.strokeStyle = C.paper;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(f(-4), -60);
  ctx.lineTo(f(0), -48);
  ctx.lineTo(f(4), -60);
  ctx.stroke();

  // sleeves by pose: each arm is one wide brush-like sweep
  const sleeve = (x1, y1, x2, y2, w) => {
    ctx.strokeStyle = tone;
    ctx.lineWidth = w;
    ctx.beginPath();
    ctx.moveTo(f(x1), y1);
    ctx.quadraticCurveTo(f((x1 + x2) / 2), Math.min(y1, y2) - 4, f(x2), y2);
    ctx.stroke();
  };
  if (pose === "point") {          // accusing arm raised
    sleeve(6, -54, 32, -82, 9);
    sleeve(-6, -52, -12, -30, 8);
  } else if (pose === "reach") {   // open reaching arm
    sleeve(6, -52, 26, -58, 9);
    sleeve(-6, -52, -22, -58, 9);
  } else if (pose === "hold") {    // hands cupped, holding something
    sleeve(6, -50, 16, -34, 10);
    sleeve(-6, -50, -16, -34, 10);
  } else if (pose === "sit") {     // seated: robe pools over folded legs
    ctx.beginPath();
    ctx.moveTo(f(-13), -14);
    ctx.quadraticCurveTo(f(0), -4, f(15), -14);
    ctx.quadraticCurveTo(f(16), -2, f(4), 1);
    ctx.lineTo(f(-10), 1);
    ctx.quadraticCurveTo(f(-16), -4, f(-13), -14);
    ctx.closePath();
    ctx.fill();
    sleeve(6, -50, 14, -34, 10);
    sleeve(-6, -50, -10, -34, 10);
  } else {                          // stand
    sleeve(6, -54, 12, -28, 9);
    sleeve(-6, -54, -12, -28, 9);
    // two feet beneath the hem
    ctx.beginPath();
    ctx.ellipse(f(-6), 0, 5, 2.4, 0, 0, Math.PI * 2);
    ctx.ellipse(f(6), 0, 5, 2.4, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function table(ctx, x, y, w, h) {
  ctx.fillStyle = "rgba(38,34,29,0.06)";
  ctx.fillRect(x, y, w, h);
  brushLine(ctx, x, y, x + w, y, 2.6, SOFT);
  brushLine(ctx, x, y + h, x + w, y + h, 2.2, SOFT);
  brushLine(ctx, x, y, x, y + h, 2.2, SOFT);
  brushLine(ctx, x + w, y, x + w, y + h, 2.6, SOFT);
}

function burst(ctx, x, y, r, tone = INK) {
  // jagged speech-burst: the shape of words said too loud
  ctx.strokeStyle = tone;
  ctx.fillStyle = "rgba(176,58,46,0.08)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  const n = 12;
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * Math.PI * 2;
    const rr = r * (1 + 0.22 * (i % 2));
    const px = x + Math.cos(a) * rr;
    const py = y + Math.sin(a) * rr * 0.72;
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
}

function doc(ctx, x, y, w, { gap = false } = {}) {
  ctx.fillStyle = PALETTE.whiteStone;
  ctx.strokeStyle = SOFT;
  ctx.lineWidth = 1.6;
  ctx.fillRect(x, y, w, w * 1.35);
  ctx.strokeRect(x, y, w, w * 1.35);
  const lines = 5;
  for (let i = 0; i < lines; i++) {
    if (gap && i === 2) {
      // the unfinished section: a red hollow
      ctx.strokeStyle = RED;
      ctx.lineWidth = 2;
      ctx.strokeRect(x + w * 0.12, y + w * (0.18 + i * 0.16), w * 0.72, w * 0.1);
      continue;
    }
    const yy = y + w * (0.2 + i * 0.16);
    brushLine(ctx, x + w * 0.12, yy, x + w * 0.84, yy, 1.6, FAINT);
  }
}

function foldedPage(ctx, x, y, s) {
  doc(ctx, x, y, s);
  // the folded corner + a weight arrow above it
  ctx.strokeStyle = SOFT;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x + s, y);
  ctx.lineTo(x + s * 0.78, y + s * 0.2);
  ctx.lineTo(x + s, y + s * 0.2);
  ctx.closePath();
  ctx.stroke();
  ctx.strokeStyle = RED;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(x + s * 0.5, y - s * 0.55);
  ctx.lineTo(x + s * 0.5, y - s * 0.1);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x + s * 0.4, y - s * 0.28);
  ctx.lineTo(x + s * 0.5, y - s * 0.08);
  ctx.lineTo(x + s * 0.6, y - s * 0.28);
  ctx.stroke();
}

function boundaryLine(ctx, x, y, w) {
  ctx.strokeStyle = RED;
  ctx.lineWidth = 3;
  ctx.setLineDash([w * 0.12, w * 0.08]);
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + w, y);
  ctx.stroke();
  ctx.setLineDash([]);
}

function watchers(ctx, x, y, n, s) {
  for (let i = 0; i < n; i++) {
    // distant colleagues as faint ink silhouettes, not dots
    ctx.beginPath();
    ctx.arc(x + i * 34 * s, y - 9 * s, 7 * s, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(38,34,29,0.3)";
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(x + i * 34 * s - 8 * s, y + 9 * s);
    ctx.quadraticCurveTo(x + i * 34 * s, y - 4 * s, x + i * 34 * s + 8 * s, y + 9 * s);
    ctx.closePath();
    ctx.fill();
  }
}

function shopfront(ctx, x, y, w, h, { glow = false } = {}) {
  ctx.fillStyle = "rgba(38,34,29,0.05)";
  ctx.fillRect(x, y, w, h);
  brushLine(ctx, x, y, x + w, y, 2.6, INK);
  brushLine(ctx, x, y, x, y + h, 2.4, INK);
  brushLine(ctx, x + w, y, x + w, y + h, 2.4, INK);
  ctx.strokeStyle = SOFT;
  ctx.lineWidth = 1.5;
  ctx.strokeRect(x + w * 0.14, y + h * 0.2, w * 0.72, h * 0.46);
  // the awning above the shop window: a small eave
  eave(ctx, x + w * 0.18, y - h * 0.14, w * 0.64, h * 0.07, SOFT);
  if (glow) {
    inkWash(ctx, x + w * 0.5, y + h * 0.43, w * 0.3, AMBER_T, 0.4);
  }
}

function openHandWithStone(ctx, x, y, s) {
  // 放下: an open palm, and the stone resting BESIDE it — not in it
  ctx.strokeStyle = INK;
  ctx.lineWidth = 4;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(x - 26 * s, y);
  ctx.quadraticCurveTo(x, y - 12 * s, x + 26 * s, y);
  ctx.stroke();
  for (let i = -2; i <= 2; i++) {
    ctx.beginPath();
    ctx.moveTo(x + i * 12 * s, y - 2 * s);
    ctx.lineTo(x + i * 13 * s, y - 12 * s);
    ctx.stroke();
  }
  panelStone(ctx, x + 52 * s, y + 4 * s, 9 * s, "black");
}

// --- the four-movement marker (visual, not verbal): one of four brush dots ---
function movementMark(ctx, x, y, index, total = 4) {
  for (let i = 0; i < total; i++) {
    const px = x + i * 22;
    if (i === index) {
      inkWash(ctx, px, y, 8, RED, 0.28);
      ctx.fillStyle = RED;
      ctx.beginPath();
      ctx.arc(px, y, 5.5, 0, Math.PI * 2);
      ctx.fill();
    } else {
      ctx.strokeStyle = FAINT;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(px, y, 5, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

const MOVEMENT_INDEX = { encounter: 0, interrelate: 1, release: 2, respond: 3, ending: 3 };

// --- scene templates ----------------------------------------------------------

export function drawPanel(canvas, panel, { time = 0, reducedMotion = false, warm = false } = {}) {
  const ctx = ctxSetup(canvas, warm);
  const W = canvas.width, H = canvas.height;
  const idx = MOVEMENT_INDEX[panel.movement] ?? 0;
  movementMark(ctx, W * 0.42, H * 0.07, idx);

  switch (panel.scene) {
    case "night-desk": {
      // 夜战 AI: a figure at a desk, the screen glowing cold, ten tally strokes
      ctx.fillStyle = C.ink;
      ctx.fillRect(W * 0.46, H * 0.32, W * 0.3, H * 0.24);           // the screen
      ctx.globalAlpha = 0.5;
      ctx.fillStyle = C.dusk;
      ctx.fillRect(W * 0.475, H * 0.34, W * 0.27, H * 0.2);          // the glow
      ctx.globalAlpha = 1;
      figure(ctx, W * 0.34, H * 0.74, H / 470, { pose: "sit" });
      ctx.strokeStyle = C.inkSoft;
      ctx.lineWidth = 3; ctx.lineCap = "round";
      for (let i = 0; i < 10; i++) {                                 // ten losses
        ctx.beginPath();
        ctx.moveTo(W * 0.08 + i * W * 0.026, H * 0.1);
        ctx.lineTo(W * 0.08 + i * W * 0.026, H * 0.18);
        ctx.stroke();
      }
      break;
    }
    case "machine-move": {
      // the three lifted stones: hollow circles rising in cold light
      for (const [u, v] of [[0.42, 0.38], [0.5, 0.28], [0.58, 0.4]]) {
        ctx.strokeStyle = C.dusk;
        ctx.lineWidth = 3;
        ctx.beginPath(); ctx.arc(W * u, H * v, H * 0.055, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.strokeStyle = C.inkSoft; ctx.lineWidth = 2;
      ctx.strokeRect(W * 0.3, H * 0.6, W * 0.4, H * 0.18);           // the scoreboard
      ctx.strokeStyle = C.sealRed; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(W * 0.34, H * 0.7); ctx.lineTo(W * 0.4, H * 0.7); ctx.stroke();
      break;
    }
    case "dark-screen": {
      ctx.fillStyle = C.ink;
      ctx.fillRect(W * 0.25, H * 0.2, W * 0.5, H * 0.4);
      ctx.strokeStyle = C.inkFaint; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(W * 0.5, H * 0.4, H * 0.07, 0, Math.PI * 2); ctx.stroke();
      ctx.strokeStyle = C.amber; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(W * 0.85, H * 0.14, H * 0.05, 0, Math.PI * 2); ctx.stroke();
      figure(ctx, W * 0.5, H * 0.88, H / 480, { pose: "stand" });
      break;
    }
    case "thin-chain": {
      for (const [u, v] of [[0.36, 0.42], [0.5, 0.42]]) {
        ctx.strokeStyle = C.ink; ctx.lineWidth = 4;
        ctx.beginPath(); ctx.arc(W * u, H * v, H * 0.06, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.strokeStyle = C.sealRed; ctx.lineWidth = 2.5;
      ctx.setLineDash([6, 6]);
      ctx.beginPath(); ctx.arc(W * 0.64, H * 0.42, H * 0.06, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      figure(ctx, W * 0.5, H * 0.86, H / 490, { pose: "hold" });
      break;
    }
    case "machine-side": {
      ctx.strokeStyle = C.dusk; ctx.lineWidth = 2;
      for (let i = 0; i < 4; i++) {
        ctx.strokeRect(W * (0.28 + i * 0.1), H * 0.28, W * 0.08, H * 0.08);
      }
      ctx.strokeStyle = C.inkFaint;
      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        ctx.moveTo(W * (0.32 + i * 0.1), H * 0.4);
        ctx.lineTo(W * (0.32 + i * 0.1), H * 0.62);
        ctx.stroke();
      }
      figure(ctx, W * 0.5, H * 0.86, H / 490, { pose: "stand" });
      break;
    }
    case "grandpa-room": {
      // warm lamp glow + two figures across a board, under an eave, by bamboo
      inkWash(ctx, W * 0.5, H * 0.24, H * 0.2, AMBER_T, 0.35);
      ctx.strokeStyle = C.amber; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(W * 0.5, H * 0.24, H * 0.05, 0, Math.PI * 2); ctx.stroke();
      eave(ctx, W * 0.16, H * 0.12, W * 0.68, H * 0.05, SOFT);
      bamboo(ctx, W * 0.9, H * 0.88, H * 0.6, C.sage);
      // the board between them: a fine grid, two stones
      ctx.strokeStyle = INK_SCALE.dan; ctx.lineWidth = 1.1;
      for (let i = 0; i <= 3; i++) {
        const u = W * (0.41 + i * 0.06);
        const v = H * 0.52 + i * (W * 0.06);
        ctx.beginPath(); ctx.moveTo(u, H * 0.52); ctx.lineTo(u, H * 0.7); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(W * 0.41, v); ctx.lineTo(W * 0.59, v); ctx.stroke();
      }
      panelStone(ctx, W * 0.47, H * 0.58, W * 0.014, "black");
      panelStone(ctx, W * 0.53, H * 0.64, W * 0.014, "white");
      figure(ctx, W * 0.3, H * 0.84, H / 480, { pose: "sit" });
      figure(ctx, W * 0.7, H * 0.84, H / 480, { pose: "sit", flip: true });
      break;
    }
    case "third-road": {
      // new joseki dots rising like mushrooms after rain
      for (const [u, v] of [[0.3, 0.62], [0.42, 0.5], [0.56, 0.56], [0.68, 0.4], [0.78, 0.5]]) {
        ctx.strokeStyle = C.sage; ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.arc(W * u, H * v, H * 0.032, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.strokeStyle = C.dusk; ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(W * 0.18, H * 0.78);
      ctx.bezierCurveTo(W * 0.4, H * 0.6, W * 0.6, H * 0.7, W * 0.84, H * 0.34);
      ctx.stroke();
      break;
    }
    case "study-night": {
      ctx.fillStyle = C.ink;
      ctx.fillRect(W * 0.42, H * 0.26, W * 0.28, H * 0.2);
      ctx.globalAlpha = 0.5;
      ctx.fillStyle = C.dusk;
      ctx.fillRect(W * 0.435, H * 0.275, W * 0.25, H * 0.17);
      ctx.globalAlpha = 1;
      ctx.strokeStyle = C.sage; ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.moveTo(W * 0.44, H * 0.44); ctx.lineTo(W * 0.5, H * 0.36);
      ctx.lineTo(W * 0.56, H * 0.42); ctx.lineTo(W * 0.64, H * 0.34); ctx.stroke();
      figure(ctx, W * 0.3, H * 0.74, H / 470, { pose: "sit" });
      break;
    }
    case "two-figures": {
      bamboo(ctx, W * 0.88, H * 0.9, H * 0.55, C.sage);
      ctx.strokeStyle = INK_SCALE.dan; ctx.lineWidth = 1.1;
      for (let i = 0; i <= 3; i++) {
        const u = W * (0.43 + i * 0.047);
        const v = H * 0.5 + i * (W * 0.047);
        ctx.beginPath(); ctx.moveTo(u, H * 0.5); ctx.lineTo(u, H * 0.64); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(W * 0.43, v); ctx.lineTo(W * 0.57, v); ctx.stroke();
      }
      panelStone(ctx, W * 0.475, H * 0.547, W * 0.011, "black");
      panelStone(ctx, W * 0.522, H * 0.547, W * 0.011, "white");
      figure(ctx, W * 0.3, H * 0.82, H / 470, { pose: "sit" });
      figure(ctx, W * 0.7, H * 0.82, H / 470, { pose: "sit", flip: true });
      break;
    }
    case "teaching": {
      inkWash(ctx, W * 0.62, H * 0.4, H * 0.24, C.sage, 0.16);
      bamboo(ctx, W * 0.12, H * 0.9, H * 0.62, C.sage);
      figure(ctx, W * 0.62, H * 0.78, H / 440, { pose: "hold" });
      figure(ctx, W * 0.34, H * 0.88, H / 560, { pose: "stand" });
      panelStone(ctx, W * 0.34, H * 0.7, H * 0.028, "black");
      break;
    }
    case "on-the-shelf": {
      ctx.strokeStyle = C.inkSoft; ctx.lineWidth = 2.5;
      ctx.strokeRect(W * 0.24, H * 0.36, W * 0.52, H * 0.1);
      ctx.strokeRect(W * 0.3, H * 0.24, W * 0.4, H * 0.12);            // the board on its side
      figure(ctx, W * 0.5, H * 0.86, H / 500, { pose: "stand" });
      break;
    }
    case "leaning-in": {
      ctx.fillStyle = C.ink;
      ctx.fillRect(W * 0.5, H * 0.26, W * 0.26, H * 0.2);
      ctx.globalAlpha = 0.4; ctx.fillStyle = C.dusk;
      ctx.fillRect(W * 0.51, H * 0.275, W * 0.24, H * 0.17);
      ctx.globalAlpha = 1;
      figure(ctx, W * 0.34, H * 0.68, H / 460, { pose: "reach" });
      break;
    }
    case "meeting-criticism": {
      table(ctx, W * 0.08, H * 0.62, W * 0.84, H * 0.1);
      figure(ctx, W * 0.62, H * 0.55, H / 460, { pose: "point", flip: true });
      figure(ctx, W * 0.30, H * 0.55, H / 480, { pose: "sit" });
      watchers(ctx, W * 0.42, H * 0.52, 3, H / 500);
      burst(ctx, W * 0.62, H * 0.24, H * 0.13, RED);
      // the mind-frame, drawn as a split bar: 我对你错, picture not words
      ctx.strokeStyle = INK;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(W * 0.44, H * 0.26);
      ctx.lineTo(W * 0.56, H * 0.26);
      ctx.stroke();
      ctx.fillStyle = INK;
      ctx.beginPath();
      ctx.arc(W * 0.44, H * 0.26, 4, 0, Math.PI * 2);
      ctx.fill();
      break;
    }
    case "meeting-still": {
      table(ctx, W * 0.08, H * 0.62, W * 0.84, H * 0.1);
      figure(ctx, W * 0.62, H * 0.55, H / 460, { pose: "stand", tone: "rgba(38,34,29,0.55)" });
      figure(ctx, W * 0.30, H * 0.55, H / 480, { pose: "sit" });
      watchers(ctx, W * 0.42, H * 0.52, 3, H / 500);
      break;
    }
    case "three-things": {
      // three unexplored directions: three faint circles waiting to be opened
      for (const [u, v] of [[0.3, 0.45], [0.5, 0.38], [0.7, 0.45]]) {
        ctx.strokeStyle = FAINT;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(W * u, H * v, H * 0.09, 0, Math.PI * 2);
        ctx.stroke();
      }
      figure(ctx, W * 0.5, H * 0.86, H / 500, { pose: "stand" });
      break;
    }
    case "his-pressure": {
      foldedPage(ctx, W * 0.4, H * 0.3, W * 0.16);
      figure(ctx, W * 0.62, H * 0.86, H / 470, { pose: "hold" });
      break;
    }
    case "my-flaw": {
      doc(ctx, W * 0.4, H * 0.24, W * 0.16, { gap: true });
      figure(ctx, W * 0.5, H * 0.88, H / 480, { pose: "hold" });
      break;
    }
    case "crossed-line": {
      burst(ctx, W * 0.5, H * 0.3, H * 0.13, RED);
      boundaryLine(ctx, W * 0.2, H * 0.56, W * 0.6);
      figure(ctx, W * 0.5, H * 0.88, H / 490, { pose: "stand" });
      break;
    }
    case "put-down": {
      openHandWithStone(ctx, W * 0.42, H * 0.42, H / 420);
      figure(ctx, W * 0.5, H * 0.9, H / 500, { pose: "stand" });
      break;
    }
    case "still-holding": {
      // the stone still gripped in the fist
      figure(ctx, W * 0.5, H * 0.9, H / 500, { pose: "hold" });
      panelStone(ctx, W * 0.5 + H * 0.05, H * 0.62, H * 0.024, "black");
      break;
    }
    case "meeting-return": {
      table(ctx, W * 0.08, H * 0.62, W * 0.84, H * 0.1);
      figure(ctx, W * 0.30, H * 0.55, H / 480, { pose: "stand" });
      figure(ctx, W * 0.62, H * 0.55, H / 460, { pose: "stand", tone: "rgba(38,34,29,0.55)" });
      break;
    }
    case "corridor": {
      // two figures walking apart then together — the offline talk
      figure(ctx, W * 0.36, H * 0.8, H / 470, { pose: "stand", flip: true });
      figure(ctx, W * 0.6, H * 0.8, H / 470, { pose: "stand" });
      boundaryLine(ctx, W * 0.3, H * 0.3, W * 0.4);
      break;
    }
    case "mirror-hub": {
      // the board itself as the protagonist: a framed board under an eave
      eave(ctx, W * 0.28, H * 0.14, W * 0.44, H * 0.045, SOFT);
      ctx.strokeStyle = INK;
      ctx.lineWidth = 2;
      ctx.strokeRect(W * 0.3, H * 0.2, W * 0.4, W * 0.4);
      ctx.strokeStyle = INK_SCALE.dan; ctx.lineWidth = 0.9;
      for (let i = 1; i < 4; i++) {
        const u = W * (0.3 + i * 0.1);
        const v = H * 0.2 + i * (W * 0.1);
        ctx.beginPath(); ctx.moveTo(u, H * 0.2); ctx.lineTo(u, H * 0.2 + W * 0.4); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(W * 0.3, v); ctx.lineTo(W * 0.7, v); ctx.stroke();
      }
      panelStone(ctx, W * 0.44, H * 0.28, W * 0.02, "black");
      panelStone(ctx, W * 0.56, H * 0.44, W * 0.02, "white");
      figure(ctx, W * 0.5, H * 0.86, H / 500, { pose: "reach" });
      break;
    }
    case "corridor-narrow": {
      // two shopfronts, one corridor; boxes on your side, a shelf on his
      shopfront(ctx, W * 0.03, H * 0.28, W * 0.3, H * 0.58);
      shopfront(ctx, W * 0.67, H * 0.28, W * 0.3, H * 0.58);
      ctx.strokeStyle = FAINT;
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(W * 0.33, H * 0.86); ctx.lineTo(W * 0.33, H * 0.28); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(W * 0.67, H * 0.86); ctx.lineTo(W * 0.67, H * 0.28); ctx.stroke();
      // boxes
      ctx.fillStyle = "rgba(38,34,29,0.2)";
      ctx.fillRect(W * 0.36, H * 0.66, W * 0.12, H * 0.14);
      ctx.fillRect(W * 0.37, H * 0.55, W * 0.1, H * 0.1);
      // shelf
      ctx.strokeStyle = INK;
      ctx.lineWidth = 2.5;
      ctx.strokeRect(W * 0.58, H * 0.5, W * 0.05, H * 0.3);
      ctx.beginPath();
      for (let i = 0; i < 3; i++) {
        const yy = H * (0.58 + i * 0.08);
        ctx.moveTo(W * 0.58, yy); ctx.lineTo(W * 0.63, yy);
      }
      ctx.stroke();
      figure(ctx, W * 0.52, H * 0.34, H / 620, { pose: "stand", tone: "rgba(38,34,29,0.5)" });
      break;
    }
    case "corridor-clear": {
      shopfront(ctx, W * 0.03, H * 0.28, W * 0.3, H * 0.58);
      shopfront(ctx, W * 0.67, H * 0.28, W * 0.3, H * 0.58);
      ctx.strokeStyle = FAINT;
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(W * 0.33, H * 0.86); ctx.lineTo(W * 0.33, H * 0.28); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(W * 0.67, H * 0.86); ctx.lineTo(W * 0.67, H * 0.28); ctx.stroke();
      figure(ctx, W * 0.4, H * 0.84, H / 480, { pose: "stand" });
      figure(ctx, W * 0.6, H * 0.84, H / 480, { pose: "stand", flip: true });
      break;
    }
    case "corridor-dawn": {
      shopfront(ctx, W * 0.03, H * 0.28, W * 0.3, H * 0.58, { glow: true });
      shopfront(ctx, W * 0.67, H * 0.28, W * 0.3, H * 0.58, { glow: true });
      // dawn: a rising amber sun with its wash, between the two roofs
      inkWash(ctx, W * 0.5, H * 0.2, H * 0.16, AMBER_T, 0.4);
      brushArc(ctx, W * 0.5, H * 0.2, H * 0.05, 2.2, C.amber ?? C.sealRed);
      figure(ctx, W * 0.42, H * 0.86, H / 500, { pose: "stand" });
      figure(ctx, W * 0.58, H * 0.86, H / 500, { pose: "stand", flip: true });
      break;
    }
    case "breath":
    default: {
      // fall back to a single breath circle — now a brush ring over its wash
      inkWash(ctx, W / 2, H / 2, H * 0.24, C.sage, 0.2);
      brushArc(ctx, W / 2, H / 2, H * 0.2, 3.2, FAINT);
    }
  }
}

// --- choice tiles ---------------------------------------------------------------

export const ICONS = {
  lid: (ctx, s) => {
    // closing the lid: a laptop closing, the screen line folding down
    ctx.strokeStyle = INK; ctx.lineWidth = 3.5;
    ctx.beginPath(); ctx.moveTo(-s * 0.3, -s * 0.18); ctx.lineTo(s * 0.3, -s * 0.18);
    ctx.lineTo(s * 0.3, s * 0.12); ctx.lineTo(-s * 0.3, s * 0.12); ctx.closePath(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-s * 0.34, s * 0.28); ctx.lineTo(s * 0.34, s * 0.28); ctx.stroke();
  },
  machine_eye: (ctx, s) => {
    // the machine's side: a cold grid with one calculated point
    ctx.strokeStyle = C.dusk; ctx.lineWidth = 2;
    for (let i = -1; i <= 1; i++) {
      ctx.beginPath(); ctx.moveTo(i * s * 0.2, -s * 0.28); ctx.lineTo(i * s * 0.2, s * 0.28); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-s * 0.28, i * s * 0.2); ctx.lineTo(s * 0.28, i * s * 0.2); ctx.stroke();
    }
    ctx.beginPath(); ctx.arc(0, 0, s * 0.09, 0, Math.PI * 2);
    ctx.fillStyle = C.dusk; ctx.fill();
  },
  grandpa_lamp: (ctx, s) => {
    // grandpa's side: a warm lamp glow over a board
    ctx.fillStyle = "rgba(217,168,108,0.35)";
    ctx.beginPath(); ctx.arc(0, -s * 0.05, s * 0.3, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = C.amber; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(0, -s * 0.05, s * 0.12, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = INK; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(-s * 0.26, s * 0.3); ctx.lineTo(s * 0.26, s * 0.3); ctx.stroke();
  },
  third_road: (ctx, s) => {
    // a third road: a curve rising past two fixed points
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(-s * 0.34, s * 0.26);
    ctx.bezierCurveTo(-s * 0.1, -s * 0.1, s * 0.1, -s * 0.34, s * 0.36, -s * 0.3);
    ctx.stroke();
    for (const [u, v] of [[-0.2, 0.14], [0.16, 0.06]]) {
      ctx.beginPath(); ctx.arc(u * s, v * s, s * 0.06, 0, Math.PI * 2); ctx.stroke();
    }
  },
  study: (ctx, s) => {
    // studying with the engine: a screen with an opening shape on it
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    ctx.strokeRect(-s * 0.3, -s * 0.26, s * 0.6, s * 0.46);
    ctx.strokeStyle = C.dusk; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(-s * 0.18, s * 0.06); ctx.lineTo(-s * 0.04, -s * 0.12);
    ctx.lineTo(s * 0.1, -s * 0.02); ctx.lineTo(s * 0.24, -s * 0.18); ctx.stroke();
  },
  human: (ctx, s) => {
    // only play people: two figures across a small board
    figure(ctx, -s * 0.26, s * 0.3, s / 150, { pose: "sit" });
    figure(ctx, s * 0.26, s * 0.3, s / 150, { pose: "sit", flip: true });
    ctx.strokeStyle = INK; ctx.lineWidth = 2;
    ctx.strokeRect(-s * 0.1, s * 0.08, s * 0.2, s * 0.14);
  },
  teach: (ctx, s) => {
    // teaching a child: a large hand and a small hand, one stone between
    ctx.strokeStyle = INK; ctx.lineWidth = 3.5;
    ctx.beginPath(); ctx.arc(-s * 0.14, s * 0.05, s * 0.14, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(s * 0.2, s * 0.14, s * 0.09, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(s * 0.02, -s * 0.06, s * 0.05, 0, Math.PI * 2);
    ctx.fillStyle = PALETTE.blackStone; ctx.fill();
  },
  shelve: (ctx, s) => {
    // the board on the shelf, waiting
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(-s * 0.34, -s * 0.14); ctx.lineTo(s * 0.34, -s * 0.14); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-s * 0.34, s * 0.3); ctx.lineTo(s * 0.34, s * 0.3); ctx.stroke();
    ctx.strokeRect(-s * 0.18, -s * 0.02, s * 0.36, s * 0.14);
  },
  curiosity: (ctx, s) => {
    // keep playing the machine, to see how it thinks: a figure leaning at the glow
    ctx.fillStyle = C.dusk; ctx.globalAlpha = 0.5;
    ctx.fillRect(s * 0.06, -s * 0.34, s * 0.3, s * 0.3);
    ctx.globalAlpha = 1;
    figure(ctx, -s * 0.14, s * 0.32, s / 140, { pose: "reach" });
  },
  reply_now: (ctx, s) => {
    // a SOLID seal-red jagged burst — must never read as remember's thin circle
    const n = 12;
    ctx.beginPath();
    for (let i = 0; i <= n; i++) {
      const a = (i / n) * Math.PI * 2;
      const rr = s * 0.34 * (1 + 0.24 * (i % 2));
      const px = Math.cos(a) * rr;
      const py = Math.sin(a) * rr * 0.8;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = RED;
    ctx.fill();
  },
  remember: (ctx, s) => {
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(0, 0, s * 0.32, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, 0, s * 0.06, 0, Math.PI * 2);
    ctx.fillStyle = INK; ctx.fill();
  },
  eye_his: (ctx, s) => {
    figure(ctx, 0, s * 0.34, s / 130, { pose: "hold" });
    ctx.strokeStyle = RED; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(0, -s * 0.4); ctx.lineTo(0, -s * 0.05); ctx.stroke();
  },
  eye_mine: (ctx, s) => doc(ctx, -s * 0.16, -s * 0.42, s * 0.32, { gap: true }),
  eye_line: (ctx, s) => {
    burst(ctx, 0, -s * 0.18, s * 0.2, RED);
    boundaryLine(ctx, -s * 0.34, s * 0.2, s * 0.68);
  },
  seen_all: (ctx, s) => {
    for (const u of [-0.3, 0, 0.3]) {
      ctx.strokeStyle = INK; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(u * s, 0, s * 0.1, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.strokeStyle = FAINT; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(-s * 0.2, 0); ctx.lineTo(s * 0.2, 0); ctx.stroke();
  },
  put_down: (ctx, s) => openHandWithStone(ctx, 0, 0, s / 110),
  not_yet: (ctx, s) => {
    figure(ctx, 0, s * 0.36, s / 130, { pose: "hold" });
    ctx.beginPath();
    ctx.arc(s * 0.06, -s * 0.1, s * 0.05, 0, Math.PI * 2);
    ctx.fillStyle = PALETTE.blackStone; ctx.fill();
  },
  try_attack: (ctx, s) => {
    // a stone placed ON a liberty mark
    ctx.strokeStyle = RED; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(0, s * 0.1, s * 0.3, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, s * 0.06, s * 0.14, 0, Math.PI * 2);
    ctx.fillStyle = PALETTE.blackStone; ctx.fill();
  },
  solidify: (ctx, s) => {
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    for (const [dx, dy] of [[-0.18, 0.08], [0, 0.08], [0.18, 0.08]]) {
      ctx.beginPath(); ctx.arc(dx * s, dy * s, s * 0.11, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.beginPath(); ctx.moveTo(-s * 0.3, s * 0.3); ctx.lineTo(s * 0.3, s * 0.3); ctx.stroke();
  },
  pass: (ctx, s) => {
    ctx.strokeStyle = FAINT; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(0, 0, s * 0.3, 0, Math.PI * 2); ctx.stroke();
  },
  back_room: (ctx, s) => {
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(-s * 0.26, -s * 0.24); ctx.lineTo(-s * 0.26, s * 0.3);
    ctx.lineTo(s * 0.26, s * 0.3); ctx.lineTo(s * 0.26, -s * 0.24); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-s * 0.34, -s * 0.24); ctx.lineTo(0, -s * 0.42);
    ctx.lineTo(s * 0.34, -s * 0.24); ctx.stroke();
  },
  ack: (ctx, s) => {
    // the gap, and the mend: a broken stroke completed in seal red
    doc(ctx, -s * 0.16, -s * 0.44, s * 0.32, { gap: true });
    ctx.strokeStyle = INK; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(s * 0.3, s * 0.26, s * 0.16, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(s * 0.22, s * 0.26); ctx.lineTo(s * 0.38, s * 0.26); ctx.stroke();
  },
  evidence: (ctx, s) => {
    ctx.strokeStyle = INK; ctx.lineWidth = 3.5;
    ctx.beginPath(); ctx.arc(-s * 0.06, -s * 0.08, s * 0.24, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(s * 0.12, s * 0.16); ctx.lineTo(s * 0.36, s * 0.4); ctx.stroke();
  },
  boundary: (ctx, s) => {
    boundaryLine(ctx, -s * 0.36, 0, s * 0.72);
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(0, -s * 0.02, s * 0.12, 0, Math.PI * 2);
    ctx.fillStyle = PALETTE.blackStone; ctx.fill();
  },
  disagree: (ctx, s) => {
    ctx.strokeStyle = INK; ctx.lineWidth = 3.5;
    ctx.beginPath(); ctx.moveTo(-s * 0.36, 0); ctx.lineTo(s * 0.36, 0); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-s * 0.12, -s * 0.14); ctx.lineTo(-s * 0.36, 0);
    ctx.lineTo(-s * 0.12, s * 0.14); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(s * 0.12, -s * 0.14); ctx.lineTo(s * 0.36, 0);
    ctx.lineTo(s * 0.12, s * 0.14); ctx.stroke();
  },
  pause: (ctx, s) => {
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(0, 0, s * 0.3, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-s * 0.08, -s * 0.14); ctx.lineTo(-s * 0.08, s * 0.14);
    ctx.moveTo(s * 0.08, -s * 0.14); ctx.lineTo(s * 0.08, s * 0.14); ctx.stroke();
  },
  sit_view: (ctx, s) => {
    // 坐观: a figure sitting before a board, breath circle above
    figure(ctx, 0, s * 0.36, s / 130, { pose: "sit" });
    ctx.strokeStyle = C.sage; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(0, -s * 0.28, s * 0.18, 0, Math.PI * 2); ctx.stroke();
  },
  replay: (ctx, s) => {
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(0, 0, s * 0.28, -0.6, Math.PI * 1.5); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(s * 0.1, -s * 0.38); ctx.lineTo(s * 0.3, -s * 0.24);
    ctx.lineTo(s * 0.06, -s * 0.14); ctx.stroke();
  },
};

export function drawIcon(canvas, iconId) {
  const ctx = ctxSetup(canvas);
  const s = Math.min(canvas.width, canvas.height);
  ctx.save();
  ctx.translate(canvas.width / 2, canvas.height / 2);
  (ICONS[iconId] ?? ICONS.remember)(ctx, s);
  ctx.restore();
}
