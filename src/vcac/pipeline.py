"""pipeline.py — plan → execute → cache: the DAG skeleton over the route modules.

Eight routes now share one de-facto contract
(``load_raw → render → measure → validate.run_acceptance → report.json →
manifest``) but orchestrate themselves as siblings, and film-mux proved the
composition seed: its content hash is a pure function of its inputs' hashes
(film_sample.py). This module generalises that into an executor with
**content-hash caching** — a node re-runs only when something that can change
its output changed (docs/roadmap-development.md §4 loop #1).

Honest scope, so nobody mistakes this for more than it is:

* **Node granularity = one whole route ``run()``.** The routes are reused
  unchanged; render/encode/validate become separate DAG nodes only when a
  second concrete case says where to cut (roadmap §3: extract, don't guess).
* **The cache key includes the whole-package code hash** — honest but coarse:
  any edit to any ``vcac/*.py`` invalidates every node. Fine-grained per-node
  code attribution is deferred with the fine-grained nodes.
* **Upstream identity in the key is the payload content hash** (frame pixels,
  samples, ...) — the ground truth the golden tests lock. A route's *own*
  manifest may still record container file hashes (film does); the two
  purposes stay distinct on purpose.
* **A cache hit re-reports the acceptance verdict recorded when the node last
  ran** — skipped ≠ passed, so a cached green still shows its checks, and the
  artifacts are re-hashed before the hit is trusted.
* No retry/resume here: the repair loop belongs to the codegen stage
  (README §5), which has not been built.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import (audio_sample, anime_sample, ffmpeg, film_sample, firstloop,
               game_sample, image_sample, ink_landscape, layout_sample,
               provenance, registry, spectrum_sample, type_sample)

PIPELINE_VERSION = "vcac-pipeline/0.1"

CACHE_KEY_FILE = "_cache_key.json"


class PlanError(ValueError):
    """The plan is malformed: unknown route, unknown input, duplicate id, cycle."""


class NodeExecutionError(RuntimeError):
    """A node's route raised. The executor has already written the node's
    ``error.json`` evidence and stopped the run; ``node_id`` names the node and
    ``partial_results`` carries everything that completed before it."""

    def __init__(self, node_id: str, cause: BaseException):
        super().__init__(f"node '{node_id}' failed: {type(cause).__name__}: {cause}")
        self.node_id = node_id
        self.cause = cause
        self.partial_results: dict[str, "NodeResult"] = {}


@dataclass(frozen=True)
class RouteEntry:
    """How a medium plugs into the executor.

    ``provides`` names the artifact downstream nodes consume when a bundle edge
    injects it into their ``inputs:`` mapping; ``requires`` are registry keys
    checked (loudly) right before the route runs — never on a cache hit.
    """
    run: object                      # callable(spec_path: Path, out_dir: Path) -> dict
    provides: str
    requires: tuple[str, ...] = ()


#: medium (a spec's ``medium`` field) -> route entry
ROUTES = {
    "video": RouteEntry(firstloop.run, "final.mp4", ("ffmpeg",)),
    "anime": RouteEntry(anime_sample.run, "clip.mp4", ("ffmpeg",)),
    "image": RouteEntry(image_sample.run, "poster.png"),
    "audio": RouteEntry(audio_sample.run, "master.wav", ("ffmpeg",)),
    "film": RouteEntry(film_sample.run, "film.mp4", ("ffmpeg",)),
    "game": RouteEntry(game_sample.run, "playtest.mp4", ("ffmpeg",)),
    "layout": RouteEntry(layout_sample.run, "poster.png",
                         ("playwright", "playwright-browsers")),
    "type": RouteEntry(type_sample.run, "type.mp4", ("fonttools",)),
    "spectrum": RouteEntry(spectrum_sample.run, "spectrum.png", ("ffmpeg",)),
    "ink": RouteEntry(ink_landscape.run, "ink.png", ("scipy", "pillow")),
}


@dataclass(frozen=True)
class Node:
    id: str
    route: str                       # key into ROUTES (or a caller-supplied map)
    spec_path: Path
    inputs: dict[str, str] = field(default_factory=dict)  # slot -> upstream node id


@dataclass(frozen=True)
class NodeResult:
    id: str
    route: str
    content_hash: str                # payload digest ("sha256:..."), the cache currency
    cached: bool
    seconds: float
    report: dict                     # the route's acceptance report (verdict + measured)
    manifest: dict
    artifacts: dict                  # artifact filename -> "sha256:..." at run time


# --- plan ---------------------------------------------------------------------

def load_plan(path: Path, routes: dict[str, RouteEntry] | None = None) -> list[Node]:
    """A plan source is either a **bundle** (has ``dag:``) or a single spec.

    Bundle nodes are ``{id, spec, inputs?}``; ``spec`` paths are resolved
    against the bundle file's directory (or absolute). A lone spec becomes a
    one-node plan, so ``vcac run <any-route-spec>`` works without a bundle.
    """
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PlanError(f"{path}: plan source must be a YAML mapping")
    if "dag" in raw:
        if not raw.get("id"):
            raise PlanError(f"{path}: bundle needs an id")
        return build_plan(raw["dag"], base_dir=path.parent, routes=routes)
    medium = raw.get("medium")
    known = routes if routes is not None else ROUTES
    if medium not in known:
        raise PlanError(f"{path}: medium '{medium}' has no route "
                        f"(known: {', '.join(sorted(known))})")
    return [Node(id=str(raw["id"]), route=medium, spec_path=path)]


def build_plan(entries: list[dict], base_dir: Path = Path("."),
               routes: dict[str, RouteEntry] | None = None) -> list[Node]:
    """Validate raw bundle entries and topologically order them (Kahn, stable)."""
    known = routes if routes is not None else ROUTES
    nodes: dict[str, Node] = {}
    order: list[str] = []
    for i, e in enumerate(entries):
        if "id" not in e or "spec" not in e:
            raise PlanError(f"dag entry #{i}: needs 'id' and 'spec', got {sorted(e)}")
        nid = str(e["id"])
        if nid in nodes:
            raise PlanError(f"duplicate node id '{nid}'")
        route = e.get("route")
        spec_path = Path(e["spec"])
        if not spec_path.is_absolute():
            spec_path = base_dir / spec_path
        if not spec_path.exists():
            raise PlanError(f"node '{nid}': spec not found: {spec_path}")
        if route is None:
            # default: the referenced spec's own medium decides the renderer
            raw_spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
            route = raw_spec.get("medium") if isinstance(raw_spec, dict) else None
        if route not in known:
            raise PlanError(f"node '{nid}': route '{route}' is not registered "
                            f"(known: {', '.join(sorted(known))})")
        nodes[nid] = Node(id=nid, route=route, spec_path=spec_path,
                          inputs={str(k): str(v)
                                  for k, v in (e.get("inputs") or {}).items()})
        order.append(nid)
    for n in nodes.values():
        for slot, up in n.inputs.items():
            if up not in nodes:
                raise PlanError(f"node '{n.id}': input slot '{slot}' points at "
                                f"unknown node '{up}'")
            if up == n.id:
                raise PlanError(f"node '{n.id}' feeds itself")
    # Kahn's algorithm; among the ready set, plan order wins so runs are stable.
    pending = dict(nodes)
    done: set[str] = set()
    plan: list[Node] = []
    while pending:
        ready = [nid for nid in order if nid in pending
                 and all(up in done for up in pending[nid].inputs.values())]
        if not ready:
            cycle = ", ".join(sorted(pending))
            raise PlanError(f"dependency cycle among: {cycle}")
        for nid in ready:
            plan.append(pending.pop(nid))
            done.add(nid)
    return plan


# --- execute ------------------------------------------------------------------

def _canonical(payload) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _declared_input_files(spec_dict: dict) -> dict[str, str]:
    """sha256 of every *existing* file the spec's own ``inputs:`` mapping names.

    Only meaningful for a single-spec plan (no bundle edges): there the
    spec-declared artifacts really are consumed, so their bytes must join the
    cache key — re-render an upstream and a stale mux must not survive. In a
    bundle these values are replaced before the route runs and the upstream
    nodes' payload hashes already cover identity."""
    ext: dict[str, str] = {}
    for slot, p in (spec_dict.get("inputs") or {}).items():
        fp = Path(p)
        if fp.is_file():
            ext[f"inputs.{slot}"] = provenance.sha256_file(fp)
    return ext


