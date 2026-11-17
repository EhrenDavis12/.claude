"""Lock the face: paste K0's face (eyes, nose, mouth, chin) onto every frame at the tracked head position, so
nothing on the face moves, blinks, talks or blurs; the head itself still rides the breathing. Offsets come from an
SSD template match (1 px, ±10) smoothed over 5 frames. usage: face_lock.py <in.mp4> <out.mp4> [--k0 <plate.png> --ref <ref.json>]; the defaults are the archer's K0 and face box;
--ref reads face_box [x0, y0, x1, y1] at 640"""
import sys, json, argparse, subprocess, numpy as np
from pathlib import Path
from PIL import Image
from scipy import ndimage
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--k0"); ap.add_argument("--ref"); args = ap.parse_args()
S = 640; K0 = np.array(Image.open(args.k0 or Path(__file__).parent.parent / "glance_v3" / "work" / "K0_plate.png").convert("RGB")).astype(float)
x0, y0, x1, y1 = json.load(open(args.ref))["face_box"] if args.ref else (268, 150, 392, 240)
FACE = (slice(y0, y1), slice(x0, x1)); R = 10
def read(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, S, S, 3).astype(float)
def write(frames, p):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S}x{S}", "-r", "16", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(p)], input=np.stack(frames).astype(np.uint8).tobytes(), check=True)
t = K0[FACE]; h, w = t.shape[:2]
feather = np.zeros((h, w)); feather[7:-7, 7:-7] = 1; feather = ndimage.gaussian_filter(feather, 3)[..., None]; ring = (feather[..., 0] > 0.02) & (feather[..., 0] < 0.6)
frames = read(args.src); offs = []
for f in frames:
    best = None
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            win = f[FACE[0].start + dy:FACE[0].start + dy + h, FACE[1].start + dx:FACE[1].start + dx + w]
            d = ((win - t) ** 2).mean()
            if best is None or d < best[0]: best = (d, dy, dx)
    offs.append(best[1:])
offs = np.array(offs, float); offs = ndimage.median_filter(offs, size=(5, 1), mode="nearest"); offs = ndimage.uniform_filter1d(offs, 3, axis=0, mode="nearest")
out = []
for n, f in enumerate(frames):
    dy, dx = [int(round(v)) for v in offs[n]]; r0, c0 = FACE[0].start + dy, FACE[1].start + dx
    region = f[r0:r0 + h, c0:c0 + w]; patch = t + (region[ring].mean(0) - t[ring].mean(0))
    f = f.copy(); f[r0:r0 + h, c0:c0 + w] = region * (1 - feather) + patch * feather; out.append(f.clip(0, 255))
write(out, args.dst); print("face locked; offsets dy", [int(round(v)) for v in offs[::8, 0]], "dx", [int(round(v)) for v in offs[::8, 1]])
