"""Probe 3: name the real families behind the files we want to use, and prove
that Pillow can render an instancer-pinned weight axis from memory (no temp file)."""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

PICKS = ["NotoSansSC-VF.ttf", "bahnschrift.ttf", "SourceSansPro", "NotoSerifSC-VF.ttf"]
roots = [r"C:\Windows\Fonts", r"C:\Users\data\AppData\Local\Microsoft\Windows\Fonts"]
found = {}
for root in roots:
    for p in Path(root).glob("*"):
        if p.suffix.lower() in (".ttf", ".otf", ".ttc"):
            for k in PICKS:
                if k.lower() in p.name.lower() and k not in found:
                    found[k] = p
for k, p in found.items():
    f = TTFont(p, lazy=True)
    name = f["name"]
    fam = name.getDebugName(1) or name.getDebugName(16)
    sub = name.getDebugName(2) or name.getDebugName(17)
    axes = [(a.axisTag, a.minValue, a.maxValue, a.defaultValue) for a in f["fvar"].axes] if "fvar" in f else None
    print(f"{p}  family={fam!r} sub={sub!r} axes={axes}")

# --- Pillow memory render at three pinned weights
from PIL import Image, ImageDraw, ImageFont
import io

vf = found.get("NotoSansSC-VF.ttf")
if vf:
    base = TTFont(vf)
    for w in (100, 500, 900):
        inst = instancer.instantiateVariableFont(base, {"wght": w}, inplace=False)
        buf = io.BytesIO()
        inst.flavor = None            # force a static TTF stream, no temp file
        inst.save(buf)
        buf.seek(0)
        font = ImageFont.truetype(buf, 72)
        img = Image.new("L", (420, 110), 0)
        ImageDraw.Draw(img).text((10, 10), "網格 GRID 重量", font=font, fill=255)
        ink = sum(1 for px in img.tobytes() if px > 0)
        print(f"  wght={w:4d} ink_pixels={ink} bytes={buf.getbuffer().nbytes} fontname={font.getname()}")
