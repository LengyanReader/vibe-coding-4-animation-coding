"""End-to-end regression tests for every media route (README §12 L2).

Each route is run into a tmp dir and asserted on:
  * acceptance PASSED (all coded gates green),
  * determinism (the route's own re-run/replay gate is part of acceptance),
  * the golden **content hash** — the bit-fingerprint of the creative payload.

Golden hashes are human-confirmed snapshots (README §12.2): they change only when
a generator intentionally changes, and the diff is the review surface. Container
byte hashes (mp4/wav) are NOT pinned here — they can move with the encoder; the
raw-payload digest is the stable ground truth.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from vcac import (audio_sample, film_sample, firstloop, game_sample, image_sample)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="routes need ffmpeg on PATH")

SPEC = Path("specs/examples")

# human-confirmed golden content hashes (raw payload digests)
GOLDEN = {
    "video": "sha256:d27999e71afd2f516700f35f188b87bc2bfaf1920a6c86f50aa52802df12511c",
    "image": "sha256:d538c35060a426347c6a798511773d3c203cc125c10ab5d9351f5a58f6882620",
    "audio": "sha256:2f9351c5a881face08590f61c61202842f2d5e408c398b0b21fd9775d3ded58a",
    "game": "sha256:c67acbf8d0afc89c89b89bbf870bd2ca7d66be1d4ac38277f234e41c75be042a",
}


def test_video_route(tmp_path):
    r = firstloop.run(SPEC / "orbiting-cubes.yaml", tmp_path / "v", keep_frames=False)
    assert r["report"]["passed"], r["report"]["checks"]
    assert r["manifest"]["frame_content_hash"] == GOLDEN["video"]


def test_image_route(tmp_path):
    r = image_sample.run(SPEC / "poster-noise.yaml", tmp_path / "i")
    assert r["report"]["passed"], r["report"]["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN["image"]


def test_audio_route(tmp_path):
    r = audio_sample.run(SPEC / "synth-pad.yaml", tmp_path / "a")
    assert r["report"]["passed"], r["report"]["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN["audio"]


def test_game_route(tmp_path):
    r = game_sample.run(SPEC / "dodge-headless.yaml", tmp_path / "g")
    assert r["report"]["passed"], r["report"]["checks"]
    assert r["manifest"]["content_hash"] == GOLDEN["game"]


def test_composability_route(tmp_path):
    # produce the two independent nodes, then join them on one clock
    v = firstloop.run(SPEC / "orbiting-cubes.yaml", tmp_path / "v", keep_frames=False)
    a = audio_sample.run(SPEC / "synth-pad.yaml", tmp_path / "a")
    assert v["report"]["passed"] and a["report"]["passed"]

    film_spec = {
        "id": "film-test",
        "acceptance": ["has video stream", "has audio stream",
                       "a/v sync within 0.1s", "duration between 5.5 and 6.5"],
        "inputs": {"video": str(tmp_path / "v" / "final.mp4"),
                   "audio": str(tmp_path / "a" / "master.wav")},
        "shortest": True,
    }
    p = tmp_path / "film.yaml"
    p.write_text(yaml.safe_dump(film_spec), encoding="utf-8")
    fr = film_sample.run(p, tmp_path / "f")
    assert fr["report"]["passed"], fr["report"]["checks"]
    assert fr["report"]["measured"]["av_delta_seconds"] <= 0.1
