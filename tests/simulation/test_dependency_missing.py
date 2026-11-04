"""L3 fault injection, part 3: missing dependencies (README §12.8).

依赖缺失时注册表必须降级或拒绝，规划器/执行器不得选不可用工具：
* `require` names the key, the reason, the via and where install notes live;
* the executor refuses a route whose required capability is absent — loudly,
  before any node runs;
* the layout route degrades loudly without a browser (skip-with-reason, never
  a fake render).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from vcac import layout_sample, pipeline, registry
from vcac.pipeline import RouteEntry


def test_require_names_reason_via_and_install_notes():
    fake = {"x": {"available": False, "kind": "t", "via": "binary",
                  "reason": "binary not on PATH"}}
    with pytest.raises(registry.CapabilityError) as e:
        registry.require("x", registry=fake)
    msg = str(e.value)
    assert "binary not on PATH" in msg and "via binary" in msg and "docs/tools.md" in msg


def _registry_without_ffmpeg(monkeypatch):
    monkeypatch.setattr(registry, "build_registry", lambda: {
        "ffmpeg": {"available": False, "kind": "video/assembly", "via": "binary",
                   "reason": "simulated absent"}})


def test_executor_refuses_a_route_whose_capability_is_absent(tmp_path, monkeypatch):
    """The gate fires BEFORE the route runs: no out_dir, no partial output."""
    _registry_without_ffmpeg(monkeypatch)
    routes = {"alpha": RouteEntry(lambda spec, out: (_ for _ in ()).throw(
        AssertionError("route must never run when a capability is missing")),
        "alpha.txt", requires=("ffmpeg",))}
    spec = tmp_path / "s.yaml"
    spec.write_text(yaml.safe_dump({"id": "s", "medium": "alpha", "seed": 1,
                                    "acceptance": ["fake rule"]}), encoding="utf-8")
    out = tmp_path / "o"
    with pytest.raises(registry.CapabilityError, match="ffmpeg"):
        pipeline.execute(pipeline.load_plan(spec, routes), out, routes=routes)
    # the gate fires before the route: node dir may exist, but no artifact and
    # no report were ever written
    assert not (out / "s" / "report.json").exists()
    assert not (out / "s" / "alpha.txt").exists()


def test_layout_degrades_loudly_without_a_browser(tmp_path, monkeypatch):
    """No playwright -> RuntimeError naming the capability. Never a fake render,
    never a silent pass (browser.py's contract, pinned here)."""
    from vcac import browser
    monkeypatch.setattr(browser, "availability", lambda: (False, "simulated absent"))
    raw = yaml.safe_load(
        Path("specs/examples/swiss-poster.yaml").read_text(encoding="utf-8"))
    spec = tmp_path / "poster.yaml"
    spec.write_text(yaml.safe_dump(raw), encoding="utf-8")
    out = tmp_path / "o"
    with pytest.raises(RuntimeError, match="browser rasterizer"):
        layout_sample.run(spec, out)
    assert not (out / "poster.png").exists()
    assert not (out / "report.json").exists()
