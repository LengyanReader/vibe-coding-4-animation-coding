// vignette.js — the story-graph runtime.
//
// The engine ONLY interprets the graph: nodes, choices, flags, transitions.
// It contains no scenario text and no scoring logic — content lives in
// specs/, and the no-scoring property is guarded by a static test that reads
// this file. Walks are pure: (graph, startNode, choiceSequence) -> walk trace,
// so the determinism test can pin "same choices in, same ending out".

import { resolveText } from "./i18n.js";

export function newWalk(graph) {
  return { graph, node: graph.start ?? firstNode(graph), flags: {}, trail: [] };
}

function firstNode(graph) {
  // deterministic entry: the first node in file order unless graph.start names one
  const ids = Object.keys(graph.nodes);
  const start = graph.start && graph.nodes[graph.start] ? graph.start : ids[0];
  return start;
}

export function currentNode(walk) {
  const node = walk.graph.nodes[walk.node];
  if (!node) throw new Error(`vignette: unknown node "${walk.node}"`);
  return node;
}

export function choose(walk, choiceIndex, lang = "zh") {
  const node = currentNode(walk);
  if (node.movement === "ending") {
    throw new Error("vignette: cannot choose on an ending node");
  }
  const choices = node.choices ?? [];
  if (choiceIndex < 0 || choiceIndex >= choices.length) {
    throw new Error(`vignette: choice index out of range at "${walk.node}"`);
  }
  const choice = choices[choiceIndex];
  const flags = { ...walk.flags };
  if (choice.flag) flags[choice.flag] = true;
  const trail = [...walk.trail, { node: walk.node, choice: choiceIndex }];
  return { ...walk, node: choice.to, flags, trail };
}

export function renderNode(walk, lang) {
  const node = currentNode(walk);
  return {
    id: walk.node,
    movement: node.movement,
    highlight: node.highlight ?? null,
    board: node.board ?? null,
    text: resolveText(node.text, lang, walk.flags),
    choices: (node.choices ?? []).map((c, i) => ({
      index: i,
      label: resolveText(c.label, lang, walk.flags),
      flag: c.flag ?? null,
    })),
  };
}

export function isEnding(walk) {
  return currentNode(walk).movement === "ending";
}

// Walk a scripted choice sequence — used by tests and by the determinism gate.
// Returns the ending node id and the full trail; throws if a step is illegal.
export function scriptedWalk(graph, choiceSequence, lang = "zh") {
  let walk = newWalk(graph);
  for (const idx of choiceSequence) {
    walk = choose(walk, idx, lang);
  }
  if (!isEnding(walk)) {
    throw new Error(`vignette: scripted walk did not reach an ending (at "${walk.node}")`);
  }
  const node = currentNode(walk);
  return {
    ending: walk.node,
    flags: walk.flags,
    trail: walk.trail,
    text: resolveText(node.text, lang, walk.flags),
  };
}

// Reachability over the whole graph: from the entry, which nodes/endings can
// be reached at all (dead branches and orphan nodes are authoring defects).
export function reachability(graph) {
  const start = graph.start ?? firstNode(graph);
  const seen = new Set([start]);
  const stack = [start];
  const endings = new Set();
  while (stack.length) {
    const id = stack.pop();
    const node = graph.nodes[id];
    if (!node) throw new Error(`vignette: unknown node "${id}"`);
    if (node.movement === "ending") {
      endings.add(id);
      continue;
    }
    for (const c of node.choices ?? []) {
      if (!graph.nodes[c.to]) {
        throw new Error(`vignette: node "${id}" points at unknown "${c.to}"`);
      }
      if (!seen.has(c.to)) {
        seen.add(c.to);
        stack.push(c.to);
      }
    }
  }
  const all = new Set(Object.keys(graph.nodes));
  const orphans = [...all].filter((id) => !seen.has(id));
  return { reachable: seen, endings: [...endings], orphans, start };
}
