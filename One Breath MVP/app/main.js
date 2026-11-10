// main.js — scene machine: title → vignette → after-image → back.
// No scoring anywhere in this file; the audio toggle is opt-in and off by
// default; reduced-motion is honored by visuals and board rendering.

import { makeT, loadLang, saveLang, resolveText } from "./i18n.js";
import { newWalk, choose, renderNode, isEnding } from "./vignette.js";
import { positionFromSpec, drawBoard, chainsAt, PALETTE } from "./board-mirror.js";

const CONTENT = window.__ONE_BREATH__;         // embedded by tools/build.py
const { strings, vignettes, boards } = CONTENT;

const state = {
  lang: loadLang(),
  reducedMotion: false,
  audioOn: false,
  vignetteId: null,
  walk: null,
};

const $ = (sel) => document.querySelector(sel);

function t(key, vars) {
  return makeT(strings, state.lang)(key, vars);
}

// --- title screen ------------------------------------------------------------

function renderTitle() {
  const root = $("#screen");
  const list = Object.values(vignettes).map((v) => {
    const ti = v.title[state.lang];
    const tg = (v.tagline?.[state.lang]) ?? "";
    return `<button class="card" data-vignette="${v.id}">
      <span class="card-title">${ti}</span>
      <span class="card-tag">${tg}</span>
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
        <label class="toggle">${t("audio")}
          <button data-act="audio">${state.audioOn ? t("on") : t("off")}</button>
        </label>
      </div>
      <h2>${t("vignettes_title")}</h2>
      <div class="cards">${list}</div>
      <p class="footer">${t("footer")}</p>
    </section>`;
}

// --- vignette screen ----------------------------------------------------------

function renderScreen(walk) {
  const v = vignettes[state.vignetteId];
  const view = renderNode(walk, state.lang);
  const movementLabel = t(`movement.${view.movement}`);
  const choices = view.choices.map((c) =>
    `<button class="choice" data-choice="${c.index}">${c.label}</button>`).join("");
  const root = $("#screen");
  root.innerHTML = `
    <section class="vignette-screen ${state.reducedMotion ? "reduced" : ""}">
      <header class="row spread">
        <button data-act="title">← ${t("back_to_list")}</button>
        <span class="movement">${movementLabel}</span>
        <button data-act="lang">${state.lang === "zh" ? "EN" : "中文"}</button>
      </header>
      <div class="stage">
        <div class="story">
          <p class="story-text">${escapeHtml(view.text).replaceAll("\n\n", "</p><p class='story-text'>")}</p>
          <div class="choices">${choices}</div>
        </div>
        <div class="mirror">
          <canvas id="board" width="300" height="300" aria-label="${t("mirror_caption")}"></canvas>
          <p class="mirror-caption" id="mirror-caption">${t("mirror_caption")}</p>
        </div>
      </div>
    </section>`;
  drawMirror(view);
}

function renderEnding(walk) {
  const v = vignettes[state.vignetteId];
  const view = renderNode(walk, state.lang);
  const equal = t("ending_all_equal");
  const reflect = t("reflection");
  const root = $("#screen");
  root.innerHTML = `
    <section class="ending-screen ${state.reducedMotion ? "reduced" : ""}">
      <header class="row spread">
        <button data-act="title">← ${t("back_to_list")}</button>
        <span class="movement">${t("movement.ending")}</span>
        <button data-act="lang">${state.lang === "zh" ? "EN" : "中文"}</button>
      </header>
      <div class="stage">
        <div class="story">
          <p class="story-text">${escapeHtml(view.text).replaceAll("\n\n", "</p><p class='story-text'>")}</p>
          <p class="ending-note"><span class="seal">${t("ending_title")}</span> — ${equal}</p>
          <p class="reflection">${reflect} <button data-act="skip" class="ghost">${t("skip_reflection")}</button></p>
          <div class="choices">
            <button class="choice" data-act="replay">${t("replay")}</button>
            <button class="choice" data-act="title">${t("back_to_list")}</button>
          </div>
        </div>
        <div class="mirror">
          <canvas id="board" width="300" height="300" aria-label="${t("afterimage_caption")}"></canvas>
          <p class="mirror-caption">${t("afterimage_caption")}</p>
        </div>
      </div>
    </section>`;
  drawMirror(view);
}

// --- mirror board --------------------------------------------------------------

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
    : view.board === "pass" ? "mirror_hint_pass" : null;
  const cap = $("#mirror-caption");
  if (cap) {
    cap.textContent = (hintKey ? `${t(hintKey)} · ` : "") + t("mirror_caption")
      + ` — ${state.lang === "zh" ? "告急的棋链" : "chains in atari"}: ${atari}`;
  }
  if (view.board === "calm" && !state.reducedMotion) afterImage(canvas);
}

// after-image: one whole-board breath, then stillness (the artistic hypothesis;
// reduced-motion keeps a single still frame — the hypothesis stays testable)
function afterImage(canvas) {
  let f = 0;
  const step = () => {
    f++;
    const ctx = canvas.getContext("2d");
    const s = 1 + 0.05 * Math.sin(f / 12) * Math.max(0, 1 - f / 60);
    canvas.style.transform = `scale(${s})`;
    if (f < 60) requestAnimationFrame(step);
    else canvas.style.transform = "scale(1)";
  };
  requestAnimationFrame(step);
}

function escapeHtml(s) {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

// --- audio: optional breath hum, off by default --------------------------------
// The bed is synthesized by the vcac audio engine (additive pad, deterministic)
// and embedded as a data URI at build time; the toggle only plays or pauses it.
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
    case "audio": toggleAudio(); render(); break;
    case "title": stopHum(); state.audioOn = false; state.walk = null; renderTitle(); break;
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
