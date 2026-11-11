#!/usr/bin/env python3
"""Ad-hoc browser smoke test for dist/one-breath.html (Playwright, dev-only).
Checks Chapter 0 end to end plus the two existing cases, and samples canvas
pixels so a blank canvas cannot pass. Screenshots go to outputs/_smoke/."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "_smoke"
OUT.mkdir(parents=True, exist_ok=True)


def board_click(page, selector, r, c, size=5, width=420):
    box = page.locator(selector).bounding_box()
    pad = width * 0.09
    cell = (width - pad * 2) / (size - 1)
    x = pad + (c - 1) * cell
    y = pad + (r - 1) * cell
    page.mouse.click(box["x"] + x * (box["width"] / width),
                     box["y"] + y * (box["height"] / width))


def canvas_ink(page, selector):
    return page.evaluate(
        """(sel) => {
            const c = document.querySelector(sel);
            const ctx = c.getContext('2d');
            const d = ctx.getImageData(0, 0, c.width, c.height).data;
            let dark = 0;
            for (let i = 0; i < d.length; i += 4) {
                if (d[i] < 90 && d[i+1] < 90 && d[i+2] < 90) dark++;
            }
            return { dark, total: c.width * c.height };
        }""", selector)


def main() -> int:
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(f"console:{m.type}:{m.text}")
                if m.type == "error" else None)
        page.goto((ROOT / "dist" / "one-breath.html").resolve().as_uri())
        page.wait_for_timeout(400)
        print("title:", page.title())
        print("cards:", page.locator(".card").count())
        page.screenshot(path=str(OUT / "01-title.png"), full_page=True)

        # Chapter 0
        page.click('[data-vignette="shared-breath"]')
        page.wait_for_timeout(300)
        page.click('[data-choice="0"]')          # n1 → n2 (the lesson node)
        page.wait_for_timeout(350)
        print("lesson rule:", page.locator(".lesson-rule").inner_text()[:60])
        print("lesson canvas:", canvas_ink(page, "#lesson-board"))
        page.screenshot(path=str(OUT / "02-lesson.png"), full_page=True)
        for pt in [(2, 3), (3, 2), (3, 4), (4, 3)]:
            board_click(page, "#lesson-board", *pt)
            page.wait_for_timeout(60)
        print("lesson message:", page.locator(".lesson-message").inner_text())
        print("continue visible:", page.locator('[data-act="lesson_next"]').count())
        page.screenshot(path=str(OUT / "03-lesson-done.png"), full_page=True)
        page.click('[data-act="lesson_next"]')
        page.wait_for_timeout(200)
        page.click('[data-act="lesson_skip"]')
        page.wait_for_timeout(300)

        # comparison
        print("compare:", page.locator("#compare-board").count())
        board_click(page, "#compare-board", 1, 1)
        page.wait_for_timeout(150)
        board_click(page, "#compare-board", 3, 2)
        page.wait_for_timeout(150)
        print("compare message:", page.locator(".lesson-prompt").inner_text())
        page.screenshot(path=str(OUT / "04-compare.png"), full_page=True)
        page.click('[data-act="compare_continue"]')
        page.wait_for_timeout(250)

        # release → sit
        page.click('[data-choice="0"]')
        page.wait_for_timeout(250)
        print("sit canvas:", canvas_ink(page, "#sit-canvas"))
        page.screenshot(path=str(OUT / "05-sit.png"), full_page=True)
        page.click('[data-act="sit_next"]')
        page.wait_for_timeout(150)
        page.click('[data-act="sit_graph_exit"]')
        page.wait_for_timeout(250)

        # respond → ending
        page.click('[data-choice="2"]')
        page.wait_for_timeout(300)
        print("ending seals:", page.locator(".seal-tile").count())
        page.screenshot(path=str(OUT / "06-ending.png"), full_page=True)

        # existing case still opens
        page.click('[data-act="title"]')
        page.wait_for_timeout(200)
        page.click('[data-vignette="two-sides"]')
        page.wait_for_timeout(250)
        print("two-sides panel:", canvas_ink(page, "#panel"))
        page.screenshot(path=str(OUT / "07-two-sides.png"), full_page=True)
        b.close()
    print("errors:", errors)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())