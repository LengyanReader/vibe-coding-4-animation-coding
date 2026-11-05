"""The three routes the 2026-11-05 WIP left untested: ink, sampled piano, anime.

Same two duties as the small cases, and the same reason.

  * the happy path is pinned to a human-confirmed **golden content hash**, read
    back by a different process than the one that recorded it, so an ordinary
    pass here is also a cross-process reproducibility proof;
  * every gate ships with a **mutant that has been seen to fail it**, or with the
    refusal that replaces the measurement. A gate nobody has watched go red is
    indistinguishable from a gate that cannot go red.

Measured per-route cost on this machine (C:/Python313, worth knowing before
adding to these): ink 4.8 s per render, fluidsynth piano 21.8 s per render
(two renders per run for the determinism gate), anime 24 fps ≈ 40 s, the 8 fps
anime mutant ≈ 19 s.

Downloaded assets (font, SoundFont, the vendored fluidsynth binary) are not in
git -- see assets/assets.lock.json and scripts/fetch_assets.py. A route whose
asset is absent **skips with the fetch command in the reason**; it does not
render a substitute and it does not report a green.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

from vcac import (anime_sample, audio_sample, ink_landscape, registry,
                  spec as spec_mod, validate)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="routes need ffmpeg on PATH")

SPEC = Path("specs/examples")
FONT = Path("assets/fonts/ZhiMangXing-Regular.ttf")
SF2 = Path("assets/soundfonts/FluidR3_GM.sf2")

# human-confirmed golden content hashes (raw payload digests, cross-process).
# ink moved twice on 2026-11-05. First move, recorded above: the route drew every
# layer's 勾/皴 onto a PIL image that did not alias the float buffer, so all but
# the nearest layer's strokes were discarded -- b1628dc9... was the hash of a
# painting that ignored its own spec, 7b767025... the same chain with the strokes
# written back. Second move, to c3706cc1...: the 山水 rework -- 远山淡墨 as a
# collapsed CONTRAST range rather than a pale mountain, a 皴法 per geology
# (雨点/披麻/斧劈/折带), 点苔 to close each mass, drifting 云气 bands instead of a
# ruled strip, and a foreground shore with 江流 + 树 + 亭 so the river the title
# promises actually passes. anime moved to 1ca18f25... for the same kind of reason:
# the roof structure, the 屋身 under it, the 飘带 and the clouds were rebuilt, and
# the clip gained a gate that reads the title element from the pixels carrying the
# roof-tile colours rather than trusting a fade to hold it.
# These two hashes are the OUTPUT OF THE REWORK, not yet a human-confirmed pair:
# the review step is the before/after look, and `git stash` of the working set
# reproduces the previous sheet from 7b767025 / c05722c8 if the rework is refused.
GOLDEN = {
    "ink": "sha256:c3706cc195f7634b701499070088a6207498385f242594dfcacf3cec313c7639",
    "piano": "sha256:b5bf04fd6bc25714837db36478a703219981570ee707fed179469fcc339ea071",
    "anime": "sha256:1ca18f254fba323945bfa7ca1836be358abeff152f790960c078693c6e2d67af",
}


def _mutated(spec_path: Path, tmp_path: Path, name: str, edit) -> Path:
    raw = spec_mod.load_raw(spec_path)
    edit(raw)
    p = tmp_path / f"{name}.yaml"
    p.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return p


def _need_asset(path: Path, what: str) -> None:
    """Skip with the fetch command instead of lying in either direction."""
    if not path.is_file():
        pytest.skip(f"{what} not fetched: run python scripts/fetch_assets.py "
                    f"(expected at {path})")


def _capability(key: str):
    try:
        return registry.require(key)
    except registry.CapabilityError as e:
        pytest.skip(str(e))


# --- A. ink-landscape: 画理 as measurable constraints -------------------------

def test_ink_route(tmp_path):
    pytest.importorskip("scipy", reason="ink route needs scipy.ndimage")
    _need_asset(FONT, "the colophon face")

    r = ink_landscape.run(SPEC / "ink-landscape.yaml", tmp_path / "ink")
    rep, m = r["report"], r["report"]["measured"]
    assert rep["passed"], rep["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN["ink"]
    assert (m["width"], m["height"]) == (768, 1024)
    # the palette ceiling rule speaks about the artifact, so the artifact's own
    # colour count is what is pinned: all seven declared tones actually appear
    assert (m["palette_distinct_colors"], m["palette_declared_colors"]) == (7, 7)
    assert m["seal_count"] == 1
    assert m["value_bands_min_pct"] > 1.0
    assert 25.0 < m["negative_space_pct"] < 60.0
    # the 留白 gate is the one with the thinnest margin on this artifact, so the
    # margin is pinned rather than asserted as comfort. It moved 237.9 -> 239.65
    # under the rework: `mist_top` went 0.26 -> 0.20 and the band now holds FULL
    # paper across its first ~60% before easing out, because the old blend let the
    # wash blur creep upward and left a grey sky. 远山淡墨 then sits ABOVE the mist
    # at alpha 0.28, so it no longer carries a contour line up into the strip --
    # the thing that used to press this number down toward its floor.
    assert m["mist_luma"] == pytest.approx(239.65, abs=0.5)
    assert m["painted_entropy"] > 1.8
    # Size is the 占空间 check from the brief, and it is a *consequence* of the
    # painting, not a quality knob: seven tones on a 768x1024 sheet compress well
    # until texture is laid on. Three ranges -> five, plus 皴法 strokes and 点苔,
    # took the entropy 1.8 -> 2.05 and the byte count ~45 KB -> 162,006. The old
    # 60 KB ceiling was pinned to whichever sheet existed when the route shipped
    # and would have refused a BETTER painting; the honest bound is the project's
    # own "small, not space-hungry" line, and 200 KB is that, with the measured
    # value written down so a future jump is a decision and not a surprise.
    assert (tmp_path / "ink" / "ink.png").stat().st_size < 200_000
    # licensed external input belongs in the record, hashed like the code
    fonts = r["manifest"]["fonts"]
    assert fonts[0]["licence"] == "OFL-1.1"
    assert fonts[0]["sha256"].startswith("sha256:")


def test_ink_writeback_puts_the_mid_ridge_strokes_on_the_sheet(tmp_path):
    """Regression pin for the defect the golden re-record bought.

    Counted off the artifact in the mid-ridge band (rows 0.40-0.72 of the
    canvas): 浓 ink pixels there were **2251** while the strokes were being
    thrown away and **6168** after the write-back. A declared `contour_ink: 4`
    and `style: yudian` on the middle layer is only a knob if the pixels move."""
    pytest.importorskip("scipy", reason="ink route needs scipy.ndimage")
    _need_asset(FONT, "the colophon face")

    ink_landscape.run(SPEC / "ink-landscape.yaml", tmp_path / "ink")
    art = np.asarray(Image.open(tmp_path / "ink" / "ink.png").convert("RGB"))
    h = art.shape[0]
    band = art[int(h * 0.40):int(h * 0.72)]
    ink4 = np.array(spec_mod.parse_hex("#3B3630"))
    assert int(np.all(band == ink4, axis=-1).sum()) > 5000


def test_ink_value_band_gate_catches_a_flattened_ramp(tmp_path):
    """Paint everything on the lightest tone: the ramp collapses, and both the
    per-band occupancy and the entropy of the painted region have to say so."""
    pytest.importorskip("scipy", reason="ink route needs scipy.ndimage")
    _need_asset(FONT, "the colophon face")

    def one_tone(raw):
        for lay in raw["layers"]:
            # every knob that picks a tone is pinned, including the 焦墨 pass: the
            # point of the mutant is "one tone everywhere", and leaving `jiao` on
            # would test the renderer's clamp instead of the renderer's ramp
            lay["ink"] = lay["contour_ink"] = lay["texture_ink"] = 1
            lay.pop("jiao", None)

    p = _mutated(SPEC / "ink-landscape.yaml", tmp_path, "flattened", one_tone)
    r = ink_landscape.run(p, tmp_path / "ink")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["five ink value bands each above 1.0%"]["status"] == "fail"
    assert ids["painted-region entropy above 1.8"]["status"] == "fail"
    m = r["report"]["measured"]
    # The collapse is read in the two numbers that actually describe it, NOT in
    # `palette_distinct_colors`. That assertion used to demand 6 and the 2026-11-05
    # rework (five ranges, 皴法 per geology, 点苔, the 江流/树/亭 markers) made it
    # unreachable at 7 -- and measuring why (scripts/probes/ink_flatten_probe.py)
    # showed the count was never a property of the ramp: with the whole sheet
    # flattened to one tone AND the features deleted, the four dark tones still
    # appear as 0.02-4.4% residues of the paper-tooth dither and the 积墨 passes.
    # Counting them was a claim about how many colours a 3-layer renderer happened
    # to leave on paper. These two are the real signal:
    assert m["value_bands_min_pct"] < 1.0          # a band went essentially unpainted
    assert m["painted_entropy"] < 1.0              # and the painted region is nearly one tone
    # the flattened sheet is dominated by the single declared tone
    art = np.asarray(Image.open(next(Path(r["out_dir"]).glob("*.png"))).convert("RGB"))
    counts = {(int(a), int(b), int(c)): n for (a, b, c), n
              in zip(*[x.tolist() for x in np.unique(art.reshape(-1, 3), axis=0,
                                                     return_counts=True)])}
    share = max(counts.values()) / sum(counts.values())
    assert share > 0.45                            # paper 45% + ink1 49%: one tone rules
    assert m["negative_space_pct"] == pytest.approx(45.0, abs=2.0)


def test_ink_whitespace_gate_catches_an_unpainted_sheet(tmp_path):
    """留白 has a *ceiling* as well as a floor: a sheet that is 99% paper is not
    more 空灵, it is blank. This mutant also pins the crash fix -- an empty layer
    list used to reach the colophon with no image object at all."""
    pytest.importorskip("scipy", reason="ink route needs scipy.ndimage")
    _need_asset(FONT, "the colophon face")

    p = _mutated(SPEC / "ink-landscape.yaml", tmp_path, "nolayers",
                 lambda raw: raw.update(layers=[]))
    r = ink_landscape.run(p, tmp_path / "ink")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["negative space between 25% and 60%"]["status"] == "fail"
    assert ids["negative space between 25% and 60%"]["actual"] == pytest.approx(99.4, abs=0.5)


def test_ink_mist_gate_catches_a_flooded_sky(tmp_path):
    """A layer whose wash reaches into the sky kills 云气: the measured strip
    drops from 237.9 to 182.8 luma, which is what the rule is for."""
    pytest.importorskip("scipy", reason="ink route needs scipy.ndimage")
    _need_asset(FONT, "the colophon face")

    def blanket(raw):
        raw["layers"].append({"base_y": 0.10, "amp": 1.4, "freq": 2, "warp": 0.0,
                              "ink": 5, "alpha": 1.0, "reach": 0.2, "style": "none",
                              "contour_ink": 5, "texture_ink": 5})

    p = _mutated(SPEC / "ink-landscape.yaml", tmp_path, "blanket", blanket)
    r = ink_landscape.run(p, tmp_path / "ink")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["mist region luminance at least 235"]["status"] == "fail"
    assert r["report"]["measured"]["mist_luma"] < 220


@pytest.mark.parametrize("name,edit,needle", [
    ("seal-as-paper", lambda raw: raw["palette"].update(
        seal=raw["palette"]["paper"]), "distinct"),
    ("ramp-collapsed", lambda raw: raw["palette"].update(
        ink2=raw["palette"]["ink1"]), "distinct"),
    ("mist-zero", lambda raw: raw.update(mist_top=0.0), "mist_top"),
    ("reach-zero", lambda raw: raw["layers"].append(
        {"base_y": 0.5, "amp": 0.3, "freq": 3, "warp": 0.0, "ink": 4,
         "alpha": 1.0, "reach": 0.0, "style": "none", "contour_ink": 4}),
     "reach must be > 0"),
    ("font-absent", lambda raw: raw["font"].update(
        paths=["assets/fonts/not-fetched.ttf"]), "colophon font"),
])
def test_ink_refuses_a_spec_whose_gates_cannot_be_measured(tmp_path, name, edit, needle):
    """Each of these once produced a confident green over a broken measurement.

    Measured on this route: an ink-coloured seal scored **5 seals** (the whole
    sheet matched the dilate-and-label filter), a ramp collapsed onto one tone
    scored 41% occupancy in every band, and `reach: 0.0` divided the wash depth
    by zero, quantised the resulting NaN onto the palette and passed **all nine**
    rules. Refusing is the layout route's stance against a grid that does not
    divide (audit A6)."""
    pytest.importorskip("scipy", reason="ink route needs scipy.ndimage")
    p = _mutated(SPEC / "ink-landscape.yaml", tmp_path, name, edit)
    with pytest.raises(ink_landscape.InkError, match=needle):
        ink_landscape.run(p, tmp_path / "ink")


# --- B. sampled piano: a real instrument behind the same audio contract --------

def test_piano_route(tmp_path):
    _need_asset(SF2, "the General MIDI SoundFont")
    entry = _capability("fluidsynth")

    r = audio_sample.run(SPEC / "kern-piano.yaml", tmp_path / "p")
    rep, m = r["report"], r["report"]["measured"]
    assert rep["passed"], rep["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN["piano"]
    assert rep["engine"] == "fluidsynth"
    assert m["sample_rate"] == 48000 and m["channels"] == 2
    assert m["lufs_i"] == pytest.approx(-18.0, abs=1.0)
    assert m["peak_dbfs"] < -1.0 and m["clipping_pct"] == 0.0
    # the score is the authored substance: every note, reviewable without a DAW.
    # the wav fluidsynth rendered from it is a transport and is deleted
    assert "score.mid" in r["manifest"]["artifacts"]
    assert not (tmp_path / "p" / "render.wav").exists()
    assert (tmp_path / "p" / "score.mid").stat().st_size > 200
    # a repo-vendored tool is not a PATH install: the record says which
    assert entry["via"] == "repo-tool"
    assert r["manifest"]["soundfont"]["sha256"].startswith("sha256:")


def test_piano_lufs_gate_catches_a_master_that_is_too_quiet(tmp_path):
    """Ask the normaliser for -30 LUFS and the delivery still reads -18: the rule
    measures the artifact, not the request."""
    _need_asset(SF2, "the General MIDI SoundFont")
    _capability("fluidsynth")

    def quieter(raw):
        raw["target_lufs"] = -30.0

    p = _mutated(SPEC / "kern-piano.yaml", tmp_path, "quiet", quieter)
    r = audio_sample.run(p, tmp_path / "p")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["loudness -18 LUFS"]["status"] == "fail"
    assert ids["loudness -18 LUFS"]["actual"] < -25.0


def test_piano_refuses_a_soundfont_that_was_never_fetched(tmp_path):
    """No silent fallback to whatever synth is installed: the spec names a
    SoundFont, and its absence is an error that says what to run."""
    _capability("fluidsynth")

    def absent(raw):
        raw["soundfont"]["paths"] = ["assets/soundfonts/not-fetched.sf2"]

    p = _mutated(SPEC / "kern-piano.yaml", tmp_path, "absent", absent)
    with pytest.raises(spec_mod.SpecError, match="needs a SoundFont"):
        audio_sample.run(p, tmp_path / "p")


# --- C. anime: the same frame contract, a second renderer ----------------------

def test_anime_route(tmp_path):
    pytest.importorskip("PIL", reason="cel renderer draws with Pillow")

    r = anime_sample.run(SPEC / "anime-eave.yaml", tmp_path / "a")
    rep, m = r["report"], r["report"]["measured"]
    assert rep["passed"], rep["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN["anime"]
    assert (m["duration"], m["width"], m["height"]) == (12.0, 960, 540)
    assert m["scene_cuts"] == 1
    # the threshold is only honest with its margin next to it: the cut's spike
    # is 4.2x the loudest shift that was NOT flagged, and the fades -- whose
    # per-frame histogram shift is *larger* than the cut's -- are counted
    # separately as gradual, not silently as cuts. The spike itself measured
    # 0.2992 before the 2026-11-05 roof rebuild and 0.2683 after: once the 屋身 is
    # drawn the two shots share more tile colour, so their histograms are closer
    # at the cut. The margin line below is the number that matters, and it held.
    cd = rep["cut_detection"]
    assert cd["hard_cut_frames"] == [144]
    assert cd["diff_at_hard_cuts"] == [pytest.approx(0.2683, abs=0.005)]
    assert cd["largest_unflagged_diff"] < cd["threshold"]
    assert cd["margin_factor"] >= 4.0
    assert cd["gradual_frames"] > 20
    assert not (tmp_path / "a" / "frames").exists()
    # Size is the brief's "不要占空间特别大" line, and like the ink sheet's ceiling
    # it moved when the artwork got better: the rebuilt roof structure, the 屋身
    # under it, the 飘带 and the layered clouds are more pixels changing between
    # frames, and 12 s of 960x540 went ~700 KB -> 1,023,646 B, past the 800 KB that
    # was pinned to whichever clip existed when the route shipped. Raising it is a
    # policy call, so the numbers are written down: the content hash, not the byte
    # count, is the integrity control, and 1.5 MB stays three orders of magnitude
    # under the 148 MB SoundFont this project already ships.
    assert (tmp_path / "a" / "clip.mp4").stat().st_size < 1_500_000


def test_anime_cut_gate_catches_a_camera_that_never_cuts(tmp_path):
    """Delete the cut event and drop to 8 fps (a cheaper render): no isolated
    histogram spike survives, so `at least 1 scene cut` must go red rather than
    count the fades as edits."""
    pytest.importorskip("PIL", reason="cel renderer draws with Pillow")

    def static(raw):
        raw["format"]["fps"] = 8
        raw["timeline"] = [e for e in raw["timeline"] if e["action"] != "cut"]

    p = _mutated(SPEC / "anime-eave.yaml", tmp_path, "nocut", static)
    r = anime_sample.run(p, tmp_path / "a")
    ids = {c["id"]: c for c in r["report"]["checks"]}
    assert ids["at least 1 scene cut"]["status"] == "fail"
    assert ids["at least 1 scene cut"]["actual"] == 0
    assert r["report"]["cut_detection"]["hard_cut_frames"] == []


def test_anime_is_a_medium_not_a_new_schema():
    """`medium: anime` reuses format/style/render/timeline; a spec that needed
    its own keys would not be a second renderer over one contract."""
    s = spec_mod.load(SPEC / "anime-eave.yaml")
    assert s.medium == "anime" and s.fps == 24 and s.n_frames == 288
    assert "anime" in spec_mod.VIDEO_CONTRACT_MEDIA
    raw = spec_mod.load_raw(SPEC / "anime-eave.yaml")
    assert set(raw) <= {"id", "title", "medium", "format", "style", "render",
                        "timeline", "acceptance", "assumptions"}


# --- wiring: the rule vocabulary the new specs rely on -------------------------

def test_scene_cuts_rule_without_the_measurement_is_skipped():
    """A route that never measured cuts must report `skipped`, never a green:
    the gate exists in the vocabulary, but this artifact cannot answer it."""
    out = validate.run_acceptance(["at least 1 scene cut"],
                                  {"duration": 12.0, "width": 960})
    assert out["checks"][0]["status"] == "skipped"
    assert "scene_cuts" in out["checks"][0]["reason"]
