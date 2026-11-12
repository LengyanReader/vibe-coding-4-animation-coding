#!/usr/bin/env python3
"""Simulated-persona walkthrough of the built One Breath artifact.

This is NOT human-subject evidence. It scripts six fictional players through the
real UI (the same clicks a person would make), measures the scripted interaction
time, counts the reading/decision load, captures screenshots, and records what
the interface actually exposes. It cannot prove comprehension, non-moralization
or real duration; S1-S3 remain open. The value is finding flow, layout and
accessibility defects before a real player sits down.

Run: python tools/human_sim.py
Out: outputs/human-sim/<persona>/*.png  +  outputs/human-sim/results.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "human-sim"
OUT.mkdir(parents=True, exist_ok=True)
CONTENT = json.loads((ROOT / "dist" / "content.json").read_text(encoding="utf-8"))
LESSON = CONTENT["lessons"]["shared-breath"]
GAME = CONTENT["games"]["guided-game"]
BOARD_W = 420

# the authored points the driver follows (the visible rule lines teach them)
LIBERTIES = {
    "l1_breath": [[2, 3], [3, 2], [3, 4], [4, 3]],
    "l2_chain": [[2, 2], [2, 3], [3, 1], [3, 4], [4, 2], [4, 3]],
}

PERSONAS = [
    {"id": "beginner-zh", "viewport": [1280, 900], "lang": "zh", "words": False,
     "reduced": False, "mode": "core", "ending": 1, "beginner": True,
     "note": "first-time player, Chinese, wordless, one deliberate wrong click"},
    {"id": "beginner-en", "viewport": [1280, 900], "lang": "en", "words": True,
     "reduced": False, "mode": "core", "ending": 2, "beginner": False,
     "note": "first-time player, English, words on"},
    {"id": "goliterate-zh", "viewport": [1280, 900], "lang": "zh", "words": True,
     "reduced": False, "mode": "full", "ending": 4, "beginner": False,
     "note": "Go-literate player, full ladder + all optional steps"},
    {"id": "mentor-fast", "viewport": [1280, 900], "lang": "zh", "words": True,
     "reduced": False, "mode": "skip", "ending": 0, "beginner": False,
     "note": "impatient mentor, skips the teaching act entirely"},
    {"id": "mobile-zh", "viewport": [390, 844], "lang": "zh", "words": False,
     "reduced": False, "mode": "core", "ending": 3, "beginner": True,
     "note": "phone-sized first-time player, core path"},
    {"id": "reduced-zh", "viewport": [1280, 900], "lang": "zh", "words": True,
     "reduced": True, "mode": "core", "ending": 0, "beginner": False,
     "note": "reduced-motion player, core path"},
]


def wait(page, ms=140):
    page.wait_for_timeout(ms)


def shot(page, persona, name):
    d = OUT / persona["id"]
    d.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(d / f"{name}.png"), full_page=True)


def text(page, sel):
    loc = page.locator(sel)
    return loc.inner_text().strip() if loc.count() else ""


def board_click(page, selector, r, c, size=5):
    loc = page.locator(selector)
    loc.scroll_into_view_if_needed()      # a human scrolls the board into view
    wait(page, 80)
    box = loc.bounding_box()
    if not box:
        raise RuntimeError(f"no bounding box for {selector}")
    pad = BOARD_W * 0.105
    cell = (BOARD_W - pad * 2) / (size - 1)
    x = pad + (c - 1) * cell
    y = pad + (r - 1) * cell
    page.mouse.click(box["x"] + x * (box["width"] / BOARD_W),
                     box["y"] + y * (box["height"] / BOARD_W))
    wait(page)


def act(page, name):
    page.locator(f'[data-act="{name}"]').first.click()
    wait(page)


def choice(page, index):
    page.locator(f'[data-choice="{index}"]').first.click()
    wait(page)


def set_ui(page, persona):
    if page.evaluate("state.lang") != persona["lang"]:
        act(page, "lang")
    if page.evaluate("state.wordsOn") != persona["words"]:
        act(page, "words")
    if page.evaluate("state.reducedMotion") != persona["reduced"]:
        act(page, "motion")


def canvas_ink(page, selector):
    return page.evaluate(
        """(sel) => {
            const c = document.querySelector(sel);
            if (!c) return { dark: -1, total: 0 };
            const ctx = c.getContext('2d');
            const d = ctx.getImageData(0, 0, c.width, c.height).data;
            let non = 0;
            for (let i = 0; i < d.length; i += 4) {
                if (Math.abs(d[i] - 251) > 25 || Math.abs(d[i+1] - 246) > 25 || Math.abs(d[i+2] - 234) > 25) non++;
            }
            return { dark: non, total: c.width * c.height };
        }""", selector)


def overflow(page):
    return page.evaluate(
        """() => {
            const bad = [];
            for (const el of document.querySelectorAll('body *')) {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.right > window.innerWidth + 1) {
                    bad.push((el.id || el.className || el.tagName).toString().slice(0, 48));
                }
            }
            return { scrollWidth: document.documentElement.scrollWidth,
                     innerWidth: window.innerWidth, offenders: bad.slice(0, 6) };
        }""")


def open_chapter(page, persona, errors):
    page.locator('[data-vignette="shared-breath"]').first.click()
    wait(page, 250)
    shot(page, persona, "n1-corridor")
    choice(page, 0)                    # n1 → n2 (the lesson node)
    wait(page, 250)
    return page.locator("#lesson-board").count() == 1


def play_game(page, persona, errors, checks):
    moves = GAME["moves"]
    for m in moves:
        if not m.get("learner"):
            continue
        if m["at"] is None:
            act(page, "lesson_pass")
            wait(page, 220)
            break
        if persona["beginner"] and m["num"] == 5:
            board_click(page, "#lesson-board", 3, 3)       # off-script legal
            checks["hint_redirect"] = ("Grandpa" in text(page, ".lesson-message")) or ("爷爷" in text(page, ".lesson-message"))
            shot(page, persona, "game-hint")
        board_click(page, "#lesson-board", *m["at"])
        wait(page, 120)
    checks["game_result_land"] = ("land" in text(page, ".lesson-result").lower()) or ("地" in text(page, ".lesson-result"))
    checks["game_result_no_winner"] = not any(
        w in text(page, ".lesson-result").lower() for w in ("winner", "loser", "win ", "lose "))
    shot(page, persona, "game-result")


def play_lesson(page, persona, errors, checks):
    for step in LESSON["steps"]:
        sid, kind = step["id"], step["kind"]
        if persona["mode"] == "core" and not step["core"]:
            act(page, "lesson_step_skip")
            checks.setdefault("skipped", []).append(sid)
            continue
        if kind == "liberties":
            if persona["beginner"] and sid == "l1_breath":
                board_click(page, "#lesson-board", 1, 1)
                checks["not_liberty_message"] = bool(text(page, ".lesson-message"))
            for p in LIBERTIES[sid]:
                board_click(page, "#lesson-board", *p)
        elif kind == "play":
            if persona["beginner"] and sid == "l3_capture":
                board_click(page, "#lesson-board", 1, 2)
                checks["no_capture_message"] = bool(text(page, ".lesson-message"))
            board_click(page, "#lesson-board", *step["solution"])
        elif kind == "refuse":
            for p in (step.get("points") or [step["point"]]):
                board_click(page, "#lesson-board", *p)
                wait(page, 100)
        elif kind == "mutual":
            board_click(page, "#lesson-board", *step["corridor"][0])
            checks["corridor_two_breaths"] = "2" in text(page, ".lesson-message")
            act(page, "lesson_pass")
        elif kind == "pass":
            act(page, "lesson_pass")
        elif kind == "game":
            play_game(page, persona, errors, checks)
        wait(page, 100)
        if page.locator('[data-act="lesson_next"]').count():
            act(page, "lesson_next")
        else:
            errors.append(f"{persona['id']}: no continue after {sid}")
            return
    checks["lesson_reached_compare"] = page.locator("#compare-board").count() == 1


def compare(page, persona, errors, checks):
    board_click(page, "#compare-board", 1, 1)      # which chain is you
    wait(page, 180)
    board_click(page, "#compare-board", 3, 2)      # a shared corridor point
    wait(page, 180)
    msg = text(page, ".lesson-prompt")
    checks["compare_shared"] = "4" in msg or "shared" in msg.lower() or "共用" in msg
    shot(page, persona, "compare")
    page.locator('[data-act="compare_continue"]').click()
    wait(page, 220)


def release_sit_respond(page, persona, errors, checks):
    choice(page, 0)                                 # n4: put it down
    wait(page, 200)
    for _ in range(3):
        act(page, "sit_next")
    shot(page, persona, "sit-view4")
    checks["sit_views"] = page.locator(".sit-dot").count() == 4
    act(page, "sit_graph_exit")
    wait(page, 220)
    choice(page, persona["ending"])                 # n6: one of five responses
    wait(page, 250)
    checks["ending_seals"] = page.locator(".seal-tile").count()
    checks["ending_no_score"] = not any(
        w in page.locator("#screen").inner_text().lower()
        for w in ("harmony", "rating", "points:", "score:"))
    shot(page, persona, "ending")
    act(page, "sit")
    wait(page, 220)
    checks["ending_sit_canvas"] = canvas_ink(page, "#sit-canvas")["dark"] > 100
    act(page, "sit_next")
    act(page, "sit_exit")
    wait(page, 180)


def keyboard_probe(page):
    """A keyboard-only player cannot play a canvas. Record the fact, not a verdict."""
    board = page.locator("#lesson-board")
    if not board.count():
        return {"board": False}
    return page.evaluate(
        """() => {
            const c = document.querySelector('#lesson-board');
            const focusables = [...document.querySelectorAll('button, [tabindex]')];
            return { canvasTabIndex: c.tabIndex,
                     canvasHasTabindexAttr: c.hasAttribute('tabindex'),
                     focusableCount: focusables.length };
        }""")


def run(browser, persona):
    errors = []
    checks = {}
    ctx = browser.new_context(viewport={"width": persona["viewport"][0],
                                        "height": persona["viewport"][1]})
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console:{m.type}:{m.text}")
            if m.type == "error" else None)
    seg = {}
    t_all = time.perf_counter()
    page.goto((ROOT / "dist" / "one-breath.html").resolve().as_uri())
    wait(page, 450)
    set_ui(page, persona)
    shot(page, persona, "title")
    checks["title_overflow"] = overflow(page)

    t = time.perf_counter()
    if not open_chapter(page, persona, errors):
        errors.append(f"{persona['id']}: lesson screen did not open")
    seg["open_chapter"] = time.perf_counter() - t
    if page.locator("#lesson-board").count():
        first_step = text(page, ".lesson-step")
        shot(page, persona, "lesson-first")
        checks["keyboard"] = keyboard_probe(page)
        checks["lesson_overflow"] = overflow(page)
        if persona["mode"] == "skip":
            act(page, "lesson_skip")
            wait(page, 250)
            checks["mentor_skipped_lesson"] = page.locator("#compare-board").count() == 1
        else:
            t = time.perf_counter()
            play_lesson(page, persona, errors, checks)
            seg["lesson"] = time.perf_counter() - t
    t = time.perf_counter()
    if page.locator("#compare-board").count():
        compare(page, persona, errors, checks)
        checks["compare_overflow"] = overflow(page)
    else:
        errors.append(f"{persona['id']}: compare screen not reached")
    seg["compare"] = time.perf_counter() - t
    t = time.perf_counter()
    release_sit_respond(page, persona, errors, checks)
    seg["release_sit_respond"] = time.perf_counter() - t
    seg["total"] = time.perf_counter() - t_all
    checks["ending_overflow"] = overflow(page)
    checks["page_errors"] = list(errors)
    result = {
        "id": persona["id"], "note": persona["note"], "lang": persona["lang"],
        "viewport": persona["viewport"], "mode": persona["mode"],
        "segments_seconds": {k: round(v, 2) for k, v in seg.items()},
        "checks": checks, "errors": errors,
    }
    ctx.close()
    return result


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for persona in PERSONAS:
            print(f"--- {persona['id']} ---")
            r = run(browser, persona)
            results.append(r)
            print(json.dumps({"segments": r["segments_seconds"],
                              "checks": {k: v for k, v in r["checks"].items()
                                         if k not in ("title_overflow", "lesson_overflow")},
                              "errors": r["errors"]}, ensure_ascii=False, indent=1))
        browser.close()
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    print(f"results: {OUT / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())