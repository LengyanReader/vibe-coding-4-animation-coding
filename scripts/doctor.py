"""vcac doctor — print the local capability registry.

Usage (from repo root):
    conda activate hy_py312 && python scripts/doctor.py
    C:\\Users\\data\\miniconda3\\envs\\hy_py312\\python.exe scripts\\doctor.py

Probes python packages (import + __version__) and external binaries
(PATH lookup + `--version`). Output is the ground truth for the
capability registry design in README §6.2: the planner may only select
tools reported AVAILABLE here.

Last full run verified: 2026-11-04 (see docs/tools.md for the ecosystem survey).
"""
import importlib
import json
import shutil
import subprocess
import sys

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
    "xelatex": ("miktex", "docs/typeset"),
    "dot": ("graphviz", "dataviz"),
    "aseprite": ("aseprite", "game/assets"),
    "tiled": ("tiled", "game/assets"),
}


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


def main() -> None:
    registry = {}
    print(f"python {sys.version.split()[0]} @ {sys.executable}\n")
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
    print("\n--- json ---")
    print(json.dumps(registry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
