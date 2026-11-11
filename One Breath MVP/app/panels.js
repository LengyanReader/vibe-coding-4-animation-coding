// panels.js — the wordless picture layer.
//
// The proposal's rule: the prototype stays wordless or minimally verbal
// (One_Breath_Mentor_MVP_Plan §3.1). This module draws every story beat as an
// ink-minimal pictogram panel on canvas — silhouettes, tables, speech bursts,
// documents — and every choice as a picture tile. No glyph carries the
// meaning; the picture does. All shapes are vector primitives so the panels
// are deterministic and zoom-clean.

import { PALETTE } from "./board-mirror.js";

// 清雅温馨 palette for the warm panels (case two): cream paper, soft brown
// ink, sage and amber accents — 治愈系 shape language instead of stark ink.
export const WARM = {
  paper: "#FBF6EA",
  ink: "#4A4038",
  inkSoft: "#7A6E60",
  inkFaint: "#D8CBB4",
  blackStone: "#3E3831",
  whiteStone: "#FDF9EF",
  sealRed: "#C2704E",
  sage: "#8A9B8E",
  amber: "#D9A86C",
  dusk: "#A8B8C8",
};

let C = { ...PALETTE };   // active palette, set per draw call (ink or warm)
let INK = C.ink, SOFT = C.inkSoft, FAINT = C.inkFaint, RED = C.sealRed;

function ctxSetup(canvas, warm = false) {
  C = warm ? { ...PALETTE, ...WARM } : PALETTE;
  INK = C.ink; SOFT = C.inkSoft; FAINT = C.inkFaint; RED = C.sealRed;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = C.paper;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  // faint paper grain: three horizontal wash strokes
  ctx.strokeStyle = warm ? "rgba(138,155,142,0.22)" : "rgba(183,174,161,0.25)";
  ctx.lineWidth = canvas.height * 0.012;
  for (const u of [0.2, 0.5, 0.8]) {
    ctx.beginPath();
    ctx.moveTo(canvas.width * 0.06, canvas.height * u);
    ctx.bezierCurveTo(canvas.width * 0.3, canvas.height * (u - 0.02),
                      canvas.width * 0.7, canvas.height * (u + 0.02),
                      canvas.width * 0.94, canvas.height * u);
    ctx.stroke();
  }
  return ctx;
}

// a person as an ink silhouette; pose changes the arms/torso lean
function figure(ctx, x, y, s, { pose = "stand", flip = false, tone = INK } = {}) {
  const f = (dx) => (flip ? -dx : dx);
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.fillStyle = tone;
  ctx.strokeStyle = tone;
  ctx.lineCap = "round";
  // head
  ctx.beginPath();
  ctx.arc(f(0), -78, 13, 0, Math.PI * 2);
  ctx.fill();
  // torso
  ctx.lineWidth = 16;
  ctx.beginPath();
  ctx.moveTo(f(0), -62);
  ctx.lineTo(f(0), -18);
  ctx.stroke();
  // legs
  ctx.lineWidth = 8;
  ctx.beginPath();
  ctx.moveTo(f(0), -18);
  ctx.lineTo(f(-9), 0);
  ctx.moveTo(f(0), -18);
  ctx.lineTo(f(9), 0);
  ctx.stroke();
  // arms by pose
  ctx.lineWidth = 7;
  const arm = (x1, y1, x2, y2) => {
    ctx.beginPath();
    ctx.moveTo(f(x1), y1);
    ctx.lineTo(f(x2), y2);
    ctx.stroke();
  };
  if (pose === "point") {          // accusing arm raised
    arm(0, -52, 34, -84);
    arm(0, -50, -12, -30);
  } else if (pose === "reach") {   // open reaching arm
    arm(0, -50, 26, -58);
    arm(0, -50, -22, -58);
  } else if (pose === "hold") {    // hands cupped, holding something
    arm(0, -48, 16, -34);
    arm(0, -48, -16, -34);
  } else if (pose === "stand") {
    arm(0, -52, 12, -28);
    arm(0, -52, -12, -28);
  } else if (pose === "sit") {     // seated: bent legs forward
    ctx.beginPath();
    ctx.moveTo(f(0), -18);
    ctx.lineTo(f(14), -14);
    ctx.lineTo(f(16), 0);
    ctx.stroke();
    arm(0, -52, 14, -34);
    arm(0, -52, -10, -34);
  }
  ctx.restore();
}

