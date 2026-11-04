"""Unit tests for the capability registry (README §6.2).

``build_registry()`` is the probe everything else trusts; these tests pin its
*shape* and the ``require`` contract. Binary-dependent assertions are gated on
the binary actually being on PATH — an absent ffmpeg must skip, not fail,
because the registry's whole point is that availability is per-machine/per-
interpreter and honestly reported.
"""
from __future__ import annotations

import shutil

import pytest

from vcac import registry


def test_registry_shape_and_core_keys():
    reg = registry.build_registry()
    # keys every interpreter this suite can run on must have
    for key in ("numpy", "pyyaml", "pytest", "playwright-browsers", "variable-fonts"):
        assert key in reg, key
    for key, e in reg.items():
        assert set(e) >= {"available", "kind", "via"}, (key, e)
        assert isinstance(e["available"], bool)
    # the interpreter running this test can obviously import these
    assert reg["numpy"]["available"] and reg["pyyaml"]["available"]
    # structure of the two non-table entries matches what doctor prints
    assert reg["playwright-browsers"]["via"] == "LOCALAPPDATA"
    assert reg["variable-fonts"]["via"] == "font dirs"


def test_require_raises_for_unknown_and_unavailable():
    with pytest.raises(registry.CapabilityError, match="unknown to the registry"):
        registry.require("definitely-not-a-capability", registry={})
    fake = {"x": {"available": False, "kind": "t", "via": "binary",
                  "reason": "binary not on PATH"}}
    with pytest.raises(registry.CapabilityError, match="binary not on PATH"):
        registry.require("x", registry=fake)


def test_path_shadows_only_reports_known_traps():
    for name, _hit in registry.path_shadows():
        assert name in registry.TRAP_NAMES


if shutil.which("ffmpeg"):
    def test_require_ffmpeg_when_present():
        e = registry.require("ffmpeg")
        assert e["available"] and e["kind"] == "video/assembly"
else:
    def test_require_ffmpeg_when_absent_is_loud():
        with pytest.raises(registry.CapabilityError, match="ffmpeg"):
            registry.require("ffmpeg")
