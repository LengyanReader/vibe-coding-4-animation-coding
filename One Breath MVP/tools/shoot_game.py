#!/usr/bin/env python3
"""Screenshots of the guided mini-game (Chapter 0, lesson step l11) for visual
acceptance. Uses the inlined bundle's own globals to jump straight to the game
step, then plays a few moves through the real clickPoint runtime."""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "_smoke"
OUT.mkdir(parents=True, exist_ok=True)

JUMP = """(() => {
  const lesson = lessons['shared-breath'];
  const base = newLessonWalk(lesson, boards[lesson.board], games);
  state.lesson = initGameStep({ ...base, stepIndex: 10 });
  const v = vignettes['shared-breath'];
  renderLesson(state.walk, v, v.nodes['n2']);
})()"""

PLAY = """((pts) => {
  const v = vignettes['shared-breath'];
  for (const p of pts) {
    state.lesson = clickPoint(state.lesson, p).walk;
    renderLesson(state.walk, v, v.nodes['n2']);
  }
})"""


def board_click(page, r, c):
    box = page.locator("#lesson-board").bounding_box()
    size, width = 5, 420
    pad = width * 0.105
    cell = (width - pad * 2) / (size - 1)
    x = pad + (c - 1) * cell
    y = pad + (r - 1) * cell
    page.mouse.click(box["x"] + x * (box["width"] / width),
                     box["y"] + y * (box["height"] / width))


def main() -> int:
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.goto((ROOT / "dist" / "one-breath.html").resolve().as_uri())
        page.wait_for_timeout(400)

        page.screenshot(path=str(OUT / "v2-title.png"), full_page=True)

        # the first lesson step (rules class), then the game step
        page.locator('[data-vignette="shared-breath"]').click()
        page.wait_for_timeout(350)
        page.locator('[data-choice="0"]').first.click()
        page.wait_for_timeout(350)
        page.screenshot(path=str(OUT / "v2-lesson-l1.png"), full_page=True)

        page.evaluate(JUMP)
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "v2-game-start.png"), full_page=True)

        # play M5 (the first capture) through the real UI
        board_click(page, 2, 2)
        page.wait_for_timeout(250)
        page.screenshot(path=str(OUT / "v2-game-m5-capture.png"), full_page=True)

        # two more exchanges
        board_click(page, 1, 2)
        page.wait_for_timeout(200)
        board_click(page, 3, 2)
        page.wait_for_timeout(250)
        page.screenshot(path=str(OUT / "v2-game-mid.png"), full_page=True)

        # the chase to the four-stone capture
        for (r, c) in [(4, 2), (5, 2)]:
            board_click(page, r, c)
            page.wait_for_timeout(200)
        page.screenshot(path=str(OUT / "v2-game-chase.png"), full_page=True)

        # finish the game: M15, M17, M19, then the closing double pass
        for (r, c) in [(4, 1), (2, 1), (2, 3)]:
            board_click(page, r, c)
            page.wait_for_timeout(180)
        page.locator('[data-act="lesson_pass"]').click()
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "v2-game-result.png"), full_page=True)

        # the mirror board on a story screen + the sit view, for palette check
        page.locator('[data-act="lesson_next"]').click()
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "v2-after-game.png"), full_page=True)

        b.close()

    if errors:
        print("❌", errors)
        return 1
    print("✅ game screenshots written to outputs/_smoke/v2-*.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
