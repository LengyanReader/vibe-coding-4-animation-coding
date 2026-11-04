"""End-to-end proof of the pipeline skeleton (roadmap §4 loop #1): the
three-node media bundle runs the *real* routes, reuses all of them on the
second pass, and re-runs exactly the affected sub-graph when one spec changes.

Golden hashes: the video/audio node payloads must equal the single-route
goldens in test_routes.py — the executor running a route has to be
indistinguishable from running the route directly. The film node's hash is
deliberately NOT pinned here: film's content hash is a function of its
inputs' *container* file hashes (its own documented semantics, film_sample.py),
so instead the executor's film node is cross-checked against a direct
film_sample.run over the same artifacts.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from vcac import film_sample, pipeline, spec as spec_mod

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="routes need ffmpeg on PATH")

SPEC = Path("specs/examples")
BUNDLE = SPEC / "media-bundle.yaml"

# raw payload goldens shared with tests/e2e/test_routes.py (README §12.2)
GOLDEN = {
    "video": "sha256:d27999e71afd2f516700f35f188b87bc2bfaf1920a6c86f50aa52802df12511c",
    "audio": "sha256:2f9351c5a881face08590f61c61202842f2d5e408c398b0b21fd9775d3ded58a",
}


def test_bundle_executes_then_caches_every_node(tmp_path):
    out = tmp_path / "b"
    r1, m1 = pipeline.run_bundle(BUNDLE, out)
    assert m1["acceptance"]["passed"], {n: r.report["checks"] for n, r in r1.items()}
    assert m1["acceptance"]["executed_n"] == 3 and m1["acceptance"]["cached_n"] == 0
    # the executor runs a route exactly as running the route does
    assert r1["video"].content_hash == GOLDEN["video"]
    assert r1["audio"].content_hash == GOLDEN["audio"]

    # the bundle edge was materialised as evidence of what actually ran
    resolved = yaml.safe_load(
        (out / "film" / "spec.resolved.yaml").read_text(encoding="utf-8"))
    assert resolved["inputs"]["video"] == str(out / "video" / "final.mp4")
    assert resolved["inputs"]["audio"] == str(out / "audio" / "master.wav")
    # and the composed node equals a direct film route over the same artifacts
    direct_spec = tmp_path / "film-direct.yaml"
    direct_spec.write_text(yaml.safe_dump({
        "id": "film-direct", "shortest": True,
        "acceptance": ["has video stream", "has audio stream",
                       "a/v sync within 0.1s"],
        "inputs": resolved["inputs"],
    }), encoding="utf-8")
    direct = film_sample.run(direct_spec, tmp_path / "direct")
    assert r1["film"].content_hash == direct["manifest"]["content_hash"]

    # second pass over the same out dir: everything cached, verdicts preserved
    r2, m2 = pipeline.run_bundle(BUNDLE, out)
    assert m2["acceptance"]["cached_n"] == 3 and m2["acceptance"]["executed_n"] == 0
    assert m2["run_id"] == m1["run_id"]          # same plan + same node hashes
    for nid, r in r1.items():
        assert r2[nid].cached and r2[nid].content_hash == r.content_hash
        assert r2[nid].report == r.report         # skipped != passed: the green
    assert r2["film"].report["measured"]["av_delta_seconds"] <= 0.1  # ...is shown


def test_bundle_invalidates_only_the_affected_subgraph(tmp_path):
    out = tmp_path / "b"
    r1, m1 = pipeline.run_bundle(BUNDLE, out)
    assert m1["acceptance"]["passed"], m1["acceptance"]

    # one field of one upstream spec moves -> that node and its consumer re-run,
    # the untouched sibling is reused from cache
    raw = spec_mod.load_raw(SPEC / "synth-pad.yaml")
    raw["seed"] = 43
    mutated = tmp_path / "synth-pad-seed43.yaml"
    mutated.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    bundle2 = tmp_path / "bundle2.yaml"
    bundle2.write_text(yaml.safe_dump({
        "id": "media-bundle-mut",
        "dag": [
            {"id": "video", "spec": str((SPEC / "orbiting-cubes.yaml").resolve())},
            {"id": "audio", "spec": str(mutated.resolve())},
            {"id": "film", "spec": str((SPEC / "film-mux.yaml").resolve()),
             "inputs": {"video": "video", "audio": "audio"}},
        ],
    }, allow_unicode=True), encoding="utf-8")
    r2, m2 = pipeline.run_bundle(bundle2, out)
    assert m2["acceptance"]["passed"], {n: r.report["checks"] for n, r in r2.items()}
    assert r2["video"].cached and r2["video"].content_hash == r1["video"].content_hash
    assert not r2["audio"].cached and r2["audio"].content_hash != r1["audio"].content_hash
    assert not r2["film"].cached
    # the cache accounting matches what actually happened
    assert m2["acceptance"]["cached_n"] == 1 and m2["acceptance"]["executed_n"] == 2


def test_cache_hit_needs_intact_artifacts(tmp_path):
    """A matching key with a moved artifact is a miss: the cache trusts files it
    re-hashed, not files it remembers."""
    out = tmp_path / "b"
    pipeline.run_bundle(BUNDLE, out)
    (out / "audio" / "master.wav").write_bytes(b"tampered")
    r2, m2 = pipeline.run_bundle(BUNDLE, out)
    assert m2["acceptance"]["passed"], m2["acceptance"]
    assert not r2["audio"].cached           # re-ran because its artifact moved
    assert r2["video"].cached and r2["film"].cached  # their files still check out
