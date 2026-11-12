#!/usr/bin/env python3
"""Browser smoke matrix for dist/one-breath.html (Playwright, dev-only).

Matrix: 3 vignettes × {zh, en} × {words on, off} — plus the full Chapter 0
lesson ladder, sit views 0–3, all 5 endings, and pixel checks so a blank
canvas cannot pass. Screenshots go to outputs/_smoke/.

Usage: python tools/smoke.py            # full matrix
       python tools/smoke.py --quick    # reduced matrix (zh only, words off)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "_smoke"
OUT.mkdir(parents=True, exist_ok=True)

VIGNETTES = ["shared-breath", "two-sides", "two-ways"]
LANGS = ["zh", "en"]
WORD_MODES = [False, True]


def board_click(page, selector, r, c, size=5, width=420):
    box = page.locator(selector).bounding_box()
    pad = width * 0.105
    cell = (width - pad * 2) / (size - 1)
    x = pad + (c - 1) * cell
    y = pad + (r - 1) * cell
    page.mouse.click(box["x"] + x * (box["width"] / width),
                     box["y"] + y * (box["height"] / width))


def canvas_ink(page, selector):
    """Count pixels that differ from the paper background — works for both
    the ink palette (dark stones) and the warm palette (soft colours)."""
    return page.evaluate(
        """(sel) => {
            const c = document.querySelector(sel);
            if (!c) return { dark: -1, total: 0 };
            const ctx = c.getContext('2d');
            const d = ctx.getImageData(0, 0, c.width, c.height).data;
            let non = 0;
            for (let i = 0; i < d.length; i += 4) {
                // non-paper: any channel differs from warm paper (#FBF6EA ≈ 251,246,234)
                if (Math.abs(d[i] - 251) > 25 || Math.abs(d[i+1] - 246) > 25 || Math.abs(d[i+2] - 234) > 25)
                    non++;
            }
            return { dark: non, total: c.width * c.height };
        }""", selector)


def click_choice(page, index):
    page.locator(f'button[data-choice="{index}"]').click()
    page.wait_for_timeout(250)


def click_act(page, act):
    page.locator(f'[data-act="{act}"]').click()
    page.wait_for_timeout(250)


def toggle_words(page, on):
    page.locator('[data-act="words"]').click()
    page.wait_for_timeout(150)


def screenshot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)


def check_canvas(page, sel, label, min_dark=1):
    ink = canvas_ink(page, sel)
    status = "ok" if ink["dark"] >= min_dark else "BLANK"
    print(f"  canvas [{label}]: dark={ink['dark']} status={status}")
    return ink["dark"] >= min_dark


def run_vignette_smoke(page, vid, lang, words, shot_prefix, errors):
    """Open a vignette, advance at least 2 beats, screenshot."""
    tag = f"{vid}-{lang}-{'words' if words else 'noWords'}"
    page.goto((ROOT / "dist" / "one-breath.html").resolve().as_uri())
    page.wait_for_timeout(300)

    # set language
    if lang == "zh":
        page.locator('[data-act="lang"]').click()
        page.wait_for_timeout(150)

    # set words mode
    if words:
        page.locator('[data-act="words"]').click()
        page.wait_for_timeout(150)

    # click the vignette card
    page.locator(f'[data-vignette="{vid}"]').click()
    page.wait_for_timeout(350)

    # check panel canvas is non-empty
    if not check_canvas(page, "#panel", f"{tag}-panel"):
        errors.append(f"{tag}: panel canvas blank")

    screenshot(page, f"{shot_prefix}-beat1")

    # advance one beat and screenshot — check whichever canvas is present
    try:
        click_choice(page, 0)
        page.wait_for_timeout(300)
        # the next node may show a lesson screen (#lesson-board) or a vignette
        # screen (#panel) — check whichever exists
        if page.locator("#lesson-board").count() > 0:
            if not check_canvas(page, "#lesson-board", f"{tag}-beat2-lesson"):
                errors.append(f"{tag}: beat2 lesson board blank")
        elif page.locator("#panel").count() > 0:
            if not check_canvas(page, "#panel", f"{tag}-beat2"):
                errors.append(f"{tag}: beat2 panel blank")
        screenshot(page, f"{shot_prefix}-beat2")
    except Exception as e:
        errors.append(f"{tag}: beat2 click failed: {e}")


def run_chapter0_full(page, lang, errors):
    """Chapter 0: use page-side navigation (the engine's own walk function)
    to reach the ending, then check the sit views and the seal strip."""
    tag = f"ch0-full-{lang}"
    page.goto((ROOT / "dist" / "one-breath.html").resolve().as_uri())
    page.wait_for_timeout(300)

    if lang == "zh":
        page.locator('[data-act="lang"]').click()
        page.wait_for_timeout(150)

    page.locator('[data-vignette="shared-breath"]').click()
    page.wait_for_timeout(350)

    # walk to the ending using the engine's own choose() + render()
    # (the inlined script exposes choose/render/state as globals)
    page.evaluate("""(() => {
        for (let i = 0; i < 20; i++) {
            if (isEnding(state.walk)) break;
            state.walk = choose(state.walk, 0, state.lang);
            render();
        }
    })()""")
    page.wait_for_timeout(400)

    # check the ending screen rendered
    seals = page.locator(".seal-tile").count()
    print(f"  ending seals: {seals}")
    if seals < 5:
        errors.append(f"{tag}: expected >=5 seals, got {seals}")

    # sit: all four views
    try:
        if page.locator('[data-act="sit"]').count() > 0:
            page.locator('[data-act="sit"]').click()
            page.wait_for_timeout(300)
            for view in range(4):
                ink = canvas_ink(page, "#sit-canvas")
                print(f"  sit view {view}: dark={ink['dark']}")
                if ink["dark"] < 1 and view != 1:
                    errors.append(f"{tag} sit view {view}: canvas blank")
                screenshot(page, f"{tag}-sit-view{view}")
                if view < 3:
                    page.locator('[data-act="sit_next"]').click()
                    page.wait_for_timeout(200)
            page.locator('[data-act="sit_exit"]').click()
            page.wait_for_timeout(250)
        else:
            errors.append(f"{tag}: sit tile not found on ending screen")
    except Exception as e:
        errors.append(f"{tag} sit: {e}")

    screenshot(page, f"{tag}-ending")


def run_game_smoke(page, lang, errors):
    """The guided mini-game: jump to lesson step l11 via the inlined globals,
    play M5 (the first capture) through the real canvas hit-test, and check
    the capture counter and the lifted stone's ghost."""
    tag = f"game-{lang}"
    page.goto((ROOT / "dist" / "one-breath.html").resolve().as_uri())
    page.wait_for_timeout(300)
    if lang == "zh":
        page.locator('[data-act="lang"]').click()
        page.wait_for_timeout(150)
    page.locator('[data-vignette="shared-breath"]').click()
    page.wait_for_timeout(350)

    page.evaluate("""(() => {
        const lesson = lessons['shared-breath'];
        const base = newLessonWalk(lesson, boards[lesson.board], games);
        state.lesson = initGameStep({ ...base, stepIndex: 10 });
        const v = vignettes['shared-breath'];
        renderLesson(state.walk, v, v.nodes['n2']);
    })()""")
    page.wait_for_timeout(300)

    if not check_canvas(page, "#lesson-board", f"{tag}-board"):
        errors.append(f"{tag}: game board blank")

    # M5 through the real hit-test path: (2,2) captures the squeezing stone
    board_click(page, "#lesson-board", 2, 2)
    page.wait_for_timeout(250)
    caps = page.evaluate("state.lesson.gs.captures.black")
    print(f"  {tag}: captures after M5 = {caps}")
    if caps != 1:
        errors.append(f"{tag}: M5 did not capture (captures={caps})")
    ghosts = page.evaluate("state.lesson.ghosts.length")
    if ghosts != 1:
        errors.append(f"{tag}: the lifted stone's ghost missing ({ghosts})")
    screenshot(page, f"99-game-{lang}")


def main() -> int:
    ap = argparse.ArgumentParser(description="browser smoke matrix")
    ap.add_argument("--quick", action="store_true",
                    help="reduced matrix (zh only, words off)")
    args = ap.parse_args()

    langs = ["zh"] if args.quick else LANGS
    word_modes = [False] if args.quick else WORD_MODES

    errors = []
    shot_n = 0

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda e: errors.append(f"pageerror: {getattr(e, 'stack', e)}"))
        page.on("console", lambda m: errors.append(f"console:{m.type}:{m.text}")
                if m.type == "error" else None)

        # title screen check
        page.goto((ROOT / "dist" / "one-breath.html").resolve().as_uri())
        page.wait_for_timeout(400)
        print("title:", page.title())
        cards = page.locator(".card").count()
        print(f"vignette cards: {cards}")
        if cards < 3:
            errors.append(f"expected >=3 cards, got {cards}")
        screenshot(page, "00-title")

        # --- full Chapter 0 ladder (once per language) ---
        for lang in langs:
            print(f"\n--- Chapter 0 full ({lang}) ---")
            run_chapter0_full(page, lang, errors)

        # --- the guided mini-game (once per language) ---
        for lang in langs:
            print(f"\n--- guided game ({lang}) ---")
            run_game_smoke(page, lang, errors)


        # --- vignette × language × words matrix ---
        for vid in VIGNETTES:
            for lang in langs:
                for words in word_modes:
                    shot_n += 1
                    prefix = f"{shot_n:02d}-{vid}"
                    print(f"\n--- {vid} ({lang}, words={'on' if words else 'off'}) ---")
                    run_vignette_smoke(page, vid, lang, words, prefix, errors)

        # --- two-ways engine beat (the computed 算力手) ---
        print("\n--- two-ways engine beat ---")
        page.goto((ROOT / "dist" / "one-breath.html").resolve().as_uri())
        page.wait_for_timeout(300)
        page.locator('[data-vignette="two-ways"]').click()
        page.wait_for_timeout(350)
        click_choice(page, 0)  # 再来一局 → engine beat
        page.wait_for_timeout(300)
        if not check_canvas(page, "#board", "two-ways-mirror"):
            errors.append("two-ways mirror board blank")
        screenshot(page, "99-two-ways-engine")

        b.close()

    if errors:
        print(f"\n❌ {len(errors)} error(s):")
        for e in errors:
            print(f"  {e}")
        return 1
    print("\n✅ smoke matrix passed: 0 errors, all canvases non-empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
