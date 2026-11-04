"""Probe 2: (a) does Chromium actually resolve the font families we claim,
(b) where are the variable fonts on disk. Layout/type routes must not silently
fall back to a default font -- that is the xkcd() failure mode found in audit."""
import glob
import hashlib
import json

# --- (b) disk scan for variable fonts (only the dirs that matter, keep it fast)
cands = []
for root in (r"C:\Windows\Fonts",
             str(glob.glob(r"C:\Users\data\AppData\Local\Microsoft\Windows\Fonts"))[0]
             if glob.glob(r"C:\Users\data\AppData\Local\Microsoft\Windows\Fonts") else None,
             r"C:\Users\data\.fonts"):
    if not root:
        continue
    for p in glob.glob(root + r"\*"):
        if p.lower().endswith((".ttf", ".otf", ".ttc")):
            cands.append(p)
print(f"font files on disk: {len(cands)}")

try:
    from fontTools.ttLib import TTFont
    vfs = []
    for p in cands:
        try:
            f = TTFont(p, lazy=True)
        except Exception:
            continue
        if "fvar" in f:
            axes = [(a.axisTag, a.minValue, a.maxValue) for a in f["fvar"].axes]
            vfs.append((p.split("\\")[-1], axes))
            f.close()
    print(f"variable fonts: {len(vfs)}")
    for n, a in vfs[:20]:
        print("   ", n, a)
except Exception as e:
    print("fontTools fail:", type(e).__name__, e)

# --- (a) what does the browser see
from playwright.sync_api import sync_playwright

JS = """
async () => {
  const fams = ['"Noto Sans SC"', '"Noto Sans"', '"Source Sans Pro"', '"Arial Black"',
                '"Arial"', '"Times New Roman"', '"KaiTi"', '"Microsoft YaHei"', '"Segoe UI"'];
  const out = {};
  const probe = (f) => {
    const s = document.createElement('span');
    s.style.cssText = 'position:absolute;font-size:100px;white-space:pre;font-family:' + f;
    s.textContent = 'Hamburgefons 網格';
    document.body.appendChild(s);
    const w = s.getBoundingClientRect().width;
    s.remove();
    return Math.round(w * 100) / 100;
  };
  for (const f of fams) out[f] = {width: probe(f), check: document.fonts.check('100px ' + f)};
  out['__monospace'] = probe('monospace');
  out['__sansserif_default'] = probe('sans-serif');
  out['__serif_default'] = probe('serif');
  return out;
}
"""
with sync_playwright() as p:
    b = p.chromium.launch(args=["--disable-gpu", "--font-render-hinting=none"])
    pg = b.new_page(viewport={"width": 480, "height": 320})
    pg.set_content("<!doctype html><meta charset=utf-8><body>")
    print(json.dumps(pg.evaluate(JS), indent=1, ensure_ascii=False))
    print("browser.version", b.version)
    b.close()
