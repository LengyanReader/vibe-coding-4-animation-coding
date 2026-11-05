"""Watch the catalog test go red, once, before trusting its green.

`tests/unit/test_route_catalog.py` asserts *set equality* between the README and
`pipeline.ROUTES`. An equality that currently holds is indistinguishable from an
equality that cannot fail, so each half is broken here in memory and the test
must say so: a route registered without a README row, a README row for a route
that is gone, a status line left behind by a new medium, a route with no
load-time schema, a spec naming a misspelled medium, a bundle that is neither.

Nothing on disk changes -- the mutations are patched into the imported modules
and reverted. Run: `python scripts/probes/catalog_mutant_probe.py`
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

# tests/ is not a package, so the module is loaded by path the way pytest loads it
_spec = importlib.util.spec_from_file_location(
    "test_route_catalog", Path("tests/unit/test_route_catalog.py"))
t = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(t)

from vcac import pipeline  # noqa: E402  (after t, so t's import is the same object)


def _expect_red(fn, what: str) -> None:
    try:
        fn()
    except AssertionError as e:
        first = (str(e).splitlines() or [""])[0]
        print(f"RED   {what}\n      {first[:170]}")
        return
    raise SystemExit(f"THE TEST CANNOT FAIL: {what}")


def _renamed_medium(medium: str) -> None:
    """Read the shipped specs with one medium misspelled, as a typo would."""
    bumped = dict(_real_spec_mediums())
    bumped[medium] = bumped.pop("illustration")
    t._spec_mediums = lambda: bumped
    try:
        t.test_no_spec_names_a_medium_the_pipeline_cannot_run()
    finally:
        t._spec_mediums = _real_spec_mediums


_real_spec_mediums = t._spec_mediums

saved = dict(pipeline.ROUTES)

# 1. a medium is registered but the README has no row for it
pipeline.ROUTES["watercolour"] = saved["ink"]
_expect_red(t.test_readme_table_documents_exactly_the_registered_mediums,
            "route registered with no README row")
_expect_red(t.test_every_registered_medium_has_an_example_spec,
            "route registered with no example spec")
pipeline.ROUTES.pop("watercolour")

# 2. the README keeps a row for a route that was removed
pipeline.ROUTES.pop("manga")
_expect_red(t.test_readme_table_documents_exactly_the_registered_mediums,
            "README row for a route that no longer exists")
pipeline.ROUTES.update(saved)

# 3. the status line falls behind the registry -- this session's actual defect
pipeline.ROUTES["hanga"] = saved["manga"]
_expect_red(t.test_readme_status_line_lists_the_same_mediums,
            "status line not updated when a medium is added")
pipeline.ROUTES.pop("hanga")

# 4. a route with no load-time schema entry
pipeline.ROUTES["watercolour"] = pipeline.RouteEntry(saved["ink"].run, "plate.png")
_expect_red(t.test_every_route_is_loadable_and_schema_known,
            "route with no REQUIRED_KEYS / frame-contract entry")
pipeline.ROUTES.pop("watercolour")

# 5. a spec whose medium name is a typo
_expect_red(lambda: _renamed_medium("illuatration"),
            "spec naming a medium the pipeline cannot run")

# 6. a file that is neither a route spec nor a bundle: neither `medium:` nor `dag:`
#    needs a real file, because the test reads the directory -- a fake list would
#    just re-read the honest bundle and pass
import tempfile  # noqa: E402

with tempfile.TemporaryDirectory() as td:
    orphan = Path(td)
    (orphan / "half-typed.yaml").write_text("id: oops\ntitle: neither\n", encoding="utf-8")
    saved_dir = t.SPEC_DIR
    t.SPEC_DIR = orphan
    try:
        _expect_red(t.test_a_spec_without_a_medium_is_a_bundle,
                    "a medium-less file that has no dag either")
    finally:
        t.SPEC_DIR = saved_dir

pipeline.ROUTES.clear()
pipeline.ROUTES.update(saved)
t.test_readme_table_documents_exactly_the_registered_mediums()
print("all six halves were seen to fail, and the restored catalog is green again")
