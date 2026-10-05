"""Close-up head clip (480x384, box rows 22-262 cols 180-480 at 640) -> full 640 frames: the close-up downscaled to
300x240 and pasted into idle frame 16 (on the plate) at the box. Only the head box is used by compose's mask, so the
body here is just filler. usage: to_full.py head_seg_retimed.mp4 ../work/head_full.mp4"""
import sys, subprocess, numpy as np
from PIL import Image
S = 640; R, C = (slice(22, 262), slice(180, 480))
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, 384, 480, 3)
base = np.array(Image.open("../weightshift/work/idle16_plate.png").convert("RGB"))
out = []
for x in f:
    g = base.copy(); g[R, C] = np.array(Image.fromarray(x).resize((300, 240), Image.LANCZOS)); out.append(g)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S}x{S}", "-r", "16", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", sys.argv[2]], input=np.stack(out).tobytes(), check=True)
print("wrote", sys.argv[2], len(out), "frames")