def _font_files(spec_dict: dict) -> dict[str, str]:
    """sha256 of the font files a spec declares (type route). A font is an
    external input exactly like an upstream artifact: swapping the face must
    invalidate, not masquerade as a hit."""
    ext: dict[str, str] = {}
    font = spec_dict.get("font")
    if isinstance(font, dict):
        for i, p in enumerate(font.get("paths") or []):
            fp = Path(p)
            if fp.is_file():
                ext[f"font.{i}"] = provenance.sha256_file(fp)
    return ext


def _cache_key(node: Node, spec_dict: dict, upstream: dict[str, str],
               tools: dict, code: dict, external: dict[str, str] | None = None) -> str:
    """Identity of a node run: its spec, its upstreams' *payload* hashes, the
    external files the spec itself names, the package code and the tool
    versions. The pre-injection spec dict is used so the key does not churn
    with the output directory's absolute path."""
    payload = {
        "pipeline": PIPELINE_VERSION,
        "node": {"id": node.id, "route": node.route,
                 "spec": spec_dict, "inputs": node.inputs},
        "upstream_content": upstream,
        "external_files": external or {},
        "code": code,
        "tools": tools,
    }
    return "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()


def _cache_valid(key_file: Path, key: str, node_dir: Path) -> bool:
    """A hit needs more than a matching key: the recorded artifacts must still
    be on disk with the recorded hashes, and the verdict files must exist."""
    try:
        rec = json.loads(key_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if rec.get("key") != key:
        return False
    for name, digest in (rec.get("artifacts") or {}).items():
        p = node_dir / name
        if not p.is_file() or provenance.sha256_file(p) != digest:
            return False
    return (node_dir / "report.json").is_file() and (node_dir / "manifest.json").is_file()


def _payload_hash(manifest: dict) -> str:
    h = manifest.get("content_hash") or manifest.get("frame_content_hash")
    if not h:
        raise PlanError(f"route manifest carries no content hash: {sorted(manifest)}")
    return h


def _run_node(node: Node, results: dict[str, NodeResult], out_dir: Path,
              routes: dict[str, RouteEntry], use_cache: bool,
              tools: dict, code: dict) -> NodeResult:
    t0 = time.perf_counter()
    node_dir = out_dir / node.id
    node_dir.mkdir(parents=True, exist_ok=True)

    spec_dict = yaml.safe_load(node.spec_path.read_text(encoding="utf-8"))
    upstream: dict[str, str] = {}
    for slot, up_id in node.inputs.items():
        if up_id not in results:
            raise PlanError(f"node '{node.id}': upstream '{up_id}' not executed yet")
        upstream[slot] = results[up_id].content_hash

    # external inputs: bundle edges are covered by upstream payload hashes;
    # a single-spec plan's declared input files and any declared font files
    # are hashed here so their bytes join the key (audit A7)
    external = _font_files(spec_dict)
    if not node.inputs:
        external.update(_declared_input_files(spec_dict))

    key = _cache_key(node, spec_dict, upstream, tools, code, external)
    key_file = node_dir / CACHE_KEY_FILE
    if use_cache and _cache_valid(key_file, key, node_dir):
        rec = json.loads(key_file.read_text(encoding="utf-8"))
        report = json.loads((node_dir / "report.json").read_text(encoding="utf-8"))
        manifest = json.loads((node_dir / "manifest.json").read_text(encoding="utf-8"))
        return NodeResult(id=node.id, route=node.route, content_hash=rec["content_hash"],
                          cached=True, seconds=time.perf_counter() - t0,
                          report=report, manifest=manifest,
                          artifacts={n: provenance.sha256_file(node_dir / n)
                                     for n in rec.get("artifacts") or {}})

    entry = routes[node.route]
    for cap in entry.requires:
        registry.require(cap)

    run_spec = node.spec_path
    if node.inputs:
        # Bundle edge: point the consumer's declared input slots at the
        # upstream nodes' provided artifacts, and keep the resolved spec as
        # evidence of what actually ran (README output layout: spec.yaml).
        inputs = dict(spec_dict.get("inputs") or {})
        for slot, up_id in node.inputs.items():
            inputs[slot] = str(out_dir / up_id / routes[results[up_id].route].provides)
        spec_dict["inputs"] = inputs
        run_spec = node_dir / "spec.resolved.yaml"
        run_spec.write_text(yaml.safe_dump(spec_dict, allow_unicode=True,
                                           sort_keys=False), encoding="utf-8")

    r = None
    try:
        r = entry.run(run_spec, node_dir)
    except Exception as exc:
        # leave machine-readable evidence next to the partial output (M0.3:
        # a crash with no record is indistinguishable from a crash nobody saw)
        (node_dir / "error.json").write_text(json.dumps(
            {"node": node.id, "route": node.route,
             "error": type(exc).__name__, "message": str(exc),
             "traceback_tail": "\n".join(
                 traceback.format_exception(exc)[-6:]).strip(),
             "created_utc": datetime.now(timezone.utc).isoformat()},
            indent=2, ensure_ascii=False), encoding="utf-8")
        raise NodeExecutionError(node.id, exc) from exc
    manifest = r["manifest"]
    content_hash = _payload_hash(manifest)
    names = sorted({*(manifest.get("artifacts") or []), entry.provides})
    artifacts = {n: provenance.sha256_file(node_dir / n)
                 for n in names if (node_dir / n).is_file()}
    key_file.write_text(json.dumps(
        {"key": key, "content_hash": content_hash, "artifacts": artifacts,
         "created_utc": datetime.now(timezone.utc).isoformat()},
        indent=2, ensure_ascii=False), encoding="utf-8")
    return NodeResult(id=node.id, route=node.route, content_hash=content_hash,
                      cached=False, seconds=time.perf_counter() - t0,
                      report=r["report"], manifest=manifest, artifacts=artifacts)


def execute(plan: list[Node], out_dir: Path, use_cache: bool = True,
            routes: dict[str, RouteEntry] | None = None,
            tools: dict | None = None, code: dict | None = None
            ) -> dict[str, NodeResult]:
    """Run the plan in topological order. ``tools``/``code`` are injectable so
    tests can pin them instead of shelling out to ffmpeg / hashing the package;
    production callers leave them None."""
    routes = routes if routes is not None else ROUTES
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tools = tools if tools is not None else provenance.tool_versions(ffmpeg.version())
    code = code if code is not None else provenance.code_hashes()
    results: dict[str, NodeResult] = {}
    for node in plan:
        # an upstream that failed acceptance must not feed its content hash
        # downstream (audit A8: poison propagates silently otherwise)
        bad_upstream = sorted({u for u in node.inputs.values()
                               if u not in results or not results[u].report.get("passed")})
        if bad_upstream:
            results[node.id] = NodeResult(
                id=node.id, route=node.route, content_hash="",
                cached=False, seconds=0.0,
                report={"passed": False, "blocked_by": bad_upstream,
                        "checks_total": 0, "passed_n": 0, "failed_n": 0,
                        "skipped_n": 0, "checks": []},
                manifest={}, artifacts={})
            continue
        try:
            results[node.id] = _run_node(node, results, out_dir, routes,
                                         use_cache, tools, code)
        except NodeExecutionError as exc:
            exc.partial_results = dict(results)
            raise
    return results


# --- bundle manifest ----------------------------------------------------------

def run_bundle(path: Path, out_dir: Path, use_cache: bool = True,
               routes: dict[str, RouteEntry] | None = None,
               ) -> tuple[dict[str, NodeResult], dict]:
    """Execute a plan source and write the bundle-level manifest (one record,
    sub-hashes per node — roadmap §2.7). Returns (results, manifest)."""
    path = Path(path)
    plan = load_plan(path, routes)
    tools = provenance.tool_versions(ffmpeg.version())
    code = provenance.code_hashes()
    exec_error = None
    try:
        results = execute(plan, out_dir, use_cache=use_cache, routes=routes,
                          tools=tools, code=code)
    except NodeExecutionError as exc:
        # the run stops, but the bundle manifest is still written — a crash
        # leaves evidence (error.json in the node dir + this record), never a
        # silent partial output (audit A8)
        results = exc.partial_results
        cause = exc.cause
        exec_error = {"node": exc.node_id, "error": type(cause).__name__,
                      "message": str(cause)}
    out_dir = Path(out_dir)

    failed = [nid for nid, r in results.items()
              if not r.report.get("passed") and not r.report.get("blocked_by")]
    blocked = [nid for nid, r in results.items() if r.report.get("blocked_by")]
    not_run = [n.id for n in plan if n.id not in results]
    node_summary = {}
    for nid, r in results.items():
        node_summary[nid] = {
            "route": r.route,
            "content_hash": r.content_hash,
            "cached": r.cached,
            "seconds": round(r.seconds, 3),
            "acceptance_passed": bool(r.report.get("passed")),
            "artifacts": sorted(r.artifacts),
        }
    manifest = {
        "run_id": "sha256:" + hashlib.sha256(_canonical(
            {"plan": [{"id": n.id, "route": n.route} for n in plan],
             "nodes": {nid: r.content_hash for nid, r in results.items()},
             "tools": tools})).hexdigest()[:16],
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": PIPELINE_VERSION,
        "bundle": str(path),
        "nodes": node_summary,
        "tools": tools,
        "acceptance": {
            "passed": not failed and not blocked and exec_error is None,
            "failed_nodes": failed,
            "blocked_nodes": blocked,
            "not_run_nodes": not_run,
            "executed_n": sum(1 for r in results.values() if not r.cached),
            "cached_n": sum(1 for r in results.values() if r.cached),
        },
        "notes": [
            "node granularity = one whole route run(); finer DAG nodes are deferred "
            "(docs/roadmap-development.md §3)",
            "cache key = spec dict + upstream payload content hashes + declared "
            "external file hashes + whole-package code hash + tool versions; any "
            "code edit invalidates every node (coarse but honest)",
            "a cached node re-reports the acceptance verdict recorded when it last "
            "ran; its artifacts are re-hashed before the hit is trusted",
            "a node whose upstream failed acceptance is blocked, not run; a node "
            "that crashes leaves error.json and stops the run",
        ],
    }
    if exec_error:
        manifest["error"] = exec_error
    provenance.write_manifest(manifest, out_dir)
    return results, manifest


# --- CLI ----------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="vcac",
        description="vcac pipeline — run a spec or a bundle DAG with content-hash caching")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run", help="execute a spec (single node) or a bundle (dag:)")
    p_run.add_argument("spec", type=Path, help="spec .yaml or bundle .yaml")
    p_run.add_argument("--out", type=Path, default=None,
                       help="output directory (default outputs/<id>)")
    p_run.add_argument("--no-cache", action="store_true",
                       help="re-execute every node even if the cache key matches")
    sub.add_parser("doctor", help="print the capability registry (scripts/doctor.py)")
    args = parser.parse_args(argv)

    if args.command == "doctor":
        registry.print_registry()
        return 0

    raw = yaml.safe_load(args.spec.read_text(encoding="utf-8"))
    out = args.out or Path("outputs") / str(raw.get("id") or args.spec.stem)
    results, manifest = run_bundle(args.spec, out, use_cache=not args.no_cache)

    print(f"[vcac:pipeline] {manifest['bundle']} -> {out}")
    for nid, r in results.items():
        rep = r.report
        status = "CACHED" if r.cached else (
            "BLOCKED" if rep.get("blocked_by") else "RAN")
        if rep.get("blocked_by"):
            checks = f"blocked by {', '.join(rep['blocked_by'])}"
        else:
            checks = (f"checks {rep.get('passed_n', '?')}/{rep.get('checks_total', '?')}"
                      if "passed_n" in rep else "no acceptance report")
        print(f"  [{status:7}] {nid:14s} "
              f"{r.content_hash[:26]}  {r.seconds:5.1f}s  {checks}")
    if manifest.get("error"):
        e = manifest["error"]
        print(f"  [CRASHED] {e['node']}: {e['error']}: {e['message']} "
              f"(evidence: {out / e['node'] / 'error.json'})")
    print(f"[vcac:pipeline] run_id={manifest['run_id']}")
    print(f"[vcac:pipeline] ACCEPTANCE {'PASSED' if manifest['acceptance']['passed'] else 'FAILED'}")
    return 0 if manifest["acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
