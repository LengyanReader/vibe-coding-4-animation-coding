"""Unit tests for the pipeline skeleton: plan validation, cache-key identity,
and cache behaviour — all with fake routes, so none of this needs ffmpeg or
any renderer. ``tools``/``code`` are injected into ``execute`` to keep the
subprocess and package-hash steps out of the unit tier (README §12.1 L0)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from vcac import pipeline, provenance, spec as spec_mod
from vcac.pipeline import Node, PlanError, RouteEntry

SPEC = Path("specs/examples")

FAKE_TOOLS = {"python": "test", "ffmpeg": "test-build"}
FAKE_CODE = {"pipeline.py": "sha256:" + "0" * 64}


def _fake_route(tag: str):
    """A route whose payload is a pure function of its spec and, when the spec
    declares inputs, of the bytes of those injected artifacts — the same shape
    of determinism the real routes are gated on."""
    def run(spec_path, out_dir):
        spec = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
        parts = [tag, str(spec.get("seed", 0))]
        for slot in sorted(spec.get("inputs") or {}):
            parts.append(provenance.sha256_file(Path(spec["inputs"][slot])))
        payload = "|".join(parts).encode("utf-8")
        out_dir = Path(out_dir)
        out = out_dir / f"{tag}.txt"
        out.write_bytes(payload)
        report = {"passed": True, "checks_total": 1, "passed_n": 1,
                  "failed_n": 0, "skipped_n": 0,
                  "checks": [{"id": "fake green", "status": "pass"}]}
        manifest = {"content_hash": provenance.sha256_bytes(payload),
                    "artifacts": [out.name, "report.json", "manifest.json"]}
        # the route contract includes the verdict files on disk (report.json /
        # manifest.json), which the executor's cache validation reads back
        (out_dir / "report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
        return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}
    return run


FAKE_ROUTES = {
    "alpha": RouteEntry(_fake_route("alpha"), "alpha.txt"),
    "beta": RouteEntry(_fake_route("beta"), "beta.txt"),
}


def _write_spec(tmp_path: Path, name: str, seed: int, medium: str = "alpha") -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump({"id": name.removesuffix(".yaml"),
                                 "medium": medium, "seed": seed}),
                 encoding="utf-8")
    return p


def _write_bundle(tmp_path: Path, dag: list[dict]) -> Path:
    p = tmp_path / "bundle.yaml"
    p.write_text(yaml.safe_dump({"id": "t", "dag": dag}), encoding="utf-8")
    return p


# --- plan ---------------------------------------------------------------------

def test_build_plan_orders_upstream_first(tmp_path):
    a = _write_spec(tmp_path, "a.yaml", 1)
    b = _write_spec(tmp_path, "b.yaml", 2, medium="beta")
    c = _write_spec(tmp_path, "c.yaml", 3)
    plan = pipeline.load_plan(_write_bundle(tmp_path, [
        {"id": "c", "spec": c.name},                      # listed first on purpose
        {"id": "b", "spec": b.name, "inputs": {"x": "a"}},
        {"id": "a", "spec": a.name},
    ]), routes=FAKE_ROUTES)
    # consumers come after their inputs; among ready nodes, bundle order wins
    assert [n.id for n in plan] == ["c", "a", "b"]
    assert plan[2].inputs == {"x": "a"}


def test_build_plan_rejects_cycles_unknown_inputs_and_routes(tmp_path):
    a = _write_spec(tmp_path, "a.yaml", 1)
    b = _write_spec(tmp_path, "b.yaml", 2, medium="beta")
    with pytest.raises(PlanError, match="cycle"):
        pipeline.build_plan([
            {"id": "a", "spec": a.name, "inputs": {"x": "b"}},
            {"id": "b", "spec": b.name, "inputs": {"x": "a"}},
        ], base_dir=tmp_path, routes=FAKE_ROUTES)
    with pytest.raises(PlanError, match="unknown node 'nope'"):
        pipeline.build_plan([{"id": "a", "spec": a.name, "inputs": {"x": "nope"}}],
                            base_dir=tmp_path, routes=FAKE_ROUTES)
    with pytest.raises(PlanError, match="not registered"):
        _write_spec(tmp_path, "haiku.yaml", 0, medium="haiku")
        pipeline.build_plan([{"id": "a", "spec": "haiku.yaml"}],
                            base_dir=tmp_path, routes=FAKE_ROUTES)
    with pytest.raises(PlanError, match="duplicate"):
        pipeline.build_plan([{"id": "a", "spec": a.name}, {"id": "a", "spec": a.name}],
                            base_dir=tmp_path, routes=FAKE_ROUTES)


def test_load_plan_single_spec_becomes_one_node(tmp_path):
    plan = pipeline.load_plan(SPEC / "film-mux.yaml")
    assert len(plan) == 1 and plan[0].id == "film-mux" and plan[0].route == "film"
    with pytest.raises(PlanError, match="no route"):
        pipeline.load_plan(_write_spec(tmp_path, "haiku.yaml", 0, medium="haiku"))


def test_every_declared_medium_is_routable():
    for name in ("orbiting-cubes.yaml", "poster-noise.yaml", "synth-pad.yaml",
                 "film-mux.yaml", "dodge-headless.yaml", "swiss-poster.yaml",
                 "variable-weight.yaml", "spectrogram-truth.yaml"):
        raw = spec_mod.load_raw(SPEC / name)
        assert raw["medium"] in pipeline.ROUTES, name


# --- cache key ----------------------------------------------------------------

def _node(spec, inputs=None):
    return Node(id="n", route="alpha", spec_path=spec, inputs=inputs or {})


def test_cache_key_is_stable_and_sensitive(tmp_path):
    s = _write_spec(tmp_path, "s.yaml", 1)
    spec_dict = yaml.safe_load(s.read_text(encoding="utf-8"))
    k1 = pipeline._cache_key(_node(s), spec_dict, {}, FAKE_TOOLS, FAKE_CODE)
    k2 = pipeline._cache_key(_node(s), dict(spec_dict), {}, FAKE_TOOLS, FAKE_CODE)
    assert k1 == k2 and k1.startswith("sha256:")

    changed_spec = dict(spec_dict, seed=2)
    assert pipeline._cache_key(_node(s), changed_spec, {},
                               FAKE_TOOLS, FAKE_CODE) != k1
    assert pipeline._cache_key(_node(s), spec_dict, {"x": "sha256:" + "1" * 64},
                               FAKE_TOOLS, FAKE_CODE) != k1
    assert pipeline._cache_key(_node(s), spec_dict, {},
                               FAKE_TOOLS, {"pipeline.py": "sha256:" + "1" * 64}) != k1
    assert pipeline._cache_key(_node(s), spec_dict, {},
                               {"python": "other"}, FAKE_CODE) != k1


# --- executor behaviour with fake routes ---------------------------------------

def _chain_bundle(tmp_path):
    a = _write_spec(tmp_path, "a.yaml", 1)
    b = _write_spec(tmp_path, "b.yaml", 2, medium="beta")
    c = _write_spec(tmp_path, "c.yaml", 3)
    return _write_bundle(tmp_path, [
        {"id": "a", "spec": a.name},
        {"id": "b", "spec": b.name, "inputs": {"x": "a"}},
        {"id": "c", "spec": c.name},                       # independent of a/b
    ])


def _run(bundle, out):
    plan = pipeline.load_plan(bundle, routes=FAKE_ROUTES)
    results = pipeline.execute(plan, out, routes=FAKE_ROUTES,
                               tools=FAKE_TOOLS, code=FAKE_CODE)
    return plan, results


def test_execute_then_cache_hit(tmp_path):
    bundle = _chain_bundle(tmp_path)
    out = tmp_path / "o"
    _, r1 = _run(bundle, out)
    assert all(not r.cached for r in r1.values())

    _, r2 = _run(bundle, out)
    assert all(r.cached for r in r2.values())
    # a cached node re-reports the recorded verdict, byte-for-byte
    for nid in r1:
        assert r2[nid].content_hash == r1[nid].content_hash
        assert r2[nid].report == r1[nid].report

    # --no-cache is the escape hatch: same dir, everything re-executes
    plan = pipeline.load_plan(bundle, routes=FAKE_ROUTES)
    r3 = pipeline.execute(plan, out, use_cache=False, routes=FAKE_ROUTES,
                          tools=FAKE_TOOLS, code=FAKE_CODE)
    assert all(not r.cached for r in r3.values())


def test_cache_hit_requires_intact_artifacts(tmp_path):
    bundle = _chain_bundle(tmp_path)
    out = tmp_path / "o"
    _run(bundle, out)
    (out / "b" / "beta.txt").write_bytes(b"tampered")
    _, r2 = _run(bundle, out)
    assert not r2["b"].cached and r2["a"].cached and r2["c"].cached


def test_bundle_edge_injects_upstream_artifacts(tmp_path):
    bundle = _chain_bundle(tmp_path)
    out = tmp_path / "o"
    _run(bundle, out)
    resolved = yaml.safe_load(
        (out / "b" / "spec.resolved.yaml").read_text(encoding="utf-8"))
    injected = Path(resolved["inputs"]["x"])
    assert injected == out / "a" / "alpha.txt" and injected.is_file()
    # the consumer's payload actually mixed in the upstream artifact bytes
    assert provenance.sha256_file(injected)[:19].encode() in (out / "b" / "beta.txt").read_bytes()


def test_invalidation_follows_the_affected_subgraph(tmp_path):
    bundle = _chain_bundle(tmp_path)
    out = tmp_path / "o"
    _, r1 = _run(bundle, out)

    # touch only the independent node c: a and b must stay cached
    _write_spec(tmp_path, "c.yaml", 99)
    _, r2 = _run(bundle, out)
    assert r2["a"].cached and r2["b"].cached and not r2["c"].cached

    # touch a: a re-runs, and b (downstream) must follow; c stays as r2 left it
    _write_spec(tmp_path, "a.yaml", 42)
    _, r3 = _run(bundle, out)
    assert not r3["a"].cached and not r3["b"].cached and r3["c"].cached
    assert r3["b"].content_hash != r1["b"].content_hash
    assert r3["c"].content_hash == r2["c"].content_hash
