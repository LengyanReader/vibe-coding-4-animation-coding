// main.js — scene machine: title → chapter (lesson → compare → sit → respond)
// or case → after-image → back.
//
// WORDLESS-FIRST (the proposal's rule, §3.1): story beats render as ink-minimal
// picture panels, choices as picture tiles; the bilingual text layer exists
// behind a "Words" toggle for mentors and for the completeness tests. Chapter 0
// is the exception: its rule lines are always visible, because a first-time
// player cannot learn a rule from a picture alone. No scoring anywhere in this
// file; audio is opt-in and off by default.

import { makeT, loadLang, saveLang, resolveText } from "./i18n.js";
import { newWalk, choose, renderNode, isEnding } from "./vignette.js";
import { emptyPosition, play, key, groupAt, eyesFor, BLACK, WHITE } from "./rules.js";
import { positionFromSpec, drawBoard, chainsAt, hitTest } from "./board-mirror.js";
import { drawPanel, drawIcon, drawAmbient } from "./panels.js";
import { ACTS } from "./tokens.js";
import { drawDharmadhatuView, VIEW_COUNT } from "./dharmadhatu.js";
import { newLessonWalk, currentStep, clickPoint, pressPass, resetStep, advanceStep, skipStep, isDone, roleAnchor, positionForStep, moveCursor } from "./teaching.js";

const CONTENT = window.__ONE_BREATH__;         // embedded by tools/build.py
const { strings, vignettes, boards, lessons, games } = CONTENT;

const state = {
  lang: loadLang(),
  reducedMotion: false,
  audioOn: false,
  wordsOn: false,          // wordless-first: the picture carries the meaning
  sitting: false,          // inside the 坐观 act
  sitView: 0,              // which of the four widening views is on screen
  sitExit: "ending",       // "ending" (after a case) or "graph" (Chapter 0)
  sitPositions: null,      // {finalPos, initialPos} for the current sit act
  mirror: null,            // the player's own game: {position, opening, captures, result}
  keyCursor: null,         // keyboard grid cursor {r,c} while a board canvas has focus
  sitConfig: null,         // Chapter 0's sit config, reused by its ending tile
  vignetteId: null,
  walk: null,
  lesson: null,            // teaching walk (Chapter 0, node.lesson)
  compare: null,           // {nodeId, step, foundYou, messageKey, vars}
};

// --- the act color script (docs/art-bible.md §4) -------------------------------
// The page shifts tone as the player moves through the arc: 遇见(0) → 气(1) →
// 对局(2) → 照见(3) → 觉(4). The canvases read the act from drawPanel/drawAmbient;
// the chrome reads it from body[data-act].

function currentAct() {
  if (!state.walk) return 0;
  const v = vignettes[state.vignetteId];
  const node = v?.nodes[state.walk.node];
  if (node?.lesson) {
    const step = state.lesson ? currentStep(state.lesson) : null;
    if (step?.kind === "game") return 2;
    if (step?.id === "l1_breath") return 0;
    return 1;
  }
  if (node?.compare) return 3;
  if (node?.sit || node?.movement === "release" || node?.movement === "respond") return 4;
  if (isEnding(state.walk)) return 4;
  return node?.movement === "encounter" ? 0 : 1;
}

function applyAct() {
  const act = currentAct();
  document.body.dataset.act = ACTS[act].id;
  return act;
}

const $ = (sel) => document.querySelector(sel);

function t(key, vars) {
  return makeT(strings, state.lang)(key, vars);
}

