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

A character with a `skill:` block also gets an effect -- a projectile it can
throw -- as two more chains from one more reference image:

  <id>-skill-reference   the effect alone, drawn in the character's style
                         (the character's own reference is the init image)
  <id>-skill-*           a looping clip of the effect animating in place;
                         the app moves it, so the review fails a clip that
                         travels (--strict-motion)
  <id>-burst-*           a one-shot clip of the effect bursting apart and
                         vanishing: its last_image is characters/<id>/blank.png,
                         a flat-background frame this script writes locally,
                         so the clip is pulled to empty (--ends-empty)

`--action skill --stage reference` is the cheap first look at the effects;
`--action skill --action burst --action hurt` generates only new work, since
references are always included.

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
    "effect": {
        "style": ("Clean 2D game effect art. One single solid opaque object, flat cel shading with "
                  "two tones per color and no gradients, thick uniform dark-charcoal outline, chunky "
                  "bold shapes with no thin lines, a vibrant but limited palette. No glow, no "
                  "transparency, no motion blur, no particles, no smoke. Centered in the frame with "
                  "even margins, pointing toward the viewer's right. Solid flat light-gray background "
                  "(#D9D9D9), nothing else in the scene: no character, no figure, no floor, no shadow, "
                  "no text."),
        "match": ("Match the exact art style, line weight, cel shading, outline thickness and colour "
                  "palette of the reference image, but draw only this effect and no character or "
                  "figure at all: "),
        "template": ("2D cartoon game animation of a single magic effect. {motion} It ends in exactly "
                     "the starting pose so the clip loops. The effect stays centered at the same size "
                     "and never travels, drifts or leaves the frame. The camera is completely static "
                     "with no zoom or pan. The flat background stays plain and unchanged. No character "
                     "appears. No text."),
        "burst_template": ("2D cartoon game animation of a magic impact. The {noun} bursts apart on the "
                           "spot into a compact round explosion of solid opaque chunky shards and rings in "
                           "the same colours with thick outlines, which fly a short way outward, shrink "
                           "and vanish completely by the middle of the clip, leaving only the plain flat "
                           "background, completely empty, for the rest of the clip. The whole burst stays "
                           "well inside the frame at all times, within the middle two thirds, with a wide "
                           "empty margin on every side: no shard, ring or spark ever reaches or leaves the "
                           "edge of the frame. No fading, no glow, no smoke, no transparency. The burst "
                           "stays centered. The camera is completely static with no zoom. The flat "
                           "background stays plain and unchanged. No character appears. No text."),
        "burst_fps": 32,
        # The burst starts from the effect shrunk to this fraction of the frame, so
        # it has room to expand without reaching the cell edge; the app draws the
        # burst sheet larger than the projectile to compensate.
        "burst_start": 0.42,
        # Effects get the framework's effect matte: the mask model loses small
        # shards and fills holes between dense ones, so outside the mask body the
        # frame is keyed by colour alone and inside it exact background is dropped.
        "matte": True,
    },
}
RESERVED_ACTIONS = {"skill", "burst", "reference"}   # taken by the <id>-<action>-<stage> naming


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
        self.effect = merged("effect", cfg)
        self.actions = cfg["actions"]
        taken = RESERVED_ACTIONS & set(self.actions)
        if taken:
            raise SystemExit(f"action names {sorted(taken)} are reserved by the skill chains")
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
        v = self.video
        for action, spec in self.actions.items():
            spec = spec or {}
            motion = spec.get("motion") or v["one_shot"].format(motion=c[action])
            out += self.chain(cid, action, ref, v["template"].format(motion=motion))
        skill = c.get("skill")
        if skill:
            k = self.effect
            sref = f"characters/{cid}/skill_reference.png"
            out.append({"name": f"{cid}-skill-reference", "type": "image", "model": r["model"],
                        "prompt_key": r["prompt_key"],
                        "prompt": f"{k['style']} {k['match']}{skill['look']}",
                        "inputs": dict(r["inputs"]),
                        "input_files": {"init_images": [f"drafts:{ref}"]},
                        "output": sref, "format": "png"})
            out += self.chain(cid, "skill", sref, k["template"].format(motion=skill["motion"]),
                              effect=k["matte"])
            noun = skill.get("noun") or skill["name"].lower()
            burst = skill.get("burst") or k["burst_template"].format(noun=noun)
            out += self.chain(cid, "burst", self.small_path(cid), burst,
                              last_image=self.blank_path(cid), effect=k["matte"])
        return out

    def chain(self, cid: str, action: str, ref: str, prompt: str, last_image: str | None = None,
              effect: bool = False) -> list[dict]:
        """The four framework entries that turn one reference image into one
        sheet: video (conditioned on `ref` first and `last_image` last, which
        defaults to `ref` so the clip returns to its pose), mask, frames, sheet."""
        v, m, s = self.video, self.mask, self.sheet
        video = f"characters/{cid}/{action}.mp4"
        mask = f"characters/{cid}/{action}_mask.mp4"
        frames_dir = f"characters/{cid}/{action}_frames"
        matte = {"mask": f"drafts:{mask}", "background": m["background"], "grow": m["grow"],
                 "threshold": m["threshold"], "feather": m["feather"]}
        if effect:
            matte["effect"] = True
        return [
            {"name": f"{cid}-{action}-video", "type": "video", "model": v["model"],
             "prompt": prompt,
             "inputs": {"num_frames": v["frames"], "frames_per_second": v["fps"], **v["inputs"]},
             "input_files": {"image": f"drafts:{ref}", "last_image": f"drafts:{last_image or ref}"},
             "output": video, "format": "mp4"},
            {"name": f"{cid}-{action}-mask", "type": "video", "model": m["model"],
             "inputs": dict(m["inputs"]), "input_files": {"video": f"drafts:{video}"},
             "output": mask, "format": "mp4"},
            {"name": f"{cid}-{action}-frames", "type": "image", "operation": "extract_frames",
             "source": f"drafts:{video}", "frame_count": v["frames"],
             "matte": matte,
             "resize": [s["frame"], s["frame"]],
             "output": f"{frames_dir}/frame_{{n:02d}}.png", "format": "png"},
            {"name": f"{cid}-{action}-sheet", "type": "sprite_sheet", "operation": "assemble_sheet",
             "frame_count": len(self.kept), "frame_size": [s["frame"], s["frame"]],
             "layout": {"columns": s["columns"], "rows": s["rows"]},
             "frames": [f"drafts:{frames_dir}/frame_{n:02d}.png" for n in self.kept],
             "output": f"characters/{cid}/{action}.png", "format": "png"},
        ]

    # ------------------------------------------------------------ per-action
    def loop_of(self, action: str) -> bool:
        if action in ("skill", "burst"):
            return action == "skill"
        return bool((self.actions.get(action) or {}).get("loop"))

    def fps_of(self, action: str, c: dict | None = None) -> int:
        """Playback fps written to the catalog; the video is always made at video.fps."""
        if action == "burst":
            return int(((c or {}).get("skill") or {}).get("burst_fps") or self.effect["burst_fps"])
        return int((self.actions.get(action) or {}).get("fps") or self.video["fps"])

    def review_flags(self, action: str) -> list[str]:
        if action == "skill":
            return ["--loop", "--strict-motion"]
        if action == "burst":
            return ["--ends-empty", "--contained"]
        return ["--loop"] if self.loop_of(action) else []

    @staticmethod
    def blank_path(cid: str) -> str:
        return f"characters/{cid}/blank.png"

    @staticmethod
    def small_path(cid: str) -> str:
        return f"characters/{cid}/skill_small.png"

    def ensure_blanks(self) -> None:
        """Two locally made images a burst needs, written beside the skill
        reference the moment it lands (the framework only accepts references
        that exist on disk). `blank.png` is a flat frame in the reference's
        background colour: conditioning the burst's last frame on it pulls the
        clip to empty. `skill_small.png` is the reference shrunk to less than half
        size on that background: a burst that starts from the full-size effect
        expands past the frame edge, and a cell cuts it off there."""
        from PIL import Image
        for c in self.characters:
            if not c.get("skill"):
                continue
            ref = self.drafts / "characters" / c["id"] / "skill_reference.png"
            blank = self.drafts / self.blank_path(c["id"])
            small = self.drafts / self.small_path(c["id"])
            if not ref.exists() or (blank.exists() and small.exists()):
                continue
            with Image.open(ref) as im:
                rgb = im.convert("RGB")
                w, h = rgb.size
                m = max(4, min(w, h) // 25)
                px = [rgb.getpixel((x, y)) for box in ((0, 0), (w - m, 0), (0, h - m), (w - m, h - m))
                      for x in range(box[0], box[0] + m) for y in range(box[1], box[1] + m)]
                colour = tuple(sorted(ch[i] for ch in px)[len(px) // 2] for i in range(3))
                if not blank.exists():
                    Image.new("RGB", (w, h), colour).save(blank)
                    print(f"  wrote {blank.relative_to(self.drafts)} ({'#%02x%02x%02x' % colour})")
                if not small.exists():
                    scale = self.effect["burst_start"]
                    shrunk = rgb.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
                    # Flatten the shrunk image's own background to the exact canvas colour,
                    # or the paste leaves a faint square seam the video model may keep.
                    data = shrunk.load()
                    for y in range(shrunk.height):
                        for x in range(shrunk.width):
                            r, g, b = data[x, y]
                            if abs(r - colour[0]) + abs(g - colour[1]) + abs(b - colour[2]) <= 45:
                                data[x, y] = colour
                    canvas = Image.new("RGB", (w, h), colour)
                    canvas.paste(shrunk, ((w - shrunk.width) // 2, (h - shrunk.height) // 2))
                    canvas.save(small)
                    print(f"  wrote {small.relative_to(self.drafts)} (x{scale})")

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
        cmd = [sys.executable, str(HERE / "review_video.py"), str(video),
               "--trim-end", str(self.video["trim_end"]),
               "--sheet", str(video.with_suffix(".review.png")),
               "--json", str(self.review_path(entry)), *self.review_flags(action)]
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

    # ---------------------------------------------------------- regenerate
    def downstream_of(self, target: dict, entries: list[dict]) -> list[dict]:
        """Every entry that was built from `target`, so its draft is stale once
        the target is redone. A character's reference feeds everything of theirs;
        a skill reference feeds the skill and burst chains; any other entry feeds
        the later stages of its own action."""
        cid, rest = target["name"].split("-", 1)
        mine = [e for e in entries if e["name"].startswith(f"{cid}-") and e is not target]
        if rest == "reference":
            return mine
        if rest == "skill-reference":
            return [e for e in mine if e["name"].split("-")[1] in ("skill", "burst")]
        action, stage = rest.rsplit("-", 1)
        return [e for e in mine if e["name"].startswith(f"{cid}-{action}-")
                and STAGES.index(stage_of(e)) > STAGES.index(stage)]

    def remove_stale(self, target: dict, entries: list[dict]) -> None:
        for e in self.downstream_of(target, entries):
            path = self.drafts / e["output"]
            victim = path.parent if "{n" in e["output"] else path
            if victim.exists():
                shutil.rmtree(victim) if victim.is_dir() else victim.unlink()
                print(f"  removed stale {victim.relative_to(self.drafts)}")
            if stage_of(e) == "video":
                self.review_path(e).unlink(missing_ok=True)
        if stage_of(target) == "video":
            self.review_path(target).unlink(missing_ok=True)
        if target["name"].endswith("-reference"):
            cid = target["name"].split("-")[0]
            for derived in (self.blank_path(cid), self.small_path(cid)):
                path = self.drafts / derived
                if path.exists():
                    path.unlink()
                    print(f"  removed stale {path.relative_to(self.drafts)}")


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
        plan.remove_stale(target, entries)
        plan.ensure_blanks()
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
        plan.ensure_blanks()
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
