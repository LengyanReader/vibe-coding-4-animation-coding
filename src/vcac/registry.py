"""Capability registry — what *this interpreter* can actually do (README §6.2).

The probe tables and probe functions moved here verbatim from
``scripts/doctor.py`` so that a planner or the pipeline executor can *import*
the registry instead of parsing doctor's stdout. ``scripts/doctor.py`` stays
the human-facing CLI over ``build_registry()`` and prints the same table.

The registry is **per-interpreter**: this machine has more than one Python
(C:\\Python313 = 3.13.5 on PATH, and conda env hy_py312 = 3.12.13), and their
package sets differ. Any "already installed" claim is interpreter-qualified;
``build_registry()`` is cheap to re-run per interpreter before believing it.
See docs/tools.md §0 / §0.2 for the human-readable tables, and
docs/coverage-audit.md §0 for the two-Python governance finding.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# module name -> (registry key, medium kind)
PY_MODULES = {
    "numpy": ("numpy", "core"),
    "scipy": ("scipy", "core"),
    "PIL": ("pillow", "image"),
    "cv2": ("opencv", "image"),
    "skimage": ("scikit-image", "image"),
    "matplotlib": ("matplotlib", "image/dataviz"),
    "cairosvg": ("cairosvg", "image/svg"),
    "resvg": ("resvg-py", "image/svg"),
    "pydantic": ("pydantic", "pipeline"),
    "yaml": ("pyyaml", "pipeline"),
    "jsonschema": ("jsonschema", "pipeline"),
    "typer": ("typer", "pipeline"),
    "rich": ("rich", "pipeline"),
    "hypothesis": ("hypothesis", "test"),
    "pytest": ("pytest", "test"),
    "music21": ("music21", "audio/symbolic"),
    "scamp": ("scamp", "audio/symbolic"),
    "soundfile": ("soundfile", "audio"),
    "librosa": ("librosa", "audio/analysis"),
    "pydub": ("pydub", "audio"),
    "mido": ("mido", "audio/midi"),
    "midiutil": ("midiutil", "audio/midi"),
    "moviepy": ("moviepy", "video"),
    "imageio": ("imageio", "video"),
    "manim": ("manim", "video/animation"),
    "pygame": ("pygame", "game"),
    "arcade": ("arcade", "game"),
    "pymunk": ("pymunk", "game/physics"),
    "trimesh": ("trimesh", "3d"),
    "moderngl": ("moderngl", "3d/shader"),
    "fontTools": ("fonttools", "image/typography"),
    "playwright": ("playwright", "image/browser-rasterizer"),
    "pypdf": ("pypdf", "docs/pdf"),
    "nbconvert": ("nbconvert", "docs/export"),
    "PIL.AvifImagePlugin": ("pillow-avif", "image/avif"),
    "PIL.ImageFont": ("pillow-imaging-font", "image/typography"),
}

# binary name -> (registry key, medium kind)
BINARIES = {
    "ffmpeg": ("ffmpeg", "video/assembly"),
    "ffprobe": ("ffprobe", "video/probe"),
    "blender": ("blender", "3d"),
    "lilypond": ("lilypond", "audio/score"),
    "fluidsynth": ("fluidsynth", "audio/synth"),
    "sox": ("sox", "audio/fx"),
    "sox_ng": ("sox_ng", "audio/fx"),
    "csound": ("csound", "audio/synth"),
    "scsynth": ("scsynth", "audio/synth"),
    "magick": ("imagemagick", "image"),
    "inkscape": ("inkscape", "image/svg"),
    "rsvg-convert": ("librsvg", "image/svg"),
    "openscad": ("openscad", "3d"),
    "godot": ("godot", "game"),
    "renpy": ("renpy", "game/narrative"),
    "love": ("love2d", "game"),
    "node": ("node", "js-runtime"),
    "npx": ("npx", "js-runtime"),
    "pandoc": ("pandoc", "docs"),
    "pdflatex": ("miktex-pdflatex", "docs/typeset"),
    "latexmk": ("miktex-latexmk", "docs/typeset"),
    "xelatex": ("miktex", "docs/typeset"),
    "potrace": ("potrace", "image/vectorize"),
    "dot": ("graphviz", "dataviz"),
    "gs": ("ghostscript", "docs/prepress"),
    "aseprite": ("aseprite", "game/assets"),
    "tiled": ("tiled", "game/assets"),
}

# Not on PATH on Windows, but installed at a known location: file-based probes.
KNOWN_PATHS = {
    r"C:\Program Files\Google\Chrome\Application\chrome.exe":
        ("chrome-headless", "image/browser-rasterizer"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe":
        ("msedge-headless", "image/browser-rasterizer"),
}

# Tools fetched by scripts/fetch_assets.py into the repo (gitignored,
# hash-locked). Repo-relative so the probe works from any cwd; the registry
# entry says `via: repo-tool` so a manifest can tell PATH installs and repo
# tools apart.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_TOOLS = {
    "fluidsynth": _REPO_ROOT / "assets" / "tools" / "fluidsynth" / "fluidsynth.exe",
}

# Windows trap: `convert` resolves to System32\convert.exe (the disk utility),
# NOT ImageMagick. That is why ImageMagick is probed as `magick` only.
TRAP_NAMES = ("convert", "ping", "curl", "timeout")


def probe_python(module: str):
    try:
        mod = importlib.import_module(module)
        return getattr(mod, "__version__", "?"), True
    except Exception:
        return None, False


def probe_binary(name: str):
    path = shutil.which(name)
    if not path:
        return None, False
    try:
        r = subprocess.run([path, "--version"], capture_output=True,
                           text=True, timeout=15)
        line = (r.stdout or r.stderr).splitlines()
        return (line[0][:100] if line else "found"), True
    except Exception as e:
        return f"present (version probe failed: {type(e).__name__})", True


def probe_path(exe: str):
    """File-based probe for binaries that live outside PATH (Chrome/Edge).

    Returns the byte size as a cheap identity token: the product version is
    read from the browser itself when a route actually launches it
    (``browser.version``), which is what belongs in a manifest.
    """
    p = Path(exe)
    if not p.exists():
        return None, False
    try:
        return f"present ({p.stat().st_size} bytes)", True
    except Exception:
        return "present", True


def probe_playwright_browsers():
    """Playwright the module is not enough — it needs a downloaded browser."""
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    if not root.exists():
        return None, False
    builds = sorted(d.name for d in root.iterdir() if d.is_dir())
    return ", ".join(builds), True


_USER_FONTS = Path(os.environ.get("LOCALAPPDATA", ""))
FONT_DIRS = (r"C:\Windows\Fonts",
             str(_USER_FONTS / "Microsoft" / "Windows" / "Fonts"))


def probe_variable_fonts():
    """The type route needs a face with an ``fvar`` table, not merely *a* font.

    Counts system font files either way, but can only name the axes when fontTools
    is importable in *this* interpreter — which is the point: the capability belongs
    to the interpreter running the route, not to the machine.
    """
    files = []
    for d in FONT_DIRS:
        p = Path(d)
        if p.exists():
            files += [f for f in p.glob("*")
                      if f.suffix.lower() in (".ttf", ".otf", ".ttc")]
    if not files:
        return None, False
    summary = f"{len(files)} font files"
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        return summary + ", axes unreadable (fontTools absent in this interpreter)", True
    faces = []
    for f in files:
        try:
            tt = TTFont(f, lazy=True)
        except Exception:
            continue
        if "fvar" in tt:
            axes = ",".join(f"{a.axisTag} {a.minValue:g}-{a.maxValue:g}"
                            for a in tt["fvar"].axes)
            faces.append(f"{f.name} [{axes}]")
        tt.close()
    return summary + f", {len(faces)} variable: " + "; ".join(faces), bool(faces)


def build_registry() -> dict:
    """Probe everything and assemble the registry dict doctor.py prints.

    Same shape as the JSON footer of ``python scripts/doctor.py``:
    ``{key: {available, kind, via, version?|reason?|path?|builds?|detail?}}``.
    A planner may only select entries with ``available: true``.
    """
    registry = {}
    for module, (key, kind) in sorted(PY_MODULES.items(), key=lambda x: x[1][0]):
        ver, ok = probe_python(module)
        registry[key] = {"available": ok, "kind": kind, "via": "pip"}
        if ok:
            registry[key]["version"] = ver
    for name, (key, kind) in sorted(BINARIES.items(), key=lambda x: x[1][0]):
        ver, ok = probe_binary(name)
        registry[key] = {"available": ok, "kind": kind, "via": "binary"}
        if ok:
            registry[key]["version"] = ver
        else:
            registry[key]["reason"] = "binary not on PATH"
    for exe, (key, kind) in sorted(KNOWN_PATHS.items(), key=lambda x: x[1][0]):
        _detail, ok = probe_path(exe)
        registry[key] = {"available": ok, "kind": kind, "via": "known-path"}
        if ok:
            registry[key]["path"] = exe
    for key, exe in sorted(_REPO_TOOLS.items()):
        if registry.get(key, {}).get("available"):
            continue  # a PATH install wins; the repo copy is the fallback
        ok = exe.is_file()
        entry = {"available": ok, "kind": "audio/synth", "via": "repo-tool"}
        if ok:
            entry["path"] = str(exe)
            entry["version"] = "repo-tool (assets/tools/fluidsynth)"
        else:
            entry["reason"] = (f"{exe.name} not fetched — run "
                               f"python scripts/fetch_assets.py")
        registry[key] = entry
    browsers, ok = probe_playwright_browsers()
    registry["playwright-browsers"] = {
        "available": ok, "kind": "image/browser-rasterizer", "via": "LOCALAPPDATA",
    }
    if ok:
        registry["playwright-browsers"]["builds"] = browsers
    faces, ok = probe_variable_fonts()
    registry["variable-fonts"] = {
        "available": ok, "kind": "type/variable-font", "via": "font dirs",
    }
    if faces:
        registry["variable-fonts"]["detail"] = faces
    return registry


class CapabilityError(RuntimeError):
    """A route asked for a capability the registry does not report AVAILABLE.

    Raised *before* a node runs, with the reason and an install hint — a loud
    refusal, never a silent degradation (docs/coverage-audit.md §0: silent
    degradation is worse than an exception for a validation pipeline).
    """


def require(key: str, registry: dict | None = None) -> dict:
    """Return the registry entry for ``key`` or raise :class:`CapabilityError`."""
    reg = registry if registry is not None else build_registry()
    entry = reg.get(key)
    if entry is None:
        raise CapabilityError(
            f"capability '{key}' is unknown to the registry "
            f"(not in PY_MODULES/BINARIES/KNOWN_PATHS)")
    if not entry.get("available"):
        reason = entry.get("reason", "not available in this interpreter")
        raise CapabilityError(
            f"capability '{key}' unavailable: {reason} "
            f"(via {entry.get('via')}; install notes: docs/tools.md)")
    return entry


def path_shadows() -> list[tuple[str, str]]:
    """PATH names that look like media tools but are not (Windows traps)."""
    hits = []
    for name in TRAP_NAMES:
        hit = shutil.which(name)
        if hit:
            hits.append((name, hit))
    return hits


def print_registry(registry: dict | None = None) -> None:
    """Print the registry as doctor's table + JSON footer (byte-stable format)."""
    reg = registry if registry is not None else build_registry()
    print(f"python {sys.version.split()[0]} @ {sys.executable}")
    print(f"prefix {sys.prefix}\n")
    for _module, (key, _kind) in sorted(PY_MODULES.items(), key=lambda x: x[1][0]):
        e = reg[key]
        print(f"{'AVAILABLE' if e['available'] else '  absent '}  pip   "
              f"{key:14s} {e.get('version') or ''}")
    print()
    for _name, (key, _kind) in sorted(BINARIES.items(), key=lambda x: x[1][0]):
        e = reg[key]
        print(f"{'AVAILABLE' if e['available'] else '  absent '}  bin   "
              f"{key:14s} {e.get('version') or e.get('reason', '')}")
    print()
    for exe, (key, _kind) in sorted(KNOWN_PATHS.items(), key=lambda x: x[1][0]):
        e = reg[key]
        print(f"{'AVAILABLE' if e['available'] else '  absent '}  file  "
              f"{key:14s} {exe if e['available'] else 'not found'}")
    e = reg["playwright-browsers"]
    print(f"{'AVAILABLE' if e['available'] else '  absent '}  dir   "
          f"playwright-browsers  {e.get('builds') or 'no ms-playwright dir'}")
    e = reg["variable-fonts"]
    print(f"{'AVAILABLE' if e['available'] else '  absent '}  font  "
          f"variable-fonts     {e.get('detail') or 'no fvar faces found'}")
    print("\n--- PATH shadows (names that look like media tools but are not) ---")
    for name, hit in path_shadows():
        print(f"  {name:8s} -> {hit}")
    print("\n--- json ---")
    print(json.dumps(reg, ensure_ascii=False, indent=2))
