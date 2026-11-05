"""anime route — 2D cel-style clip: 飞檐少年 (the boy on the temple eave).

A style-level homage to modern Chinese fantasy animation (赛璐璐 cel shading,
dusk palette, upswept temple eaves, drifting embers). **No copyrighted
characters**: the boy is a generic silhouette; what is quoted is the *visual
grammar* — two-tone hard shadows, a warm rim light against a dusk sky,
parallax depth, one hard cut on the beat.

The route proves the video contract generalises beyond the first loop:
  spec.load (video contract) → seeded scene → pure frame function of t
  → content-hash determinism gate → encode → acceptance → manifest.
The shot cut at 6s is *measured* from the rendered frames (luma-histogram total
variation), not asserted: a clip that loses its cut fails the gate.

Determinism: every element is seeded at setup and a pure function of the
frame index — same (spec, seed) ⇒ same payload hash.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageStat

from . import cli, ffmpeg, provenance, spec as spec_mod, validate

# world canvas the scene is authored on (camera crops/zooms into it)
WORLD_W, WORLD_H = 1280, 720

# --- shot-boundary detector ---------------------------------------------------
# The cut position is authored in the spec's timeline; this is how the route
# *verifies* it survived the renderer. Both numbers below come from measurement
# (scripts/probes/hist_cut_probe.py, then the first full run of this route):
#
#   * ordinary inter-frame motion inside a shot: total variation <= 0.0009
#   * the scripted cut at frame 144:                     0.2992
#   * a 0.75s fade: 0.07-0.51 across the ramp -- most of it trips the threshold,
#     so a fade is larger than a cut far more often than not, and amplitude alone
#     cannot tell the two apart
#
# Hence 0.10 as the spike threshold (110x the motion floor, a third of the cut)
# *plus* the isolated-peak test below, which is what separates a cut from a fade.
# On the shipped clip that leaves exactly one hard cut, with the loudest shift the
# gate ignores being a ramp frame at 0.072 -- a margin of 4.2x, carried in the
# report rather than asserted here.
# The first version of this gate used |mean luma| > 18.0 and counted the real cut
# as zero: same clip, two shots, 15.1 of mean shift -- an exposure threshold has
# to know the scene's brightness, and a gate calibrated by guess does not.
_CUT_BINS = 32
_CUT_L1_THRESHOLD = 0.10
#: shot 1 travels 40 px over the first authored shot (6 s); the same rate is used
#: when the clip has no edit at all, so a cut-less spec differs only in the switch
_SHOT1_DRIFT_PX_PER_S = 40.0 / 6.0


def _luma_hist(img: Image.Image) -> np.ndarray:
    """32-bin normalised luma histogram (integer bins; float only at the end)."""
    hist = img.convert("L").histogram()                     # 256 exact counts
    bins = np.array(hist, dtype=np.float64).reshape(_CUT_BINS, -1).sum(axis=1)
    return bins / bins.sum()


def classify_cuts(hists: list, threshold: float = _CUT_L1_THRESHOLD):
    """Split frame-to-frame luma-distribution shifts into cuts and gradual edits.

    Signal is total variation between histograms (sum |h1 - h2| / 2: the share of
    pixels that would have to change bin). A **hard cut is an isolated spike** --
    the pair exceeds the threshold while both neighbouring pairs sit below it. A
    fade or a dissolve is the same shift smeared across a run of consecutive
    pairs, and every one of those pairs can be larger than the cut's spike; the
    shape is the evidence, not the size. Returning only the isolated peaks keeps
    'at least 1 scene cut' meaning one edit rather than one edit plus N ramp
    frames; the gradual frames are reported too, because a gate that silently
    discards a category is how a green run hides an unverified claim.

    Returns ``(hard_cut_frames, gradual_frames, diffs)``; ``diffs[i]`` compares
    frames ``i`` and ``i+1``.
    """
    diffs = [float(np.abs(a - b).sum() / 2.0) for a, b in zip(hists, hists[1:])]
    hard, gradual = [], []
    for i, d in enumerate(diffs):
        if d <= threshold:
            continue
        left = diffs[i - 1] if i > 0 else 0.0
        right = diffs[i + 1] if i + 1 < len(diffs) else 0.0
        (hard if left <= threshold and right <= threshold else gradual).append(i + 1)
    return hard, gradual, diffs


def _shade(c: tuple, k: float) -> tuple:
    return tuple(max(0, min(255, int(v * k))) for v in c)


def _mix(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# --- seeded scene ---------------------------------------------------------------

def _ridge_poly(seed: int, n: int, base_y: float, amp: float, freq: int) -> list:
    """A mountain silhouette polyline across the world (ridged noise)."""
    rng = random.Random(seed)
    g = [rng.random() for _ in range(freq + 1)]
    pts = []
    for i in range(n + 1):
        x = i / n * WORLD_W
        u = i / n * freq
        i0, i1 = int(u), min(int(u) + 1, freq)
        t = u - i0
        t = t * t * (3 - 2 * t)
        v = g[i0] * (1 - t) + g[i1] * t
        # ridged fold: sharp peaks, shallow valleys
        v = (1 - abs(2 * v - 1)) ** 1.6
        pts.append((x, base_y - v * amp))
    return pts


def _cloud_blobs(seed: int, n: int, y0: float, y1: float) -> list:
    """Flat cel clouds: a list of blob polygons with a two-tone band."""
    rng = random.Random(seed)
    out = []
    for k in range(n):
        cx, cy = rng.uniform(0, WORLD_W), rng.uniform(y0, y1)
        w, h = rng.uniform(120, 300), rng.uniform(22, 44)
        blob = []
        for i in range(14):
            a = i / 14 * 2 * math.pi
            r = 1.0 + 0.35 * math.sin(a * 3 + k * 1.7) + 0.2 * math.sin(a * 7 + k)
            blob.append((cx + math.cos(a) * w / 2 * r, cy + math.sin(a) * h / 2 * r))
        out.append({"pts": blob, "cx": cx, "cy": cy, "w": w})
    return out


def _embers(seed: int, n: int) -> list:
    rng = random.Random(seed)
    return [{"x0": rng.uniform(0, WORLD_W), "y0": rng.uniform(0, WORLD_H),
             "rise": rng.uniform(14, 42), "drift": rng.uniform(-10, 14),
             "phase": rng.uniform(0, 2 * math.pi), "r": rng.uniform(1.2, 2.8),
             "tw": rng.uniform(1.5, 3.5)} for _ in range(n)]


def make_scene(spec) -> dict:
    """Everything static, all from spec.seed — the frame function's input."""
    rng = random.Random(spec.seed)
    return {
        "mtn_far": _ridge_poly(spec.seed + 1, 64, WORLD_H * 0.66, WORLD_H * 0.20, 6),
        "mtn_near": _ridge_poly(spec.seed + 2, 64, WORLD_H * 0.78, WORLD_H * 0.16, 7),
        "clouds_hi": _cloud_blobs(spec.seed + 3, 4, WORLD_H * 0.14, WORLD_H * 0.30),
        "clouds_lo": _cloud_blobs(spec.seed + 4, 3, WORLD_H * 0.40, WORLD_H * 0.52),
        "embers": _embers(spec.seed + 5, 26),
        "boy_x": WORLD_W * 0.62, "boy_y": WORLD_H * 0.60,
        "lean": rng.uniform(-0.03, 0.03),
    }


