#!/usr/bin/env python3
"""
Generate character animations as transparent sprite sheets, from a YAML
config, through the Asset-Gen-Framework.

  animate.py animate.yaml                        everything in the config
  animate.py animate.yaml --character knight     one character
  animate.py animate.yaml --action idle          one action (plus references)
  animate.py animate.yaml --stage reference      stop after that stage
  animate.py animate.yaml --dry-run              write the manifest, spend nothing
  animate.py animate.yaml --regenerate knight-idle-video
                                                 redo one entry; its downstream
                                                 drafts are deleted so they rebuild

Per character: a reference image, then per action a chain of video ->
review -> mask -> frames -> sheet. Every generated step is a framework
manifest entry, run by name and recorded; this script only decides which
entries exist yet. The framework refuses a manifest naming a file that is not
there, so the manifest is rewritten with only the entries whose inputs exist,
the pending ones are generated, and that repeats until the chains complete.

The review is the one step that is not a framework entry: after a video
lands it is measured (see review_video.py) and a failing video blocks its
chain -- a `<action>.review.json` with "ok": false sits beside it until the
video is regenerated. Warnings are printed and do not block; look at the
contact sheet written beside the video.

Run with the framework venv's python, from the directory holding the
config, which is also where assetgen.yaml lives. Needs REPLICATE_API_TOKEN.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
STAGES = ["reference", "video", "mask", "frames", "sheet"]

DEFAULTS = {
    "reference": {
        "model": "sourceful/riverflow-2.0-pro",
        "prompt_key": "instruction",
        "inputs": {"aspect_ratio": "1:1", "resolution": "1K", "transparency": False,
                   "output_format": "png", "enhance_prompt": False},
        "match": ("Match the exact art style, line weight, shading and proportions of the "
                  "reference image, but draw a different character: "),
    },
    "video": {
        "model": "wan-video/wan-2.2-i2v-fast",
        "frames": 81, "fps": 16, "trim_end": 6, "keep_every": 2,
        "inputs": {"resolution": "480p", "go_fast": True, "interpolate_output": False},
        "template": ("2D cartoon game animation. {motion} The camera is completely static "
                     "with no zoom or pan. The character stays centered and the same size. "
                     "The flat background stays plain and unchanged. No text."),
        "one_shot": "The character briskly {motion}, then returns to exactly the starting pose and holds it.",
    },
    "mask": {
        "model": "sprited/birefnet-video:d4fd02a2eaddddfd6fbe77570e7408b3f15ee4dcf2ded407ace7a0f9d114ae87",
        "inputs": {"variant": "toonout", "output_format": "mask", "video_output_type": "mp4",
                   "video_quality": "maximum"},
        "grow": 3, "threshold": 60, "feather": 0, "background": "auto",
    },
    "sheet": {"frame": 256, "columns": 7, "rows": 6},
}


def merged(section: str, cfg: dict) -> dict:
    out = json.loads(json.dumps(DEFAULTS[section]))
    user = cfg.get(section) or {}
    for key, value in user.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key].update(value)
        else:
            out[key] = value
    return out


class Plan:
    def __init__(self, config_path: Path):
        self.root = config_path.resolve().parent
        cfg = yaml.safe_load(config_path.read_text())
        self.cfg = cfg
        self.agf = (self.root / cfg.get("agf", "../Asset-Gen-Framework/.venv/bin/agf")).resolve()
        agf_cfg = yaml.safe_load((self.root / "assetgen.yaml").read_text())
        self.drafts = (self.root / agf_cfg["drafts"]).resolve()
        self.style = cfg["style"].strip()
        self.reference = merged("reference", cfg)
        self.video = merged("video", cfg)
        self.mask = merged("mask", cfg)
        self.sheet = merged("sheet", cfg)
        self.actions = cfg["actions"]
        self.characters = cfg["characters"]
        self.style_anchor = cfg.get("style_anchor") or self.characters[0]["id"]
        v = self.video
        self.kept = list(range(1, v["frames"] - v["trim_end"] + 1, v["keep_every"]))
        cells = self.sheet["columns"] * self.sheet["rows"]
        if len(self.kept) > cells:
            raise SystemExit(f"{len(self.kept)} kept frames do not fit a {self.sheet['columns']}x{self.sheet['rows']} sheet")

    # ---------------------------------------------------------------- entries
    def entries_for(self, c: dict) -> list[dict]:
        cid = c["id"]
        ref = f"characters/{cid}/reference.png"
        r = self.reference
        prompt = f"{self.style} The character: {c['look']}"
        entry = {"name": f"{cid}-reference", "type": "image", "model": r["model"],
                 "prompt_key": r["prompt_key"], "prompt": prompt, "inputs": dict(r["inputs"]),
                 "output": ref, "format": "png"}
        if cid != self.style_anchor:
            entry["prompt"] = f"{self.style} {r['match']}{c['look']}"
            entry["input_files"] = {"init_images": [f"drafts:characters/{self.style_anchor}/reference.png"]}
        out = [entry]
        v, m, s = self.video, self.mask, self.sheet
        for action, spec in self.actions.items():
            spec = spec or {}
            motion = spec.get("motion") or v["one_shot"].format(motion=c[action])
            video = f"characters/{cid}/{action}.mp4"
            mask = f"characters/{cid}/{action}_mask.mp4"
            frames_dir = f"characters/{cid}/{action}_frames"
            out += [
                {"name": f"{cid}-{action}-video", "type": "video", "model": v["model"],
                 "prompt": v["template"].format(motion=motion),
                 "inputs": {"num_frames": v["frames"], "frames_per_second": v["fps"], **v["inputs"]},
                 "input_files": {"image": f"drafts:{ref}", "last_image": f"drafts:{ref}"},
                 "output": video, "format": "mp4"},
                {"name": f"{cid}-{action}-mask", "type": "video", "model": m["model"],
                 "inputs": dict(m["inputs"]), "input_files": {"video": f"drafts:{video}"},
                 "output": mask, "format": "mp4"},
                {"name": f"{cid}-{action}-frames", "type": "image", "operation": "extract_frames",
                 "source": f"drafts:{video}", "frame_count": v["frames"],
                 "matte": {"mask": f"drafts:{mask}", "background": m["background"], "grow": m["grow"],
                           "threshold": m["threshold"], "feather": m["feather"]},
                 "resize": [s["frame"], s["frame"]],
                 "output": f"{frames_dir}/frame_{{n:02d}}.png", "format": "png"},
                {"name": f"{cid}-{action}-sheet", "type": "sprite_sheet", "operation": "assemble_sheet",
                 "frame_count": len(self.kept), "frame_size": [s["frame"], s["frame"]],
                 "layout": {"columns": s["columns"], "rows": s["rows"]},
                 "frames": [f"drafts:{frames_dir}/frame_{n:02d}.png" for n in self.kept],
                 "output": f"characters/{cid}/{action}.png", "format": "png"},
            ]
        return out

    # ------------------------------------------------------------- readiness
    def refs_of(self, entry: dict) -> list[str]:
        refs = []
        for value in (entry.get("input_files") or {}).values():
            refs += value if isinstance(value, list) else [value]
        refs += entry.get("frames") or []
        if "source" in entry:
            refs.append(entry["source"])
        if "matte" in entry:
            refs.append(entry["matte"]["mask"])
        return refs

    def ready(self, entry: dict) -> bool:
        for ref in self.refs_of(entry):
            root, rel = ref.split(":", 1)
            if root != "drafts" or not (self.drafts / rel).exists():
                return False
        if stage_of(entry) == "mask":
            review = self.review_path(entry)
            if review.exists() and not json.loads(review.read_text()).get("ok", False):
                return False
        return True

    def review_path(self, entry: dict) -> Path:
        cid, action = entry["name"].split("-")[0], entry["name"].split("-")[1]
        return self.drafts / "characters" / cid / f"{action}.review.json"

    # ----------------------------------------------------------------- agf
    def write_manifest(self, entries: list[dict]) -> None:
        header = ("# GENERATED by the animate-characters skill from animate.yaml -- edit that,\n"
                  "# not this. Only entries whose inputs already exist are listed.\n")
        (self.root / "asset_prompts.yaml").write_text(header + yaml.safe_dump(entries, sort_keys=False, width=88))

    def agf_run(self, *args: str) -> dict:
        proc = subprocess.run([str(self.agf), *args], cwd=self.root, capture_output=True, text=True)
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            print(proc.stdout, proc.stderr, file=sys.stderr)
            raise SystemExit(f"agf {' '.join(args)} produced no JSON (exit {proc.returncode})")

    def generate(self, name: str) -> dict:
        """Run one entry, waiting out Replicate's rate limit (429) rather
        than dying mid-chain: a burst of short mask jobs trips it."""
        delay = 30
        for attempt in range(6):
            result = self.agf_run("generate", name)
            message = (result.get("error") or {}).get("message", "") if "error" in result else ""
            if "429" not in message:
                return result
            print(f"  rate limited; waiting {delay}s (attempt {attempt + 1}/6)", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 240)
        return result

    # -------------------------------------------------------------- review
    def review(self, entry: dict) -> bool:
        cid, action = entry["name"].split("-")[0], entry["name"].split("-")[1]
        video = self.drafts / "characters" / cid / f"{action}.mp4"
        loop = bool((self.actions.get(action) or {}).get("loop"))
        cmd = [sys.executable, str(HERE / "review_video.py"), str(video),
               "--trim-end", str(self.video["trim_end"]),
               "--sheet", str(video.with_suffix(".review.png")),
               "--json", str(self.review_path(entry))]
        if loop:
            cmd.append("--loop")
        if self.mask["background"] != "auto":
            cmd += ["--background", self.mask["background"]]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            print(proc.stdout, proc.stderr, file=sys.stderr)
            raise SystemExit("review_video.py produced no JSON")
        for w in report["warnings"]:
            print(f"  warning {entry['name']}: {w}")
        for f in report["failures"]:
            print(f"  FAILED  {entry['name']}: {f}")
        if not report["ok"]:
            print(f"  {entry['name']} is blocked; look at {video.with_suffix('.review.png')} and "
                  f"regenerate with --regenerate {entry['name']}")
        return report["ok"]


def stage_of(entry: dict) -> str:
    return entry["name"].rsplit("-", 1)[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("--character", action="append")
    ap.add_argument("--action", action="append")
    ap.add_argument("--stage", choices=STAGES, default="sheet")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--regenerate", metavar="ENTRY")
    ap.add_argument("--no-review", action="store_true", help="skip the video review gate")
    args = ap.parse_args()

    plan = Plan(args.config)
    if not os.environ.get("REPLICATE_API_TOKEN") and not args.dry_run:
        raise SystemExit("REPLICATE_API_TOKEN is not set")

    wanted = [c for c in plan.characters if not args.character or c["id"] in args.character]
    entries: list[dict] = []
    for c in wanted:
        entries += plan.entries_for(c)
    limit = STAGES.index(args.stage)
    entries = [e for e in entries if STAGES.index(stage_of(e)) <= limit]
    if args.action:
        entries = [e for e in entries if stage_of(e) == "reference" or e["name"].split("-")[1] in args.action]

    if args.regenerate:
        target = next((e for e in entries if e["name"] == args.regenerate), None)
        if target is None:
            raise SystemExit(f"no entry named {args.regenerate!r} in this selection")
        # Everything downstream of it is now stale: delete those drafts so the loop rebuilds them.
        cid, rest = args.regenerate.split("-", 1)
        action = rest.split("-")[0] if "-" in rest else None
        for e in entries:
            same_chain = e["name"].startswith(f"{cid}-") and (
                stage_of(target) == "reference" or e["name"].startswith(f"{cid}-{action}-"))
            if same_chain and STAGES.index(stage_of(e)) > STAGES.index(stage_of(target)):
                path = plan.drafts / e["output"]
                victim = path.parent if "{n" in e["output"] else path
                if victim.exists():
                    shutil.rmtree(victim) if victim.is_dir() else victim.unlink()
                    print(f"  removed stale {victim.relative_to(plan.drafts)}")
        if stage_of(target) == "video":
            plan.review_path(target).unlink(missing_ok=True)
        plan.write_manifest([e for e in entries if plan.ready(e)])
        result = plan.agf_run("regenerate", args.regenerate)
        if "error" in result:
            print(json.dumps(result, indent=1))
            return 1
        print(f"regenerated {args.regenerate}")
        if stage_of(target) == "video" and not args.no_review:
            plan.review(target)
        # fall through into the loop so the chain rebuilds

    while True:
        ready = [e for e in entries if plan.ready(e)]
        plan.write_manifest(ready)
        if args.dry_run:
            print(f"manifest: {len(ready)} of {len(entries)} entries have their inputs")
            return 0
        listing = plan.agf_run("list")
        if "error" in listing:
            print(json.dumps(listing, indent=1))
            return 1
        pending = [e["name"] for e in listing["entries"] if not e["draft_exists"]]
        if not pending:
            blocked = [e["name"] for e in entries if not plan.ready(e)]
            print(f"done: {len(ready)} entries drafted" + (f"; {len(blocked)} not built: {blocked}" if blocked else ""))
            return 0 if not blocked else 1
        for name in pending:
            entry = next(e for e in entries if e["name"] == name)
            print(f"generate {name} ...", flush=True)
            result = plan.generate(name)
            if "error" in result:
                print(json.dumps(result, indent=1))
                return 1
            outs = result.get("output")
            print(f"  {len(outs)} file(s)" if isinstance(outs, list) else f"  {outs}")
            if stage_of(entry) == "video" and not args.no_review:
                plan.review(entry)


if __name__ == "__main__":
    raise SystemExit(main())
