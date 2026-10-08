"""v3 glance trial: K0 -> K1 (whole-body key) -> K0, Wan 2.2 14B first-last-frame, 33 frames a segment,
breathing in every prompt, GREY plate (#7f7f7f) instead of magenta, no upscale (640 -> 512 cell).
usage: build_v3.py <K1.png>   outputs: work/seg*.mp4, glance_v3.png + .sheet.json, preview gif"""
import sys, io, json, math, subprocess, numpy as np
from pathlib import Path
from PIL import Image
sys.path.insert(0, "/Users/ehrendavis/work/local-RED-dev/src/Asset-Gen-Framework"); sys.path.insert(0, "/Users/ehrendavis/work/local-RED-dev/src/LLMs")
from agf import matting; import generate as G
HERE = Path(__file__).parent; W = HERE / "work"; W.mkdir(exist_ok=True)
S, CELL, FR, FPS, SEED = 640, 512, 33, 16, 7; PLATE = (127, 127, 127); PLATE_HEX = "#7f7f7f"
def log(*a): print(*a, flush=True)
def png(a): b = io.BytesIO(); Image.fromarray(a).save(b, "PNG"); return b.getvalue()
def matte(rgb, mask):
    return np.array(Image.open(io.BytesIO(matting.apply(png(rgb), png(mask), {"grow": 3, "erode": 1, "threshold": 60, "background": PLATE_HEX,
            "despill": False, "drop_backdrop_inside": True}))).convert("RGBA"))
def birefnet_mask(rgb, name):
    """No model: the plate is flat grey, so flood-fill plate-coloured pixels from the corners; everything the flood
    cannot reach is the figure. Enclosed pockets are handled by pocket_mask as before."""
    from scipy import ndimage
    x = rgb.astype(int); plate = ((x.max(2) - x.min(2)) < 24) & (x.mean(2) > 100) & (x.mean(2) < 160)
    lab, n = ndimage.label(plate); edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(edge)); return np.where(bg, 0, 255).astype(np.uint8)
def stats(rgba): m = rgba[..., 3] > 200; px = rgba[..., :3][m].astype(float); return px.mean(0), px.std(0)
def colour_match(rgba, ref):
    mu, sd = stats(rgba); rmu, rsd = ref; out = rgba.astype(float).copy(); m = out[..., 3] > 0
    out[..., :3][m] = ((out[..., :3][m] - mu) / np.maximum(sd, 1) * rsd + rmu); return out.clip(0, 255).astype(np.uint8)
def on_plate(rgba):
    im = Image.fromarray(rgba, "RGBA").resize((S, S), Image.LANCZOS); bg = Image.new("RGBA", im.size, PLATE + (255,)); bg.alpha_composite(im); return np.array(bg.convert("RGB"))
def read(p):
    w, h = [int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.split(",")[:2]]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
k0 = np.array(Image.open(HERE.parent / "approve" / "K0_start_pose.png").convert("RGBA")); REF = stats(k0)
from scipy import ndimage
# pockets: where K0 is transparent (eroded 2 px so edges are safe), at the 640 working size
K0_HOLE = np.array(Image.fromarray(k0[..., 3]).resize((S, S), Image.BILINEAR)) < 8   # no erosion: the arrow gaps are only ~5 px wide here
POCKET_BOXES = [(slice(90, 210), slice(140, 230)), (slice(340, 380), slice(405, 445))]   # (rows, cols) at 640: quiver, glove-to-bow gap
def pocket_mask(raw, mask):
    rgb = raw.astype(int); plate = ((rgb.max(2) - rgb.min(2)) < 40) & (rgb.mean(2) > 80) & (rgb.mean(2) < 205)
    box = np.zeros(plate.shape, bool)
    for r, c in POCKET_BOXES: box[r, c] = True
    mask = mask.copy(); mask[plate & box] = 0; return mask
def drop_pockets(rgba):
    rgb = rgba[..., :3].astype(int); plate = ((rgb.max(2) - rgb.min(2)) < 28) & (rgb.mean(2) > 90) & (rgb.mean(2) < 195)
    rgba = rgba.copy(); rgba[..., 3][plate & K0_HOLE] = 0; return rgba
BASE = ("2D cartoon game animation of this chibi forest archer standing in place, alive and breathing: his chest and shoulders rise and fall "
        "with one slow breath, the cloak swaying a little with it. {motion} Both feet stay planted; the bow stays in his hand; the quiver stays on "
        "his back. Calm face, eyes open, mouth closed. Exactly the same flat cel shading, shadows and colours throughout. Static camera, flat grey background.")
OUT = "He turns his head and shoulders a little to glance toward his bow, the hood turning with the head."
BACK = "He turns back to face forward and settles into his rest pose, the hood turning with the head."
seq = list(read(HERE / "breathe_locked.mp4"))[:-1]   # last frame == first (both K0): drop it so the loop continues cleanly
log("sequence", len(seq), "frames")
cells = []
for n, f in enumerate(seq):
    rgba = colour_match(drop_pockets(matte(f, pocket_mask(f, birefnet_mask(f, f"mask_{n:03d}")))), REF)
    a = rgba[..., 3:4].astype(float) / 255
    pre = np.array(Image.fromarray((rgba[..., :3] * a).astype(np.uint8)).resize((CELL, CELL), Image.LANCZOS)).astype(float)
    al = np.array(Image.fromarray(rgba[..., 3]).resize((CELL, CELL), Image.LANCZOS)).astype(float)[..., None] / 255
    cells.append(np.dstack([np.where(al > 0, pre / np.maximum(al, 1e-3), 0), al[..., 0] * 255]).clip(0, 255).astype(np.uint8))
    if n % 10 == 0: log(" frame", n)
def pre(c): a = c[..., 3:4] / 255.0; return np.concatenate([c[..., :3] * a, c[..., 3:4]], -1)
def un(p): a = p[..., 3:4]; return np.concatenate([np.where(a > 0, p[..., :3] / np.maximum(a / 255, 1e-3), 0), a], -1).clip(0, 255)
A, B = pre(cells[-1].astype(float)), pre(cells[0].astype(float)); cells[-1] = un(A * 2 / 3 + B / 3).astype(np.uint8); cells[0] = un(A / 3 + B * 2 / 3).astype(np.uint8)
cols = math.ceil(math.sqrt(len(cells))); rows = math.ceil(len(cells) / cols); sheet = np.zeros((rows * CELL, cols * CELL, 4), np.uint8)
for n, c in enumerate(cells): r, q = divmod(n, cols); sheet[r * CELL:(r + 1) * CELL, q * CELL:(q + 1) * CELL] = c
Image.fromarray(sheet, "RGBA").save(HERE / "idle_v5.png"); json.dump({"frames": len(cells), "columns": cols, "rows": rows, "frame": CELL, "fps": 16, "loop": True}, open(HERE / "idle_v5.sheet.json", "w"))
bg = np.array([40, 40, 40], np.float32); frames = [Image.fromarray((c[..., :3] * (c[..., 3:4] / 255) + bg * (1 - c[..., 3:4] / 255)).astype(np.uint8)).resize((320, 320), Image.LANCZOS) for c in cells]
frames[0].save(HERE / "idle_v5_preview.gif", save_all=True, append_images=frames[1:], duration=1000 // 16, loop=0)
log("sheet idle_v5.png", len(cells), "frames")
