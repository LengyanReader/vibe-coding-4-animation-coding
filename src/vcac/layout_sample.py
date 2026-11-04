"""Layout route sample — a Swiss-grid poster painted by a browser, gated by DOM geometry.

Why this case exists (docs/styles.md §10 + docs/tools.md §0.2): a design movement
is not a mood, it is a verifiable 4-tuple — palette + grid + type-pair + motif.
So "make it look Swiss" is *testable*: every text block's left edge must land on
the column field, every top edge on the baseline grid, the declared palette must
stay small, and the pixels must actually be those colours.

The renderer is Chromium (a layout engine we did not write) and the instrument is
the browser's own ``getBoundingClientRect``: the route never grades its own
arithmetic. Two surfaces, one spec -- a raster PNG (the content hash) and a vector
PDF -- which is the point of treating HTML as a print medium.

Run:
    $env:PYTHONPATH="src"; python -m vcac.layout_sample specs/examples/swiss-poster.yaml
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import browser, ffmpeg, provenance, spec as spec_mod, validate

# Ask the layout engine where it actually put each block, then measure the error
# against the grid the spec declared. Offsets are absolute px, worst case per axis.
# "Overflow" is deliberately strict: a block that leaves the canvas *or* outgrows
# the column span it declared is a grid failure, and a shrink-wrapped block reports
# its real text advance, so overlong copy cannot hide behind an explicit width.
GEOMETRY_JS = """
(args) => {
  const cols = args.columnXs, base = args.baseline, org = args.originY;
  const W = args.width, H = args.height;
  const near = (v, xs) => xs.reduce((b, x) => Math.abs(x - v) < Math.abs(b - v) ? x : b, xs[0]);
  let worstLeft = 0, worstTop = 0, overflow = 0;
  const blocks = [];
  for (const el of document.querySelectorAll('[data-grid]')) {
    const r = el.getBoundingClientRect();
    const dl = Math.abs(r.left - near(r.left, cols));
    const dt = Math.abs(r.top - (org + Math.round((r.top - org) / base) * base));
    worstLeft = Math.max(worstLeft, dl);
    worstTop = Math.max(worstTop, dt);
    const right = parseFloat(el.getAttribute('data-right'));
    const out = r.left < -0.01 || r.top < -0.01 || r.bottom > H + 0.01
             || (Number.isFinite(right) && r.right > right + 0.01);
    if (out) overflow++;
    blocks.push({id: el.getAttribute('data-grid'), left: r.left, top: r.top,
                 right: r.right, bottom: r.bottom,
                 spanRight: Number.isFinite(right) ? right : null,
                 leftOffset: Math.round(dl * 1000) / 1000,
                 topOffset: Math.round(dt * 1000) / 1000, outside: out});
  }
  return {worstLeft, worstTop, overflow, blocks};
}
"""


class LayoutError(ValueError):
    pass


def _grid(spec_dict: dict) -> dict:
    """Derive the column field. Non-integer column widths are refused, not rounded:
    a rounded grid is a poster that quietly fails its own acceptance rule."""
    cw = int(spec_dict["canvas"]["width"])
    ch = int(spec_dict["canvas"]["height"])
    g = spec_dict["grid"]
    cols, gutter, margin, baseline = (int(g["columns"]), int(g["gutter"]),
                                      int(g["margin"]), int(g["baseline"]))
    usable = cw - 2 * margin - (cols - 1) * gutter
    if usable <= 0 or usable % cols:
        raise LayoutError(
            f"grid does not divide evenly: canvas {cw}, margin {margin}, "
            f"gutter {gutter}, columns {cols} -> {usable}px left for {cols} columns")
    col_w = usable // cols
    return {"width": cw, "height": ch, "cols": cols, "col_w": col_w,
            "gutter": gutter, "margin": margin, "baseline": baseline,
            "column_xs": [margin + i * (col_w + gutter) for i in range(cols)],
            "origin_y": margin}


def _size(step: int, base_px: float, ratio: float) -> int:
    return round(base_px * (ratio ** step))


def build_html(spec_dict: dict, grid: dict) -> str:
    """Deterministic HTML: no clock, no RNG, no network. Every colour and every
    coordinate in here comes from the spec, which is what makes the acceptance
    rules about *this string* meaningful."""
    pal = spec_dict["palette"]
    ty = spec_dict["type"]
    ratio, base_px = float(ty["scale_ratio"]), float(ty["base_px"])
    paper, ink = pal["paper"], pal["ink"]

    def font_of(kind_cfg: dict) -> str:
        return (f"font-family:'{kind_cfg['family']}',{kind_cfg.get('fallback', 'sans-serif')};"
                f"font-weight:{int(kind_cfg.get('weight', 400))}")

    parts = [
        "<!doctype html><meta charset=utf-8>",
        "<style>",
        "html,body{margin:0;padding:0;overflow:hidden}",
        f"body{{position:relative;width:{grid['width']}px;height:{grid['height']}px;"
        f"background:{paper}}}",
        ".b{position:absolute;white-space:pre;line-height:1;margin:0;padding:0}",
        "</style><body>",
    ]
    declared = {paper.upper(), ink.upper(), str(pal.get("accent", "")).upper()}
    for i, blk in enumerate(spec_dict["blocks"]):
        kind = blk.get("kind", "text")
        fcfg = ty["display"] if kind == "display" else ty["text"]
        col, span = int(blk["col"]), int(blk.get("span", 1))
        x = grid["column_xs"][col]
        w = (grid["col_w"] + grid["gutter"]) * span - grid["gutter"]
        y = grid["origin_y"] + int(blk["row"]) * grid["baseline"]
        px = _size(int(blk.get("step", 0)), base_px, ratio)
        colour = blk.get("color", "ink")
        hexv = pal[colour] if colour in pal else colour
        declared.add(hexv.upper())
        ident = blk.get("id", f"b{i}")
        # An optical nudge is a real typographic act (a cap sitting on a rule wants
        # to be moved a pixel or two off the mathematically exact position). It is
        # declared, not hidden in the renderer -- and the geometry gate still reads
        # the browser's answer, so a nudge that misses the grid fails the poster.
        dx = float(blk.get("nudge_px", {}).get("dx", 0))
        dy = float(blk.get("nudge_px", {}).get("dy", 0))
        x += dx
        y += dy
        # a motif is geometry on the grid, so a rule/bar is a block with no text
        if kind == "rule":
            style = (f"left:{x}px;top:{y}px;width:{w}px;height:{int(blk.get('height', grid['baseline']))}px;"
                     f"background:{hexv}")
            parts.append(f'<div class=b data-grid="{ident}" data-right="{x + w}" '
                         f'style="{style}"></div>')
        else:
            # no width on a text block: it shrink-wraps, so getBoundingClientRect()
            # reports the real text advance and overlong copy cannot hide.
            style = (f"left:{x}px;top:{y}px;font-size:{px}px;"
                     f"color:{hexv};{font_of(fcfg)}")
            parts.append(f'<div class=b data-grid="{ident}" data-right="{x + w}" '
                         f'style="{style}">{blk["text"]}</div>')
    parts.append("</body>")
    grid["declared_colors"] = sorted(c for c in declared if c.startswith("#"))
    return "".join(parts)


def _palette_exact_pct(png: bytes, declared: list[str]) -> float:
    """How much of the bitmap is a *flat* declared colour. Everything else is
    grayscale antialiasing on glyph edges -- so this measures the claim 'this
    poster uses only these colours' against pixels instead of against CSS."""
    img = Image.open(io.BytesIO(png)).convert("RGB")
    px = np.asarray(img).reshape(-1, 3)
    want = np.array([spec_mod.parse_hex(c) for c in declared], dtype=np.uint8)
    hit = (px[:, None, :] == want[None, :, :]).all(-1).any(-1)
    return float(hit.mean() * 100.0)


