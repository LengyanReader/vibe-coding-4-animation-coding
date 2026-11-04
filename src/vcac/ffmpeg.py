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


def audio_summary(path: Path) -> dict:
    a = next((s for s in probe(path).get("streams", [])
              if s.get("codec_type") == "audio"), {})
    return {
        "sample_rate": int(a["sample_rate"]) if a.get("sample_rate") else None,
        "channels": a.get("channels"),
        "codec_name": a.get("codec_name"),
        "duration": float(a["duration"]) if a.get("duration") else None,
    }


def _loudnorm_ff(in_wav, out_wav, target_i, target_tp, lra, measured=None):
    if measured:
        ln = (f"loudnorm=I={target_i}:TP={target_tp}:LRA={lra}"
              f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
              f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
              f":offset={measured['target_offset']}:linear=true")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(in_wav),
               "-af", ln, "-ar", "48000", str(out_wav)]
    else:
        # measure pass: loudnorm prints its JSON summary at info level, so we
        # must NOT silence it with -loglevel error here.
        ln = f"loudnorm=I={target_i}:TP={target_tp}:LRA={lra}:print_format=json"
        cmd = ["ffmpeg", "-y", "-hide_banner", "-i", str(in_wav),
               "-af", ln, "-f", "null", "-"]
    return _run(cmd)


def _loudnorm_measure(wav: Path) -> dict:
    import re
    r = _loudnorm_ff(wav, wav, -24.0, -2.0, 11.0)
    m = re.search(r"\{[^}]*\}", r.stderr or "", re.S)
    if not m:
        raise FFmpegError(f"loudnorm measure failed:\n{r.stderr}")
    return json.loads(m.group(0))


def measure_lufs(wav: Path) -> float:
    """Integrated loudness (EBU R128 LUFS) of a file, via ffmpeg loudnorm."""
    return float(_loudnorm_measure(wav)["input_i"])


def loudnorm_to_target(in_wav: Path, out_wav: Path, i: float = -16.0,
                       tp: float = -1.5, lra: float = 11.0) -> dict:
    """Two-pass EBU R128 normalisation. Pass 1 measures (JSON on stderr),
    pass 2 applies linearly. Returns the measured values for the manifest."""
    measured = _loudnorm_measure(in_wav)
    _loudnorm_ff(in_wav, out_wav, i, tp, lra, measured)
    return measured


def av_summary(path: Path) -> dict:
    """Stream-level view of a muxed file: presence, durations, and the A/V start
    offset (the sync gate for the composability route)."""
    data = probe(path)
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})
    vs = float(v["start_time"]) if v and v.get("start_time") else 0.0
    as_ = float(a["start_time"]) if a and a.get("start_time") else 0.0
    return {
        "duration": float(fmt.get("duration") or 0.0),
        "has_video": v is not None,
        "has_audio": a is not None,
        "video_codec": v.get("codec_name") if v else None,
        "audio_codec": a.get("codec_name") if a else None,
        "av_delta_seconds": abs(vs - as_),
    }


def mux(video: Path, audio: Path, out: Path, shortest: bool = True) -> Path:
    """Combine an existing video stream + audio track into one mp4 (no re-encode
    of video). The composability primitive: audio & frames are separate DAG
    nodes joined on one clock here (README §6.6)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
           "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
    if shortest:
        cmd += ["-shortest"]
    cmd += [str(out)]
    r = _run(cmd)
    if r.returncode != 0:
        raise FFmpegError(f"ffmpeg mux failed ({r.returncode}):\n{r.stderr}")
    return Path(out)
