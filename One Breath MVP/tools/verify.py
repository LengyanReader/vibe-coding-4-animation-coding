#!/usr/bin/env python3
"""verify.py — an INDEPENDENT Python implementation of the Go-rules subset the
mirror board needs, cross-validating the same board spec the JS engine renders.

Why two implementations: a single mistake in one rules brain would silently
prove a false position property (the audit's F-class lesson). The JS engine
drives the demo; this verifier re-derives every asserted property from the
same spec. Both must agree — tests fail loudly if they diverge.

Also, deliberately: this file doubles as the "算力" reference for the future
The-Two-Ways case — a tiny deterministic calculator, no LLM.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class Rules:
    def __init__(self, size: int):
        self.size = size
        self.stones: dict[tuple[int, int], int] = {}
        self.ko: tuple | None = None

    def neighbors(self, p):
        r, c = p
        out = []
        if r > 1: out.append((r - 1, c))
        if r < self.size: out.append((r + 1, c))
        if c > 1: out.append((r, c - 1))
        if c < self.size: out.append((r, c + 1))
        return out

    def chain(self, p):
        color = self.stones[p]
        stones, libs, stack = {p}, set(), [p]
        while stack:
            cur = stack.pop()
            for n in self.neighbors(cur):
                v = self.stones.get(n)
                if v is None:
                    libs.add(n)
                elif v == color and n not in stones:
                    stones.add(n)
                    stack.append(n)
        return stones, libs

    def play(self, p, color: int):
        if p in self.stones:
            return False, "occupied"
        if self.ko == p:
            return False, "ko"
        self.stones[p] = color
        enemy = 3 - color
        captured = []
        for n in self.neighbors(p):
            if self.stones.get(n) == enemy and (n, p) not in captured:
                stones, libs = self.chain(n)
                if libs == set():
                    captured.append((stones, p))
        seen = set()
        for stones, _ in captured:
            for s in stones:
                if s not in seen:
                    seen.add(s)
                    del self.stones[s]
        self.ko = None
        if len(captured) == 1 and len(captured[0][0]) == 1:
            self.ko = next(iter(captured[0][0]))
        stones, libs = self.chain(p)
        if not libs:
            return False, "suicide"
        return True, len(seen)


def build_position(board_spec, beat_name):
    r = Rules(board_spec["size"])
    for p in board_spec["stones"]["black"]:
        ok, why = r.play(tuple(p), 1)
        if not ok:
            raise SystemExit(f"verify: illegal setup stone {p}: {why}")
    for p in board_spec["stones"]["white"]:
        ok, why = r.play(tuple(p), 2)
        if not ok:
            raise SystemExit(f"verify: illegal setup stone {p}: {why}")
    beat = board_spec["beats"][beat_name]
    seq = list(beat.get("moves") or []) + ([beat["reply"]] if beat.get("reply") else [])
    for m in seq:
        if m["at"] is None:
            continue
        ok, why = r.play(tuple(m["at"]), 1 if m["color"] == "black" else 2)
        if not ok:
            raise SystemExit(f"verify: beat '{beat_name}' scripted move illegal: {why}")
    return r


def chains(r: Rules):
    seen, out = set(), []
    for p in list(r.stones):
        if p in seen:
            continue
        stones, libs = r.chain(p)
        seen |= stones
        out.append({"color": r.stones[p], "stones": stones, "libs": len(libs)})
    return out


def check_assert(r: Rules, spec_assert: dict, where: str) -> None:
    cs = chains(r)
    if "all_chains_liberties" in spec_assert:
        want = spec_assert["all_chains_liberties"]
        assert all(c["libs"] == want for c in cs), f"{where}: chain liberties {[(c['color'], c['libs']) for c in cs]}"
    if "all_chains_min_liberties" in spec_assert:
        want = spec_assert["all_chains_min_liberties"]
        assert all(c["libs"] >= want for c in cs), f"{where}: chain below {want}"
    if "chain_liberties" in spec_assert:
        for key_, want in spec_assert["chain_liberties"].items():
            color_s, at = key_.split("@")
            p = tuple(int(x) for x in at.split(","))
            color = 1 if color_s == "black" else 2
            stones, libs = r.chain(p)
            assert r.stones.get(p) == color, f"{where}: {key_} wrong color"
            assert len(libs) == want, f"{where}: {key_} libs {len(libs)} != {want}"


def main() -> int:
    board = yaml.safe_load((ROOT / "specs" / "board-two-sides.yaml").read_text(encoding="utf-8"))
    for beat_name in board["beats"]:
        r = build_position(board, beat_name)
        check_assert(r, board["beats"][beat_name].get("assert") or {}, beat_name)
        print(f"  [VERIFY] {beat_name:<8} chains={len(chains(r))} assertions ok")
    # cross-check the chain count the JS tests pin (B W B W B => 5 chains)
    r = build_position(board, "initial")
    cs = chains(r)
    assert len(cs) == 5 and sum(1 for c in cs if c["color"] == 1) == 3 \
        and sum(1 for c in cs if c["color"] == 2) == 2, "chain composition drifted"
    print("verify.py: all mirror-board assertions hold under the independent Python rules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