def render(spec_dict: dict) -> bytes:
    grid = _grid(spec_dict)
    html = build_html(spec_dict, grid)
    with browser.BrowserRender() as br:
        return br.render_png(html, grid["width"], grid["height"])


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, detail = browser.availability()
    if not ok:
        raise RuntimeError(f"layout route needs a browser rasterizer: {detail}")

    grid = _grid(spec_dict)
    html = build_html(spec_dict, grid)
    with browser.BrowserRender() as br:
        png = br.render_png(html, grid["width"], grid["height"])
        geo = br.measure(html, GEOMETRY_JS, grid["width"], grid["height"], args={
            "columnXs": grid["column_xs"], "baseline": grid["baseline"],
            "originY": grid["origin_y"], "width": grid["width"], "height": grid["height"]})
        fams = sorted({spec_dict["type"]["display"]["family"],
                       spec_dict["type"]["text"]["family"]})
        fonts = br.measure(html, browser.FONT_FINGERPRINT_JS,
                           grid["width"], grid["height"],
                           args={"families": fams, "probe": "Hamburgefons 網格"})
        pdf = br.render_pdf(html, out_dir / "poster.pdf", grid["width"], grid["height"])
        png2 = br.render_png(html, grid["width"], grid["height"])
        version = br.version

    poster = out_dir / "poster.png"
    poster.write_bytes(png)

    declared = grid["declared_colors"]
    measured = {
        "width": grid["width"], "height": grid["height"],
        "left_edge_max_offset_px": geo["worstLeft"],
        "baseline_max_offset_px": geo["worstTop"],
        "palette_distinct_colors": len(declared),
        "palette_exact_pct": _palette_exact_pct(png, declared),
        "overflow_elements": geo["overflow"],
        "fonts_unresolved": [f["family"] for f in fonts["families"] if not f["resolved"]],
        "deterministic": provenance.sha256_bytes(png) == provenance.sha256_bytes(png2),
    }
    report = validate.run_acceptance(spec_dict["acceptance"], measured)
    report["measured"] = measured
    report["rasterizer"] = {"browser": version, "args": browser.LAUNCH_ARGS,
                            "interpreter": detail}
    report["grid"] = {k: grid[k] for k in ("cols", "col_w", "gutter", "margin", "baseline")}
    report["geometry"] = {"worstLeft": geo["worstLeft"], "worstTop": geo["worstTop"],
                          "blocks": geo["blocks"]}
    report["fonts"] = fonts
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    chash = provenance.sha256_bytes(png)
    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict, content_hash=chash,
        artifact_hashes={"poster.png": provenance.sha256_file(poster),
                         # container hash for information only: the PDF carries a
                         # production date, so it is never the reproducibility anchor
                         "poster.pdf": provenance.sha256_file(pdf)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["poster.png", "poster.pdf", "report.json", "manifest.json"],
        notes=list(spec_dict.get("assumptions", [])) + [
            "content hash = PNG pixels; PDF is a convenience vector surface",
            "font resolution is inferred from glyph-advance geometry, not from "
            "document.fonts.check(), which reports true for substituted system fonts",
        ],
        pipeline="vcac-layout/0.1",
        extra={"fonts": [{"family": f["family"], "resolved": f["resolved"],
                          "advance_px": f["width"], "fell_back_to": f["fell_back_to"]}
                         for f in fonts["families"]],
               "rasterizer": {"name": "chromium", "version": version,
                              "flags": browser.LAUNCH_ARGS}})
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="vcac layout route sample (browser rasterizer)")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    spec_dict = spec_mod.load_raw(a.spec)
    out_dir = a.out or (Path("outputs") / spec_dict["id"])
    r = run(a.spec, out_dir)
    rep, m = r["report"], r["report"]["measured"]
    print(f"[vcac:layout] {spec_dict['id']} -> {r['out_dir']}")
    print(f"[vcac:layout] {m['width']}x{m['height']} "
          f"grid_err L={m['left_edge_max_offset_px']:.3f}px T={m['baseline_max_offset_px']:.3f}px "
          f"palette={m['palette_distinct_colors']}c exact={m['palette_exact_pct']:.2f}% "
          f"overflow={m['overflow_elements']} chromium={rep['rasterizer']['browser']}")
    for c in rep["checks"]:
        extra = (f"  (exp {c.get('expected')}, act {c.get('actual')})"
                 if c["status"] in ("pass", "fail") else f"  ({c.get('reason','')})")
        print(f"  [{c['status'].upper():7}] {c['id']}{extra}")
    print(f"[vcac:layout] run_id={r['manifest']['run_id']}")
    print(f"[vcac:layout] ACCEPTANCE {'PASSED' if rep['passed'] else 'FAILED'}")
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
