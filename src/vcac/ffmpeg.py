"""FFmpeg encode + ffprobe probe helpers.

Thin, honest subprocess wrappers around the two binaries the first loop needs.
No shell string interpolation (README §6.4: forbid shell concat) — every call
is an argv list. Paths are passed as str/Path; the caller owns the working dir.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def _run(argv: list[str]) -> subprocess.CompletedProcess:
    exe = shutil.which(argv[0])
    if not exe:
        raise FFmpegError(f"binary not on PATH: {argv[0]}")
    return subprocess.run([exe, *argv[1:]], capture_output=True, text=True)


def version() -> str:
    r = _run(["ffmpeg", "-version"])
    return r.stdout.splitlines()[0].strip() if r.stdout else "unknown"


def encode_images(frames_dir: Path, fps: int, out_mp4: Path,
                  crf: int = 18, pix_fmt: str = "yuv420p") -> Path:
    """PNG sequence (%04d.png) -> H.264 mp4. Deterministic given the frames:
    we disable the muxer timestamp with -fflags +bitexact so container bytes
    are reproducible (the frame content hash is the primary fingerprint)."""
    pattern = str(Path(frames_dir) / "%04d.png")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", str(fps), "-i", pattern,
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", pix_fmt,
        "-fflags", "+bitexact", "-movflags", "+faststart",
        str(out_mp4),
    ]
    r = _run(cmd)
    if r.returncode != 0:
        raise FFmpegError(f"ffmpeg encode failed ({r.returncode}):\n{r.stderr}")
    return Path(out_mp4)


def probe(path: Path) -> dict:
    """Return ffprobe stream+format metadata as a dict."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    r = _run(cmd)
    if r.returncode != 0:
        raise FFmpegError(f"ffprobe failed ({r.returncode}):\n{r.stderr}")
    return json.loads(r.stdout or "{}")


def video_summary(path: Path) -> dict:
    """Pull the handful of load-bearing fields a validator checks."""
    data = probe(path)
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    fmt = data.get("format", {})
    return {
        "duration": float(v.get("duration") or fmt.get("duration") or 0.0),
        "width": v.get("width"),
        "height": v.get("height"),
        "codec_name": v.get("codec_name"),
        "pix_fmt": v.get("pix_fmt"),
        "nb_frames": int(v["nb_frames"]) if v.get("nb_frames") else None,
        "avg_frame_rate": v.get("avg_frame_rate"),
        "format_name": fmt.get("format_name"),
        "probe": data,
    }
