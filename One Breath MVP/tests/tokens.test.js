// tokens.test.js — the visual single-source gate (docs/art-bible.md §8).
//
// 1. BARE-HEX GATE: no hex literal may appear in any rendering module outside
//    app/tokens.js. A colour that lives in two places is a colour that drifts.
// 2. CSS SYNC: every hex in styles.css must exist in tokens.js — the UI chrome
//    and the canvases must be one palette, not two.
// 3. COLOR SCRIPT: the five-act paper progression is distinct and warms
//    monotonically toward 觉 (the Journey/Gris rule: colour = emotional arc).
// 4. DETERMINISM: the rendering modules stay free of Math.random.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { INK, PAPER, GOLD, SEAL, DAI, MOSS, AMBER, OCHRE, STONE, ACTS, PALETTE, WARM, DHARMA } from "../app/tokens.js";

const ROOT = new URL("..", import.meta.url);
const read = (p) => readFileSync(new URL(p, ROOT), "utf-8");
// strip line comments so prose that MENTIONS colours/random never trips a gate
const code = (p) => read(p).replace(/\/\/.*$/gm, "");

const RENDER_MODULES = ["app/panels.js", "app/board-mirror.js", "app/dharmadhatu.js"];

test("bare-hex gate: rendering modules carry no colour literals outside tokens.js", () => {
  for (const mod of RENDER_MODULES) {
    const bare = [...code(mod).matchAll(/"#[0-9A-Fa-f]{3,8}"/g)].map((m) => m[0]);
    assert.deepEqual(bare, [],
      `${mod}: bare hex literals must live in app/tokens.js (found ${bare.join(", ")})`);
  }
});

test("css sync: every hex in styles.css is a token value", () => {
  const tokenHexes = new Set(
    [...read("app/tokens.js").matchAll(/#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b/g)].map((m) => m[0].toUpperCase()));
  const cssHexes = [...read("app/styles.css").matchAll(/#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b/g)].map((m) => m[0]);
  const strays = cssHexes.filter((h) => !tokenHexes.has(h.toUpperCase()));
  assert.deepEqual(strays, [],
    `styles.css colours must come from app/tokens.js (strays: ${strays.join(", ")})`);
});

test("color script: five acts, distinct papers, warming monotonically toward 觉", () => {
  assert.equal(ACTS.length, 5);
  const ids = ACTS.map((a) => a.id);
  assert.deepEqual(ids, ["meet", "air", "game", "mirror", "lucid"]);
  const papers = ACTS.map((a) => a.paper);
  assert.equal(new Set(papers).size, 5, "each act has its own paper");
  const lum = (hex) => {
    const n = parseInt(hex.slice(1), 16);
    // warmth = red channel dominance over blue (the arc must warm, not brighten)
    return ((n >> 16) & 255) - ((n & 255) * 0.5);
  };
  for (let i = 1; i < papers.length; i++) {
    assert.ok(lum(papers[i]) >= lum(papers[i - 1]),
      `act ${ACTS[i].id} paper must be at least as warm as ${ACTS[i - 1].id}`);
  }
  assert.equal(ACTS[4].accent, GOLD, "the lucid act's accent is 觉光金 — and gold appears nowhere earlier");
  for (const a of ACTS.slice(0, 4)) {
    assert.notEqual(a.accent, GOLD, `act ${a.id} must not spend gold before 觉`);
  }
});

test("the token surfaces are complete and cross-referenced", () => {
  for (const key of ["jiao", "nong", "zhong", "dan", "qing"]) {
    assert.ok(INK[key], `INK.${key} (墨五阶)`);
  }
  for (const key of ["mist", "plain", "lamp", "warm", "lucid", "deep"]) {
    assert.ok(PAPER[key], `PAPER.${key} (五幕纸色)`);
  }
  for (const key of ["black", "blackHi", "blackLo", "white", "whiteHi", "whiteLo",
    "bleedDark", "bleedLight", "shadow"]) {
    assert.ok(STONE[key], `STONE.${key} (哑光墨面)`);
  }
  // the board's public PALETTE is token-fed, not a second palette
  assert.equal(PALETTE.ink, INK.nong);
  assert.equal(PALETTE.sealRed, SEAL);
  assert.equal(PALETTE.sage, MOSS);
  // case variants stay distinct from the base
  assert.notEqual(WARM.paper, PALETTE.paper);
  assert.ok(DHARMA.gold === GOLD, "the fourth view's gold is THE 觉光金");
  assert.ok(DAI && MOSS && AMBER && OCHRE, "accent set complete");
});

test("determinism: the rendering modules never call Math.random", () => {
  for (const mod of RENDER_MODULES) {
    assert.equal(/\bMath\.random\b/.test(code(mod)), false,
      `${mod}: atmosphere must be coordinate-seeded, never random`);
  }
});