function escapeHtml(s) {
  return String(s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function langText(pair, vars) {
  return resolveText(pair, state.lang, vars ?? {});
}

// --- title screen ------------------------------------------------------------

function renderTitle() {
  state.keyCursor = null;
  applyAct();
  const root = $("#screen");
  const ordered = Object.values(vignettes)
    .sort((a, b) => (a.chapter ?? 9) - (b.chapter ?? 9) || a.id.localeCompare(b.id));
  const list = ordered.map((v) => {
    const ti = v.title[state.lang];
    const tg = (v.tagline?.[state.lang]) ?? "";
    const chapter = v.chapter === 0;
    const min = chapter
      ? (state.lang === "zh" ? "第零章 · 主线约 8–10 分钟" : "Chapter 0 · core about 8–10 min")
      : (state.lang === "zh" ? "约 3 分钟" : "about 3 minutes");
    return `<button class="card ${chapter ? "card-chapter" : ""}" data-vignette="${v.id}" aria-label="${escapeHtml(ti)}">
      ${chapter ? `<span class="card-badge">${state.lang === "zh" ? "先学一手" : "Start here"}</span>` : ""}
      <span class="card-title">${escapeHtml(ti)}</span>
      <span class="card-tag">${escapeHtml(tg)}</span>
      <span class="card-min">${min}</span>
    </button>`;
  }).join("");
  root.innerHTML = `
    <section class="title-screen">
      <div class="masthead">
        <span class="seal-stamp">一息</span>
        <div>
          <h1 class="brush">${t("app_title")}</h1>
          <p class="subtitle">${t("app_subtitle")}</p>
        </div>
      </div>
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
    if (hintKey) {
      const tail = state.lang === "zh" ? "告急的棋链" : "chains in atari";
      cap.textContent = `${t(hintKey)} · ${atari} ${tail}`;
    } else {
      const tail = state.lang === "zh" ? "块棋" : "chains";
      cap.textContent = `${t("mirror_caption")} · ${chainsAt(pos).length} ${tail}`;
    }
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
  const node = v.nodes[walk.node];
  if (node.lesson) return renderLesson(walk, v, node);
  if (node.compare) return renderCompare(walk, v, node);
  if (node.sit) return renderSitAct(walk, v, node);

  const view = renderNode(walk, state.lang);
  const panel = node.panel ?? { scene: "breath" };
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
  drawPanel($("#panel"), panel, { reducedMotion: state.reducedMotion, warm, act: currentAct() });
  for (const cv of root.querySelectorAll("canvas[data-icon]")) {
    drawIcon(cv, cv.dataset.icon);
  }
  drawMirror(view);
}

// --- Chapter 0 · the lesson screen ---------------------------------------------

function lessonMessage() {
  const m = state.lesson?.message;
  return m ? t(m.key, m.vars) : "";
}

function drawLessonBoard() {
  const canvas = $("#lesson-board");
  if (!canvas || !state.lesson) return;
  const lw = state.lesson;
  const step = currentStep(lw);
  const markers = [];
  for (const k of lw.clicked) markers.push({ at: k, kind: "clicked" });
  for (const k of lw.refused) markers.push({ at: k, kind: "refused" });
  if (step.kind === "mutual") {
    for (const [r, c] of step.corridor) {
      const k = key(r, c);
      if (!lw.pos.stones.has(k)) markers.push({ at: k, kind: "corridor" });
    }
  }
  if (step.kind === "game" && lw.hint) {
    const tgt = lw.record.moves[lw.gameIdx]?.at;
    if (tgt) markers.push({ at: key(...tgt), kind: "hint" });
  }
  if (document.activeElement?.id === "lesson-board" && state.keyCursor) {
    markers.push({ at: key(state.keyCursor.r, state.keyCursor.c), kind: "cursor" });
  }
  if (lw.lastMove) markers.push({ at: lw.lastMove, kind: "last" });
  drawBoard(canvas, lw.pos, {
    reducedMotion: state.reducedMotion,
    time: performance.now(),
    highlightPulse: true,
    libertiesFor: step.chain ? key(...step.chain) : null,
    markers,
    ghostPoints: lw.ghosts,
  });
}

function renderLesson(walk, v, node) {
  const lesson = lessons[node.lesson];
  if (!lesson) throw new Error(`lesson "${node.lesson}" is not in the build`);
  if (!state.lesson || state.lesson.lesson.id !== lesson.id) {
    state.lesson = newLessonWalk(lesson, boards[lesson.board], games);
    state.lesson.storyNode = walk.node;   // the board-click handler re-renders with this node
  }
  const lw = state.lesson;
  const step = currentStep(lw);
  const total = lesson.steps.length;
  const done = isDone(lw);
  const pct = Math.round(((lw.stepIndex + 1) / total) * 100);
  // the guided game's live sidebar: move counter, phase, grandpa's bubble,
  // captures — plus the final count once both sides have rested
  const isGame = step.kind === "game";
  let gameSide = "";
  if (isGame) {
    const m = lw.record.moves[Math.min(lw.gameIdx, lw.record.moves.length - 1)];
    const phase = lw.record.phases[m.phase] ?? { zh: m.phase, en: m.phase };
    const moveLabel = t("lesson.msg.game_move", { n: m.num, phase: phase[state.lang] });
    const bubble = lw.gameBubble;
    const caps = bubble?.captures ?? lw.gs.captures;
    gameSide = `
      <p class="lesson-step">${escapeHtml(moveLabel)}</p>
      <p class="lesson-rule">${escapeHtml(bubble?.main?.[state.lang] ?? step.prompt[state.lang])}</p>
      ${bubble?.prev ? `<p class="lesson-prompt">${escapeHtml(bubble.prev[state.lang])}</p>` : ""}
      <p class="lesson-message" role="status">${escapeHtml(lessonMessage())}</p>
      <p class="lesson-captions">${escapeHtml(t("lesson.msg.game_captures", { b: caps.black, w: caps.white }))}</p>
      ${lw.gameResult ? `
        <p class="lesson-result">${escapeHtml(lw.gameResult.note[state.lang])}</p>` : ""}`;
  }
  const root = $("#screen");
  root.innerHTML = `
    <section class="lesson-screen ${state.reducedMotion ? "reduced" : ""}">
      ${chrome(`
        <div class="lesson-head">
          <div class="masthead">
            <span class="seal-stamp small">学</span>
            <div>
              <p class="lesson-chapter">${t("lesson.chapter_label")}</p>
              <h2 class="lesson-title">${escapeHtml(lesson.title[state.lang])}</h2>
            </div>
          </div>
          <div class="story-text">${escapeHtml(resolveText(node.text, state.lang, walk.flags)).replaceAll("\n\n", "</p><p class='story-text'>")}</div>
        </div>
        <div class="lesson-stage">
          <canvas id="lesson-scene" width="640" height="420" aria-hidden="true"></canvas>
          <canvas id="lesson-board" width="420" height="420" tabindex="0" role="application"
            aria-label="${t("lesson.board_caption")}"></canvas>
          <div class="lesson-side">
            ${isGame ? gameSide : `
              <p class="lesson-step">${t("lesson.step", { n: lw.stepIndex + 1, total })} · ${step.core ? t("lesson.core") : t("lesson.optional")}</p>
              <p class="lesson-rule">${escapeHtml(step.rule[state.lang])}</p>
              <p class="lesson-prompt">${escapeHtml(step.prompt[state.lang])}</p>
              <p class="lesson-message" role="status">${escapeHtml(lessonMessage())}</p>`}
            <div class="row">
              ${done ? `<button data-act="lesson_next">${t("lesson.continue")}</button>` : ""}
              <button data-act="lesson_reset">${t("lesson.reset")}</button>
              ${(step.kind === "pass" || step.kind === "mutual" || (isGame && lw.awaitingPass)) ? `<button data-act="lesson_pass">${t("lesson.pass")}</button>` : ""}
              ${!step.core && !isGame ? `<button class="ghost" data-act="lesson_step_skip">${t("lesson.step_skip")}</button>` : ""}
              <button class="ghost" data-act="lesson_skip">${t("lesson.skip")}</button>
            </div>
            <div class="lesson-progress" role="progressbar" aria-valuemin="1" aria-valuemax="${total}" aria-valuenow="${lw.stepIndex + 1}"><span style="width:${pct}%"></span></div>
          </div>
        </div>`)}
    </section>`;
  drawLessonBoard();
  const sceneByAct = ["room", "corridor", "room", "", ""];
  const sc = $("#lesson-scene");
  if (sc) {
    // draw at the laid-out pixel size so the atmosphere never stretches
    sc.width = Math.max(320, Math.round(sc.getBoundingClientRect().width));
    sc.height = 300;
    drawAmbient(sc, {
      act: currentAct(),
      scene: sceneByAct[currentAct()],
      time: performance.now(),
      reducedMotion: state.reducedMotion,
    });
  }
}

// --- Chapter 0 · the comparison screen ------------------------------------------

function compareMessage(st) {
  return st.messageKey ? t(st.messageKey, st.vars) : "";
}

function compareOwnFooter(st) {
  if (st.mode !== "own" || !state.mirror) return "";
  if (st.foundEyes.length < 2) return "";
  const r = state.mirror.result;
  return `<p class="lesson-result">${escapeHtml(t("compare.own_count", { b: r.black, w: r.white }))}</p>
    <p class="story-text">${escapeHtml(t("compare.own_bridge"))}</p>`;
}

function drawCompareBoard(cfg, st) {
  const canvas = $("#compare-board");
  if (!canvas) return;
  if (st.mode === "own" && state.mirror) {
    // act 4 照见: the board the PLAYER made — doors found, lifted stones,
    // and the land, all read from their own game
    const markers = (st.foundEyes ?? []).map((k) => ({ at: k, kind: "clicked" }));
    if (document.activeElement?.id === "compare-board" && state.keyCursor) {
      markers.push({ at: key(state.keyCursor.r, state.keyCursor.c), kind: "cursor" });
    }
    drawBoard(canvas, state.mirror.position, {
      reducedMotion: state.reducedMotion,
      time: performance.now(),
      highlightPulse: false,
      markers,
      ghostPoints: st.step >= 1 ? state.mirror.captures : [],
    });
    return;
  }
  const boardSpec = boards[cfg.board];
  const pos = positionFromSpec(boardSpec, cfg.beat);
  const markers = [];
  if (st.step > 1) {
    for (const [r, c] of (boardSpec.lesson_checks?.corridor?.corridor ?? [])) {
      markers.push({ at: key(r, c), kind: "corridor" });
    }
  }
  drawBoard(canvas, pos, {
    reducedMotion: state.reducedMotion,
    time: performance.now(),
    highlightPulse: true,
    markers,
    roles: st.step > 0
      ? { you: roleAnchor(boardSpec, "you"), them: roleAnchor(boardSpec, "them") }
      : null,
  });
}

function playerEyes() {
  if (!state.mirror) return [];
  const pos = state.mirror.position;
  const seen = new Set();
  for (const [k, v] of pos.stones) {
    if (v !== BLACK || seen.has(k)) continue;
    const g = groupAt(pos, k);
    for (const s of g.stones) seen.add(s);
    const eyes = eyesFor(pos, k);
    if (eyes.length === 2) return eyes;   // the group that made two doors
  }
  return [];
}

function renderCompare(walk, v, node) {
  const cfg = node.compare;
  if (!state.compare || state.compare.nodeId !== walk.node) {
    state.compare = cfg.mode === "own-position" && state.mirror
      ? { nodeId: walk.node, mode: "own", step: 0, foundEyes: [],
          eyes: playerEyes(), messageKey: "compare.own_find_eyes", vars: null }
      : { nodeId: walk.node, step: 0, foundCorridor: false,
          messageKey: "compare.find_you", vars: null };
  }
  const st = state.compare;
  const root = $("#screen");
  root.innerHTML = `
    <section class="compare-screen ${state.reducedMotion ? "reduced" : ""}">
      ${chrome(`
        <div class="compare-copy">
          <div class="masthead">
            <span class="seal-stamp small">照</span>
            <div><p class="lesson-chapter">${t("compare.title")}</p></div>
          </div>
          <div class="story-text">${escapeHtml(resolveText(node.text, state.lang, walk.flags)).replaceAll("\n\n", "</p><p class='story-text'>")}</div>
          <p class="lesson-prompt" role="status">${escapeHtml(compareMessage(st))}</p>
          ${compareOwnFooter(st)}
          <div class="row">
            <button data-act="compare_continue" ${st.mode === "own"
              ? (st.foundEyes.length >= 2 ? "" : "disabled")
              : (st.step > 1 ? "" : "disabled")}>${t("compare.continue")}</button>
          </div>
        </div>
        <div class="compare-board">
          <canvas id="compare-board" width="420" height="420" tabindex="0" role="application"
            aria-label="${t("mirror_caption")}"></canvas>
        </div>`)}
    </section>`;
  drawCompareBoard(cfg, st);
}

// --- Chapter 0 · the 坐观 act ---------------------------------------------------

function sitPositionsFrom(config) {
  const boardSpec = boards[config.board];
  return {
    finalPos: positionFromSpec(boardSpec, config.final),
    initialPos: positionForStep({ beat: config.initial }, boardSpec),
  };
}

function finalAndInitialPositions() {
  const v = vignettes[state.vignetteId];
  const boardSpec = boards[v.board];
  const finalPos = positionFromSpec(boardSpec, "engine");
  const init = emptyPosition(boardSpec.size);
  for (const [r, c] of boardSpec.stones.black) {
    const res = play(init, key(r, c), BLACK);
    if (res.ok) init.stones = res.pos.stones;
  }
  for (const [r, c] of boardSpec.stones.white) {
    const res = play(init, key(r, c), WHITE);
    if (res.ok) init.stones = res.pos.stones;
  }
  return { finalPos, initialPos: init };
}

function renderSitAct(walk, v, node) {
  state.sitting = true;
  state.sitView = 0;
  state.sitExit = "sit_graph_exit";
  state.sitPositions = state.mirror
    ? { finalPos: state.mirror.position, initialPos: state.mirror.opening }
    : sitPositionsFrom(node.sit);
  applyAct();
  renderSitScreen();
}

function renderSit() {
  state.sitting = true;
  state.sitExit = "sit_exit";
  state.sitPositions = state.mirror
    ? { finalPos: state.mirror.position, initialPos: state.mirror.opening }
    : state.sitConfig
      ? sitPositionsFrom(state.sitConfig)
      : finalAndInitialPositions();
  applyAct();
  renderSitScreen();
}

function renderSitScreen() {
  const viewNames = ["view_phenomena", "view_principle", "view_interwork", "view_indra"];
  const dots = [0, 1, 2, 3].map((i) =>
    `<span class="sit-dot ${i === state.sitView ? "on" : ""}"></span>`).join("");
  const root = $("#screen");
  root.innerHTML = `
    <section class="sit-screen ${state.reducedMotion ? "reduced" : ""}">
      <header class="row spread">
        <button data-act="${state.sitExit}" aria-label="${t("return_board")}">×</button>
        <button data-act="lang">${state.lang === "zh" ? "EN" : "中文"}</button>
        <button data-act="words" aria-label="${t("words")}">${t("words")}</button>
        <button data-act="motion" aria-label="${t("reduced_motion")}">${state.reducedMotion ? "◉" : "○"}</button>
      </header>
      <div class="sit-stage">
        <canvas id="sit-canvas" width="560" height="560"
          aria-label="${t(viewNames[state.sitView])}"></canvas>
        <p class="sit-caption"><span class="seal-stamp small">观</span>${t(viewNames[state.sitView])}</p>
        <div class="sit-nav row">
          <button data-act="sit_prev" aria-label="${t("prev_view")}" ${state.sitView === 0 ? "disabled" : ""}>←</button>
          <span class="sit-dots">${dots}</span>
          <button data-act="sit_next" aria-label="${t("next_view")}" ${state.sitView === 3 ? "disabled" : ""}>→</button>
        </div>
        <p class="footer">${state.wordsOn ? t("ending_all_equal") : t("return_board")}</p>
      </div>
    </section>`;
  const { finalPos, initialPos } = state.sitPositions;
  drawDharmadhatuView($("#sit-canvas"), state.sitView, finalPos, initialPos, {
    reducedMotion: state.reducedMotion,
    time: performance.now(),
  });
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
      data-icon="${c.icon ?? "remember"}" aria-label="${escapeHtml(c.label?.[state.lang] ?? "")}"></canvas>`;
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
            <button class="icon-tile" data-act="sit" aria-label="${t("sit_view")}">
              <canvas class="tile" width="72" height="72" data-icon="sit_view"></canvas>
            </button>
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
  drawPanel($("#panel"), panel, { reducedMotion: state.reducedMotion, warm, act: currentAct() });
  for (const cv of root.querySelectorAll("canvas[data-icon]")) {
    drawIcon(cv, cv.dataset.icon);
  }
  drawMirror(view);
}

// --- audio: optional breath bed, off by default --------------------------------
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

// --- canvas interaction (teaching + comparison) ---------------------------------

document.addEventListener("click", (e) => {
  if (e.target.id === "lesson-board" && state.lesson) {
    const lw = state.lesson;
    const pt = hitTest(e.target, e.clientX, e.clientY, lw.pos.size);
    if (!pt) return;
    state.lesson = clickPoint(lw, pt).walk;
    const v = vignettes[state.vignetteId];
    const remembered = v.nodes[state.lesson.storyNode ?? state.walk.node];
    const node = remembered?.lesson === lw.lesson.id
      ? remembered
      : Object.values(v.nodes).find((n) => n.lesson === lw.lesson.id);
    renderLesson(state.walk, v, node);
    return;
  }
  if (e.target.id === "compare-board" && state.compare) {
    const pt = hitTest(e.target, e.clientX, e.clientY, 5);
    if (!pt) return;
    runComparePoint(pt);
    return;
  }
});



// --- keyboard access (docs/gdd.md §6) -------------------------------------------
// The teaching and mirror boards are canvases; a keyboard-only player walks a
// cursor with the arrow keys and commits with Enter/Space. The cursor ring is
// drawn by drawBoard's "cursor" marker.

const BOARD_KEYS = new Set(["lesson-board", "compare-board"]);

function runComparePoint(pt) {
  const st = state.compare;
  const node = vignettes[state.vignetteId].nodes[state.walk.node];
  if (st.mode === "own" && state.mirror) {
    const k = key(...pt);
    if (!st.eyes.includes(k)) {
      st.messageKey = "compare.own_not_eye";
    } else if (!st.foundEyes.includes(k)) {
      st.foundEyes = [...st.foundEyes, k];
      st.messageKey = st.foundEyes.length === 1 ? "compare.own_one_door" : "compare.own_ghosts";
      st.step = 1;
      st.vars = { n: state.mirror.captures.length };
    }
  } else {
    const cfg = node.compare;
    const boardSpec = boards[cfg.board];
    const k = key(...pt);
    const pos = positionFromSpec(boardSpec, cfg.beat);
    if (st.step === 0) {
      const anchor = roleAnchor(boardSpec, "you");
      if (anchor && groupAt(pos, anchor).stones.has(k)) {
        st.step = 1;
        st.messageKey = "compare.find_corridor";
      } else {
        st.messageKey = "compare.try_again";
      }
    } else if (st.step === 1) {
      const corridor = boardSpec.lesson_checks?.corridor?.corridor ?? [];
      if (corridor.some(([r, c]) => key(r, c) === k)) {
        st.step = 2;
        st.foundCorridor = true;
        st.messageKey = "compare.found_corridor";
        st.vars = { n: corridor.length };
      } else {
        st.messageKey = "compare.try_again";
      }
    }
  }
  renderCompare(state.walk, vignettes[state.vignetteId], node);
}

function cursorPointFor(canvasId) {
  if (canvasId === "lesson-board") return state.lesson ? state.lesson.pos.size : 0;
  if (canvasId === "compare-board") {
    if (state.compare?.mode === "own" && state.mirror) return state.mirror.position.size;
    const node = vignettes[state.vignetteId]?.nodes[state.walk?.node];
    return node?.compare ? boards[node.compare.board].size : 0;
  }
  return 0;
}

function commitCursor(canvasId) {
  const pt = [state.keyCursor.r, state.keyCursor.c];
  if (canvasId === "lesson-board") {
    if (!state.lesson) return;
    state.lesson = clickPoint(state.lesson, pt).walk;
    const v = vignettes[state.vignetteId];
    const remembered = v.nodes[state.lesson.storyNode ?? state.walk.node];
    const node = remembered?.lesson === state.lesson.lesson.id
      ? remembered
      : Object.values(v.nodes).find((n) => n.lesson === state.lesson.lesson.id);
    renderLesson(state.walk, v, node);
  } else {
    runComparePoint(pt);
  }
}

document.addEventListener("keydown", (e) => {
  const t = document.activeElement;
  if (!t || !BOARD_KEYS.has(t.id)) return;
  const size = cursorPointFor(t.id);
  if (!size) return;
  if (e.key.startsWith("Arrow")) {
    e.preventDefault();
    state.keyCursor = moveCursor(state.keyCursor ?? { r: 3, c: 3 }, e.key, size);
    render();
    // the render rebuilds the canvas — put the hand back on the board
    document.getElementById(t.id)?.focus();
  } else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    if (!state.keyCursor) state.keyCursor = { r: 3, c: 3 };
    commitCursor(t.id);
    document.getElementById(t.id)?.focus();
  } else if (e.key === "Escape") {
    t.blur();
  }
});

// --- event wiring ---------------------------------------------------------------

document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-act], [data-choice], [data-vignette]");
  if (!el) return;
  if (el.dataset.vignette) {
    state.vignetteId = el.dataset.vignette;
    state.walk = newWalk(vignettes[state.vignetteId]);
    state.lesson = null;
    state.compare = null;
    state.mirror = null;
    state.sitting = false;
    const v = vignettes[state.vignetteId];
    const sitNode = Object.values(v.nodes).find((n) => n.sit);
    state.sitConfig = sitNode?.sit ?? null;
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
      state.sitting ? renderSitScreen() : render();
      break;
    case "words":
      state.wordsOn = !state.wordsOn;
      state.sitting ? renderSitScreen() : render();
      break;
    case "audio": toggleAudio(); state.sitting ? renderSitScreen() : render(); break;
    case "lesson_next": {
      const r = advanceStep(state.lesson);
      // the guided game's final board becomes the personal mirror (act 4):
      // 照见 and 坐观 play on the position the PLAYER made, not a canned one
      if (r.event === "lesson-done" && state.lesson?.gameResult) {
        state.mirror = {
          position: state.lesson.gs.pos,
          opening: state.lesson.openingPos,
          captures: state.lesson.captureLog ?? [],
          result: state.lesson.gameResult,
        };
      }
      state.lesson = r.walk;
      if (r.event === "lesson-done") {
        state.lesson = null;
        state.walk = choose(state.walk, 0);
      }
      render();
      break;
    }
    case "lesson_reset":
      state.lesson = resetStep(state.lesson);
      render();
      break;
    case "lesson_pass":
      state.lesson = pressPass(state.lesson).walk;
      render();
      break;
    case "lesson_step_skip": {
      const r = skipStep(state.lesson);
      state.lesson = r.walk;
      if (r.event === "lesson-done") {
        state.lesson = null;
        state.walk = choose(state.walk, 0);
      }
      render();
      break;
    }
    case "lesson_skip":
      state.lesson = null;
      state.walk = choose(state.walk, 0);
      render();
      break;
    case "compare_continue":
      state.compare = null;
      state.walk = choose(state.walk, 0);
      render();
      break;
    case "sit":
      state.sitView = 0;
      renderSit();
      break;
    case "sit_exit":
      state.sitting = false;
      state.sitPositions = null;
      render();
      break;
    case "sit_graph_exit":
      state.sitting = false;
      state.sitPositions = null;
      state.walk = choose(state.walk, 0);
      render();
      break;
    case "sit_next":
      state.sitView = Math.min(VIEW_COUNT - 1, state.sitView + 1);
      renderSitScreen();
      break;
    case "sit_prev":
      state.sitView = Math.max(0, state.sitView - 1);
      renderSitScreen();
      break;
    case "title":
      state.audioOn = false;
      breathAudio?.pause();
      state.sitting = false;
      state.lesson = null;
      state.compare = null;
      state.mirror = null;
      state.sitConfig = null;
      state.sitPositions = null;
      state.walk = null;
      renderTitle();
      break;
    case "replay":
      state.lesson = null;
      state.compare = null;
      state.mirror = null;
      state.walk = newWalk(vignettes[state.vignetteId]);
      renderScreen(state.walk);
      break;
    case "skip": {
      const p = document.querySelector(".reflection");
      if (p) p.remove();
      break;
    }
  }
});

function render() {
  applyAct();
  if (!state.walk) return renderTitle();
  if (isEnding(state.walk)) return renderEnding(state.walk);
  return renderScreen(state.walk);
}

renderTitle();