#!/usr/bin/env python3
"""
Review a generated character video before anything is built from it.

A video model's failures are quiet: a lighting flash in the last few frames,
a loop that does not close, a character that drifts or changes size, a
background that stops being flat. Each of those becomes a visible defect
several paid steps later, so this script measures them on the raw video and
says pass or fail, with a contact sheet to look at.

  review_video.py <video.mp4> [--trim-end N] [--loop] [--sheet out.png]
                  [--json out.json] [--background auto|#rrggbb]

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
from PIL import Image

# Thresholds. Measured on clean clips the foreground luminance wobbles by
# about +-1 per frame; a lighting flash moved it +5 to +7.
END_FLASH_DELTA = 3.0      # last kept frames vs. the body median: fail
SPIKE_DELTA = 4.0          # any frame vs. the clip median: warn (effects do this on purpose)
LOOP_GAP = 8.0             # first vs last kept frame, 64px, foreground: warn
DRIFT_FRACTION = 0.06      # bbox centre travel as a fraction of frame width: warn (loop only)
SIZE_FRACTION = 0.12       # bbox height change as a fraction of its first value: warn (loop only)
BACKGROUND_STD = 8.0       # colour std-dev of the corner regions: fail
FG_DISTANCE = 45.0         # colour distance from the background that counts as foreground


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


def review(path: Path, background_spec: str, trim_end: int, loop: bool) -> dict:
    frames = _frames(path)
    background = _background(frames[0], background_spec)
    h, w = frames[0].shape[:2]
    kept = frames[: max(1, len(frames) - trim_end)]

    lum, boxes, bg_std = [], [], 0.0
    for rgb in kept:
        dist = np.sqrt(((rgb.astype(float) - background) ** 2).sum(-1))
        fg = dist > FG_DISTANCE
        bg_std = max(bg_std, float(_corners(rgb).std()))
        if not fg.any():
            lum.append(0.0)
            continue
        lum.append(float(rgb[fg].mean()))
        ys, xs = np.where(fg)
        boxes.append([int(np.percentile(xs, 1)), int(np.percentile(ys, 1)),
                      int(np.percentile(xs, 99)), int(np.percentile(ys, 99))])
    lum = np.array(lum)

    failures, warnings = [], []
    body = float(np.median(lum[10:-4])) if len(lum) > 20 else float(np.median(lum))
    end_delta = float(lum[-3:].mean() - body)
    if end_delta > END_FLASH_DELTA:
        failures.append({"flag": "end_flash", "end_minus_body": round(end_delta, 1),
                         "remedy": "raise trim_end, or regenerate the video"})
    spikes = [i + 1 for i, v in enumerate(lum) if abs(v - np.median(lum)) > SPIKE_DELTA]
    if spikes:
        warnings.append({"flag": "luminance_spikes", "frames": spikes[:12], "count": len(spikes),
                         "note": "an intended effect (glow, flash) looks like this too; check the sheet"})
    if bg_std > BACKGROUND_STD:
        failures.append({"flag": "background_not_flat", "max_corner_std": round(bg_std, 1)})

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
            heights = np.array([b[3] - b[1] for b in boxes])
            drift = float((cx.max() - cx.min()) / w)
            size = float((heights.max() - heights.min()) / max(1, heights[0]))
            if drift > DRIFT_FRACTION:
                warnings.append({"flag": "drift", "centre_travel_fraction": round(drift, 3)})
            if size > SIZE_FRACTION:
                warnings.append({"flag": "size_change", "height_change_fraction": round(size, 3)})

    return {
        "video": str(path), "frames": len(frames), "kept": len(kept), "size": [w, h],
        "background": [int(v) for v in background], "loop": loop,
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
    args = ap.parse_args()

    report = review(args.video, args.background, args.trim_end, args.loop)
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
