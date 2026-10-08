"""One front door for every model job, in three modes. Same commands and flags as src/LLMs/generate.py.

  python3 gen.py --mode local   keyframes "..." --start a.png --end b.png --frames 33 -o a_to_b.mp4
  python3 gen.py --mode fast    edit K0.png "same archer, head turned" --seed 71 -o key.png
  GEN_MODE=fast ./render_hit.sh 7          # a script that calls gen.py picks the mode up from the environment
  python3 gen.py --mode fast --dry-run keyframes ...     # say where it would run and what it would cost; no call

  local    everything on this Mac (ComfyUI through generate.py). Free. The default.
  fast     the two slow jobs go to Replicate - edit (Qwen) and keyframes (Wan first-last-frame).
           Everything else stays local, where it already takes seconds.
  100fast  fast, plus video matte and video upscale on Replicate. interpolate (FILM) and single-image
           matte / upscale stay local in every mode: local is the faster side for those.

`--mode` wins over GEN_MODE; with neither, local. Replicate needs REPLICATE_API_TOKEN and ffmpeg.
Every paid call prints its cost and adds a line to the ledger (GEN_LEDGER, default
src/asset-animation-demo/local_runs/replicate_spend.csv). Standard library only.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GENERATE = ROOT / "src/LLMs/generate.py"
LEDGER = Path(os.environ.get("GEN_LEDGER", ROOT / "src/asset-animation-demo/local_runs/replicate_spend.csv"))
API = "https://api.replicate.com/v1"
MODES = ("local", "fast", "100fast")
NEUTRAL = "0x808080"                     # generate.py lays a transparent input on this before edit / keyframes
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}

# Which commands leave the Mac in each mode. matte and upscale go only when the source is a video.
REMOTE = {"local": set(), "fast": {"edit", "keyframes"}, "100fast": {"edit", "keyframes", "matte", "upscale"}}

# Community models need a pinned version; official ones are called by name. Prices read 2026-10-06.
EDIT_MODEL, EDIT_PRICE = "qwen/qwen-image-edit-2511", 0.03                       # per image
KEYFRAME_MODEL, KEYFRAME_PRICE = "wan-video/wan-2.2-i2v-fast", {"480p": 0.05, "720p": 0.11}   # per video
MATTE_VERSION = "d4fd02a2eaddddfd6fbe77570e7408b3f15ee4dcf2ded407ace7a0f9d114ae87"   # sprited/birefnet-video
UPSCALE_VERSION = "3e56ce4b57863bd03048b42bc09bdd4db20d427cca5fde9d8ae4dc60e1bb4775"  # lucataco/real-esrgan-video
L40S, A100 = 0.000975, 0.0014            # $ per second, for the two models billed by time
KEYFRAME_MIN, KEYFRAME_MAX = 81, 121     # the hosted Wan will not make fewer than 81 frames


# ---------- small local helpers ----------
def _sh(*cmd: str) -> str:
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {done.stderr.strip()[-800:]}")
    return done.stdout


def _probe(path: Path) -> tuple[int, int, int]:
    """Width, height and frame count of an image or video."""
    out = _sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
              "stream=width,height,nb_read_frames", "-of", "json", str(path))
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"]), int(s.get("nb_read_frames") or 1)


def _flat(path: Path, tmp: Path) -> Path:
    """The image laid on flat mid grey, as generate.py does: see-through pixels hold colour a model would draw."""
    w, h, _ = _probe(path)
    out = tmp / f"flat_{path.stem}_{len(list(tmp.iterdir()))}.png"
    _sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={NEUTRAL}:s={w}x{h}", "-i", str(path),
        "-filter_complex", "[0][1]overlay=format=auto", "-frames:v", "1", str(out))
    return out


def _data_uri(path: Path) -> str:
    kind = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".mp4": "video/mp4",
            ".mov": "video/quicktime", ".webm": "video/webm"}.get(path.suffix.lower(), "application/octet-stream")
    return f"data:{kind};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _ledger(command: str, model: str, seconds: float, dollars: float, out: Path) -> None:
    new = not LEDGER.exists()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["when", "command", "model", "seconds", "dollars", "output"])
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), command, model, f"{seconds:.0f}", f"{dollars:.3f}", str(out)])


# ---------- Replicate ----------
def _api(url: str, body: dict | None = None, wait: bool = False) -> dict:
    # Replicate answers urllib's default User-Agent with 403.
    headers = {"Authorization": "Bearer " + os.environ["REPLICATE_API_TOKEN"], "User-Agent": "gen.py/1"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if wait:
        headers["Prefer"] = "wait=60"
    data = None if body is None else json.dumps(body).encode()
    for pause in (30, 60, 120, 240, None):     # a burst of short jobs trips the rate limit
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and pause:
                time.sleep(pause)
                continue
            raise RuntimeError(f"Replicate rejected the call ({e.code}): {e.read().decode(errors='replace')[:800]}") from None
    raise RuntimeError("unreachable")


def _predict(model: str, inputs: dict, raw: Path, timeout: float = 1800) -> float:
    """Run one prediction, write its first output file to `raw`, return the seconds Replicate billed."""
    if ":" in model:
        p = _api(f"{API}/predictions", {"version": model.split(":")[1], "input": inputs}, wait=True)
    else:
        p = _api(f"{API}/models/{model}/predictions", {"input": inputs}, wait=True)
    deadline = time.time() + timeout
    while p["status"] in ("starting", "processing"):
        if time.time() > deadline:
            raise TimeoutError(f"{model}: prediction {p['id']} did not finish within {timeout:.0f}s")
        time.sleep(3)
        p = _api(p["urls"]["get"])
    if p["status"] != "succeeded":
        raise RuntimeError(f"{model}: {p['status']}: {p.get('error')}")
    output = p["output"][0] if isinstance(p["output"], list) else p["output"]
    with urllib.request.urlopen(urllib.request.Request(output, headers={"User-Agent": "gen.py/1"}), timeout=600) as r:
        raw.write_bytes(r.read())
    return float((p.get("metrics") or {}).get("predict_time") or 0)


def edit(a, tmp: Path, dry: bool) -> tuple[str, float, float]:
    if not 1 <= len(a.images) <= 3:
        raise ValueError("edit takes one to three images")
    if dry:
        return EDIT_MODEL, 0, EDIT_PRICE
    inputs = {"image": [_data_uri(_flat(p, tmp)) for p in a.images], "prompt": a.instruction,
              "output_format": "png", "aspect_ratio": "match_input_image"}
    if a.seed is not None:
        inputs["seed"] = a.seed
    raw = tmp / "edit.png"
    seconds = _predict(EDIT_MODEL, inputs, raw)
    w, h, _ = _probe(a.images[0])             # the result has the first image's size, as it does locally
    a.out.parent.mkdir(parents=True, exist_ok=True)
    _sh("ffmpeg", "-y", "-v", "error", "-i", str(raw), "-vf", f"scale={w}:{h}:flags=lanczos", "-frames:v", "1", str(a.out))
    return EDIT_MODEL, seconds, EDIT_PRICE


def keyframes(a, tmp: Path, dry: bool) -> tuple[str, float, float]:
    if a.frames % 4 != 1:
        raise ValueError("frames must be 4n+1 (e.g. 17, 33, 49, 81)")
    if a.frames > KEYFRAME_MAX:
        raise ValueError(f"the hosted Wan makes at most {KEYFRAME_MAX} frames; run this one with --mode local")
    resolution = "480p" if max(a.width, a.height) <= 640 else "720p"
    if dry:
        return KEYFRAME_MODEL, 0, KEYFRAME_PRICE[resolution]
    made = max(a.frames, KEYFRAME_MIN)
    inputs = {"image": _data_uri(_flat(a.start, tmp)), "last_image": _data_uri(_flat(a.end, tmp)), "prompt": a.prompt,
              "num_frames": made, "resolution": resolution, "frames_per_second": 16}
    if a.seed is not None:
        inputs["seed"] = a.seed
    raw = tmp / "keyframes.mp4"
    seconds = _predict(KEYFRAME_MODEL, inputs, raw)
    w, h, got = _probe(raw)
    if abs(w / h - a.width / a.height) > 0.02:
        kept = a.out.with_suffix(".raw.mp4")
        kept.write_bytes(raw.read_bytes())
        raise RuntimeError(f"Replicate returned {w}x{h}, not the {a.width}x{a.height} shape asked for; raw clip kept at {kept}")
    # The clip lands on the end frame only at its last frame, so a shorter clip is the whole move sampled
    # evenly - first and last frames kept - never the first N frames.
    keep = sorted({round(i * (got - 1) / (a.frames - 1)) for i in range(a.frames)})
    pick = "+".join(f"eq(n\\,{n})" for n in keep)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    _sh("ffmpeg", "-y", "-v", "error", "-i", str(raw), "-vf",
        f"select='{pick}',setpts=N/({a.fps}*TB),scale={a.width}:{a.height}:flags=lanczos",
        "-r", str(a.fps), "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", str(a.out))
    return KEYFRAME_MODEL, seconds, KEYFRAME_PRICE[resolution]


def matte(a, tmp: Path, dry: bool) -> tuple[str, float, float]:
    """Video only: a white-on-black mask video, as generate.py returns."""
    model = "sprited/birefnet-video:" + MATTE_VERSION
    if dry:
        return model, 0, 8 * L40S
    raw = tmp / "mask.mp4"
    seconds = _predict(model, {"video": _data_uri(a.source), "variant": "toonout", "output_format": "mask",
                               "video_output_type": "mp4", "video_quality": "maximum"}, raw)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(raw.read_bytes())
    return model, seconds, seconds * L40S


def upscale(a, tmp: Path, dry: bool) -> tuple[str, float, float]:
    """Video only. The clip goes inline: this model fails on Replicate file URLs. It also dies on long clips."""
    model = "lucataco/real-esrgan-video:" + UPSCALE_VERSION
    if dry:
        return model, 0, 75 * A100
    raw = tmp / "upscaled.mp4"
    seconds = _predict(model, {"video_path": _data_uri(a.source), "model": "RealESRGAN_x4plus_anime_6B",
                               "resolution": "2k"}, raw)
    w, h, _ = _probe(a.source)
    tw, th = round(w * a.scale / 2) * 2, round(h * a.scale / 2) * 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    _sh("ffmpeg", "-y", "-v", "error", "-i", str(raw), "-vf", f"scale={tw}:{th}:flags=lanczos",
        "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", str(a.out))
    return model, seconds, seconds * A100


def _parse(argv: list[str]) -> argparse.Namespace:
    """generate.py's own flags for the four commands that can leave the Mac."""
    ap = argparse.ArgumentParser(prog="gen.py")
    sub = ap.add_subparsers(dest="kind", required=True)
    e = sub.add_parser("edit")
    e.add_argument("images", type=Path, nargs="+")
    e.add_argument("instruction")
    e.add_argument("-o", "--out", type=Path, required=True)
    e.add_argument("--steps", type=int, default=4)
    e.add_argument("--seed", type=int)
    k = sub.add_parser("keyframes")
    k.add_argument("prompt")
    k.add_argument("--start", type=Path, required=True)
    k.add_argument("--end", type=Path, required=True)
    k.add_argument("-o", "--out", type=Path, default=Path("keyframes.mp4"))
    k.add_argument("--width", type=int, default=640)
    k.add_argument("--height", type=int, default=640)
    k.add_argument("--frames", type=int, default=81)
    k.add_argument("--fps", type=int, default=16)
    k.add_argument("--steps", type=int, default=4)
    k.add_argument("--seed", type=int)
    m = sub.add_parser("matte")
    m.add_argument("source", type=Path)
    m.add_argument("-o", "--out", type=Path, required=True)
    m.add_argument("--mask-only", action="store_true")
    u = sub.add_parser("upscale")
    u.add_argument("source", type=Path)
    u.add_argument("-o", "--out", type=Path, required=True)
    u.add_argument("--scale", type=float, default=4.0)
    u.add_argument("--model")
    return ap.parse_args(argv)


