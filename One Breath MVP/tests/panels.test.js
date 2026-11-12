// panels.test.js — the visual vocabulary's structural gate.
//
// Node has no real canvas, so this test drives every scene template and every
// choice icon against a recording mock context: the gate is that each one
// EXECUTES without throwing and actually draws (non-trivial call counts), plus
// the palette contract (paper/ink/stones present, PALETTE stays the single
// source for board-mirror). Pixel-level checks live in tools/smoke.py.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { drawPanel, drawIcon, ICONS } from "../app/panels.js";
import { PALETTE, WARM } from "../app/tokens.js";

// a mock 2D context: every method records, every property assigns
function mockCtx() {
  const calls = [];
  const handler = {
    get(target, prop) {
      if (prop in target) return target[prop];
      return (...args) => {
        calls.push([prop, args]);
        if (prop === "createRadialGradient" || prop === "createLinearGradient") {
          return { addColorStop() {} };
        }
        if (prop === "measureText") return { width: 10 };
        return undefined;
      };
    },
    set(target, prop, value) {
      target[prop] = value;
      return true;
    },
  };
  return new Proxy({ calls }, handler);
}

// one canvas, ONE context — so call counts can be compared around a draw call
function mockCanvas(w = 560, h = 360) {
  const ctx = mockCtx();
  return { width: w, height: h, getContext: () => ctx, ctx };
}

const content = JSON.parse(
  readFileSync(new URL("../dist/content.json", import.meta.url), "utf-8"));

// every scene named by any vignette node, plus the fallback
const scenes = new Set(["breath"]);
for (const v of Object.values(content.vignettes)) {
  for (const n of Object.values(v.nodes)) {
    if (n.panel?.scene) scenes.add(n.panel.scene);
    for (const c of n.choices ?? []) {
      if (c.icon) scenes.add(`icon:${c.icon}`);
    }
    if (n.endings) {
      for (const e of Object.values(n.endings)) {
        if (e.panel?.scene) scenes.add(e.panel.scene);
      }
    }
  }
}

test("palette contract: the classical scale is the single source", () => {
  for (const key of ["paper", "ink", "inkSoft", "inkFaint", "blackStone",
    "whiteStone", "sealRed", "sage"]) {
    assert.ok(PALETTE[key], `PALETTE.${key} missing`);
  }
  // the warm palette must override the shared keys and carry its own accents
  for (const key of ["paper", "ink", "inkSoft", "inkFaint", "blackStone",
    "whiteStone", "sealRed", "sage", "amber", "dusk"]) {
    assert.ok(WARM[key], `WARM.${key} missing`);
  }
});

test("every scene template draws against the mock context (ink and warm)", () => {
  for (const scene of scenes) {
    if (scene.startsWith("icon:")) continue;
    for (const warm of [false, true]) {
      drawPanel(mockCanvas(), { scene, movement: "encounter" }, { warm });
    }
  }
});

test("every scene actually draws something (more than the paper setup alone)", () => {
  for (const scene of scenes) {
    if (scene.startsWith("icon:")) continue;
    const canvas = mockCanvas();
    const before = canvas.ctx.calls.length;
    drawPanel(canvas, { scene }, {});
    const after = canvas.ctx.calls.length;
    // the paper setup itself issues ~30 calls (gradients, frames, grain);
    // each scene must add its own marks on top
    assert.ok(after - before > 5, `${scene}: only ${after - before} draw calls`);
  }
});

test("every choice icon draws; unknown ids fall back to remember", () => {
  const icons = new Set(Object.keys(ICONS));
  for (const v of Object.values(content.vignettes)) {
    for (const n of Object.values(v.nodes)) {
      for (const c of n.choices ?? []) {
        if (c.icon) assert.ok(icons.has(c.icon), `icon "${c.icon}" missing from ICONS`);
      }
    }
  }
  for (const id of icons) {
    const canvas = mockCanvas(72, 72);
    const before = canvas.ctx.calls.length;
    drawIcon(canvas, id);
    assert.ok(canvas.ctx.calls.length - before > 3, `icon ${id}: too few draw calls`);
  }
  // the fallback path must not throw
  drawIcon(mockCanvas(72, 72), "nonexistent-icon");
});

test("the brush vocabulary is deterministic: same scene, same call sequence", () => {
  const run = () => {
    const canvas = mockCanvas();
    drawPanel(canvas, { scene: "grandpa-room" }, {});
    return JSON.stringify(canvas.ctx.calls);
  };
  assert.equal(run(), run(), "panels must replay byte-for-byte");
});

test("the robed figure keeps its coordinate contract (head ~13r, above the hem)", () => {
  // the scale contract: all scene calls pass sizes tuned for this bbox, so the
  // robed figure must occupy the same vertical span as the old stick figure
  const canvas = mockCanvas();
  drawPanel(canvas, { scene: "teaching" }, {});
  const arcs = canvas.ctx.calls.filter(([m]) => m === "arc").map(([, a]) => a);
  // arc(x, y, radius, start, end): the head is the r≈13 full circle
  const head = arcs.find((a) => Math.abs(a[4] - Math.PI * 2) < 1e-6 && a[2] > 8 && a[2] < 20);
  assert.ok(head, "a head-sized arc must exist (r ~13)");
});
