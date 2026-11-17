"""Sub-pixel, smooth face lock for any character with a keys/K0_<class>.ref.json (face_box, head_box).
Head offsets come from tracking the whole head box (hood + face) against K0 -- SSD on a +/-R px grid, parabola-refined to
sub-pixel in x and y -- then made monotone along the rise (isotonic regression, direction taken from the net move), smoothed,
and shifted so cell 1 is exactly the rest position (0, 0). The K0 face and its feather are resampled at the sub-pixel
offset (cubic for colour, linear for the feather), so the paste glides with the head instead of hopping in whole pixels.
usage: facelock_smooth.py <in.mp4> <out.mp4> --k0 <plate.png> --ref <ref.json>"""
import sys, json, argparse, subprocess, numpy as np
from PIL import Image
from scipy import ndimage
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--k0", required=True); ap.add_argument("--ref", required=True); ap.add_argument("--sigma", type=float, default=1.5); args = ap.parse_args()
S = 640; R = 10
K0 = np.array(Image.open(args.k0).convert("RGB")).astype(float); ref = json.load(open(args.ref))
fx0, fy0, fx1, fy1 = ref["face_box"]; hx0, hy0, hx1, hy1 = ref["head_box"]
def read(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, S, S, 3).astype(float)
def write(frames, p):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S}x{S}", "-r", "16", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(p)], input=np.stack(frames).astype(np.uint8).tobytes(), check=True)
def track(f):
    t = K0[hy0:hy1, hx0:hx1].mean(2); h, w = t.shape; g = f.mean(2)
    ssd = np.zeros((2 * R + 1, 2 * R + 1))
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1): ssd[dy + R, dx + R] = ((g[hy0 + dy:hy0 + dy + h, hx0 + dx:hx0 + dx + w] - t) ** 2).mean()
    iy, ix = np.unravel_index(ssd.argmin(), ssd.shape)
    def par(a, b, c): d = a - 2 * b + c; return 0.0 if d <= 1e-9 else 0.5 * (a - c) / d
    sy = par(ssd[iy - 1, ix], ssd[iy, ix], ssd[iy + 1, ix]) if 0 < iy < 2 * R else 0.0
    sx = par(ssd[iy, ix - 1], ssd[iy, ix], ssd[iy, ix + 1]) if 0 < ix < 2 * R else 0.0
    return iy - R + sy, ix - R + sx
def pav(y, increasing):
    y = np.asarray(y, float) * (1 if increasing else -1); blocks = []
    for v in y:
        blocks.append([v, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s, n = blocks.pop(); blocks[-1][0] += s; blocks[-1][1] += n
    return np.concatenate([[b[0] / b[1]] * b[1] for b in blocks]) * (1 if increasing else -1)
frames = read(args.src); raw = np.array([track(f) for f in frames])
sm = np.zeros_like(raw)
for a in (0, 1):
    inc = (raw[-1, a] - raw[0, a]) >= 0; m = pav(raw[:, a], inc); m = ndimage.gaussian_filter1d(m, args.sigma, mode="nearest"); sm[:, a] = m - m[0]
h, w = fy1 - fy0, fx1 - fx0
feather = np.zeros((S, S)); b = np.zeros((h, w)); b[7:-7, 7:-7] = 1; feather[fy0:fy1, fx0:fx1] = ndimage.gaussian_filter(b, 3)
ring = np.zeros((S, S), bool); ring[fy0:fy1, fx0:fx1] = (feather[fy0:fy1, fx0:fx1] > 0.02) & (feather[fy0:fy1, fx0:fx1] < 0.6)
out = []
for n, f in enumerate(frames):
    dy, dx = sm[n]
    mask = np.clip(ndimage.shift(feather, (dy, dx), order=1, mode="constant"), 0, 1)
    patch = ndimage.shift(K0, (dy, dx, 0), order=3, mode="nearest")
    rm = (mask > 0.02) & (mask < 0.6)
    patch = patch + (f[rm].mean(0) - patch[rm].mean(0))
    out.append((f * (1 - mask[..., None]) + patch * mask[..., None]).clip(0, 255))
json.dump({"dy": [round(float(v), 3) for v in sm[:, 0]], "dx": [round(float(v), 3) for v in sm[:, 1]], "raw_dy": [round(float(v), 2) for v in raw[:, 0]], "raw_dx": [round(float(v), 2) for v in raw[:, 1]], "note": "px at 640, head-box track, isotonic + gaussian, cell 1 = 0"}, open(str(args.dst) + ".offsets.json", "w"))
write(out, args.dst); print("dy", np.round(sm[:, 0], 2).tolist()); print("dx", np.round(sm[:, 1], 2).tolist())
