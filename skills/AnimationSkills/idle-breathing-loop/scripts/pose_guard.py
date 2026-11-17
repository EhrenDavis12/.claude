"""Pose guard: measures a whole-body key against the approved K0 and says PASS or REJECT with reasons.
The body may breathe; it may not walk, resize, or lose the bow. usage: pose_guard.py <key.png> [more keys]"""
import sys, numpy as np
from pathlib import Path
from PIL import Image
K0P = Path(__file__).parent.parent / "approve" / "K0_start_pose.png"
LIMITS = dict(feet_shift_px=8, feet_bottom_px=6, width_change=0.03, height_change=0.03, bow_shift_px=12, quiver_shift_px=12, eye_shift_px=0)
def load(p): return np.array(Image.open(p).convert("RGBA"))
def bbox(mask):
    ys, xs = np.where(mask); return (xs.min(), ys.min(), xs.max(), ys.max()) if len(ys) else None
def feet(im):           # bottom 60 rows of the figure
    a = im[..., 3] > 128; b = bbox(a); rows = a[b[3] - 60:b[3] + 1]; ys, xs = np.where(rows); return (xs.min(), xs.max(), b[3])
def bow(im):            # the bow: brown/orange pixels on the right third, rows 250-700
    r, g, b, a = [im[..., i].astype(int) for i in range(4)]; m = (a > 128) & (r > 120) & (r > g + 30) & (g > b + 10); m[:, :640] = False; m[:330] = False; m[700:] = False
    bb = bbox(m); return ((bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2) if bb else None
def quiver(im):         # red fletching: top-left
    r, g, b, a = [im[..., i].astype(int) for i in range(4)]; m = (a > 128) & (r > 150) & (g < 90) & (b < 90); m[:, 400:] = False; m[350:] = False
    bb = bbox(m); return ((bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2) if bb else None
k0 = load(K0P); kb = bbox(k0[..., 3] > 128); kf = feet(k0); kbow = bow(k0); kq = quiver(k0)
for p in sys.argv[1:]:
    im = load(p); b = bbox(im[..., 3] > 128); f = feet(im); bo = bow(im); q = quiver(im); why = []
    w = (b[2] - b[0]) / (kb[2] - kb[0]) - 1; h = (b[3] - b[1]) / (kb[3] - kb[1]) - 1
    if abs(w) > LIMITS["width_change"]: why.append(f"width {w:+.1%}")
    if abs(h) > LIMITS["height_change"]: why.append(f"height {h:+.1%}")
    fs = max(abs(f[0] - kf[0]), abs(f[1] - kf[1]));  fb = abs(f[2] - kf[2])
    if fs > LIMITS["feet_shift_px"]: why.append(f"feet moved {fs}px")
    if fb > LIMITS["feet_bottom_px"]: why.append(f"feet bottom moved {fb}px")
    if bo is None: why.append("bow not found")
    else:
        d = max(abs(bo[0] - kbow[0]), abs(bo[1] - kbow[1]))
        if d > LIMITS["bow_shift_px"]: why.append(f"bow moved {d}px")
    if q is None: why.append("quiver not found")
    else:
        d = max(abs(q[0] - kq[0]), abs(q[1] - kq[1]))
        if d > LIMITS["quiver_shift_px"]: why.append(f"quiver moved {d}px")
    print(("REJECT " if why else "PASS   ") + Path(p).name + (": " + ", ".join(why) if why else f"  (size {w:+.1%}/{h:+.1%}, feet {fs}px, bow {max(abs(bo[0]-kbow[0]),abs(bo[1]-kbow[1])) if bo else '-'}px, quiver {max(abs(q[0]-kq[0]),abs(q[1]-kq[1])) if q else '-'}px)"))
