#!/usr/bin/env python3
"""Deterministic build: inline specs (as JSON) + app modules + CSS into ONE
self-contained dist/one-breath.html — double-click to open, no server, no
network. The build is reproducible: same sources -> same bytes -> same sha256
(recorded into dist/build-manifest.json). No timestamps enter the artifact.

Also emits dist/content.json — the same embedded content as JSON — so the node
tests read exactly what the browser will read (gate and game share one view).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def build() -> dict:
    strings = _load_yaml(ROOT / "specs" / "strings.yaml")["ui"]
    vignettes = {}
    for p in sorted((ROOT / "specs" / "vignettes").glob("*.yaml")):
        v = _load_yaml(p)
        vignettes[v["id"]] = v
    boards = {}
    for p in sorted((ROOT / "specs").glob("board-*.yaml")):
        b = _load_yaml(p)
        boards[b["id"]] = b

    lessons = {}
    for p in sorted((ROOT / "specs").glob("lessons*.yaml")):
        lesson = _load_yaml(p)
        lessons[lesson["id"]] = lesson

    content = {"strings": strings, "vignettes": vignettes, "boards": boards,
               "lessons": lessons}
    content_json = json.dumps(content, ensure_ascii=False,
                              sort_keys=True, separators=(",", ":"))

    # optional breath audio: synthesized by the vcac audio engine (deterministic),
    # embedded as a data URI, opt-in via the sound toggle
    breath = ROOT / "assets" / "breath-pad.wav"
    breath_uri = None
    if breath.is_file():
        import base64
        breath_uri = "data:audio/wav;base64," + base64.b64encode(breath.read_bytes()).decode()
    content_json = content_json[:-1] + f', "breathWav": {json.dumps(breath_uri)}}}'         if breath_uri else content_json

    css = (ROOT / "app" / "styles.css").read_text(encoding="utf-8")
    template = (ROOT / "tools" / "index.template.html").read_text(encoding="utf-8")

    # module assembly: i18n -> rules -> board-mirror -> panels -> dharmadhatu
    # -> vignette -> teaching -> main, stripped of import/export statements
    app_order = ["i18n.js", "rules.js", "board-mirror.js", "panels.js",
                   "dharmadhatu.js", "vignette.js", "teaching.js", "main.js"]
    js_parts = []
    for name in app_order:
        src = (ROOT / "app" / name).read_text(encoding="utf-8")
        # strip multi-line and single-line imports; the build inlines one scope
        src = re.sub(r"^import\s*\{[^}]*\}\s*from\s*[\"'][^\"']+[\"'];\s*$", "", src, flags=re.M)
        src = re.sub(r"^import\s.+?;\s*$", "", src, flags=re.M)
        src = re.sub(r"^export\s+", "", src, flags=re.M)
        js_parts.append(f"// ---- {name} ----\n{src.strip()}")
    app_js = "\n\n".join(js_parts)

    html = template.replace("{{CSS}}", css).replace(
        "{{CONTENT_JSON}}", content_json).replace("{{APP_JS}}", app_js)
    # guard: no unresolved template markers
    if re.search(r"\{\{[A-Z_]+\}\}", html):
        raise SystemExit("build: unresolved template markers")

    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "one-breath.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    (out_dir / "content.json").write_text(content_json, encoding="utf-8", newline="\n")

    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    manifest = {
        "artifact": "dist/one-breath.html",
        "sha256": sha,
        "bytes": out.stat().st_size,
        "vignettes": sorted(vignettes),
        "note": "deterministic build: no timestamps, sorted JSON, fixed module order",
    }
    (out_dir / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    m = build()
    print(f"built dist/one-breath.html ({m['bytes']} bytes) sha256={m['sha256']}")
