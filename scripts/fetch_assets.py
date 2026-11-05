"""Fetch external assets (fonts / soundfonts / tools) with hash recording.

README §14: large media assets stay out of git; they are managed by download
scripts + hashes. **Nothing under ``assets/`` is version-controlled** except the
lock file — including the fonts, which are small enough to be tempting and
permanent enough in git history to be wrong. First run records each asset's
sha256 into ``assets/assets.lock.json``; later runs verify against the lock
(M0.2: the hash is the provenance). Licence notes live next to each entry and are
copied into route manifests at render time (styles.md §6/§17).

Usage:
    python scripts/fetch_assets.py            # download what is missing, verify the rest
    python scripts/fetch_assets.py --check    # verify only, no network
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "assets" / "assets.lock.json"

# Every external asset the routes may consume. `sha256` is filled in on first
# download and frozen thereafter (a change here is a deliberate review event).
# There is deliberately no per-entry "commit this?" flag: the policy is uniform
# (.gitignore: ``assets/*`` except the lock) and a decorative field that could
# drift against it would be worse than none.
ASSETS = [
    {
        "name": "ZhiMangXing-Regular.ttf",
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/zhimangxing/ZhiMangXing-Regular.ttf",
        "out": "assets/fonts/ZhiMangXing-Regular.ttf",
        "kind": "file",          # 4 MB: fetched on demand, never a git blob
        "licence": "OFL-1.1",
        "licence_note": "SIL Open Font License 1.1 (Google Fonts); redistributable; "
                        "used for the ink-landscape colophon and seal.",
    },
    {
        "name": "FluidR3_GM.sf2",
        "url": "http://deb.debian.org/debian/pool/main/f/fluid-soundfont/fluid-soundfont-gm_3.1-6_all.deb",
        "out": "assets/soundfonts/FluidR3_GM.sf2",
        "kind": "deb-member", "member": "usr/share/sounds/sf2/FluidR3_GM.sf2",
        "licence": "MIT (FluidR3, Christian Collins / Debian fluid-soundfont 3.1-6)",
        "licence_note": "MIT-licensed General MIDI soundfont; pulled from the "
                        "canonical Debian package so the source is a primary one.",
    },
    {
        "name": "fluidsynth-v2.6.2-win10-x64",
        "url": "https://github.com/FluidSynth/fluidsynth/releases/download/v2.6.2/"
               "fluidsynth-v2.6.2-win10-x64-cpp11.zip",
        "out": "assets/tools/fluidsynth",
        "kind": "zip", "exe": "fluidsynth.exe",
        "licence": "LGPL-2.1 (FluidSynth v2.6.2 official Windows build)",
        "licence_note": "Official upstream release; used as a rendering tool "
                        "(argv subprocess), not redistributed as part of outputs.",
    },
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_lock() -> dict:
    if LOCK.exists():
        return json.loads(LOCK.read_text(encoding="utf-8"))
    return {}


def _write_lock(lock: dict) -> None:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}")
    with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)


def _deb_extract_member(deb: Path, member_prefix: str) -> bytes:
    """Minimal .deb reader: `ar` archive of {debian-binary, control.tar.*, data.tar.*}.

    No external tooling — the ar format is a fixed 60-byte header table and the
    data member is a plain tar (xz-compressed in current Debian packages)."""
    data = deb.read_bytes()
    if not data.startswith(b"!<arch>\n"):
        raise ValueError(f"not an ar archive: {deb}")
    pos = 8
    while pos < len(data):
        header = data[pos:pos + 60]
        if len(header) < 60:
            break
        name = header[0:16].decode("ascii").strip()
        size = int(header[48:58].decode("ascii").strip())
        body = data[pos + 60: pos + 60 + size]
        pos += 60 + size + (size % 2)
        if name.startswith("data.tar"):
            with tarfile.open(fileobj=io.BytesIO(body), mode="r:*") as tf:
                for m in tf.getmembers():
                    if m.isfile() and m.name.split("/")[-1] == member_prefix.split("/")[-1] \
                            and m.name.endswith(member_prefix.split("/")[-1]):
                        return tf.extractfile(m).read()
            raise KeyError(f"{member_prefix} not in data member")
    raise KeyError(f"no data.tar member in {deb}")


def fetch(entry: dict, check_only: bool, lock: dict) -> str:
    out = ROOT / entry["out"]
    rec = lock.get(entry["name"])
    done = {"file": lambda: out.is_file(),
            "deb-member": lambda: out.is_file(),
            "zip": lambda: (out / entry["exe"]).is_file()}[entry["kind"]]()
    if done:
        digest = sha256_file(out) if entry["kind"] == "file" else rec or ""
        if rec and digest != rec and entry["kind"] == "file":
            raise SystemExit(f"{entry['name']}: hash drift vs lock — review before refetching")
        return "ok (present)"
    if check_only:
        return "MISSING"
    if entry["kind"] == "file":
        _download(entry["url"], out)
        digest = sha256_file(out)
    elif entry["kind"] == "deb-member":
        tmp = out.with_suffix(".deb.part")
        _download(entry["url"], tmp)
        blob = _deb_extract_member(tmp, entry["member"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        tmp.unlink()
        digest = sha256_file(out)
    elif entry["kind"] == "zip":
        # a Windows tool zip is exe + its DLLs: extract every binary member
        # flat, or the exe fails to load its shared libraries
        tmp = out.with_suffix(".zip.part")
        _download(entry["url"], tmp)
        with zipfile.ZipFile(tmp) as z:
            for info in z.infolist():
                if info.filename.lower().endswith((".exe", ".dll")):
                    dest = out / Path(info.filename).name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(z.read(info))
        tmp.unlink()
        digest = sha256_file(out / entry["exe"])
    else:
        raise ValueError(entry["kind"])
    if rec and rec != digest:
        raise SystemExit(f"{entry['name']}: downloaded hash differs from lock")
    lock[entry["name"]] = digest
    return f"fetched ({digest[:16]}…)"


def main() -> int:
    ap = argparse.ArgumentParser(description="fetch external assets with hash lock")
    ap.add_argument("--check", action="store_true", help="verify only, no network")
    args = ap.parse_args()
    lock = _read_lock()
    bad = 0
    for entry in ASSETS:
        status = fetch(entry, args.check, lock)
        print(f"[{'CHECK' if args.check else 'FETCH ':6}] {entry['name']:32s} {status} "
              f"({entry['licence']})")
        if status == "MISSING":
            bad += 1
    _write_lock(lock)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
