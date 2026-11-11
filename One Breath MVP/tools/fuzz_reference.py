#!/usr/bin/env python3
"""Differential fuzz reference: generates deterministic random Go sequences
and outputs them as JSON for the JS differential test to compare against.

The JS engine (app/rules.js) and the Python engine (tools/verify.py Rules)
must agree on every step: captured count, refusal reason, and final position.
This script generates the shared input; both brains run it independently.

Usage: python tools/fuzz_reference.py --seeds 10 --steps 30 > dist/fuzz-seqs.json
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class Rules:
    """Independent Go rules — the Python brain for differential testing."""

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
        """Returns (ok, captured_count, refusal_reason)."""
        if p in self.stones:
            return False, 0, "occupied"
        if self.ko == p:
            return False, 0, "ko"
        self.stones[p] = color
        enemy = 3 - color
        captured_groups = []
        handled = set()
        for n in self.neighbors(p):
            if self.stones.get(n) == enemy and n not in handled:
                stones, libs = self.chain(n)
                handled |= stones
                if not libs:
                    captured_groups.append(stones)
        captured = set()
        for g in captured_groups:
            captured |= g
        for s in captured:
            del self.stones[s]
        ko = None
        if len(captured_groups) == 1 and len(captured) == 1:
            ko = next(iter(captured))
        self.ko = ko
        stones, libs = self.chain(p)
        if not libs:
            return False, 0, "suicide"
        return True, len(captured), None

    def hash(self):
        """Must match JS hashPosition in app/rules.js byte for byte."""
        entries = sorted(self.stones.items(), key=lambda x: x[0])
        body = ";".join(f"{r},{c}:{v}" for (r, c), v in entries) +             f"|ko:{f'{self.ko[0]},{self.ko[1]}' if self.ko else '-'}"
        h = 0x811c9dc5
        for ch in body:
            h ^= ord(ch)
            h = (h * 0x01000193) & 0xFFFFFFFF
        return format(h, "08x")


def generate_sequence(seed: int, size: int, n_steps: int) -> list[dict]:
    """Generate a random sequence of legal (or attempted) moves."""
    rng = random.Random(seed)
    rules = Rules(size)
    seq = []
    for i in range(n_steps):
        color = (i % 2) + 1  # alternate black/white
        candidates = [(r, c) for r in range(1, size + 1)
                      for c in range(1, size + 1)
                      if (r, c) not in rules.stones]
        if not candidates:
            break
        p = rng.choice(candidates)
        ok, captured, reason = rules.play(p, color)
        seq.append({
            "step": i,
            "at": list(p),
            "color": "black" if color == 1 else "white",
            "ok": ok,
            "captured": captured,
            "reason": reason,
            "hash": rules.hash() if ok else None,
        })
    return seq


def main() -> int:
    ap = argparse.ArgumentParser(description="generate deterministic fuzz sequences")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--size", type=int, default=5)
    args = ap.parse_args()

    sequences = []
    for seed in range(args.seeds):
        seq = generate_sequence(seed, args.size, args.steps)
        sequences.append({"seed": seed, "size": args.size, "steps": seq})

    out = {"generated_by": "tools/fuzz_reference.py",
           "seeds": args.seeds, "steps_per_seq": args.steps,
           "size": args.size, "sequences": sequences}

    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "fuzz-seqs.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(len(s["steps"]) for s in sequences)
    refused = sum(1 for s in sequences for st in s["steps"] if not st["ok"])
    captured_n = sum(st["captured"] for s in sequences for st in s["steps"] if st["ok"])
    print(f"generated {len(sequences)} sequences, {total} moves, "
          f"{refused} refusals, {captured_n} captured -> dist/fuzz-seqs.json")
    return 0


if __name__ == "__main__":
    sys_exit = main()
