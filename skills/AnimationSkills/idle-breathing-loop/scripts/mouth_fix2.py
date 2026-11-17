"""Close the mouth on every frame of the named segments (work/<name>_unpatched.mp4 -> work/<name>.mp4).
Per frame: SSD template match of the eye/nose region against both approved keys (1 px steps, ±14 px), then the
offsets are median-smoothed over 5 frames so the pasted mouth never jitters; the nearer key's closed mouth is
pasted with a 5 px feather and a per-frame tone shift. usage: mouth_fix2.py seg1 hold"""
import sys, subprocess, numpy as np
from pathlib import Path
from PIL import Image
from scipy import ndimage
W = Path("work"); S = 640
FACE = (slice(150, 235), slice(270, 390)); MOUTH = (slice(194, 240), slice(284, 366)); R = 14   # whole lower face: an open jaw spills below the lips
def read(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, S, S, 3).copy()
def write(frames, p):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S}x{S}", "-r", "16", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(p)], input=np.stack(frames).tobytes(), check=True)
keys = [np.array(Image.open(W / n).convert("RGB")).astype(float) for n in ("K0_plate.png", "K1_plate.png")]
templates = [k[FACE] for k in keys]
feather = np.zeros((MOUTH[0].stop - MOUTH[0].start, MOUTH[1].stop - MOUTH[1].start)); feather[6:-6, 6:-6] = 1
feather = ndimage.gaussian_filter(feather, 2.5)[..., None]; ring = (feather[..., 0] > 0.02) & (feather[..., 0] < 0.6)
def match(ff):
    best = None
    for ki, t in enumerate(templates):
        for dy in range(-R, R + 1):
            for dx in range(-R, R + 1):
                r0, c0 = FACE[0].start + dy, FACE[1].start + dx
                win = ff[r0:r0 + t.shape[0], c0:c0 + t.shape[1]]
                d = ((win - t) ** 2).mean()
                if best is None or d < best[0]: best = (d, ki, dy, dx)
    return best
for name in sys.argv[1:]:
    src = W / f"{name}_unpatched.mp4"
    if not src.exists(): (W / f"{name}.mp4").rename(src)
    frames = read(src).astype(float)
    m = [match(f) for f in frames]
    ki = np.array([x[1] for x in m]); dy = ndimage.median_filter(np.array([x[2] for x in m], float), 5, mode="nearest"); dx = ndimage.median_filter(np.array([x[3] for x in m], float), 5, mode="nearest")
    dy = ndimage.uniform_filter1d(dy, 3, mode="nearest"); dx = ndimage.uniform_filter1d(dx, 3, mode="nearest")
    out = []
    for n, ff in enumerate(frames):
        y, x = int(round(dy[n])), int(round(dx[n])); mouth = keys[ki[n]][MOUTH]
        r0, c0 = MOUTH[0].start + y, MOUTH[1].start + x; region = ff[r0:r0 + mouth.shape[0], c0:c0 + mouth.shape[1]]
        mouth = mouth + (region[ring].mean(0) - mouth[ring].mean(0))
        ff[r0:r0 + mouth.shape[0], c0:c0 + mouth.shape[1]] = region * (1 - feather) + mouth * feather
        out.append(ff.clip(0, 255).astype(np.uint8))
    write(out, W / f"{name}.mp4")
    print(name, "patched; offsets dx", [int(round(v)) for v in dx[::4]], "dy", [int(round(v)) for v in dy[::4]], "key", ki[::4].tolist())
