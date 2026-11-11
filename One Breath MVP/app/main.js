// main.js — scene machine: title → vignette → after-image → back.
//
// WORDLESS-FIRST (the proposal's rule, §3.1: "the prototype itself can remain
// wordless or minimally verbal"): story beats render as ink-minimal picture
// panels, choices as picture tiles; the bilingual text layer exists behind a
// "Words" toggle for mentors and for the completeness tests. No scoring
// anywhere in this file; audio is opt-in and off by default.

import { makeT, loadLang, saveLang, resolveText } from "./i18n.js";
import { newWalk, choose, renderNode, isEnding } from "./vignette.js";
import { positionFromSpec, drawBoard, chainsAt } from "./board-mirror.js";
import { drawPanel, drawIcon } from "./panels.js";

const CONTENT = window.__ONE_BREATH__;         // embedded by tools/build.py
const { strings, vignettes, boards } = CONTENT;

const state = {
  lang: loadLang(),
  reducedMotion: false,
  audioOn: false,
  wordsOn: false,          // wordless-first: the picture carries the meaning
  vignetteId: null,
  walk: null,
};

const $ = (sel) => document.querySelector(sel);

function t(key, vars) {
  return makeT(strings, state.lang)(key, vars);
}

function escapeHtml(s) {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

// --- title screen ------------------------------------------------------------

function renderTitle() {
  const root = $("#screen");
  const list = Object.values(vignettes).map((v) => {
    const ti = v.title[state.lang];
    const tg = (v.tagline?.[state.lang]) ?? "";
    return `<button class="card" data-vignette="${v.id}" aria-label="${escapeHtml(ti)}">
      <span class="card-title">${escapeHtml(ti)}</span>
      <span class="card-tag">${escapeHtml(tg)}</span>
      <span class="card-min">${state.lang === "zh" ? "约 3 分钟" : "about 3 minutes"}</span>
    </button>`;
  }).join("");
  root.innerHTML = `
    <section class="title-screen">
      <h1 class="brush">${t("app_title")}</h1>
      <p class="subtitle">${t("app_subtitle")}</p>
      <div class="row">
        <label class="toggle">${t("choose_language")}
          <button data-act="lang">${state.lang === "zh" ? "中文 → EN" : "EN → 中文"}</button>
        </label>
        <label class="toggle">${t("reduced_motion")}
          <button data-act="motion">${state.reducedMotion ? t("on") : t("off")}</button>
        </label>
        <label class="toggle">${t("words")}
          <button data-act="words">${state.wordsOn ? t("on") : t("off")}</button>
        </label>
        <label class="toggle">${t("audio")}
          <button data-act="audio">${state.audioOn ? t("on") : t("off")}</button>
        </label>
      </div>
      <h2>${t("vignettes_title")}</h2>
      <div class="cards">${list}</div>
      <p class="footer">${t("footer")}</p>
    </section>`;
}

// --- shared chrome -------------------------------------------------------------

function chrome(inner) {
  return `
    <header class="row spread">
      <button data-act="title" aria-label="${t("back_to_list")}">←</button>
      <button data-act="lang">${state.lang === "zh" ? "EN" : "中文"}</button>
      <button data-act="words" aria-label="${t("words")}">${t("words")}</button>
      <button data-act="motion" aria-label="${t("reduced_motion")}">${state.reducedMotion ? "◉" : "○"}</button>
      <button data-act="audio" aria-label="${t("audio")}">${state.audioOn ? "♪" : "–"}</button>
    </header>
    <div class="stage">${inner}</div>`;
}

function iconTiles(walk) {
  const view = renderNode(walk, state.lang);
  return view.choices.map((c) => {
    const icon = c.icon ?? "remember";
    return `<button class="icon-tile" data-choice="${c.index}"
      aria-label="${escapeHtml(c.label)}">
      <canvas class="tile" width="72" height="72" data-icon="${icon}"></canvas>${state.wordsOn ? `<span class="tile-label">${escapeHtml(c.label)}</span>` : ""}
    </button>`;
  }).join("");
}

function textLayer(walk) {
  if (!state.wordsOn) return "";
  const view = renderNode(walk, state.lang);
  return `<div class="story-text">${escapeHtml(view.text).replaceAll("\n\n", "</p><p class='story-text'>")}</div>`;
}

function drawMirror(view) {
  const canvas = $("#board");
  if (!canvas || !view.board) return;
  const boardSpec = boards[vignettes[state.vignetteId].board];
  const pos = positionFromSpec(boardSpec, view.board);
  drawBoard(canvas, pos, {
    highlightPulse: true,
    reducedMotion: state.reducedMotion,
    time: performance.now(),
    showLiberties: false,
  });
  const atari = chainsAt(pos).filter((c) => c.atari).length;
  const hintKey = view.board === "attack" ? "mirror_hint_attack"
    : view.board === "calm" ? "mirror_hint_calm"
    : view.board === "pass" ? "mirror_hint_pass"
    : view.board === "engine" ? "mirror_hint_engine" : null;
  const cap = $("#mirror-caption");
  if (cap) {
    const hint = hintKey ? `${t(hintKey)} · ` : "";
    const tail = state.lang === "zh" ? "告急的棋链" : "chains in atari";
    cap.textContent = `${hint}${atari} ${tail}`;
  }
  if (view.board === "calm" && !state.reducedMotion) afterImage(canvas);
}

// after-image: one whole-board breath, then stillness (the artistic hypothesis;
// reduced-motion keeps a single still frame — the hypothesis stays testable)
function afterImage(canvas) {
  let f = 0;
  const step = () => {
    f++;
    const s = 1 + 0.05 * Math.sin(f / 12) * Math.max(0, 1 - f / 60);
    canvas.style.transform = `scale(${s})`;
    if (f < 60) requestAnimationFrame(step);
    else canvas.style.transform = "scale(1)";
  };
  requestAnimationFrame(step);
}

// --- vignette screen (wordless-first) ------------------------------------------

function renderScreen(walk) {
  const v = vignettes[state.vignetteId];
  const view = renderNode(walk, state.lang);
  const panel = v.nodes[walk.node]?.panel ?? { scene: "breath" };
  const warm = v.style === "warm";
  const root = $("#screen");
  root.innerHTML = `
    <section class="vignette-screen ${state.reducedMotion ? "reduced" : ""} ${state.wordsOn ? "words" : "wordless"}">
      ${chrome(`
        <div class="story">
          <canvas id="panel" width="560" height="360"
            aria-label="${escapeHtml(view.text.replaceAll("\n", " ").slice(0, 120))}"></canvas>
          ${textLayer(walk)}
          <div class="choices icon-row">${iconTiles(walk)}</div>
        </div>
        <div class="mirror">
          <canvas id="board" width="280" height="280" aria-label="${t("mirror_caption")}"></canvas>
          <p class="mirror-caption" id="mirror-caption">${t("mirror_caption")}</p>
        </div>`)}
    </section>`;
  drawPanel($("#panel"), panel, { reducedMotion: state.reducedMotion, warm });
  for (const cv of root.querySelectorAll("canvas[data-icon]")) {
    drawIcon(cv, cv.dataset.icon);
  }
  drawMirror(view);
}

// --- ending screen: five seals, one inked ----------------------------------------

function renderEnding(walk) {
  const v = vignettes[state.vignetteId];
  const view = renderNode(walk, state.lang);
  const panel = v.nodes[walk.node]?.panel ?? { scene: "breath" };
  const warm = v.style === "warm";
  // the five responses stand side by side as seal tiles; the chosen one is inked
  const respondNode = Object.values(v.nodes).find((n) => n.movement === "respond");
  const seals = (respondNode?.choices ?? []).map((c) => {
    const chosen = c.to === walk.node;
    return `<canvas class="seal-tile ${chosen ? "chosen" : "faded"}" width="64" height="64"
      data-icon="${c.icon ?? "remember"}" aria-label="${escapeHtml(c.label)}"></canvas>`;
  }).join("");
  const root = $("#screen");
  root.innerHTML = `
    <section class="ending-screen ${state.reducedMotion ? "reduced" : ""} ${state.wordsOn ? "words" : "wordless"}">
      ${chrome(`
        <div class="story">
          <canvas id="panel" width="560" height="360"
            aria-label="${escapeHtml(view.text.replaceAll("\n", " ").slice(0, 120))}"></canvas>
          <div class="seal-strip">${seals}</div>
          ${textLayer(walk)}
          <div class="choices icon-row">
            <button class="icon-tile" data-act="replay" aria-label="${t("replay")}">
              <canvas class="tile" width="72" height="72" data-icon="replay"></canvas>
            </button>
            <button class="icon-tile" data-act="title" aria-label="${t("back_to_list")}">
              <canvas class="tile" width="72" height="72" data-icon="back_room"></canvas>
            </button>
          </div>
        </div>
        <div class="mirror">
          <canvas id="board" width="280" height="280" aria-label="${t("afterimage_caption")}"></canvas>
          <p class="mirror-caption">${t("afterimage_caption")}</p>
        </div>`)}
    </section>`;
  drawPanel($("#panel"), panel, { reducedMotion: state.reducedMotion, warm });
  for (const cv of root.querySelectorAll("canvas[data-icon]")) {
    drawIcon(cv, cv.dataset.icon);
  }
  drawMirror(view);
}

// --- audio: optional breath bed, off by default --------------------------------
// Synthesized by the vcac additive engine (deterministic) and embedded as a
// data URI at build time; the toggle only plays or pauses it.
let breathAudio = null;
function toggleAudio() {
  if (state.audioOn) {
    breathAudio?.pause();
    state.audioOn = false;
    return;
  }
  if (!breathAudio) {
    breathAudio = new Audio(CONTENT.breathWav);
    breathAudio.loop = true;
    breathAudio.volume = 0.5;
  }
  breathAudio.play().catch(() => {});
  state.audioOn = true;
}

// --- event wiring ---------------------------------------------------------------

document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-act], [data-choice], [data-vignette]");
  if (!el) return;
  if (el.dataset.vignette) {
    state.vignetteId = el.dataset.vignette;
    state.walk = newWalk(vignettes[state.vignetteId]);
    renderScreen(state.walk);
    return;
  }
  if (el.dataset.choice !== undefined && state.walk) {
    state.walk = choose(state.walk, Number(el.dataset.choice), state.lang);
    render();
    return;
  }
  switch (el.dataset.act) {
    case "lang":
      state.lang = state.lang === "zh" ? "en" : "zh";
      saveLang(state.lang);
      render();
      break;
    case "motion":
      state.reducedMotion = !state.reducedMotion;
      render();
      break;
    case "words":
      state.wordsOn = !state.wordsOn;
      render();
      break;
    case "audio": toggleAudio(); render(); break;
    case "title": state.audioOn = false; breathAudio?.pause(); state.walk = null; renderTitle(); break;
    case "replay":
      state.walk = newWalk(vignettes[state.vignetteId]);
      renderScreen(state.walk);
      break;
    case "skip": { // the reflection is skippable — its presence is not a demand
      const p = document.querySelector(".reflection");
      if (p) p.remove();
      break;
    }
  }
});

function render() {
  if (!state.walk) return renderTitle();
  if (isEnding(state.walk)) return renderEnding(state.walk);
  return renderScreen(state.walk);
}

renderTitle();
