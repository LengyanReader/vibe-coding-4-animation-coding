"""The two routes added on 2026-11-05/06: the inked page and the illustration sheet.

Same two duties as the other route files, with one refusal added:

  * every gate ships with a **mutant that has been seen to fail it**, or with the
    refusal that replaces the measurement;
  * a measurement that was **withdrawn** must come back as `skipped`, never as a
    green and never as a number someone re-derived until it looked right;
  * and a hash pinned here for a sheet the viewer REFUSED is a change lock, not an
    approval. The illustration route's eleven rules are green on all three shipped
    sheets and the eye still said no -- which is the finding in
    `docs/styles.md` §0.1, not a defect in this file. Pinning its hashes says "the
    sheet changed, go look"; it does not say the sheet is good.

Cost measured on this machine (C:/Python313): illustration 8.7-9.2 s per sheet
(two renders per run for the determinism gate), manga 9.6 s per run. The mutants
add one render each, so this file is roughly 2 minutes.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from vcac import illustration_sample, manga_ink, spec as spec_mod, validate

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="routes need ffmpeg on PATH")

SPEC = Path("specs/examples")

#: recorded by `scripts/probes/routes_audit_probe.py` on 2026-11-06. The manga
#: hash is a **golden** in the repo's sense -- the page was looked at, its single
#: faces were judged readable and its limits were named in §0.1 -- while the
#: illustration hashes are change locks on sheets the viewer refused. Both are
#: pinned; only one of them means "this is the good one".
HASHES = {
    "manga-guild": "sha256:9a5b280cfc6717a556e26e2b67280be5439609cd825c965695156fa03d18fc09",
    "illust-guild": "sha256:d58ee1f0f2897b569026569c65dc4150b76f52003e8aa956be730a7150071b30",
    "illust-fox": "sha256:92bb376d22cce24100c4dc35bb643c55e34d71a7c679dffc561b70d4ec876745",
    "illust-cumulus": "sha256:864f3a05cee9720401f7d6433c30b78b0c4ed0b59fa5d3f09b36e1f08579d4f8",
}


def _mutated(spec_path: Path, tmp_path: Path, name: str, edit) -> Path:
    raw = spec_mod.load_raw(spec_path)
    edit(raw)
    p = tmp_path / f"{name}.yaml"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return p


def _ids(report) -> dict:
    return {c["id"]: c for c in report["checks"]}


def _need_scipy():
    pytest.importorskip("scipy", reason="both routes measure through scipy.ndimage")


# --- A. manga-ink: the nib is measurable, the eye is not -----------------------

def test_manga_route(tmp_path):
    _need_scipy()
    r = manga_ink.run(SPEC / "manga-guild.yaml", tmp_path / "manga")
    rep, m = r["report"], r["report"]["measured"]
    assert rep["passed"], rep["checks"]
    assert r["manifest"]["content_hash"] == HASHES["manga-guild"]
    assert (m["width"], m["height"]) == (1400, 1000)
    assert (m["palette_distinct_colors"], m["palette_declared_colors"]) == (8, 8)
    assert m["palette_exact_pct"] == 100.0
    # the page is mostly white: the measure that the illustration route lacked
    assert 20.0 < m["paper_negative_pct"] < 70.0
    assert m["screentone_dot_pct"] > 1.0


def test_manga_pen_gate_reads_the_nib_and_keeps_the_print_gap(tmp_path):
    """The gate was briefly green for the wrong reason and this pins the fix.

    What the pen gate used to read on this page: `spread = 2.00 px`, comfortably
    above its 1.4 px floor. What was actually on the sheet: **three** distinct
    widths (2.00 px on 67.4% of ridge samples, 4.00 on 23.7%, 4.47 on 4.1%),
    because the raster it measured is the downsampled, quantised print -- 1.8 px
    and 2.2 px both land on 2 px, so the pressure curve was destroyed before the
    gate looked at it (scripts/probes/manga_weight_probe.py).

    It now measures the pre-downsample hard-edged raster, and BOTH numbers stay in
    the manifest: the gap between them is the amount of nib the resizer threw
    away, which is a fact worth keeping visible rather than a detail to hide.
    """
    _need_scipy()
    r = manga_ink.run(SPEC / "manga-guild.yaml", tmp_path / "manga")
    m = r["report"]["measured"]
    assert m["ink_weight_spread"] == m["ink_weight_spread_nib"]      # the gate's number
    assert m["ink_weight_spread_nib"] > m["ink_weight_spread_print"]  # 4.00 vs 2.00
    assert m["ink_weight_median"] > 1.0


def test_manga_pen_gate_reports_how_much_of_it_is_not_the_pen(tmp_path):
    """A diagnostic that corrected an earlier wrong claim of mine.

    When I first moved the measurement onto the nib raster I asserted that a
    THIRD of the width samples were mass shoulders wider than any authored nib,
    and wrote it into the docstrings. That was WRONG, and the leak probe shows
    why: I compared the ridge widths only against `figures[].parts` (widest
    3.60 px) and never looked at the templates, backdrop or foreground. The
    widest nib the WHOLE page authors is 6.36 px (a `backdrop` burst), and the
    5.33 px mode I had called "masses" is an authored flat line, not a leak --
    only 0.4% of ridge samples exceed the widest authored nib. `nib_leak_probe.py`
    prints the histogram against both candidate caps.

    The number is still reported and not gated: a gate that consults the spec it
    audits is a different kind of false green. What this pins is the corrected
    value, so nobody re-imports my original 31.5% mistake.
    """
    _need_scipy()
    r = manga_ink.run(SPEC / "manga-guild.yaml", tmp_path / "manga")
    m = r["report"]["measured"]
    assert m["widest_authored_nib_px"] == pytest.approx(6.36, abs=0.5)
    assert m["ink_weight_over_nib_pct"] < 1.0        # not the 33.8% I first claimed
    assert m["ink_weight_ridge_samples"] > 10_000


def test_manga_pen_gate_catches_a_constant_width_nib(tmp_path):
    """The mutant the gate exists for: lay every stroke with one width.

    A page drawn with a constant-width pen is the exact fault this route was
    built to kill -- it is what the illustration route shipped green -- so the
    gate must be able to see it. Flattening all nib widths in the spec is the
    faithful artifact-side mutation.

    Writing this test is what found the fourth false green of the session: with
    the floor where I had left it (1.4 px) the mutant came back **green**, at
    1.84 px. Moving the measurement to the nib raster had been necessary and was
    not sufficient -- a 1.7 px line is 5.1 px on a 3x raster, and half-pixel
    landing plus the pen's own jitter do not flatten to nothing. The floor is
    therefore 2.4 px now, set between the two measured values (1.84 constant /
    4.00 authored) and closer to the fault; `nib_gate_mutant_probe.py` prints both.
    """
    _need_scipy()

    def one_width(node):
        if isinstance(node, dict):
            w = node.get("w")
            if isinstance(w, dict):
                node["w"] = {"profile": "flat", "a": 1.7, "b": 1.7}
            elif isinstance(w, list):
                node["w"] = [1.7, 1.7]
            for v in node.values():
                one_width(v)
        elif isinstance(node, list):
            for v in node:
                one_width(v)

    p = _mutated(SPEC / "manga-guild.yaml", tmp_path, "one-width", one_width)
    r = manga_ink.run(p, tmp_path / "manga-flat")
    ids = _ids(r["report"])
    check = ids["ink weight spread above 2.4 px"]
    assert check["status"] == "fail"
    assert check["actual"] < 2.4
    # and the authored page clears the same floor with room, so the mutant is not
    # red merely because the threshold was raised over both of them
    real = manga_ink.run(SPEC / "manga-guild.yaml", tmp_path / "manga")
    assert _ids(real["report"])["ink weight spread above 2.4 px"]["status"] == "pass"


def test_manga_withdrawn_eye_count_reports_skipped_not_green():
    """A measurement taken away must leave a `skipped`, not a silence.

    `at least 8 drawn eyes` once reported **67 eyes** on a page that authors ten,
    and every one of the 75 accepted candidates had `enclosed == 0` -- none
    contains an iris. They were the counterspaces of the logotype's glyphs, the
    毛筋 highlights punched through the hair mass, and slivers between figures:
    all of them legitimately white, ink-ringed and eye-shaped (scripts/probes/
    manga_count_probe.py prints the whole list). The second definition, "a small
    dark island sitting on skin", was tried and measured too and returned **0**,
    because the eye's ink is continuous with its lash and brow.

    So `eye_count` is not produced at all. The rule survives in the spec as prose
    and the gate reports it `skipped` with the reason -- which is the only
    honest shape left, and this test is what stops a future edit from quietly
    inventing a third heuristic to turn the light green again.
    """
    m = {}                            # the route's own measurement is absent
    rep = validate.run_acceptance(["at least 8 drawn eyes"], m)
    check = _ids(rep)["at least 8 drawn eyes"]
    assert check["status"] == "skipped"
    assert "eye_count" in check["reason"]
    assert rep["skipped_n"] == 1 and rep["failed_n"] == 0
    # and read the rest of the report, because it is the shape of the whole
    # problem: `passed` is defined as `failed == 0`, so a page whose rules were ALL
    # skipped "passes". Twelve green checks and a refusal by the eye are not a
    # contradiction -- a report is green when nothing failed, not when something
    # was seen.
    assert rep["passed"] is True and rep["passed_n"] == 0


def test_manga_figure_count_is_the_cast_list_not_a_pixel_count(tmp_path):
    """`at least 4 separate figures` was another false green, and its replacement
    is weaker on purpose.

    The pixel count said **11** on a five-person page: a face broken by the
    mouth, the chin shadow or a 毛筋 crossing the jaw becomes two skin masses,
    and each still holds a paper spot, so one head counted twice. The rule now
    reads the spec's own `figures:` list, which proves the author asked for five
    faces and proves nothing about what came out. Whether five came out is the
    thing the gates cannot see (docs/styles.md §0.1, 丙档).
    """
    _need_scipy()
    raw = spec_mod.load_raw(SPEC / "manga-guild.yaml")
    r = manga_ink.run(SPEC / "manga-guild.yaml", tmp_path / "manga")
    assert r["report"]["measured"]["figure_count"] == len(raw["figures"]) == 5


@pytest.mark.parametrize("name,edit,needle", [
    ("collapsed-palette", lambda raw: raw["palette"].update(
        tone_lite=raw["palette"]["skin"]), "distinct"),
    ("flat-at-1:1", lambda raw: raw.update(supersample=1), "supersample"),
    ("no-cast", lambda raw: raw.update(figures=[]), "figures is empty"),
    ("tone-below-a-pixel", lambda raw: raw["tone"].update(pitch=2), "tone.pitch"),
    ("unknown-kind", lambda raw: raw["figures"][0]["parts"].append(
        {"kind": "watercolour", "d": "M0,0 L1,1"}), "unknown kind"),
    ("unknown-profile", lambda raw: raw["figures"][0]["parts"].append(
        {"kind": "ink", "d": "M0,0 L1,1", "w": {"profile": "airbrush"}}),
     "unknown nib profile"),
    ("ghost-template", lambda raw: raw["figures"][0]["parts"].append(
        {"kind": "ink", "use": "wing"}), "which nobody drew"),
])
def test_manga_refuses_a_spec_whose_gates_cannot_be_measured(tmp_path, name, edit,
                                                             needle):
    """Each of these would otherwise have produced a number instead of a painting.

    The two profile- and kind-typo cases are the ones with a history: an unknown
    nib profile falling back to a constant width would be this route's specific
    self-betrayal, since a constant width is the fault the route exists to kill.
    """
    _need_scipy()
    p = _mutated(SPEC / "manga-guild.yaml", tmp_path, name, edit)
    with pytest.raises(manga_ink.MangaError, match=needle):
        manga_ink.run(p, tmp_path / "manga")


# --- B. illustration: green gates on refused sheets ----------------------------

@pytest.mark.parametrize("sheet", ["illust-guild", "illust-fox", "illust-cumulus"])
def test_illustration_sheet_is_reproducible(tmp_path, sheet):
    """The lock, stated as what it is.

    Eleven rules, all green, on all three sheets -- and the viewer refused them.
    That combination is the result, not a contradiction: these gates measure a
    palette, a dot screen, an edge density and a sky's blankness, and none of
    those is the property that decides whether an illustration is good. See
    docs/styles.md §0.1 (档 乙/丙) before reading a pass here as a judgement.
    """
    _need_scipy()
    r = illustration_sample.run(SPEC / f"{sheet}.yaml", tmp_path / sheet)
    rep = r["report"]
    assert rep["passed"], rep["checks"]
    assert rep["failed_n"] == 0
    assert r["manifest"]["content_hash"] == HASHES[sheet]


def test_illustration_screentone_gate_catches_a_sheet_without_dots(tmp_path):
    """网点 is the one thing in this grammar that is a *mechanism*, so the route
    counts its pixels: zero the dot radius and the gate says so."""
    _need_scipy()
    p = _mutated(SPEC / "illust-guild.yaml", tmp_path, "no-dots",
                 lambda raw: raw["tone"].update(dot=0.0))
    r = illustration_sample.run(p, tmp_path / "no-dots")
    ids = _ids(r["report"])
    check = ids["screentone coverage between 2% and 14%"]
    assert check["status"] == "fail"
    assert check["actual"] < 2.0


def test_illustration_sky_gate_catches_a_cluttered_sky(tmp_path):
    """The dusk sheet's floor is `sky negative space between 78% and 92%`, and this
    is the mutant that decides where the floor sits.

    Writing the first version of this test found the FIFTH false green of the
    session. Read off a raw luma gradient, `sky_negative_pct` was measuring the
    Bayer dither, not the composition, and the numbers were INVERTED: flooding the
    sky with two enormous smooth cloud banks took the sheet 45.9 -> 75.6 (painting
    INTO it made it read emptier), while deleting every cloud took it 45.9 -> 44.7.
    An "emptied sky" mutant therefore went the wrong way and could not pin anything.

    The fix was in the measurement, not the mutant: busyness is now judged on a 5x5
    median of the luma, which cancels a 4x4 alternation and keeps a hard edge
    (`illustration_sample._dither_free_edges`). With that, the direction is monotone
    and the honest way to busy a sky -- ten small hard-edged clouds -- drops the
    dusk sheet to 73.5, below the 78% floor. That is what this asserts; the
    flooding and bare mutants both stay inside the band and are logged in
    `docs/styles.md` §8.3 rather than gated.
    """
    _need_scipy()

    def speckled(raw):
        banks = []
        for i in range(10):
            banks.append({"at": [0.06 + 0.1 * (i % 5), 0.17 + 0.05 * (i // 5)],
                          "scale": 0.035, "shade": "shadow", "lit": "rim",
                          "edge": "ink", "band": "top",
                          "lobes": [[-0.6, 0.0, 0.5], [0.0, -0.2, 0.7],
                                    [0.6, 0.05, 0.45]]})
        raw["backdrop"]["clouds"].extend(banks)

    p = _mutated(SPEC / "illust-fox.yaml", tmp_path, "speckled", speckled)
    r = illustration_sample.run(p, tmp_path / "speckled")
    ids = _ids(r["report"])
    check = ids["sky negative space between 78% and 92%"]
    assert check["status"] == "fail", r["report"]["measured"]["sky_negative_pct"]
    assert check["actual"] < 78.0
    # and the authored sheet clears the same floor, so 78 is not a threshold raised
    # over both of them: the direction that was watched going red is the FLOOR
    real = illustration_sample.run(SPEC / "illust-fox.yaml", tmp_path / "fox")
    assert _ids(real["report"])["sky negative space between 78% and 92%"][
        "status"] == "pass"


@pytest.mark.parametrize("name,edit,needle", [
    ("collapsed-palette", lambda raw: raw["palette"].update(
        rim=raw["palette"]["light"]), "distinct"),
    ("no-cast", lambda raw: raw.update(figures=[]), "figures is empty"),
    ("tone-below-a-pixel", lambda raw: raw["tone"].update(pitch=2), "tone.pitch"),
    ("hair-not-a-colour", lambda raw: raw["figures"][0].update(
        hair="wind-swept"), "not a palette"),
])
def test_illustration_refuses_a_spec_whose_gates_cannot_be_measured(tmp_path, name,
                                                                    edit, needle):
    _need_scipy()
    p = _mutated(SPEC / "illust-guild.yaml", tmp_path, name, edit)
    with pytest.raises(illustration_sample.IllusError, match=needle):
        illustration_sample.run(p, tmp_path / name)
