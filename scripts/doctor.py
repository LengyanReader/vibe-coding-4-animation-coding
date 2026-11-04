"""vcac doctor — print the local capability registry.

Usage (from repo root):
    conda activate hy_py312 && python scripts/doctor.py
    C:\\Users\\data\\miniconda3\\envs\\hy_py312\\python.exe scripts\\doctor.py

The probing logic lives in ``src/vcac/registry.py`` (importable by the
planner and the pipeline executor, also reachable as ``vcac doctor``); this
file is its human-facing CLI and prints the identical table + JSON footer.
Output is the ground truth for the capability registry design in README §6.2:
the planner may only select tools reported AVAILABLE here.

The registry is **per-interpreter**: this machine has more than one Python
(C:\\Python313 = 3.13.5 on PATH, and conda env hy_py312 = 3.12.13), and their
package sets differ. Run this file with *each* interpreter you intend to ship
on and compare the JSON before believing any "already installed" claim in
`docs/tools.md`. The interpreter identity is part of every manifest
(`provenance.tool_versions` records `sys.version`).

Last full run verified: 2026-11-05 — suite 91 tests on 3.13.5 (12 browser/
variable-font tests skip on hy_py312); see docs/tools.md §0 / §0.2 and
docs/audit-2026-11-05.md.
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from vcac.registry import print_registry  # noqa: E402


def main() -> None:
    print_registry()


if __name__ == "__main__":
    main()
