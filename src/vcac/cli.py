"""Shared CLI plumbing for the route modules.

Eight near-identical ``main()`` blocks (audit B2: ~212 lines of copy-paste)
reduce to: standard argparse flags, one route-specific summary line, then
:func:`finish` prints the check table, the run_id and the verdict, and returns
the process exit code. The printed check format is the one the seven
``load_raw`` routes already used; firstloop's "(expected/actual)" wording
converges to the same shape, and its log tag converges from ``[vcac]`` to
``[vcac:video]``. Log lines only — no manifest/report content changes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def write_report(out_dir, report: dict) -> Path:
    """The one way a route writes its acceptance report (was: 8 copies)."""
    p = Path(out_dir) / "report.json"
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def parse_args(description: str, argv=None, extra=None) -> argparse.Namespace:
    """`spec` positional + `--out`, plus route-specific extras."""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    for args, kwargs in (extra or []):
        ap.add_argument(*args, **kwargs)
    return ap.parse_args(argv)


def print_check_table(report: dict) -> None:
    for c in report["checks"]:
        extra = (f"  (exp {c.get('expected')}, act {c.get('actual')})"
                 if c["status"] in ("pass", "fail")
                 else f"  ({c.get('reason', '')})")
        print(f"  [{c['status'].upper():7}] {c['id']}{extra}")


def finish(tag: str, r: dict, summaries=None) -> int:
    """Print summaries + check table + verdict; return the exit code."""
    rep = r["report"]
    for s in (summaries or []):
        print(f"[vcac:{tag}] {s}")
    print_check_table(rep)
    print(f"[vcac:{tag}] run_id={r['manifest']['run_id']}")
    print(f"[vcac:{tag}] ACCEPTANCE {'PASSED' if rep['passed'] else 'FAILED'}")
    return 0 if rep["passed"] else 1