function table(ctx, x, y, w, h) {
  ctx.fillStyle = "rgba(38,34,29,0.07)";
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = SOFT;
  ctx.lineWidth = 2;
  ctx.strokeRect(x, y, w, h);
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
  ctx.strokeStyle = FAINT;
  ctx.lineWidth = 1;
  const lines = 5;
  for (let i = 0; i < lines; i++) {
    if (gap && i === 2) {
      // the unfinished section: a red hollow
      ctx.strokeStyle = RED;
      ctx.lineWidth = 2;
      ctx.strokeRect(x + w * 0.12, y + w * (0.18 + i * 0.16), w * 0.72, w * 0.1);
      ctx.strokeStyle = FAINT;
      ctx.lineWidth = 1;
      continue;
    }
    const yy = y + w * (0.2 + i * 0.16);
    ctx.beginPath();
    ctx.moveTo(x + w * 0.12, yy);
    ctx.lineTo(x + w * 0.84, yy);
    ctx.stroke();
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
    ctx.beginPath();
    ctx.arc(x + i * 34 * s, y, 9 * s, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(38,34,29,0.35)";
    ctx.fill();
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
  ctx.beginPath();
  ctx.arc(x + 52 * s, y + 4 * s, 9 * s, 0, Math.PI * 2);
  ctx.fillStyle = PALETTE.blackStone;
  ctx.fill();
}

// --- the four-movement marker (visual, not verbal): one of four brush dots ---
function movementMark(ctx, x, y, index, total = 4) {
  for (let i = 0; i < total; i++) {
    ctx.beginPath();
    if (i === index) {
      ctx.fillStyle = RED;
      ctx.arc(x + i * 22, y, 6, 0, Math.PI * 2);
      ctx.fill();
    } else {
      ctx.strokeStyle = FAINT;
      ctx.lineWidth = 1.5;
      ctx.arc(x + i * 22, y, 5, 0, Math.PI * 2);
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
      // warm lamp glow + two figures across a board
      ctx.fillStyle = "rgba(217,168,108,0.3)";
      ctx.beginPath(); ctx.arc(W * 0.5, H * 0.24, H * 0.16, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = C.amber; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(W * 0.5, H * 0.24, H * 0.05, 0, Math.PI * 2); ctx.stroke();
      ctx.strokeStyle = C.inkSoft; ctx.lineWidth = 1.5;
      ctx.strokeRect(W * 0.4, H * 0.52, W * 0.2, W * 0.2);
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
      ctx.strokeStyle = C.sage; ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.moveTo(W * 0.44, H * 0.44); ctx.lineTo(W * 0.5, H * 0.36);
      ctx.lineTo(W * 0.56, H * 0.42); ctx.lineTo(W * 0.64, H * 0.34); ctx.stroke();
      figure(ctx, W * 0.3, H * 0.74, H / 470, { pose: "sit" });
      break;
    }
    case "two-figures": {
      ctx.strokeStyle = C.inkSoft; ctx.lineWidth = 2;
      ctx.strokeRect(W * 0.42, H * 0.5, W * 0.16, W * 0.16);
      figure(ctx, W * 0.3, H * 0.82, H / 470, { pose: "sit" });
      figure(ctx, W * 0.7, H * 0.82, H / 470, { pose: "sit", flip: true });
      break;
    }
    case "teaching": {
      figure(ctx, W * 0.62, H * 0.78, H / 440, { pose: "hold" });
      figure(ctx, W * 0.34, H * 0.88, H / 560, { pose: "stand" });
      ctx.beginPath(); ctx.arc(W * 0.34, H * 0.7, H * 0.028, 0, Math.PI * 2);
      ctx.fillStyle = C.ink; ctx.fill();
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
      ctx.beginPath();
      ctx.arc(W * 0.5 + H * 0.05, H * 0.62, H * 0.022, 0, Math.PI * 2);
      ctx.fillStyle = PALETTE.blackStone;
      ctx.fill();
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
      // the board itself as the protagonist: an outlined frame and two hands
      ctx.strokeStyle = INK;
      ctx.lineWidth = 2;
      ctx.strokeRect(W * 0.3, H * 0.16, W * 0.4, W * 0.4);
      figure(ctx, W * 0.5, H * 0.86, H / 500, { pose: "reach" });
      break;
    }
    case "breath":
    default: {
      // fall back to a single breath circle
      ctx.strokeStyle = FAINT;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(W / 2, H / 2, H * 0.2, 0, Math.PI * 2);
      ctx.stroke();
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
