"""Measure the two unregistered routes before writing them into README §0.

Neither has ever been through the e2e suite, so the table would otherwise be
recording a route whose gates nobody has run. This collects, per spec: the
content hash, the acceptance tally, every rule with its expected/actual, and the
wall-clock cost -- and writes it to a text file so the numbers in the README and
in the new test file are copied from a measurement, not typed from memory.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from vcac import illustration_sample, manga_ink

SPEC = Path("specs/examples")
OUT = Path("outputs/_probe/routes_audit")
CASES = [
    ("illustration", illustration_sample, "illust-guild.yaml"),
    ("illustration", illustration_sample, "illust-fox.yaml"),
    ("illustration", illustration_sample, "illust-cumulus.yaml"),
    ("manga", manga_ink, "manga-guild.yaml"),
]

lines: list[str] = []
for medium, mod, name in CASES:
    t0 = time.perf_counter()
    try:
        r = mod.run(SPEC / name, OUT / name.replace(".yaml", ""))
    except Exception as exc:                     # noqa: BLE001 - probing everything
        lines.append(f"{medium} {name}: RAISED {type(exc).__name__}: {exc}")
        continue
    dt = time.perf_counter() - t0
    rep = r["report"]
    lines.append("")
    lines.append(f"=== {medium} / {name}  ({dt:.1f} s) ===")
    lines.append(f"content_hash : {r['manifest'].get('content_hash')}")
    lines.append(f"artifact     : {r['manifest'].get('artifact')} "
                 f"bytes={r['manifest'].get('size_bytes')}")
    lines.append(f"passed={rep['passed']} total={rep['checks_total']} "
                 f"pass={rep['passed_n']} fail={rep['failed_n']} "
                 f"skipped={rep['skipped_n']}")
    for c in rep["checks"]:
        lines.append(f"  [{c['status']:7s}] {c['id']}"
                     + (f"  expected={c.get('expected')} actual={c.get('actual')}"
                        if c["status"] != "skipped" else f"  {c.get('reason')}"))
    meas = rep.get("measured") or {}
    lines.append("  measured: " + json.dumps(
        {k: (round(v, 3) if isinstance(v, float) else v)
         for k, v in meas.items() if not isinstance(v, (list, dict))},
        ensure_ascii=False, sort_keys=True))

text = "\n".join(lines) + "\n"
Path("outputs/_probe/routes_audit.txt").write_text(text, encoding="utf-8")
print(text)
