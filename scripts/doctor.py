"""vcac doctor — print the local capability registry.

Usage (from repo root):
    conda activate hy_py312 && python scripts/doctor.py
    C:\\Users\\data\\miniconda3\\envs\\hy_py312\\python.exe scripts\\doctor.py

Probes python packages (import + __version__) and external binaries
(PATH lookup + `--version`). Output is the ground truth for the
capability registry design in README §6.2: the planner may only select
tools reported AVAILABLE here.

The registry is **per-interpreter**: this machine has more than one Python
(C:\Python313 = 3.13.5 on PATH, and conda env hy_py312 = 3.12.13), and their
package sets differ. Run this file with *each* interpreter you intend to ship
on and compare the JSON before believing any "already installed" claim in
`docs/tools.md`. The interpreter identity is part of every manifest
(`provenance.tool_versions` records `sys.version`).

Last full run verified: 2026-11-04, both interpreters (17/17 tests pass under
either). See docs/tools.md §0 / §0.2 for the human-readable table.
"""
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


def main() -> None:
    registry = {}
    print(f"python {sys.version.split()[0]} @ {sys.executable}")
    print(f"prefix {sys.prefix}\n")
    for module, (key, kind) in sorted(PY_MODULES.items(), key=lambda x: x[1][0]):
        ver, ok = probe_python(module)
        registry[key] = {"available": ok, "kind": kind, "via": "pip"}
        if ok:
            registry[key]["version"] = ver
        print(f"{'AVAILABLE' if ok else '  absent '}  pip   {key:14s} {ver or ''}")
    print()
    for name, (key, kind) in sorted(BINARIES.items(), key=lambda x: x[1][0]):
        ver, ok = probe_binary(name)
        registry[key] = {"available": ok, "kind": kind, "via": "binary"}
        if ok:
            registry[key]["version"] = ver
        else:
            registry[key]["reason"] = "binary not on PATH"
        print(f"{'AVAILABLE' if ok else '  absent '}  bin   {key:14s} {ver or registry[key]['reason']}")
    print()
    for exe, (key, kind) in sorted(KNOWN_PATHS.items(), key=lambda x: x[1][0]):
        ver, ok = probe_path(exe)
        registry[key] = {"available": ok, "kind": kind, "via": "known-path"}
        if ok:
            registry[key]["path"] = exe
        print(f"{'AVAILABLE' if ok else '  absent '}  file  {key:14s} {exe if ok else 'not found'}")
    browsers, ok = probe_playwright_browsers()
    registry["playwright-browsers"] = {
        "available": ok, "kind": "image/browser-rasterizer", "via": "LOCALAPPDATA",
    }
    if ok:
        registry["playwright-browsers"]["builds"] = browsers
    print(f"{'AVAILABLE' if ok else '  absent '}  dir   playwright-browsers  {browsers or 'no ms-playwright dir'}")
    print("\n--- PATH shadows (names that look like media tools but are not) ---")
    for name in TRAP_NAMES:
        hit = shutil.which(name)
        if hit:
            print(f"  {name:8s} -> {hit}")
    print("\n--- json ---")
    print(json.dumps(registry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
