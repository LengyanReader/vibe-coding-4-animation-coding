"""Chromium as a deterministic rasterizer + layout engine (docs/tools.md §0.2).

The capability is *optional* and *interpreter-scoped*: playwright is installed in
one interpreter on this machine and absent from the conda env the golden manifests
came from. So every entry point here degrades loudly — ``available()`` reports why,
and callers turn a missing browser into a ``skipped`` acceptance check, never a
silent pass and never a fake render (M0.2).

Reproducibility contract, measured rather than assumed: three independent
interpreter launches of the pinned Chromium build produced a byte-identical PNG
(sha256 matched, 6595 B for a 480x320 page). The flags below are what makes that
true -- software rasterisation (no GPU-dependent glyph atlases), a fixed colour
profile, and no font hinting (hinting is a per-machine pixel grid fit).
"""
from __future__ import annotations

from pathlib import Path

# Flags that turn a browser into a *measurement instrument*. Anything that can
# vary with the host GPU, colour pipeline, or font-smoothing policy is pinned.
LAUNCH_ARGS = [
    "--disable-gpu",
    "--force-color-profile=srgb",
    "--font-render-hinting=none",
    "--hide-scrollbars",
    "--disable-lcd-text",
]


def availability() -> tuple[bool, str]:
    """(can render, detail). ``detail`` is the interpreter path when usable and the
    import error when not; it goes into the report so a skip stays auditable."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment dependent
        return False, f"playwright not importable in this interpreter: {exc}"
    import sys
    return True, sys.executable


class BrowserRender:
    """One headless Chromium held open for a batch of renders from one spec."""

    def __init__(self):
        ok, why = availability()
        if not ok:
            raise RuntimeError(why)
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(args=LAUNCH_ARGS)

    @property
    def version(self) -> str:
        return self._browser.version

    def render_png(self, html: str, width: int, height: int,
                   scale: float = 1.0) -> bytes:
        page = self._browser.new_page(
            viewport={"width": width, "height": height}, device_scale_factor=scale)
        try:
            page.set_content(html, wait_until="load")
            # Fonts are resolved and laid out before the shot; without this the
            # first paint can land before a late glyph fallback settles.
            page.evaluate("document.fonts.ready.then(() => true)")
            page.wait_for_timeout(50)
            return page.screenshot(type="png", clip={"x": 0, "y": 0,
                                                     "width": width, "height": height})
        finally:
            page.close()

    def render_pdf(self, html: str, out_pdf: Path, width_px: int, height_px: int) -> Path:
        """Vector surface from the same spec: layout -> PDF (print), not just pixels.
        Chromium only ships ``page.pdf()`` in headless mode, which launch() gives us."""
        page = self._browser.new_page(viewport={"width": width_px, "height": height_px})
        try:
            page.set_content(html, wait_until="load")
            page.evaluate("document.fonts.ready.then(() => true)")
            out_pdf.parent.mkdir(parents=True, exist_ok=True)
            page.pdf(path=str(out_pdf), print_background=True,
                     width=f"{width_px}px", height=f"{height_px}px",
                     margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
            return out_pdf
        finally:
            page.close()

    def measure(self, html: str, script: str, width: int, height: int,
                args=None) -> object:
        """Run DOM geometry measurement inside the same layout pass that painted
        the poster. The gate reads the *browser's* numbers, not our own arithmetic."""
        page = self._browser.new_page(viewport={"width": width, "height": height})
        try:
            page.set_content(html, wait_until="load")
            page.evaluate("document.fonts.ready.then(() => true)")
            return page.evaluate(script, args)
        finally:
            page.close()

    def close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._pw.stop()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# --- font resolution: prove the family in the spec is the family on the pixels --
# ``document.fonts.check()`` answers *true* for a system font even when the shaper
# fell back, so it cannot detect a substitution. Geometry can: measure one probe
# string in the target family and in each generic default. A family that fell back
# renders at exactly the generic's width. Same trick as the matplotlib ``xkcd()``
# silent-degradation finding in docs/coverage-audit.md §0, turned into a gate.
FONT_FINGERPRINT_JS = """
(args) => {
  const {families, probe} = args;
  const widthOf = (css) => {
    const s = document.createElement('span');
    s.style.cssText = 'position:absolute;left:0;top:0;white-space:pre;'
      + 'font-size:100px;line-height:1;font-family:' + css;
    s.textContent = probe;
    document.body.appendChild(s);
    const w = s.getBoundingClientRect().width;
    s.remove();
    return Math.round(w * 1000) / 1000;
  };
  const generics = {
    'sans-serif': widthOf('sans-serif'),
    'serif': widthOf('serif'),
    'monospace': widthOf('monospace'),
  };
  const out = [];
  for (const f of families) {
    const w = widthOf('"' + f + '"');
    const matched = Object.entries(generics).find(([, g]) => Math.abs(g - w) < 0.01);
    out.push({family: f, width: w,
              resolved: matched ? false : true,
              fell_back_to: matched ? matched[0] : null});
  }
  return {generics, families: out};
}
"""
