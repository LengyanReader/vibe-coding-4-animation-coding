"""The route catalog has to agree with the code, or the code is not findable.

Commit 01a5e13 exists because it did not: nine routes were registered and the
README documented a subset, so "what can this project do?" had no true answer
without reading `pipeline.ROUTES`. The same drift reopened the moment this
session added `illustration` and `manga` to the registry -- two new mediums went
into `ROUTES` and `spec.REQUIRED_KEYS` while the README still said ten routes.
A human does not go look for that; a test does.

No rendering here: this reads the registry, the spec files and the README.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from vcac import pipeline, spec as spec_mod

ROOT = Path(".")
README = (ROOT / "README.md").read_text(encoding="utf-8")
SPEC_DIR = ROOT / "specs" / "examples"


def _spec_mediums() -> dict[str, list[str]]:
    """medium -> shipped specs. A file with no `medium:` is a bundle (a `dag:`
    of nodes), which is why the two are separated instead of defaulting."""
    out: dict[str, list[str]] = {}
    for p in sorted(SPEC_DIR.glob("*.yaml")):
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        medium = (raw or {}).get("medium")
        if medium is None:
            continue
        out.setdefault(str(medium), []).append(p.name)
    return out


def _bundles() -> list[str]:
    return [p.name for p in sorted(SPEC_DIR.glob("*.yaml"))
            if "medium" not in (yaml.safe_load(p.read_text(encoding="utf-8")) or {})]


def test_readme_table_documents_exactly_the_registered_mediums():
    """Every `medium` in the registry owns a row in README §0, and no row belongs
    to a medium the registry does not have.

    The second half matters as much as the first: a documented route that was
    removed reads as a promise the pipeline will refuse to run."""
    documented = set(re.findall(r"^\| `([a-z]+)` \|", README, re.M))
    registered = set(pipeline.ROUTES)
    assert documented == registered, (
        f"documented but not registered: {sorted(documented - registered)}; "
        f"registered but not documented: {sorted(registered - documented)}")


def test_readme_status_line_lists_the_same_mediums():
    """The prose count in the header is the first thing anyone reads, so it is
    checked against the registry too -- by name, not by a digit that would also
    have to be recounted by hand."""
    cn = re.search(r"已跑通 \d+ 条确定性媒体路线（([^；]+)；", README)
    # the English count is a word, not a digit: capture only the list so both
    # languages are read the same way
    en = re.search(r"\w+ deterministic media routes \(([^;]+);", README)
    assert cn and en, "README status line (CN + EN) must both enumerate the mediums"
    for m in (cn, en):
        assert set(m.group(1).split("/")) == set(pipeline.ROUTES), m.group(1)


def test_every_registered_medium_has_an_example_spec():
    """A route nobody can invoke with a shipped spec is a code path, not a
    capability. `python -m vcac.<module> specs/examples/<id>.yaml` is the whole
    public interface (README §0), so the example IS the proof it runs."""
    have = _spec_mediums()
    for medium in sorted(pipeline.ROUTES):
        assert have.get(medium), f"medium {medium!r} is registered but has no spec " \
                                 f"in specs/examples"


def test_no_spec_names_a_medium_the_pipeline_cannot_run():
    for medium, names in sorted(_spec_mediums().items()):
        assert medium in pipeline.ROUTES, f"{names}: medium {medium!r} is not in ROUTES"


def test_a_spec_without_a_medium_is_a_bundle():
    """`medium` absent means "this file is a DAG", not "this file forgot a field".

    The distinction is worth pinning: `build_plan` reads `dag:` for bundles and
    `medium:` for single-node specs, so a typo in either key silently turns a
    deliverable into a file no command can run."""
    for name in _bundles():
        raw = yaml.safe_load((SPEC_DIR / name).read_text(encoding="utf-8"))
        assert "dag" in raw, f"{name}: no `medium:` and no `dag:` -- neither a route " \
                             f"nor a bundle"


def test_every_route_is_loadable_and_schema_known():
    """`load_raw` rejects an unknown medium's required keys at load time, so a
    registered route missing from that table would fail late, inside a render,
    with a bare KeyError -- the audit's class-A defect."""
    known = set(spec_mod.REQUIRED_KEYS) | set(spec_mod.VIDEO_CONTRACT_MEDIA)
    for medium, entry in sorted(pipeline.ROUTES.items()):
        assert medium in known, medium
        assert callable(entry.run), medium
        # `provides` is the artifact downstream bundle nodes read, so an empty
        # name would register a route that can run but cannot be fed forward
        assert entry.provides.endswith(
            (".mp4", ".wav", ".png", ".pdf", ".json", ".epub")), \
            (medium, entry.provides)


def test_video_contract_media_are_registered_routes():
    """The frame contract is shared by `video` and `anime` on purpose (a second
    renderer is not a second schema); if one of them stops being a route the
    sharing becomes a hidden alias."""
    for medium in spec_mod.VIDEO_CONTRACT_MEDIA:
        assert medium in pipeline.ROUTES, medium


def test_readme_structure_line_names_every_route_module():
    """The §0 table can be complete while the prose "route modules (...)" list is
    a stale subset -- which is exactly how `illustration_sample` and `manga_ink`
    went unlisted the moment their mediums were registered. The engine module
    backing every route must be findable in the README Structure line, so a new
    route cannot ship as a registry entry only."""
    line = next(l for l in README.splitlines()
                if l.startswith("- **Structure (actual today):**"))
    named = set(re.findall(r"`([a-z_]+)`", line))
    for medium, entry in sorted(pipeline.ROUTES.items()):
        module = entry.run.__module__.rsplit(".", 1)[-1]
        assert module in named, (
            f"route {medium!r} runs in {module!r}, missing from README Structure line")
