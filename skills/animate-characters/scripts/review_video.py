#!/usr/bin/env python3
"""
Review a generated character video before anything is built from it.

A video model's failures are quiet: a lighting flash in the last few frames,
a loop that does not close, a character that drifts or changes size, a
background that stops being flat. Each of those becomes a visible defect
several paid steps later, so this script measures them on the raw video and
says pass or fail, with a contact sheet to look at.

  review_video.py <video.mp4> [--trim-end N] [--loop] [--strict-motion]
                  [--ends-empty] [--sheet out.png] [--json out.json]
                  [--background auto|#rrggbb]

`--contained` fails a clip whose foreground touches the frame border in any
kept frame: a sheet cell cuts it off there, and the cut edge reads as a box.
`--strict-motion` turns the loop's drift warning into a failure: a
projectile effect that travels inside its own clip cannot be used, because
the app supplies the travel. `--ends-empty` is for a burst that must vanish:
the end-flash check is skipped (the end *is* a change) and instead the clip
fails if its last kept frame still holds foreground, or its first has none.

`--trim-end N` ignores the last N frames, because the sheet will too: a
first-and-last-frame conditioned model blends toward its last frame over the
final few frames, which brightens them (measured +4 to +14 luminance on 13 of
18 clips) -- the frames are dropped, not fixed. `--loop` adds the checks a
looping clip needs: that the last kept frame matches the first, and that the
character neither drifts nor changes size.

Failures (exit 1) are defects nothing downstream can repair: a brightness
jump at the end of the kept range, a background that is not flat. Warnings
(exit 0, listed) are things a person should look at on the contact sheet: a
luminance spike mid-clip (often an intended effect), a loop that does not
quite close, drift.

Only the framework's PyAV, Pillow and numpy are needed; run it with the
Asset-Gen-Framework venv's python.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageFilter

# Thresholds. Measured on clean clips the foreground luminance wobbles by
# about +-1 per frame; a lighting flash moved it +5 to +7.
END_FLASH_DELTA = 3.0      # last kept frames vs. the body median: fail
SPIKE_DELTA = 4.0          # any frame vs. the clip median: warn (effects do this on purpose)
LOOP_GAP = 8.0             # first vs last kept frame, 64px, foreground: warn
DRIFT_FRACTION = 0.06      # bbox centre travel as a fraction of frame width: warn (loop only)
SIZE_FRACTION = 0.12       # bbox height change as a fraction of its first value: warn (loop only)
BACKGROUND_STD = 8.0       # colour std-dev of the corner regions: fail
FG_DISTANCE = 45.0         # colour distance from the background that counts as foreground
EMPTY_FRACTION = 0.005     # foreground pixels left in a burst's last kept frame: fail (--ends-empty)
BORDER_FRACTION = 0.04     # width of the frame border judged by --contained
BORDER_DENSITY = 0.02      # share of that border still foreground after eroding 2px: fail
                           # (a spray of dots erodes to nothing; a cut shard is ~1% of the border)


def _frames(path: Path) -> list[np.ndarray]:
    out = []
    with av.open(str(path)) as container:
        for frame in container.decode(container.streams.video[0]):
            out.append(frame.to_ndarray(format="rgb24"))
    if not out:
        raise SystemExit(f"{path}: no frames decoded")
    return out


def _corners(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    m = max(4, min(h, w) // 25)
    return np.concatenate([rgb[:m, :m].reshape(-1, 3), rgb[:m, -m:].reshape(-1, 3),
                           rgb[-m:, :m].reshape(-1, 3), rgb[-m:, -m:].reshape(-1, 3)])


def _background(rgb: np.ndarray, spec: str) -> np.ndarray:
    if spec != "auto":
        return np.array([int(spec[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
    return np.median(_corners(rgb), axis=0)


def review(path: Path, background_spec: str, trim_end: int, loop: bool,
           strict_motion: bool = False, ends_empty: bool = False, contained: bool = False) -> dict:
    frames = _frames(path)
    background = _background(frames[0], background_spec)
    h, w = frames[0].shape[:2]
    kept = frames[: max(1, len(frames) - trim_end)]

    lum, boxes, fg_fraction, corner_std, touching = [], [], [], [], []
    b = max(2, int(round(min(h, w) * BORDER_FRACTION)))
    for i, rgb in enumerate(kept):
        dist = np.sqrt(((rgb.astype(float) - background) ** 2).sum(-1))
        fg = dist > FG_DISTANCE
        corner_std.append(float(_corners(rgb).std()))
        fg_fraction.append(float(fg.mean()))
        border = np.zeros_like(fg)
        border[:b], border[-b:], border[:, :b], border[:, -b:] = True, True, True, True
        solid = np.array(Image.fromarray((fg & border).astype(np.uint8) * 255).filter(ImageFilter.MinFilter(5))) > 0
        if float(solid.sum()) / float(border.sum()) > BORDER_DENSITY:
            touching.append(i + 1)
        if not fg.any():
            lum.append(0.0)
            continue
        lum.append(float(rgb[fg].mean()))
        ys, xs = np.where(fg)
        boxes.append([int(np.percentile(xs, 1)), int(np.percentile(ys, 1)),
                      int(np.percentile(xs, 99)), int(np.percentile(ys, 99))])
    lum = np.array(lum)

    failures, warnings = [], []
    # A burst's shards legitimately cross the corners mid-clip, so its background is
    # judged where nothing should be: the first frame and the empty tail.
    bg_std = max(corner_std[:1] + corner_std[-5:]) if ends_empty else max(corner_std)
    if ends_empty:
        if fg_fraction[-1] > EMPTY_FRACTION:
            failures.append({"flag": "not_empty_at_end", "foreground_fraction": round(fg_fraction[-1], 4),
                             "remedy": "regenerate; ask for the burst to vanish sooner"})
        if fg_fraction[0] <= EMPTY_FRACTION:
            failures.append({"flag": "first_frame_empty", "remedy": "regenerate; the effect must be there at the start"})
        with_fg = lum[np.array(fg_fraction) > EMPTY_FRACTION]
        lum_for_spikes = with_fg if len(with_fg) else lum
    else:
        body = float(np.median(lum[10:-4])) if len(lum) > 20 else float(np.median(lum))
        end_delta = float(lum[-3:].mean() - body)
        if end_delta > END_FLASH_DELTA:
            failures.append({"flag": "end_flash", "end_minus_body": round(end_delta, 1),
                             "remedy": "raise trim_end, or regenerate the video"})
        lum_for_spikes = lum
    spikes = [i + 1 for i, v in enumerate(lum_for_spikes) if abs(v - np.median(lum_for_spikes)) > SPIKE_DELTA]
    if spikes:
        warnings.append({"flag": "luminance_spikes", "frames": spikes[:12], "count": len(spikes),
                         "note": "an intended effect (glow, flash) looks like this too; check the sheet"})
    if bg_std > BACKGROUND_STD:
        failures.append({"flag": "background_not_flat", "max_corner_std": round(bg_std, 1)})
    if contained and touching:
        failures.append({"flag": "touches_edge", "frames": touching[:12], "count": len(touching),
                         "remedy": "regenerate; the effect must stay inside the frame, or it is cut off by the cell"})

    if loop:
        small = lambda f: np.array(Image.fromarray(f).resize((64, 64), Image.BOX)).astype(float)
        a, b = small(kept[0]), small(kept[-1])
        fg = (np.sqrt(((a - background) ** 2).sum(-1)) > FG_DISTANCE) | (
            np.sqrt(((b - background) ** 2).sum(-1)) > FG_DISTANCE)
        gap = float(np.abs(a - b)[fg].mean()) if fg.any() else 0.0
        if gap > LOOP_GAP:
            warnings.append({"flag": "loop_gap", "first_vs_last_kept": round(gap, 1)})
        if boxes:
            cx = np.array([(b[0] + b[2]) / 2 for b in boxes])
            # The box's longer side: a thin horizontal projectile doubles its *height*
            # by tilting a few degrees, which is not a change of size.
            extents = np.array([max(b[2] - b[0], b[3] - b[1]) for b in boxes])
            drift = float((cx.max() - cx.min()) / w)
            size = float((extents.max() - extents.min()) / max(1, extents[0]))
            # Travel is what makes a projectile clip unusable; a flapping tassel or
            # licking flame changes the box's size without moving it, so that stays a warning.
            if drift > DRIFT_FRACTION:
                (failures if strict_motion else warnings).append(
                    {"flag": "drift", "centre_travel_fraction": round(drift, 3)})
            if size > SIZE_FRACTION:
                warnings.append({"flag": "size_change", "extent_change_fraction": round(size, 3)})

    return {
        "video": str(path), "frames": len(frames), "kept": len(kept), "size": [w, h],
        "background": [int(v) for v in background], "loop": loop,
        "strict_motion": strict_motion, "ends_empty": ends_empty,
        "foreground_fraction": [round(v, 4) for v in fg_fraction],
        "luminance": [round(float(v), 1) for v in lum],
        "failures": failures, "warnings": warnings, "ok": not failures,
    }


def contact_sheet(path: Path, out: Path, columns: int = 12, cell: int = 160) -> None:
    frames = _frames(path)
    picks = np.linspace(0, len(frames) - 1, min(columns, len(frames))).round().astype(int)
    sheet = Image.new("RGB", (len(picks) * cell, cell))
    for i, n in enumerate(picks):
        sheet.paste(Image.fromarray(frames[n]).resize((cell, cell)), (i * cell, 0))
    sheet.save(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--sheet", type=Path, help="write a contact sheet PNG here")
    ap.add_argument("--json", type=Path, help="write the full report here")
    ap.add_argument("--background", default="auto")
    ap.add_argument("--trim-end", type=int, default=0, help="ignore the last N frames, as the sheet will")
    ap.add_argument("--loop", action="store_true", help="this clip must loop: check closure and drift")
    ap.add_argument("--strict-motion", action="store_true", help="drift and size change fail instead of warn")
    ap.add_argument("--ends-empty", action="store_true", help="the clip must end on the empty background")
    ap.add_argument("--contained", action="store_true", help="no frame may have foreground at the border")
    args = ap.parse_args()

    report = review(args.video, args.background, args.trim_end, args.loop,
                    strict_motion=args.strict_motion, ends_empty=args.ends_empty, contained=args.contained)
    if args.sheet:
        contact_sheet(args.video, args.sheet)
        report["sheet"] = str(args.sheet)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + "\n")
    summary = {k: report[k] for k in ("video", "frames", "kept", "size", "ok", "failures", "warnings")}
    print(json.dumps(summary, indent=1))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
