"""Cleaning passes for Wan in-betweens. Import from a build/compose script.

enclosed_plate(rgb, mask, k0_hole12): zero the mask wherever a pixel is plate-coloured (grey, low saturation,
    mid brightness) AND lies within 12 px of a region K0 has transparent. Catches the bow interior when the string
    closes it, the arrow gaps, the glove gap. Leaves the belt buckle (never near a K0 hole) alone.
still_face(frames, box, win=5): temporal median over a face box — kills blinks and mouth flicker (1-3 frame events)
    without pasting a key, so a turning face keeps its own angle.
crossfade_joins(frames, joins, n=3): premultiplied-free RGB crossfade over n frames centred on each join index."""
import numpy as np
from scipy import ndimage
def k0_hole12(k0_rgba, size):
    from PIL import Image
    a = np.array(Image.fromarray(k0_rgba[..., 3]).resize((size, size), Image.BILINEAR))
    return ndimage.binary_dilation(a < 8, iterations=12)
def enclosed_plate(rgb, mask, hole12):
    x = rgb.astype(int); plate = ((x.max(2) - x.min(2)) < 26) & (x.mean(2) > 90) & (x.mean(2) < 175)
    out = mask.copy(); out[plate & hole12] = 0; return out
def still_face(frames, box, win=5):
    f = np.stack(frames).astype(float); r, c = box
    f[:, r, c] = ndimage.median_filter(f[:, r, c], size=(win, 1, 1, 1), mode="nearest"); return list(f)
def crossfade_joins(frames, joins, n=3):
    """At each join j (first frame of the next piece), blend the n frames on each side toward the other side,
    so the texture change is spread over 2n frames instead of one."""
    f = [x.astype(float) for x in frames]; src = [x.copy() for x in f]
    for j in joins:
        A, B = src[j - 1], src[j]
        for i in range(n):
            w = (i + 1) / (2 * n + 1)                       # small near the ends, larger near the join
            f[j - 1 - i] = src[j - 1 - i] * (1 - (0.5 - w / 2)) + B * (0.5 - w / 2) if False else src[j - 1 - i] * (1 - (n - i) / (2 * n + 1)) + B * ((n - i) / (2 * n + 1))
            f[j + i] = src[j + i] * (1 - (n - i) / (2 * n + 1)) + A * ((n - i) / (2 * n + 1))
    return [x.clip(0, 255) for x in f]
def unblink(frames, eye_box, dark=60, drop=0.9, feather=3):
    """Find blink runs (frames whose eye box has far fewer very-dark pixels than the clip's median) and replace the eye
    box on those frames by a linear blend of the last open frame before and the first open frame after. Touches only
    the eye box, only on blink frames, so a turning head keeps its own angle everywhere else."""
    f = [x.astype(float) for x in frames]; r, c = eye_box
    openness = np.array([(x[r, c].mean(2) < dark).mean() for x in f]); ref = np.median(openness)
    blink = openness < ref * drop
    m = np.zeros((r.stop - r.start, c.stop - c.start)); m[feather:-feather, feather:-feather] = 1
    m = ndimage.gaussian_filter(m, feather)[..., None]
    i = 0; runs = []
    while i < len(f):
        if blink[i]:
            j = i
            while j < len(f) and blink[j]: j += 1
            a, b = max(i - 1, 0), min(j, len(f) - 1)
            for k in range(i, j):
                t = (k - a) / max(b - a, 1); patch = f[a][r, c] * (1 - t) + f[b][r, c] * t
                f[k][r, c] = f[k][r, c] * (1 - m) + patch * m
            runs.append((i, j - 1)); i = j
        else: i += 1
    return [x.clip(0, 255) for x in f], runs
def retime_uniform(frames, n_out, region=None):
    """Resample a clip so every output frame carries the same amount of motion. Motion = mean |diff| between
    consecutive frames (over `region` if given); frames are picked at equal steps of cumulative motion, nearest
    neighbour. Feed it a FILM-doubled clip so the fast part has frames to pick from. First and last frames kept."""
    f = [x.astype(float) for x in frames]
    sel = (lambda x: x[region]) if region is not None else (lambda x: x)
    small = lambda x: ndimage.zoom(sel(x).mean(2), 0.25, order=1)          # 4x downsample: pixel noise is not motion
    d = np.array([0.0] + [abs(small(f[i]) - small(f[i + 1])).mean() for i in range(len(f) - 1)])
    cum = np.cumsum(d); targets = np.linspace(0, cum[-1], n_out)
    idx = [int(np.argmin(np.abs(cum - t))) for t in targets]; idx[0], idx[-1] = 0, len(f) - 1
    for i in range(1, len(idx)):                                   # never pick the same source frame twice
        if idx[i] <= idx[i - 1]: idx[i] = min(idx[i - 1] + 1, len(f) - 1)
    return [frames[i] for i in idx], idx
