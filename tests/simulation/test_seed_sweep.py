"""L3 fault injection, part 4: the seed sweep (README §12.8).

不确定性扫描: same seed twice -> identical payload; different seeds -> different
payloads. Uses *shrunken* specs (README §12.2's VCAC_TEST_MODE idea) so the
sweep stays seconds-scale and never touches the golden-locked spec files.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from vcac import audio_sample, game_sample, image_sample

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="routes need ffmpeg on PATH")

SEEDS = (0, 1, 2, 3, 4)


def _run(name: str, raw: dict, tmp_path: Path, run_fn) -> dict:
    raw = dict(raw)
    raw["acceptance"] = raw["acceptance"]
    p = tmp_path / f"{name}.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return run_fn(p, tmp_path / name)


def test_image_route_seed_sweep(tmp_path):
    base = yaml.safe_load(
        Path("specs/examples/poster-noise.yaml").read_text(encoding="utf-8"))
    base.update({"width": 256, "height": 256, "octaves": 3})
    base["acceptance"] = ["resolution exactly 256x256", "entropy > 3.0"]

    hashes = []
    for seed in SEEDS:
        r = _run(f"img-seed{seed}", dict(base, seed=seed), tmp_path, image_sample.run)
        assert r["report"]["passed"], r["report"]["checks"]
        hashes.append(r["manifest"]["content_hash"])
    assert len(set(hashes)) == len(SEEDS), "different seeds must differ"

    # same seed, fresh directory -> the same payload again
    r0 = _run("img-seed0-again", dict(base, seed=0), tmp_path, image_sample.run)
    assert r0["manifest"]["content_hash"] == hashes[0]


def test_audio_route_seed_sweep(tmp_path):
    base = yaml.safe_load(
        Path("specs/examples/synth-pad.yaml").read_text(encoding="utf-8"))
    base.update({"duration": "0.6s", "bars": 1})
    base["acceptance"] = ["duration between 0.4 and 0.8",
                          "sample rate exactly 48000", "loudness -16 LUFS",
                          "peak below -1 dBFS", "not silent"]

    hashes = []
    for seed in (0, 1, 2):
        r = _run(f"aud-seed{seed}", dict(base, seed=seed), tmp_path, audio_sample.run)
        assert r["report"]["passed"], r["report"]["checks"]
        hashes.append(r["manifest"]["content_hash"])
    assert len(set(hashes)) == 3, "different seeds must differ"


def test_game_route_seed_sweep(tmp_path):
    base = yaml.safe_load(
        Path("specs/examples/dodge-headless.yaml").read_text(encoding="utf-8"))
    base.update({"duration": "3s"})
    # the sweep asserts determinism/distinctness, not gameplay quality: a 3s
    # session does not guarantee a score or a collision on every seed
    base["acceptance"] = ["player moved", "session terminated"]

    hashes = []
    for seed in (0, 1, 2):
        r = _run(f"game-seed{seed}", dict(base, seed=seed), tmp_path, game_sample.run)
        assert r["report"]["passed"], r["report"]["checks"]
        hashes.append(r["manifest"]["content_hash"])
    assert len(set(hashes)) == 3, "different seeds must differ"

    # determinism across *runs*, not just the in-route replay gate
    r0 = _run("game-seed0-again", dict(base, seed=0), tmp_path, game_sample.run)
    assert r0["manifest"]["content_hash"] == hashes[0]