# --- the boy: a generic silhouette (no IP likeness) ------------------------------

def _boy(scale: float, flip: bool) -> dict:
    """Vector parts in local units (roughly 5 heads tall), origin at feet."""
    s = scale
    def P(*pts):
        out = []
        for x, y in pts:
            if flip:
                x = -x
            out.append((x * s, y * s))
        return out
    head_c = (0, -150)
    return {
        "head_c": P(head_c)[0], "head_r": 22 * s,
        "body": P((-16, -128), (16, -128), (12, -60), (-12, -60)),
        "legs": P((-12, -60), (-9, 0), (-2, 0), (-3, -60)),
        "legs2": P((2, -60), (8, 0), (14, 0), (11, -60)),
        "arm": P((-14, -118), (-26, -88), (-20, -62)),
        "hair_pts": P((-20, -160), (0, -172), (20, -160), (12, -150), (-10, -152)),
        "ribbon_a": [(-20, -120), (-58, -96), (-96, -104), (-138, -84)],
        "ribbon_b": [(18, -122), (60, -110), (104, -122), (150, -100)],
    }


def _ribbon(pts: list, t: float, phase: float, amp: float) -> list:
    """A ribbon polyline waving in the wind: perpendicular ripple along it."""
    out = []
    for i, (x, y) in enumerate(pts):
        dy = math.sin(t * 2.4 + phase + i * 0.9) * amp * (i / max(1, len(pts) - 1))
        dx = math.sin(t * 1.7 + phase + i * 0.6) * amp * 0.35 * (i / max(1, len(pts) - 1))
        out.append((x + dx, y + dy))
    return out


# --- eave (飞檐): the upswept temple roof corner ---------------------------------

