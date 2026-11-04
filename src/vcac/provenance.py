"""Provenance & reproducibility record (README §6.5 / §10).

A run is pinned by ``hash(spec + code + tool_versions + seeds)``. We record:
  * sha256 of every generator source file (the *editable medium*),
  * sha256 of the spec,
  * the frame **content hash** — the fingerprint that must be identical across
    reruns with the same seed (the mp4 container is secondary; its bytes can
    differ by encoder, so the raw-frame digest is the ground truth),
  * tool + runtime versions, and the resolved seed.

`remake` (README §8) is out of scope for loop #1; this only writes the record.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def content_hash(frame_iter) -> str:
    """Fold raw frame bytes into one digest (streaming, no full-materialise)."""
    h = hashlib.sha256()
    n = 0
    for frame in frame_iter:
        h.update(frame)
        n += 1
    h.update(n.to_bytes(8, "big"))
    return f"sha256:{h.hexdigest()}"


def code_hashes() -> dict:
    pkg = Path(__file__).resolve().parent
    out = {}
    for p in sorted(pkg.rglob("*.py")):
        out[p.relative_to(pkg).as_posix()] = sha256_file(p)
    return out


def tool_versions(ffmpeg_version: str) -> dict:
    try:
        from PIL import __version__ as pillow
    except Exception:
        pillow = "unknown"
    return {
        "python": sys.version.split()[0],
        "pillow": pillow,
        "ffmpeg": ffmpeg_version,
        "platform": platform.platform(),
    }


def build_manifest(*, spec_path, spec_dict, run_id, frame_hash, mp4_hash,
                   ffmpeg_version, acceptance, artifacts, notes=None) -> dict:
    return {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": "vcac-firstloop/0.1",
        "spec": str(spec_path),
        "spec_resolved": spec_dict,
        "code_hashes": code_hashes(),
        "tools": tool_versions(ffmpeg_version),
        "seeds": {"global": spec_dict["seed"]},
        "frame_content_hash": frame_hash,
        "mp4_hash": mp4_hash,
        "acceptance": acceptance,
        "artifacts": artifacts,
        "notes": notes or [],
    }


def write_manifest(manifest: dict, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "manifest.json"
    p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def derive_run_id(spec_dict: dict, frame_hash: str, tools: dict) -> str:
    material = json.dumps(
        {"spec": spec_dict, "frame": frame_hash, "tools": tools},
        sort_keys=True, ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(material).hexdigest()[:16]


def build_record(*, spec_path, spec_dict, content_hash, artifact_hashes,
                 ffmpeg_version, acceptance, artifacts, notes=None,
                 pipeline="vcac-sample/0.1") -> dict:
    """Route-agnostic provenance record: any media (image/audio/video/game) pins
    a run by hash(spec + code + tools + content). ``artifact_hashes`` maps output
    filename -> sha256; ``content_hash`` is the deterministic ground-truth digest
    of the rendered payload (frames, samples, or final game state)."""
    tools = tool_versions(ffmpeg_version)
    return {
        "run_id": derive_run_id(spec_dict, content_hash, tools),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": pipeline,
        "spec": str(spec_path),
        "spec_resolved": spec_dict,
        "code_hashes": code_hashes(),
        "tools": tools,
        "seeds": {"global": spec_dict.get("seed")},
        "content_hash": content_hash,
        "artifact_hashes": artifact_hashes,
        "acceptance": acceptance,
        "artifacts": artifacts,
        "notes": notes or [],
    }
