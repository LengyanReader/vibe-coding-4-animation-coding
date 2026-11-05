"""Probe: what does the shot boundary at t=6s actually look like, numerically?

anime_sample WIP counted scene cuts as |mean luma| jumps > 18 between consecutive
frames, and on the authored shot the gate reported 0. Before changing either the
composition or the detector, measure the two candidate signals at the real cut,
at ordinary motion, **and in the fade windows**:

  * global mean luma            -- the WIP detector
  * normalised histogram L1     -- the standard shot-boundary signal
                                   (total variation: sum |h1-h2| / 2)

Result (24 fps, cut at frame 144):

  pair        d_mean_luma   hist_L1
  motion          0.003-0.027   0.0002-0.0009
  CUT 143->144       15.068      0.2992
  fade frames        3.0-4.9     0.072-0.505   <-- every sampled pair inside a ramp

So the WIP threshold (18.0) sat *above* the real cut's mean-luma shift: an
exposure threshold has to know the scene's brightness. Histogram TV separates
motion from the cut by 330x, which is why the route switched signal -- but the
first run of that switch counted 34 cuts, because most of a fade's frames trip
the 0.10 threshold too. Sampling only mid-shot pairs is what let that hide: the
fade windows belong in any threshold's search space, and amplitude alone cannot
name an edit. The route now gates on an *isolated* spike, which a fade by
construction is not; the one ramp pair under threshold (0.072) is the clip's
largest unflagged shift and therefore the margin the gate reports (4.2x).

In-memory only; writes no files.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from vcac import anime_sample, spec as spec_mod  # noqa: E402

BINS = 32


def stats_for(spec, scene, idxs):
    out = {}
    for f in idxs:
        img = anime_sample.frame_image(spec, scene, f / spec.fps)
        g = img.convert("L")
        hist = np.histogram(np.frombuffer(g.tobytes(), dtype=np.uint8),
                            bins=BINS, range=(0, 256))[0].astype(float)
        hist /= hist.sum()
        out[f] = (ImageStat.Stat(g).mean[0], hist)
    return out


def main():
    spec = spec_mod.load(ROOT / "specs/examples/anime-eave.yaml")
    scene = anime_sample.make_scene(spec)
    cut_frame = int(6.0 * spec.fps)
    # the cut, its neighbours, two mid-shot pairs, and the two fade ramps -- the
    # ramp is where a threshold can be quietly wrong, so it is not skipped
    idxs = sorted({cut_frame - 2, cut_frame - 1, cut_frame, cut_frame + 1,
                   cut_frame + 2, 40, 41, 42, 200, 201, 202,
                   *range(1, 12), *range(spec.n_frames - 11, spec.n_frames)})
    s = stats_for(spec, scene, idxs)

    print(f"fps={spec.fps} cut frame={cut_frame}")
    print(f"{'pair':>12} {'d_mean_luma':>12} {'hist_L1':>9}  (kind)")
    for a, b in zip(idxs, idxs[1:]):
        if b - a != 1:
            continue
        dl = abs(s[b][0] - s[a][0])
        dh = float(np.abs(s[b][1] - s[a][1]).sum() / 2.0)
        kind = ("CUT" if a + 1 == cut_frame else
                "fade" if a < 12 or b > spec.n_frames - 12 else "motion")
        print(f"{a:>5}->{b:<5} {dl:12.3f} {dh:9.4f}  {kind}")

    means = [v[0] for v in s.values()]
    print(f"\nmean luma across sampled frames: min={min(means):.1f} max={max(means):.1f}")


if __name__ == "__main__":
    main()