def _eave_pts(kind: str) -> list:
    if kind == "wide":       # shot 1: ridge line across the lower frame
        return [(-40, 620), (180, 600), (420, 592), (700, 596),
                (980, 584), (1240, 566), (1330, 540)]
    return [(-60, 760), (160, 700), (380, 610), (560, 520),  # shot 2: sweeping corner
            (700, 420), (790, 330), (840, 250)]


def _draw_eave(d: ImageDraw.ImageDraw, pal, pts: list, cam) -> None:
    roof = pal[4]
    body = []
    for x, y in pts:
        body.append(_cam_pt(x, y, cam))
    # roof body hangs below the ridge line
    depth = 90 * cam["zoom"]
    under = [(x, y + depth) for x, y in body]
    d.polygon(body + under[::-1], fill=roof)
    # two-tone: underside band darker (cel shadow)
    d.polygon([(x, y + depth) for x, y in body] +
              [(x, y + depth * 0.62) for x, y in body[::-1]],
              fill=_shade(roof, 0.72))
    # upswept tip accent + tile ticks
    d.line(body, fill=_shade(roof, 1.45), width=max(2, int(4 * cam["zoom"])))
    for x, y in body[1:-1]:
        d.line([_cam_pt(x, y, cam), _cam_pt(x, y + depth * 0.55, cam)],
               fill=_shade(roof, 0.85), width=1)


# --- camera ----------------------------------------------------------------------

def _cam_for(t: float, cut: float | None, scene: dict) -> dict:
    """Shot 1: slow drift right. Shot 2: closer, dolly-in on the boy.

    ``cut is None`` means the spec authors no edit at all: the take stays wide
    and keeps drifting, so nothing switches and the cut gate has nothing to find.
    (There used to be a hardcoded default cut at 6s here, which let a spec delete
    the timeline event and still get the visual cut -- a gate measuring a shot the
    spec never asked for.)
    """
    if cut is None or t < cut:
        return {"x": _SHOT1_DRIFT_PX_PER_S * t, "y": 0.0, "zoom": 1.0}
    u = min(1.0, (t - cut) / 5.0)
    return {"x": scene["boy_x"] - WORLD_W / 2 / 1.8 + 30 * (1 - u),
            "y": scene["boy_y"] - 170 - WORLD_H / 2 / 1.8,
            "zoom": 1.8 + 0.08 * u}


def _cam_pt(x: float, y: float, cam: dict) -> tuple:
    return ((x - cam["x"]) * cam["zoom"], (y - cam["y"]) * cam["zoom"])


def _fade(spec, t: float) -> float:
    b = 1.0
    for ev in spec.timeline:
        if ev.get("action") == "fade-in":
            a = spec.seconds_at(ev["at"]); d = max(1e-6, spec.seconds_at(ev.get("duration", "1s")))
            if t < a + d:
                b = min(b, max(0.0, (t - a) / d))
        if ev.get("action") == "fade-out":
            a = spec.seconds_at(ev["at"]); d = max(1e-6, spec.seconds_at(ev.get("duration", "1s")))
            if t > a:
                b = min(b, max(0.0, 1 - (t - a) / d))
    return b


# --- the frame function -----------------------------------------------------------

