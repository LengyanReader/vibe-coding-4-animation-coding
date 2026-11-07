"""End-to-end tests for the ebook route (《水墨笔记》).

Same doctrine as the other route tests: a human-confirmed golden **normalised
payload hash** (spine-order XHTML + OPF — deliberately NOT the zip bytes, whose
timestamps are container noise), plus mutants watched going red, plus named
refusals. The determinism gate inside the route re-renders and compares the
normalised payload, so a pass here doubles as a cross-process reproducibility
proof for a document deliverable.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from vcac import ebook, spec as spec_mod

pytestmark = pytest.mark.skipif(
    shutil.which("pandoc") is None, reason="ebook route needs pandoc on PATH")

SPEC = Path("specs/examples")
GOLDEN = "sha256:9947c986fcd9526c88fcfeba4be10bb3d0a7df57d19738547648720bac1a6346"


def _mutated(tmp_path: Path, edit) -> Path:
    raw = spec_mod.load_raw(SPEC / "ebook-ink-notes.yaml")
    edit(raw)
    p = tmp_path / "mut.yaml"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return p


def test_ebook_route(tmp_path):
    r = ebook.run(SPEC / "ebook-ink-notes.yaml", tmp_path / "b")
    rep, m = r["report"], r["report"]["measured"]
    assert rep["passed"], rep["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN
    assert m["spine_count"] == 5 and m["toc_entries"] == 5
    assert m["language"] == "zh-CN" and m["cover_present"]
    assert m["missing_hrefs"] == []
    assert m["deterministic"]
    assert (tmp_path / "b" / "book.epub").stat().st_size > 50_000
    assert (tmp_path / "b" / "book.pdf").stat().st_size > 50_000
    # the pinned identifier travels into the OPF — no generated uuid anywhere
    assert m["identifier"] == "urn:vcac:ink-notes:2026-11-07"
    assert "uuid" not in m["identifier"].lower()


def test_ebook_spine_gate_catches_a_sixth_chapter(tmp_path):
    def add_chapter(raw):
        extra = tmp_path / "ch06-extra.md"
        extra.write_text("# 附录\n\n多出来的一章。\n", encoding="utf-8")
        raw["chapters"].append(str(extra))

    p = _mutated(tmp_path, add_chapter)
    r = ebook.run(p, tmp_path / "b")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["spine count exactly 5"]["status"] == "fail"
    assert ids["spine count exactly 5"]["actual"] == 6


def test_ebook_refuses_a_missing_chapter_file(tmp_path):
    def drop(raw):
        raw["chapters"][1] = "specs/ebooks/ink-notes/nope.md"

    p = _mutated(tmp_path, drop)
    with pytest.raises(spec_mod.SpecError, match="missing on disk"):
        ebook.run(p, tmp_path / "b")


def test_ebook_refuses_an_unpinned_identifier(tmp_path):
    """dc:identifier is the determinism anchor: a spec without one must be
    refused at load of the route, before pandoc can invent a random uuid."""
    def strip_id(raw):
        raw["metadata"].pop("identifier")

    p = _mutated(tmp_path, strip_id)
    with pytest.raises(spec_mod.SpecError, match="identifier"):
        ebook.run(p, tmp_path / "b")


def test_ebook_refuses_a_missing_cover(tmp_path):
    def drop_cover(raw):
        raw["cover"] = "specs/ebooks/ink-notes/no-cover.png"

    p = _mutated(tmp_path, drop_cover)
    with pytest.raises(spec_mod.SpecError, match="cover image"):
        ebook.run(p, tmp_path / "b")


def test_ebook_pdf_checks_report_skipped_without_pypdf(tmp_path, monkeypatch):
    """pypdf is interpreter-scoped (docs/tools.md §0): where it is absent the
    PDF rules measure None and the gate reports `skipped` with the reason —
    never a fake green, never a crash."""
    import builtins
    real_import = builtins.__import__

    def no_pypdf(name, *args, **kwargs):
        if name == "pypdf":
            raise ImportError("simulated absent interpreter")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_pypdf)
    r = ebook.run(SPEC / "ebook-ink-notes.yaml", tmp_path / "b")
    m = r["report"]["measured"]
    assert "pdf_pages" not in m                      # nothing measured...
    assert "pypdf absent" in m["pdf_reason"]         # ...but the reason is on record
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["page count between 4 and 24"]["status"] == "skipped"
    assert "pdf_pages" in ids["page count between 4 and 24"]["reason"]
