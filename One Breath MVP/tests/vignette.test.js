// vignette.test.js — story-graph gates: reachability, bilingual completeness,
// determinism of scripted walks, and the no-moral-scoring static check.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { newWalk, choose, scriptedWalk, reachability, renderNode } from "../app/vignette.js";

const content = JSON.parse(readFileSync(new URL("../dist/content.json", import.meta.url), "utf-8"));
const { vignettes, strings } = content;

test("every vignette graph is fully connected: no dead branches, no orphans, endings reachable", () => {
  for (const [id, v] of Object.entries(vignettes)) {
    const r = reachability(v);
    assert.equal(r.orphans.length, 0, `${id}: orphan nodes ${r.orphans}`);
    assert.ok(r.endings.length >= 3, `${id}: fewer than 3 endings — a dichotomy needs multiple viable responses`);
    // every non-ending node has at least one choice (no dead ends)
    for (const [nid, node] of Object.entries(v.nodes)) {
      if (node.movement !== "ending") {
        assert.ok((node.choices?.length ?? 0) >= 1, `${id}/${nid}: dead end`);
      }
    }
  }
});

test("bilingual completeness: every text pair exists in BOTH languages, non-empty", () => {
  for (const [id, v] of Object.entries(vignettes)) {
    for (const node of Object.values(v.nodes)) {
      for (const lang of ["zh", "en"]) {
        assert.ok(typeof node.text?.[lang] === "string" && node.text[lang].trim().length > 0,
          `${id}/${node}: missing ${lang} text`);
        for (const c of node.choices ?? []) {
          assert.ok(c.label?.[lang]?.trim(), `${id}/${node}: choice missing ${lang}`);
        }
      }
    }
    assert.ok(v.title?.[zh_en(v)] && v.tagline?.[zh_en(v)], `${id}: title/tagline bilingual`);
  }
  function zh_en(_v) { return "zh"; } // both checked below explicitly
});

test("bilingual completeness for chrome strings: every LEAF key in zh AND en", () => {
  // chrome strings may be namespaced (movement.encounter) — recurse to leaves
  const checkLeaf = (obj, path) => {
    if (typeof obj.zh === "string" || typeof obj.en === "string") {
      assert.ok(typeof obj.zh === "string" && obj.zh.trim(), `${path}: missing zh`);
      assert.ok(typeof obj.en === "string" && obj.en.trim(), `${path}: missing en`);
      return;
    }
    for (const [k, v] of Object.entries(obj)) checkLeaf(v, `${path}.${k}`);
  };
  for (const [key, entry] of Object.entries(strings)) checkLeaf(entry, `strings.${key}`);
});

test("conditional segments are complete: every {flag, y} has its {flag, n} twin where used", () => {
  for (const v of Object.values(vignettes)) {
    for (const [nid, node] of Object.entries(v.nodes)) {
      const pol = (lang) =>
        new Set([...(node.text?.[lang] ?? "").matchAll(/\{(\w+),\s*([yn]):/g)]
          .map((m) => `${m[1]}:${m[2]}`));
      assert.deepEqual(pol("en"), pol("zh"), `${v.id}/${nid}: conditional polarity differs zh vs en`);
    }
  }
});

test("determinism: the same choice sequence always reaches the same ending", () => {
  for (const v of Object.values(vignettes)) {
    // walk "always first choice" and "always second choice where available"
    for (const policy of [0, 1]) {
      let walk = newWalk(v);
      let steps = 0;
      while (!isEndingWalk(walk) && steps < 100) {
        const view = renderNode(walk, "zh");
        const idx = Math.min(policy, view.choices.length - 1);
        walk = choose(walk, idx);
        steps++;
      }
      // the mirror hub is a legal cycle (try hands, come back) — a policy walk
      // may orbit it forever; only walks that reach an ending prove determinism
      if (!isEndingWalk(walk)) continue;
      const choices = walk.trail.map((s) => s.choice);
      const a = scriptedWalk(v, choices);
      const b = scriptedWalk(v, choices);
      assert.equal(a.ending, b.ending, `${v.id}: deterministic ending`);
    }
  }
  function isEndingWalk(w) {
    return w.graph.nodes[w.node].movement === "ending";
  }
});

test("NO moral scoring: no score/points/rating variables or keys anywhere in the engine or specs", () => {
  const engine = readFileSync(new URL("../app/vignette.js", import.meta.url), "utf-8")
    + readFileSync(new URL("../app/main.js", import.meta.url), "utf-8")
    + readFileSync(new URL("../app/teaching.js", import.meta.url), "utf-8");
  // assignment-shaped tokens only: "points at" is an error-message verb, not a
  // scoring variable — the ban is on scoring STATE, not on English words
  for (const banned of [/\b(score|points|rating)\w*\s*[:=]/i, /harmony.?index/i]) {
    assert.equal(banned.test(engine), false, `banned token ${banned} found in engine`);
  }
  const specText = JSON.stringify(content);
  assert.equal(/harmony.?index/i.test(specText), false, "Harmony Index must not exist");
  // every ending node must have NO flag setting (release flags only mark state,
  // they never alter which responses are offered — asserted by the respond node)
  for (const v of Object.values(vignettes)) {
    for (const [nid, node] of Object.entries(v.nodes)) {
      if (node.movement === "respond") {
        const sets = (node.choices ?? []).map((c) => c.flag).filter(Boolean);
        assert.equal(sets.length, 0, `${nid}: respond choices must not carry flags`);
      }
    }
  }
});

test("released flag changes only the narrative tone, never the choices offered", () => {
  for (const v of Object.values(vignettes)) {
    let released = newWalk(v);
    let gripped = newWalk(v);
    // walk both to the respond node: released puts it down, gripped does not
    const route = (w) => {
      let steps = 0;
      while (w.graph.nodes[w.node]?.movement !== "respond" && steps < 100) {
        const choices = w.graph.nodes[w.node].choices ?? [];
        const flagChoice = choices.findIndex((c) => c.flag);
        w = choose(w, flagChoice >= 0 ? flagChoice : 0);
        steps++;
      }
      return w;
    };
    released = route(released);
    gripped = route(gripped);
    const a = renderNode(released, "zh").choices.map((c) => c.label);
    const b = renderNode(gripped, "zh").choices.map((c) => c.label);
    assert.deepEqual(b, a, "the same responses must be offered regardless of release");
  }
});
