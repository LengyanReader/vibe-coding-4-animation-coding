#!/usr/bin/env python3
"""Standalone self-check for this generated harness.

Verifies that every file listed in .harness/manifest.json exists and that no
unrendered template placeholders remain. Exit code 0 = pass.

Usage: python .harness/check.py [root]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MANIFEST = ".harness/manifest.json"
SCAN_SUFFIXES = {".md", ".py", ".json", ".txt", ".toml", ".cfg"}
PLACEHOLDER = "{" * 2


def main(root: str) -> int:
    base = Path(root)
    manifest = base / MANIFEST
    if not manifest.exists():
        print(f"FAIL: missing {MANIFEST}")
        return 1
    try:
        plan = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"FAIL: manifest is not valid JSON: {exc}")
        return 1

    problems: list[str] = []
    files = plan.get("files", [])
    for rel in files:
        if not (base / rel).exists():
            problems.append(f"missing file: {rel}")
    for rel in files:
        path = base / rel
        if path.exists() and path.suffix in SCAN_SUFFIXES:
            try:
                if PLACEHOLDER in path.read_text(encoding="utf-8"):
                    problems.append(f"unrendered placeholder in: {rel}")
            except OSError:
                pass

    if problems:
        print("FAIL")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("OK: harness self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