def frame_image(spec, scene: dict, t: float) -> Image.Image:
    # spec.load already resolved style.palette into RGB tuples; re-parsing them
    # as hex is a TypeError waiting for the first frame (found by running it)
    pal = list(spec.palette)
    w, h = spec.width, spec.height
    cut = None                                   # the spec owns the edit, or there is none
    for ev in spec.timeline:
        if ev.get("action") == "cut":
            cut = spec.seconds_at(ev["at"])
    cam = _cam_for(t, cut, scene)
    img = Image.new("RGB", (w, h), pal[0])
    d = ImageDraw.Draw(img)

    # dusk sky: vertical gradient through three stops + low sun glow
    top, mid, hor = pal[0], _mix(pal[0], pal[1], 0.55), pal[1]
    sun_x, sun_y = _cam_pt(WORLD_W * 0.30, WORLD_H * 0.62, cam)
    for y in range(h):
        u = y / h
        col = top if u < 0.45 else (_mix(top, mid, (u - 0.45) / 0.25) if u < 0.70
                                    else _mix(mid, hor, (u - 0.70) / 0.30))
        d.line([(0, y), (w, y)], fill=col)
    glow_r = 210 * cam["zoom"]
    sun = Image.new("RGB", (w, h), (0, 0, 0))
    sd = ImageDraw.Draw(sun)
    sd.ellipse([sun_x - glow_r, sun_y - glow_r, sun_x + glow_r, sun_y + glow_r],
               fill=_mix(pal[1], (255, 214, 150), 0.55))
    sun = sun.filter(ImageFilter.GaussianBlur(90))
    img = Image.blend(img, Image.composite(sun, img, sun.convert("L").point(lambda v: min(255, int(v * 0.9)))), 0.55)
    d = ImageDraw.Draw(img)

    # far mountains (two layers, parallax via camera x shift)
    for layer, col, par in (("mtn_far", _mix(pal[3], pal[0], 0.45), 0.25),
                            ("mtn_near", pal[3], 0.5)):
        pts = [_cam_pt(x - cam["x"] * (1 - par), y, cam) for x, y in scene[layer]]
        d.polygon(pts + [(w, h), (0, h)], fill=col)

    # clouds (two depths, drifting; two-tone cel underside)
    for group, speed, col, shade in (("clouds_hi", 6.0, _mix(pal[2], pal[0], 0.35), 0.8),
                                     ("clouds_lo", 12.0, pal[2], 0.78)):
        for c in scene[group]:
            dx = (t * speed) % (WORLD_W + 400) - 200
            pts = [_cam_pt(x + dx - cam["x"] * 0.2, y, cam) for x, y in c["pts"]]
            d.polygon(pts, fill=col)
            under = [(x, y + 5 * cam["zoom"]) for x, y in pts]
            d.polygon(pts[7:] + under[7:][::-1], fill=_shade(col, shade))

    # eave + boy (world geometry, camera-transformed)
    eave_kind = "wide" if cut is None or t < cut else "corner"
    _draw_eave(d, pal, _eave_pts(eave_kind), cam)

    bx, by = scene["boy_x"], scene["boy_y"]
    breathe = 1.0 + 0.012 * math.sin(t * 2.1)
    boy = _boy(scale=breathe, flip=(cut is not None and t >= cut))
    rib_a = _ribbon(boy["ribbon_a"], t, phase=0.3, amp=7.0)
    rib_b = _ribbon(boy["ribbon_b"], t, phase=2.1, amp=6.0)
    ribbon_col = pal[5]
    for rib in (rib_a, rib_b):
        pts = [_cam_pt(bx + x, by + y, cam) for x, y in rib]
        d.line(pts, fill=ribbon_col, width=max(2, int(3 * cam["zoom"])), joint="curve")

    body_dark = pal[6] if len(pal) > 6 else _shade(pal[4], 0.9)
    rim = _mix(ribbon_col, (255, 240, 210), 0.4)
    parts = [boy["legs"], boy["legs2"], boy["body"], boy["arm"]]
    # rim light: draw the whole silhouette shifted toward the sun in rim colour
    sx = -3 * cam["zoom"]
    for poly in parts + [boy["hair_pts"]]:
        d.polygon([_cam_pt(bx + x + sx, by + y, cam) for x, y in poly], fill=rim)
    d.ellipse([_cam_pt(bx + boy["head_c"][0] + sx, by + boy["head_c"][1] - boy["head_r"], cam)[0],
               _cam_pt(bx, by + boy["head_c"][1] - boy["head_r"] + sx, cam)[1],
               _cam_pt(bx + boy["head_c"][0] + sx + boy["head_r"] * 2, by + boy["head_c"][1] + boy["head_r"] + sx, cam)[0],
               _cam_pt(bx, by + boy["head_c"][1] + boy["head_r"] + sx, cam)[1]], fill=rim)
    # body on top, slightly away from the rim side
    for poly in parts + [boy["hair_pts"]]:
        d.polygon([_cam_pt(bx + x, by + y, cam) for x, y in poly], fill=body_dark)
    hr = boy["head_r"]
    hx, hy = _cam_pt(bx + boy["head_c"][0], by + boy["head_c"][1], cam)
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=body_dark)

    # embers rising, twinkling (accent colour)
    for e in scene["embers"]:
        et = (t * e["rise"] + e["y0"]) % (WORLD_H + 60)
        ex = (e["x0"] + math.sin(t * 0.7 + e["phase"]) * 18 + t * e["drift"]) % WORLD_W
        a = 0.45 + 0.55 * math.sin(t * e["tw"] + e["phase"]) ** 2
        col = _mix(pal[0], pal[5], 0.35 + 0.65 * a)
        r = e["r"] * cam["zoom"]
        p = _cam_pt(ex, WORLD_H + 30 - et, cam)
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)

    # vignette (cinematic edge falloff)
    vig = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-w * 0.25, -h * 0.25, w * 1.25, h * 1.25], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGB", (w, h), _shade(pal[0], 0.45))
    img = Image.composite(img, dark, vig)

    # timeline fade
    b = _fade(spec, t)
    if b < 1.0:
        img = Image.blend(Image.new("RGB", (w, h), (0, 0, 0)), img, b)
    return img


