"""v3: whole-body key finish, no graft. Qwen edit (opaque on grey) -> BiRefNet mask (hardened: solid
inside, 1 px edge) -> drop any plate-grey pixel -> colour-match to the approved K0 -> RGBA.
usage: finish_key_body.py <edit.png> <out.png> [--mask m.png]"""
import sys, numpy as np
from pathlib import Path
from PIL import Image
from scipy import ndimage
sys.path.insert(0, "/Users/ehrendavis/work/local-RED-dev/src/LLMs"); import generate as G
HERE = Path(__file__).parent; K0P = HERE.parent / "approve" / "K0_start_pose.png"; S = 1024
edit_p, out_p = Path(sys.argv[1]), Path(sys.argv[2]); mask_p = Path(sys.argv[sys.argv.index("--mask") + 1]) if "--mask" in sys.argv else None
ed = Image.open(edit_p).convert("RGB").resize((S, S), Image.LANCZOS); raw = np.array(ed).astype(float)
if mask_p is None:
    tmp = HERE / "tmp"; tmp.mkdir(exist_ok=True); src = tmp / (edit_p.stem + "_src.png"); mask_p = tmp / (edit_p.stem + "_m.png")
    ed.save(src); G.matte(src, mask_p, mask_only=True)
m = np.array(Image.open(mask_p).convert("L").resize((S, S), Image.BILINEAR)).astype(float) / 255
solid = m > 0.5
plate = np.abs(raw - 128).max(2) < 6                      # the grey plate Qwen painted behind/through the figure
solid &= ~plate
a = ndimage.gaussian_filter(solid.astype(float), 0.8)
k0 = np.array(Image.open(K0P).convert("RGBA")).astype(float)
def stats(rgb, sel): px = rgb[sel]; return px.mean(0), px.std(0)
mu, sd = stats(raw, solid); rmu, rsd = stats(k0[..., :3], k0[..., 3] > 200)
rgb = ((raw - mu) / np.maximum(sd, 1) * rsd + rmu).clip(0, 255)
out = np.dstack([rgb, a * 255]).astype(np.uint8); Image.fromarray(out, "RGBA").save(out_p)
print("wrote", out_p, "px", int(solid.sum()), "plate px dropped inside mask", int((plate & (m > 0.5)).sum()))
