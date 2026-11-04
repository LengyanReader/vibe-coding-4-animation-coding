"""Game route sample — headless deterministic playtest of a "dodge/collect" sim.

Proves the *interactive* branch without installing pygame: the game is a pure
Python fixed-timestep simulation driven by a scripted input track, so it can run
headless, be asserted on internal state (movement, scoring, damage, termination),
and be replayed bit-identically N times (the README's playtest contract, §7/§12).
The same state trace is then rendered with Pillow -> FFmpeg into a playtest.mp4
so a human can eyeball what the machine asserted.

When pygame-ce/Godot are adopted (docs/roadmap-development.md) they replace this
sim as the runtime; the headless harness (scripted input -> state assertions ->
determinism -> rendered trace) is the durable part and stays.

Run:
    $env:PYTHONPATH="src"; python -m vcac.game_sample specs/examples/dodge-headless.yaml
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

from . import ffmpeg, provenance, spec as spec_mod, validate


def _action_at(tick: int, inp: dict) -> str:
    """Scripted input: a left/right sweep, or an explicit per-tick event list."""
    events = inp.get("events")
    if events:
        for e in events:
            if e["tick"] == tick:
                return e["action"]
    period = int(inp.get("period", 20))
    return ["right", "right", "left", "left"][(tick // period) % 4]


def simulate(spec_dict: dict) -> tuple[list[dict], dict]:
    """Deterministic fixed-timestep sim. Returns (trace, final_state)."""
    w, h = int(spec_dict["width"]), int(spec_dict["height"])
    fps = int(spec_dict["fps"])
    duration = float(spec_mod.parse_duration(spec_dict["duration"]))
    n = round(duration * fps)
    dt = 1.0 / fps
    g = spec_dict.get("game", {})
    speed = float(g.get("player_speed", 420.0))
    spawn_p = float(g.get("spawn_rate", 0.14))
    hazard_p = float(g.get("hazard_rate", 0.45))
    start_hp = int(g.get("hp", 3))
    seed = int(spec_dict.get("seed", 42))
    inp = spec_dict.get("input", {})

    rng = random.Random(seed)
    px = w / 2.0
    pw = float(g.get("player_w", 70.0))
    py = h - 34.0
    orbs: list[dict] = []
    score = 0
    hp = start_hp
    trace: list[dict] = []
    terminated = False

    for tick in range(n):
        act = _action_at(tick, inp)
        if act == "left":
            px -= speed * dt
        elif act == "right":
            px += speed * dt
        px = max(pw / 2, min(w - pw / 2, px))

        if rng.random() < spawn_p:
            orbs.append({"x": rng.uniform(24, w - 24), "y": 0.0,
                         "vy": rng.uniform(180, 340), "r": 16.0,
                         "hazard": rng.random() < hazard_p})

        kept = []
        for o in orbs:
            o["y"] += o["vy"] * dt
            hit = (abs(o["x"] - px) < pw / 2 + o["r"]) and (abs(o["y"] - py) < 34 + o["r"])
            if hit:
                if o["hazard"]:
                    hp -= 1
                else:
                    score += 1
                continue  # consumed
            if o["y"] <= h + o["r"]:
                kept.append(o)
        orbs = kept

        trace.append({"tick": tick, "px": round(px, 3), "score": score, "hp": hp,
                      "orbs": [[round(o["x"], 1), round(o["y"], 1), bool(o["hazard"])]
                               for o in orbs]})
        if hp <= 0:
            terminated = True
            break

    if not terminated and tick >= n - 1:
        terminated = True  # session ran to its time limit

    moved = max(abs(t["px"] - trace[0]["px"]) for t in trace) > 1.0
    final = {"score": score, "hp": hp, "start_hp": start_hp, "px": round(px, 3),
             "moved": moved, "terminated": terminated, "ticks": len(trace)}
    return trace, final


def _state_hash(trace: list[dict]) -> str:
    payload = json.dumps(trace, separators=(",", ":"), sort_keys=True).encode()
    return provenance.sha256_bytes(payload)


def _render_frame(spec_dict, step) -> Image.Image:
    w, h = int(spec_dict["width"]), int(spec_dict["height"])
    pal = [spec_mod.parse_hex(c) for c in spec_dict["palette"]]
    img = Image.new("RGB", (w, h), pal[0])
    d = ImageDraw.Draw(img)
    pw = float(spec_dict.get("game", {}).get("player_w", 70.0))
    py = h - 34.0
    for ox, oy, hazard in step["orbs"]:
        r = 16.0
        col = pal[2] if hazard else pal[1]
        d.ellipse([ox - r, oy - r, ox + r, oy + r], fill=col)
    px = step["px"]
    d.rectangle([px - pw / 2, py - 12, px + pw / 2, py + 12], fill=pal[3])
    d.text((12, 10), f"score {step['score']}    hp {step['hp']}", fill=(255, 255, 255))
    return img


def run(spec_path: Path, out_dir: Path) -> dict:
    spec_dict = spec_mod.load_raw(spec_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    trace, final = simulate(spec_dict)

    # determinism gate: replay 3x, all state hashes must match
    h0 = _state_hash(trace)
    deterministic = all(_state_hash(simulate(spec_dict)[0]) == h0 for _ in range(3))

    # render the playtest
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for i, step in enumerate(trace):
        _render_frame(spec_dict, step).save(frames_dir / f"{i:04d}.png", optimize=True)
    fps = int(spec_dict["fps"])
    mp4 = out_dir / "playtest.mp4"
    ffmpeg.encode_images(frames_dir, fps, mp4)

    measured = {
        "duration": len(trace) / fps, "width": int(spec_dict["width"]),
        "height": int(spec_dict["height"]),
        "moved": final["moved"], "score": final["score"], "hp": final["hp"],
        "start_hp": final["start_hp"], "terminated": final["terminated"],
        "deterministic": deterministic,
    }
    report = validate.run_acceptance(spec_dict["acceptance"], measured)
    report["measured"] = measured
    report["game"] = final
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "trace.json").write_text(
        json.dumps(trace, ensure_ascii=False), encoding="utf-8")

    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec_dict, content_hash=h0,
        artifact_hashes={"playtest.mp4": provenance.sha256_file(mp4)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["playtest.mp4", "trace.json", "report.json", "manifest.json"],
        notes=spec_dict.get("assumptions", []), pipeline="vcac-game/0.1")
    provenance.write_manifest(manifest, out_dir)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="vcac game route sample")
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    spec_dict = spec_mod.load_raw(a.spec)
    out_dir = a.out or (Path("outputs") / spec_dict["id"])
    r = run(a.spec, out_dir)
    rep, g = r["report"], r["report"]["game"]
    print(f"[vcac:game] {spec_dict['id']} -> {r['out_dir']}")
    print(f"[vcac:game] ticks={g['ticks']} score={g['score']} hp={g['hp']}/{g['start_hp']} "
          f"moved={g['moved']} terminated={g['terminated']}")
    for c in rep["checks"]:
        extra = (f"  (exp {c.get('expected')}, act {c.get('actual')})"
                 if c["status"] in ("pass", "fail") else f"  ({c.get('reason','')})")
        print(f"  [{c['status'].upper():7}] {c['id']}{extra}")
    print(f"[vcac:game] run_id={r['manifest']['run_id']}")
    print(f"[vcac:game] ACCEPTANCE {'PASSED' if rep['passed'] else 'FAILED'}")
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
