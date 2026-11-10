// i18n.js — bilingual runtime. Language is a per-session choice persisted in
// localStorage; both languages are first-class renderings of one meaning
// (M4.10), so every lookup must exist in BOTH — the completeness test guards
// that at build time, and this module refuses loudly at runtime if not.

const STORE_KEY = "one-breath-lang";

export function loadLang() {
  try {
    const saved = localStorage.getItem(STORE_KEY);
    if (saved === "zh" || saved === "en") return saved;
  } catch { /* storage unavailable — fall through to locale */ }
  return navigator.language?.toLowerCase().startsWith("zh") ? "zh" : "en";
}

export function saveLang(lang) {
  try { localStorage.setItem(STORE_KEY, lang); } catch { /* ignore */ }
}

export function makeT(strings, lang) {
  const lookup = (key) => {
    let cur = strings;
    for (const seg of key.split(".")) {
      if (cur == null) return undefined;
      cur = cur[seg];
    }
    return cur;
  };
  return (key, vars) => {
    const entry = lookup(key);
    if (!entry || typeof entry[lang] !== "string" || !entry[lang]) {
      throw new Error(`i18n missing: "${key}" for "${lang}"`);
    }
    let s = entry[lang];
    if (vars) for (const [k, v] of Object.entries(vars)) {
      s = s.replaceAll(`{${k}}`, String(v));
    }
    return s;
  };
}

// Conditional segments inside vignette text: `{flag, y: ...}` / `{flag, n: ...}`.
// Parse once, resolve against flags — a missing segment pair is an authoring
// defect surfaced by the completeness test, not silently dropped here.
export function resolveText(textObj, lang, flags) {
  const raw = textObj[lang];
  const out = [];
  const re = /\{(\w+),\s*([yn]):\s*([\s\S]*?)\}/g;
  let last = 0, m;
  while ((m = re.exec(raw)) !== null) {
    out.push(renderSpans(raw.slice(last, m.index)));
    const [, flag, polarity, body] = m;
    const wanted = polarity === "y";
    if ((flags[flag] ?? false) === wanted) out.push(renderSpans(body));
    last = re.lastIndex;
  }
  out.push(renderSpans(raw.slice(last)));
  return out.join("");

  function renderSpans(s) {
    // one em-dash set-off per segment; keep the author's line breaks
    return s.trim().replace(/\s*\n\s*/g, "\n\n");
  }
}

// Collect every {zh,en} pair from a vignette graph — used by the completeness
// test (same traversal as the runtime, so the gate and the game see the same data).
export function collectPairs(vignette) {
  const pairs = [];
  const visit = (obj, path) => {
    if (obj === null || typeof obj !== "object") return;
    if (typeof obj.zh === "string" && typeof obj.en === "string") {
      pairs.push({ path, zh: obj.zh, en: obj.en });
      return;
    }
    for (const [k, v] of Object.entries(obj)) visit(v, `${path}.${k}`);
  };
  visit(vignette, vignette.id ?? "vignette");
  return pairs;
}
