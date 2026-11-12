// tokens.js — the visual single source of truth (docs/art-bible.md §2).
//
// Every hex the product renders lives here: the ink scale, the five-act paper
// script (the color story of 觉), the stone material stops, and the case
// variant palettes. A gate test (tests/tokens.test.js) fails the build if a
// bare hex literal appears in any rendering module outside this file, and
// keeps styles.css's custom properties in sync with these values.
//
// Naming follows art-bible: 墨五阶 焦浓重淡清 · 五幕纸色 · 觉光金.

// --- the ink scale (everything drawn) ----------------------------------------
export const INK = {
  jiao: "#221D17",   // 焦 — seals, the darkest point
  nong: "#2E2A24",   // 浓 — primary text and body strokes
  zhong: "#5C5449",  // 重 — secondary lines
  dan: "#8C8477",    // 淡 — receding shapes (far hills, onlookers)
  qing: "#BDB49F",   // 清 — faintest layer (paper grain, guides)
};

// --- the five-act paper script (留白 · 气韵 · 觉光) ----------------------------
export const PAPER = {
  mist: "#F6F4EE",   // 一 遇见 — cool dawn haze, not yet awake
  plain: "#F8F5ED",  // 二 气 — plain paper, attention
  lamp: "#FAF4E6",   // 三 第一盘棋 — the lamp is lit
  warm: "#FAF1E0",   // 四 照见 — warmer; ghosts speak
  lucid: "#FBF3E2",  // 五 觉 — faint light; gold may appear
  deep: "#EFE3C8",
  warmRim: "#F2E7CF",   // warm-case panel rim   // wash rim, card bottoms, the board's wooden edge
  cardTop: "#FBF7EC",
  cardBottom: "#F1E9D7",
};

// --- accents (used sparingly; see art-bible §2.3) -----------------------------
export const GOLD = "#C9A227";   // 觉光金 — ONLY: Indra's-net lines, lucid hairlines
export const SEAL = "#A33B2B";   // 朱砂 — seals, refusal crosses, movement dots
export const SEAL_DARK = "#8C3124";  // seal hover (primary buttons)   // 朱砂 — seals, refusal crosses, movement dots
export const OCHRE = "#8A5A3B";  // hover borders, warm UI accents
export const DAI = "#46586B";    // 黛青 — far hills, cool accents
export const MOSS = "#8A9B8E";   // 苔 — breath points, corridor marks, bamboo
export const AMBER = "#D9A86C";  // 灯 — lamp glow, warm scenes
export const DUSK = "#A8B8C8";   // 暮 — the machine's cold light (two-ways only)

// --- the stone material (matte ink, not a digital marble) ---------------------
export const STONE = {
  black: "#26221D",     // body
  blackHi: "#5D564C",   // dome sheen (deliberately faint)
  blackLo: "#29251F",   // rim
  white: "#F6F2E6",     // clamshell body
  whiteHi: "#FFFDF4",
  whiteLo: "#E2D8BE",
  bleedDark: "#8C8377", // ink-bleed arc on black stones
  bleedLight: "#B9AE99",
  shadow: "rgba(58,50,38,0.2)",
  blackEdge: "rgba(30,26,21,0.5)",
  whiteEdge: "rgba(118,108,88,0.55)",
};

// --- the act color script (one entry per act; see narrative-design §2) --------
// paper: the shell's ground; wash: the atmosphere layer over the far hills;
// accent: the one colour this act may point with.
export const ACTS = [
  { id: "meet", paper: PAPER.mist, wash: "rgba(70,88,107,0.10)", accent: DAI },
  { id: "air", paper: PAPER.plain, wash: "rgba(92,84,73,0.08)", accent: INK.zhong },
  { id: "game", paper: PAPER.lamp, wash: "rgba(217,168,108,0.12)", accent: AMBER },
  { id: "mirror", paper: PAPER.warm, wash: "rgba(138,155,142,0.12)", accent: MOSS },
  { id: "lucid", paper: PAPER.lucid, wash: "rgba(201,162,39,0.10)", accent: GOLD },
];

// --- the board's own palette (legacy surface, now token-fed) ------------------
// board-mirror.js re-exports this as PALETTE so existing imports keep working.
export const PALETTE = {
  paper: "#F5F1E6",
  paperDeep: "#EFE9DC",
  ink: INK.nong,
  inkSoft: INK.zhong,
  inkFaint: INK.qing,
  blackStone: STONE.black,
  whiteStone: STONE.white,
  sealRed: SEAL,
  breath: "#7B736B",
  sage: MOSS,
};

// --- the warm case variant (case two/two-ways; a softer, ambered reading) -----
export const WARM = {
  paper: "#FBF6EA",
  ink: "#4A4038",
  inkSoft: "#7A6E60",
  inkFaint: "#D8CBB4",
  blackStone: "#3E3831",
  whiteStone: "#FDF9EF",
  sealRed: "#C2704E",
  sage: MOSS,
  amber: AMBER,
  dusk: DUSK,
};

// --- the dharmadhatu views' palette -------------------------------------------
export const DHARMA = {
  paper: "#F8F3E6",
  inkSoft: INK.zhong,
  inkFaint: INK.qing,
  stone: STONE.black,
  whiteStone: STONE.white,
  sage: MOSS,
  seal: SEAL,
  gold: GOLD,
};
