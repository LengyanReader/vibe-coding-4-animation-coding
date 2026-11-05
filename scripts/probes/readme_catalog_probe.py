"""What the README's route table and status line actually say, as the test reads them.

`tests/unit/test_route_catalog.py` compares three things against
`pipeline.ROUTES`: the §0 table's first column, the parenthesised medium list in
the bilingual status line, and the `medium:` field of every shipped spec. This
prints all three so the assertion is written against output and not against a
regex guessed at the keyboard (PowerShell eats backticks in `-c` strings).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from vcac import pipeline

text = Path("README.md").read_text(encoding="utf-8")

rows = sorted(set(re.findall(r"^\| `([a-z]+)` \|", text, re.M)))
print("table rows      :", rows)
print("ROUTES          :", sorted(pipeline.ROUTES))
print("rows-ROUTES     :", set(rows) - set(pipeline.ROUTES))
print("ROUTES-rows     :", set(pipeline.ROUTES) - set(rows))

cn = re.search(r"已跑通 \d+ 条确定性媒体路线（([^；]+)；", text)
en = re.search(r"\w+ deterministic media routes \(([^;]+);", text)
print("cn groups       :", cn.groups() if cn else None)
print("en groups       :", en.groups() if en else None)
for name, m in (("cn", cn), ("en", en)):
    if m:
        got = set(m.group(1).split("/"))
        print(f"{name} == ROUTES   :", got == set(pipeline.ROUTES), sorted(got))

mediums: dict[str, list[str]] = {}
bundles: list[str] = []
for p in sorted(Path("specs/examples").glob("*.yaml")):
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if "medium" not in raw:
        # the test's rule: no `medium` must mean a `dag` bundle, not a typo
        bundles.append(f"{p.name} ({'dag' in raw})")
        continue
    mediums.setdefault(str(raw["medium"]), []).append(p.name)
for k, v in sorted(mediums.items()):
    flag = "OK " if k in pipeline.ROUTES else "!! not in ROUTES"
    print(f"spec medium {k:14s} {v}  {flag}")
print(f"bundle files (dag=True)  : {bundles}")