def render_frames(spec, scene: dict):
    """Yield raw RGB bytes per frame — pure function of (t, spec, seed)."""
    fps = spec.fps
    for f in range(spec.n_frames):
        yield frame_image(spec, scene, f / fps).tobytes()


# --- route driver (firstloop skeleton) --------------------------------------------

def run(spec_path: Path, out_dir: Path, keep_frames: bool = False) -> dict:
    spec = spec_mod.load(spec_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    scene = make_scene(spec)
    luma_by_frame: list[float] = []
    hist_by_frame: list[np.ndarray] = []

    def _saved():
        fps = spec.fps
        for f in range(spec.n_frames):
            img = frame_image(spec, scene, f / fps)
            luma_by_frame.append(ImageStat.Stat(img.convert("L")).mean[0])
            hist_by_frame.append(_luma_hist(img))
            img.save(frames_dir / f"{f:04d}.png", optimize=True)
            yield img.tobytes()

    payload = provenance.content_hash(_saved())
    deterministic = provenance.content_hash(render_frames(spec, scene)) == payload

    mp4 = out_dir / "clip.mp4"
    ffmpeg.encode_images(frames_dir, spec.fps, mp4)
    summary = ffmpeg.video_summary(mp4)

    # scene cuts: isolated spikes of frame-to-frame luma-distribution shift
    cuts, gradual, tv = classify_cuts(hist_by_frame)
    # the loudest shift that is neither a cut nor part of a ramp is the motion
    # floor the threshold clears. Reporting it alongside the cut's own spike is
    # what makes the threshold auditable: a number with no stated margin is an
    # uncalibrated check (audit B)
    flagged = set(cuts) | set(gradual)
    floor = max((d for i, d in enumerate(tv) if i + 1 not in flagged), default=0.0)
    at_cut = [tv[i - 1] for i in cuts]

    measured = {
        "duration": summary["duration"], "width": summary["width"],
        "height": summary["height"],
        "max_black_run_seconds": validate.max_black_run_seconds(luma_by_frame, spec.fps),
        "scene_cuts": len(cuts),
        "deterministic": deterministic,
    }
    report = validate.run_acceptance(spec.acceptance, measured)
    report["measured"] = measured
    report["cut_detection"] = {
        "method": f"luma histogram total variation, {_CUT_BINS} bins, isolated peak",
        "threshold": _CUT_L1_THRESHOLD,
        "hard_cut_frames": cuts,
        "gradual_frames": len(gradual),
        "diff_at_hard_cuts": [round(d, 4) for d in at_cut],
        "luma_delta_at_hard_cuts": [
            round(abs(luma_by_frame[i] - luma_by_frame[i - 1]), 2) for i in cuts],
        "largest_unflagged_diff": round(floor, 4),
        "margin_factor": round(min(at_cut, default=0.0) / max(floor, 1e-9), 1),
    }
    report["clip"] = {k: summary[k] for k in
                      ("duration", "width", "height", "codec_name", "pix_fmt", "nb_frames")}
    cli.write_report(out_dir, report)

    manifest = provenance.build_record(
        spec_path=str(spec_path), spec_dict=spec.to_dict(), content_hash=payload,
        artifact_hashes={"clip.mp4": provenance.sha256_file(mp4)},
        ffmpeg_version=ffmpeg.version(), acceptance=report,
        artifacts=["clip.mp4", "report.json", "manifest.json"],
        notes=spec.assumptions, pipeline="vcac-anime/0.1")
    provenance.write_manifest(manifest, out_dir)

    if not keep_frames:
        import shutil
        shutil.rmtree(frames_dir, ignore_errors=True)
    return {"report": report, "manifest": manifest, "out_dir": str(out_dir)}


def main(argv=None) -> int:
    a = cli.parse_args("vcac anime route (2D cel clip)", argv, extra=[
        (("--keep-frames",), dict(action="store_true")),
    ])
    spec = spec_mod.load(a.spec)
    r = run(a.spec, a.out or (Path("outputs") / spec.id), keep_frames=a.keep_frames)
    m = r["report"]["measured"]
    return cli.finish("anime", r, summaries=[
        f"{spec.id} -> {r['out_dir']}",
        f"{m['duration']:.2f}s {m['width']}x{m['height']} "
        f"cuts={m['scene_cuts']} black_run={m['max_black_run_seconds']:.2f}s"])


if __name__ == "__main__":
    raise SystemExit(main())
