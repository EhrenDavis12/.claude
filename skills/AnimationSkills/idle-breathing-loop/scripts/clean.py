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
def retime_progress(frames, n_out, band, plate_lum=(90, 175), ease=True, drop_pinned=True):
    """Resample a one-way move by how far the body has actually travelled. Progress = horizontal centroid of the figure
    (non-plate pixels) in a row band, signed toward the end frame, taken as a running maximum so a backward wobble
    (Wan goes out, back, then lunges to the pinned key) is skipped rather than played. Targets are cosine-eased, so the
    move starts and ends slowly — a reversal built from this clip and its mirror has no snap at the peak.
    drop_pinned: ignore the first and last source frames (the pinned inputs; the model's own neighbours differ in texture)."""
    f = list(frames)
    if drop_pinned and len(f) > 2: f = f[1:-1]
    def cx(x):
        g = x[band].astype(int); plate = ((g.max(2) - g.min(2)) < 26) & (g.mean(2) > plate_lum[0]) & (g.mean(2) < plate_lum[1])
        xs = np.where(~plate)[1]; return xs.mean() if len(xs) else 0.0
    c = np.array([cx(x) for x in f]); c -= c[0]
    if c[-1] < 0: c = -c
    prog = np.maximum.accumulate(np.maximum(c, 0)); total = prog[-1] if prog[-1] > 0 else 1.0
    last = int(np.argmax(prog))                      # the furthest frame: Wan overshoots a pinned key, so the key frame itself can sit BEHIND the extreme
    f, prog = f[:last + 1], prog[:last + 1]
    t = np.linspace(0, 1, n_out); targets = total * ((1 - np.cos(np.pi * t)) / 2 if ease else t)
    idx = [int(np.argmin(np.abs(prog - v))) for v in targets]; idx[0], idx[-1] = 0, len(f) - 1
    for i in range(1, len(idx)):
        if idx[i] <= idx[i - 1]: idx[i] = min(idx[i - 1] + 1, len(f) - 1)
    return [f[i] for i in idx], idx, np.round(prog[idx], 1)
def bridge_jumps(frames, progress=None, ratio=3.0, tmp="/tmp/bridge"):
    """After a retime skipped a wobble, one pair of consecutive frames can differ in texture far more than the rest.
    A jump is a pair whose mean |diff| exceeds ratio x the MEAN step (not the median — a retime leaves near-duplicate
    frames at the ends that make the median tiny). Each jump is bridged with the 3 middle frames of a FILM 4x of just
    that pair; the same number of frames is then dropped from true duplicates (progress unchanged, i.e. the flat tail)
    so the count is unchanged. `progress` is the per-frame progress array from retime_progress."""
    import subprocess
    from pathlib import Path
    f = [np.asarray(x) for x in frames]; H, W = f[0].shape[:2]
    d = np.array([abs(f[i].astype(float) - f[i + 1].astype(float)).mean() for i in range(len(f) - 1)])
    jumps = [i for i in range(len(d)) if d[i] > ratio * d.mean()]
    if not jumps: return f, []
    G = "/Users/ehrendavis/work/local-RED-dev/src/LLMs/generate.py"; Path(tmp).mkdir(parents=True, exist_ok=True)
    def write(fr, p): subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "16", "-i", "-", "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p", p], input=np.stack(fr).astype(np.uint8).tobytes(), check=True)
    def read(p): raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout; return list(np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3))
    out = []; keep = []; inserted = 0
    for i, x in enumerate(f):
        out.append(x); keep.append(progress[i] if progress is not None else None)
        if i in jumps:
            write([f[i], f[i + 1]], f"{tmp}/pair.mp4")
            subprocess.run(["python3", G, "interpolate", f"{tmp}/pair.mp4", "-o", f"{tmp}/pair2.mp4"], check=True, capture_output=True)
            subprocess.run(["python3", G, "interpolate", f"{tmp}/pair2.mp4", "-o", f"{tmp}/pair4.mp4"], check=True, capture_output=True)
            mid = read(f"{tmp}/pair4.mp4")[1:-1]; out.extend(mid); keep.extend([None] * len(mid)); inserted += len(mid)
    # trim back to the original count: repeatedly drop the frame with the smallest step to its neighbour, never the ends
    while len(out) > len(f):
        dd = [abs(out[i].astype(float) - out[i + 1].astype(float)).mean() for i in range(len(out) - 1)]
        del out[int(np.argmin(dd[1:])) + 1]
    return out, jumps