def main() -> None:
    argv = sys.argv[1:]
    mode, dry = os.environ.get("GEN_MODE", "local"), False
    while argv and argv[0] in ("--mode", "--dry-run"):
        if argv[0] == "--dry-run":
            dry, argv = True, argv[1:]
        else:
            mode, argv = argv[1], argv[2:]
    if mode not in MODES:
        sys.exit(f"gen.py: mode must be one of {', '.join(MODES)} (got {mode!r})")
    if not argv or argv[0] in ("-h", "--help"):
        sys.exit(__doc__)
    command = argv[0]
    remote = command in REMOTE[mode]
    if remote and command in ("matte", "upscale"):
        source = next((Path(x) for x in argv[1:] if not x.startswith("-")), Path(""))
        remote = source.suffix.lower() in VIDEO_SUFFIXES       # a single image is seconds locally
    if not remote:
        if dry:
            print(f"[{mode}] {command}: local, free")
            return
        os.execv(sys.executable, [sys.executable, str(GENERATE), *argv])
    a = _parse(argv)
    if "REPLICATE_API_TOKEN" not in os.environ and not dry:
        sys.exit("gen.py: REPLICATE_API_TOKEN is not set")
    started = time.time()
    with tempfile.TemporaryDirectory() as t:
        try:
            model, seconds, dollars = {"edit": edit, "keyframes": keyframes, "matte": matte, "upscale": upscale}[command](a, Path(t), dry)
        except Exception as e:
            sys.exit(f"gen.py: {e}")
    if dry:
        print(f"[{mode}] {command}: Replicate {model.split(':')[0]}, about ${dollars:.2f}")
        return
    _ledger(command, model.split(":")[0], seconds, dollars, a.out)
    print(f"{a.out}  ({time.time() - started:.0f}s, Replicate {model.split(':')[0]}, ${dollars:.2f})")


if __name__ == "__main__":
    main()
