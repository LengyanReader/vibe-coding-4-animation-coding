"""Probe: is a Playwright Chromium screenshot reproducible ACROSS processes?

This is the load-bearing unknown for the layout route. A single process taking
two screenshots proves nothing (skia caches, same font caches). Two independent
interpreters launching their own browser and producing the same byte digest is
the claim we actually need. Prints the digest so the shell can diff them.
"""
import hashlib
import sys

HTML = """<!doctype html><meta charset=utf-8>
<style>
 html,body{margin:0;background:#F4F1EA}
 .c{position:absolute;left:80px;top:120px;font-family:'Noto Sans SC',sans-serif;
    font-size:56px;font-weight:700;color:#141414;letter-spacing:-1px}
 .r{position:absolute;left:80px;top:210px;width:200px;height:6px;background:#D6412C}
</style><div class=c>GRID 網</div><div class=r></div>
"""

out = sys.argv[1]
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(args=["--disable-gpu", "--force-color-profile=srgb",
                                "--font-render-hinting=none"])
    pg = b.new_page(viewport={"width": 480, "height": 320}, device_scale_factor=1)
    pg.set_content(HTML)
    pg.wait_for_timeout(80)
    png = pg.screenshot(type="png")
    b.close()

with open(out, "wb") as f:
    f.write(png)
print(f"bytes={len(png)} sha256={hashlib.sha256(png).hexdigest()}")
