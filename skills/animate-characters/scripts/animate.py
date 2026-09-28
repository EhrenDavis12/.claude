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
review -> upscale -> mask -> frames -> sheet. Every generated step is a framework
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
video is regenerated. It runs on the raw video, before the upscale, so a bad
roll costs nothing more than itself.

The upscale is what makes the outline clean. The video model draws at 720p
(a square clip comes back under 1000px) through a lossy codec, so an outline
read straight from it is soft, and a 256px cell of it is soft again once a
game scales it up. An anime-tuned super-resolution pass (Real-ESRGAN
anime6B, one call per clip) redraws the clip at 1920px with hard edges; the
mask and the matte then run at that size and the fit to the cell is a
downscale, so the edge on the sheet is antialiased line art rather than
codec blur. `upscale: {enabled: false}` in the config restores the cheap
path. Warnings are printed and do not block; look at the
contact sheet written beside the video.

Run with the framework venv's python, from the directory holding the
config, which is also where assetgen.yaml lives. Needs REPLICATE_API_TOKEN.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
STAGES = ["reference", "video", "upscale", "interpolate", "mask", "frames", "sheet"]

DEFAULTS = {
    # The flat colour every reference and clip is drawn on, and the words the
    # prompts use for it. Every `{background}` in a style, look or effect string
    # becomes "<words> background (<hex>)". Chroma green, because the key and the
    # mask both need distance from every colour a character wears: silver armour
    # sits ~50 from a light grey, below the key's threshold, so any silver the
    # mask missed was lost and its edge flickered; from green it sits ~300.
    "background": {"hex": "#00FF00", "words": "bright chroma-key green"},
    "reference": {
        "model": "sourceful/riverflow-2.0-pro",
        "prompt_key": "instruction",
        "inputs": {"aspect_ratio": "1:1", "resolution": "1K", "transparency": False,
                   "output_format": "png", "enhance_prompt": False},
        # Flood-fill tolerance (sum of per-channel differences) for flattening the
        # background: a soft ground shadow sits ~90 from the background, the
        # outline ~600 and its darkest core ~200, so 300 takes the shadow and stops at the outline.
        "flatten_tolerance": 300,
        "match": ("Match the exact art style, line weight, shading and proportions of the "
                  "reference image, but draw a different character: "),
    },
    "video": {
        "model": "wan-video/wan-2.2-i2v-fast",
        # Every frame is kept and played at the rate it was made, so motion runs
        # at real speed; `hold` is how many settled frames a one-shot action keeps
        # after its last moving one (see review_video.py --settle).
        # `frames`/`fps` describe the model's output for planning before a clip
        # exists; once it lands the review measures the real count and rate and
        # those win. `keys` names the model's inputs for the first and last frame,
        # and `frame_inputs` says whether it takes num_frames/frames_per_second.
        # A loop that was not pinned to its first frame is closed in the sheet:
        # the best-matching late/early frame pair bounds the loop and
        # `loop_blend` frames are crossfaded across the join.
        "frames": 81, "fps": 16, "trim_end": 6, "keep_every": 1, "hold": 4, "loop_blend": 10,
        "keys": {"image": "image", "last_image": "last_image"}, "frame_inputs": True,
        "inputs": {"resolution": "720p", "go_fast": True, "interpolate_output": False},
        "template": ("2D cartoon game animation. {motion} The face stays calm and steady with "
                     "the mouth closed and the eyes open, never talking. The camera is completely "
                     "static with no zoom or pan. The character stays centered and the same size. "
                     "The flat background stays plain and unchanged. No text."),
        "one_shot": "The character briskly {motion}, then returns to exactly the starting pose and holds it.",
    },
    "interpolate": {
        # When the review finds the clip holds each drawn frame for several
        # output frames, the moving frames are written to `<action>_unique.mp4`
        # locally, *that* small clip is upscaled, and FILM fills in between the
        # upscaled frames; `steps` 2 gives four frames per drawn one, so an
        # 8 fps drawing rate plays back at 32 fps. The upscaler dies on a long
        # clip (161 frames at 1440px, every time), so it must run on the short
        # one; FILM copes with 2560px frames, slowly. Clips with no held frames
        # skip this stage.
        "enabled": True,
        "model": "zsxkib/film-frame-interpolation-for-large-motion:222d67420da179935a68afff47093bab48705fe9e09c3c79268c1eb2ee7c5e91",
        "steps": 2,
    },
    "upscale": {
        # Anime-tuned super-resolution of the whole clip, keeping its frame
        # count and rate. A square clip comes back square at the setting's
        # height ("2k" -> 2560px); "FHD" fails outright on a 960px square
        # input (six of six), so it is not the default. Runs after the
        # review so a failed roll is never upscaled.
        "enabled": True,
        "model": "lucataco/real-esrgan-video:3e56ce4b57863bd03048b42bc09bdd4db20d427cca5fde9d8ae4dc60e1bb4775",
        "inputs": {"model": "RealESRGAN_x4plus_anime_6B", "resolution": "2k"},
    },
    "mask": {
        "model": "sprited/birefnet-video:d4fd02a2eaddddfd6fbe77570e7408b3f15ee4dcf2ded407ace7a0f9d114ae87",
        "inputs": {"variant": "toonout", "output_format": "mask", "video_output_type": "mp4",
                   "video_quality": "maximum"},
        # `grow` is in pixels of the matted video: 3 was tuned at 624px, and the
        # matte now runs on the 2560px upscale, where the same outline is four
        # times as thick. Bring it back to 3 with `upscale: {enabled: false}`.
        # `erode` shrinks the mask body by that many pixels before the colour
        # key decides the edge: the model's body edge lands a pixel or two
        # outside the outline, in the background blend, and those pixels at
        # full alpha average into a pale rim once the frame is downscaled.
        "grow": 12, "erode": 3, "threshold": 60, "feather": 0, "background": "auto",
    },
    # Cells are `frame` px square; the grid is computed per sheet from its frame
    # count (as square as possible), since actions no longer share one length.
    "sheet": {"frame": 512},
    "effect": {
        "style": ("Clean 2D game effect art. One single solid opaque object, flat cel shading with "
                  "two tones per color and no gradients, thick uniform dark-charcoal outline, chunky "
                  "bold shapes with no thin lines, a vibrant but limited palette. No glow, no "
                  "transparency, no motion blur, no particles, no smoke. Centered in the frame with "
                  "even margins, pointing toward the viewer's right. Solid flat {background}, nothing "
                  "else in the scene: no character, no figure, no floor, no shadow, no text."),
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
        bg = merged("background", cfg)
        self.background = f"{bg['words']} background ({bg['hex']})"
        self.agf = (self.root / cfg.get("agf", "../Asset-Gen-Framework/.venv/bin/agf")).resolve()
        agf_cfg = yaml.safe_load((self.root / "assetgen.yaml").read_text())
        self.drafts = (self.root / agf_cfg["drafts"]).resolve()
        self.style = self.fill(cfg["style"].strip())
        self.reference = merged("reference", cfg)
        self.video = merged("video", cfg)
        self.interpolate = merged("interpolate", cfg)
        self.upscale = merged("upscale", cfg)
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

    def fill(self, text: str) -> str:
        """Substitute `{background}` in a prompt string."""
        return text.replace("{background}", self.background)

    # ---------------------------------------------------------------- entries
    def entries_for(self, c: dict) -> list[dict]:
        cid = c["id"]
        ref = f"characters/{cid}/reference.png"
        r = self.reference
        prompt = f"{self.style} The character: {self.fill(c['look'])}"
        entry = {"name": f"{cid}-reference", "type": "image", "model": r["model"],
                 "prompt_key": r["prompt_key"], "prompt": prompt, "inputs": dict(r["inputs"]),
                 "output": ref, "format": "png"}
        if cid != self.style_anchor:
            entry["prompt"] = f"{self.style} {r['match']}{self.fill(c['look'])}"
            entry["input_files"] = {"init_images": [f"drafts:characters/{self.style_anchor}/reference.png"]}
        out = [entry]
        v = self.video
        for action, spec in self.actions.items():
            spec = spec or {}
            motion = spec.get("motion") or v["one_shot"].format(motion=c[action])
            # `end_frame: false` on an action drops the last-frame conditioning:
            # a clip pinned to end exactly where it started can come back nearly
            # still, and a loop can close on its own well enough for a sheet.
            out += self.chain(cid, action, ref, v["template"].format(motion=motion),
                              end_frame=spec.get("end_frame", True))
        skill = c.get("skill")
        if skill:
            k = self.effect
            sref = f"characters/{cid}/skill_reference.png"
            out.append({"name": f"{cid}-skill-reference", "type": "image", "model": r["model"],
                        "prompt_key": r["prompt_key"],
                        "prompt": f"{self.fill(k['style'])} {k['match']}{self.fill(skill['look'])}",
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
              effect: bool = False, end_frame: bool = True) -> list[dict]:
        """The framework entries that turn one reference image into one sheet:
        video (conditioned on `ref` first and `last_image` last, which defaults
        to `ref` so the clip returns to its pose), upscale (unless disabled),
        mask, frames, sheet. The mask and the frames read the upscaled clip."""
        v, u, m, s = self.video, self.upscale, self.mask, self.sheet
        video = f"characters/{cid}/{action}.mp4"
        hd = f"characters/{cid}/{action}_hd.mp4"
        mask = f"characters/{cid}/{action}_mask.mp4"
        frames_dir = f"characters/{cid}/{action}_frames"
        matte = {"mask": f"drafts:{mask}", "background": m["background"], "grow": m["grow"],
                 "erode": m["erode"], "threshold": m["threshold"], "feather": m["feather"]}
        if effect:
            matte["effect"] = True
        inputs = dict(v["inputs"])
        if v["frame_inputs"]:
            inputs = {"num_frames": v["frames"], "frames_per_second": v["fps"], **inputs}
        entries = [
            {"name": f"{cid}-{action}-video", "type": "video", "model": v["model"],
             "prompt": prompt, "inputs": inputs,
             "input_files": {v["keys"]["image"]: f"drafts:{ref}",
                             **({v["keys"]["last_image"]: f"drafts:{last_image or ref}"} if end_frame else {})},
             "output": video, "format": "mp4"},
        ]
        review = self.review_of(cid, action)
        period = int(review.get("hold_period") or 1)
        held = self.interpolate["enabled"] and period > 1
        unique = f"characters/{cid}/{action}_unique.mp4"
        source = unique if held else video
        if u["enabled"]:
            # The upscaler fails on a clip handed to it as a Replicate file
            # URL and succeeds on the same clip inlined (twelve of twelve vs
            # four of four), so this entry sends its input as a data URI.
            entries.append({"name": f"{cid}-{action}-upscale", "type": "video", "model": u["model"],
                            "inputs": dict(u["inputs"]), "input_files": {"video_path": f"drafts:{source}"},
                            "inline_inputs": True, "output": hd, "format": "mp4"})
            source = hd
        if held:
            smooth = f"characters/{cid}/{action}_smooth.mp4"
            factor = 2 ** int(self.interpolate["steps"])
            entries.append({"name": f"{cid}-{action}-interpolate", "type": "video",
                            "model": self.interpolate["model"],
                            "inputs": {"num_interpolation_steps": int(self.interpolate["steps"]),
                                       "playback_frames_per_second": int(round(float(review["fps"]) / period * factor))},
                            "input_files": {"mp4": f"drafts:{source}"}, "inline_inputs": True,
                            "output": smooth, "format": "mp4"})
            source = smooth
        # The mask model infers at 1024px whatever it is given, and an
        # interpolated 2560px clip is over Replicate's upload limit, so the
        # mask reads a local 1024px copy of the cut clip (`_maskin.mp4`).
        maskin = f"characters/{cid}/{action}_maskin.mp4"
        return entries + [
            {"name": f"{cid}-{action}-mask", "type": "video", "model": m["model"],
             "inputs": dict(m["inputs"]), "input_files": {"video": f"drafts:{maskin}"},
             "output": mask, "format": "mp4"},
            {"name": f"{cid}-{action}-frames", "type": "image", "operation": "extract_frames",
             "source": f"drafts:{source}", "frame_count": self.clip_frames(cid, action),
             "matte": matte,
             "resize": [s["frame"], s["frame"]],
             "output": f"{frames_dir}/frame_{{n:02d}}.png", "format": "png"},
            self.sheet_entry(cid, action),
        ]

    @staticmethod
    def layout_for(count: int) -> dict:
        columns = max(1, math.ceil(math.sqrt(count)))
        return {"columns": columns, "rows": max(1, math.ceil(count / columns))}

    def kept_for(self, cid: str, action: str) -> list[int]:
        """The frames this action's sheet keeps. Every kept frame, except that a
        one-shot action stops `video.hold` frames after the last one that still
        moves (the review's `settled_frame`), so the return-to-pose hold does not
        pad the sheet. Loops and bursts keep everything."""
        v = self.video
        kept = list(range(1, self.clip_frames(cid, action) - v["trim_end"] + 1, v["keep_every"]))
        if self.loop_of(action) or action == "burst":
            return kept
        review = self.drafts / "characters" / cid / f"{action}.review.json"
        if not review.exists():
            return kept
        settled = json.loads(review.read_text()).get("settled_frame")
        if not settled:
            return kept
        # settled_frame is measured on the raw clip; scale it to the clip being cut.
        raw_frames = int(json.loads(review.read_text()).get("frames") or 1)
        settled = int(round(settled * self.clip_frames(cid, action) / raw_frames))
        end = settled + int(self.video["hold"])
        return [n for n in kept if n <= end] or kept

    def close_loop(self, cid: str, action: str, kept: list[int]) -> list[str] | None:
        """For a loop whose clip was not pinned to end on its first frame: find
        the frame pair (j early, i late) that matches best, keep j..i, and
        crossfade the first `loop_blend` frames of that window from the frames
        that follow i, so the join carries no cut. Returns the frame file names
        in order, or None while the frames are not all there. The choice is
        written to `<action>.loop.json` beside the frames."""
        from PIL import Image
        import numpy as np
        blend = int(self.video["loop_blend"])
        frames_dir = self.drafts / "characters" / cid / f"{action}_frames"
        paths = [frames_dir / f"frame_{n:02d}.png" for n in kept]
        if blend <= 0 or not all(p.exists() for p in paths):
            return None
        loop_json = self.drafts / "characters" / cid / f"{action}.loop.json"
        if loop_json.exists():
            chosen = json.loads(loop_json.read_text())
            if chosen.get("kept") == kept and all((frames_dir / n).exists() for n in chosen["names"]):
                return chosen["names"]
        small = [np.array(Image.open(p).convert("RGBA").resize((128, 128), Image.BOX)).astype(float) for p in paths]
        def diff(a, b):
            pa, pb = a[:, :, :3] * a[:, :, 3:] / 255, b[:, :, :3] * b[:, :, 3:] / 255
            return float(np.abs(pa - pb).mean() + np.abs(a[:, :, 3] - b[:, :, 3]).mean())
        n = len(small)
        best = None
        for j in range(0, max(1, n // 4)):
            for i in range(j + int(n * 0.7), n - 1 - blend):
                d = diff(small[i], small[j])
                if best is None or d < best[0]:
                    best = (d, j, i)
        if best is None:
            return None
        seam_before, j, i = best
        names = []
        for t in range(blend):
            w = (t + 1) / (blend + 1)
            a = np.array(Image.open(paths[i + 1 + t]).convert("RGBA")).astype(float)
            b = np.array(Image.open(paths[j + t]).convert("RGBA")).astype(float)
            pa, pb = a[:, :, :3] * a[:, :, 3:] / 255, b[:, :, :3] * b[:, :, 3:] / 255
            alpha = (1 - w) * a[:, :, 3:] + w * b[:, :, 3:]
            prem = (1 - w) * pa + w * pb
            rgb = np.where(alpha > 0, prem * 255 / np.maximum(alpha, 1e-3), 0)
            out = np.dstack([np.clip(rgb, 0, 255), np.clip(alpha, 0, 255)]).astype(np.uint8)
            name = f"loop_{t:02d}.png"
            Image.fromarray(out, "RGBA").save(frames_dir / name)
            names.append(name)
        names += [paths[k].name for k in range(j + blend, i + 1)]
        typical = float(np.mean([diff(small[k], small[k + 1]) for k in range(n - 1)]))
        loop_json.write_text(json.dumps({"kept": kept, "start": j, "end": i, "blend": blend,
                                         "seam_before": round(seam_before, 2), "typical_step": round(typical, 2),
                                         "names": names}) + "\n")
        print(f"  closed {action} loop: frames {j}..{i} of {n}, {blend}-frame crossfade "
              f"(seam {seam_before:.1f} vs typical step {typical:.1f})")
        return names

    def sheet_entry(self, cid: str, action: str) -> dict:
        s = self.sheet
        kept = self.kept_for(cid, action)
        frames_dir = f"characters/{cid}/{action}_frames"
        names = [f"frame_{n:02d}.png" for n in kept]
        if self.loop_of(action):
            names = self.close_loop(cid, action, kept) or names
        return {"name": f"{cid}-{action}-sheet", "type": "sprite_sheet", "operation": "assemble_sheet",
                "frame_count": len(names), "frame_size": [s["frame"], s["frame"]],
                "layout": self.layout_for(len(names)),
                "frames": [f"drafts:{frames_dir}/{name}" for name in names],
                "output": f"characters/{cid}/{action}.png", "format": "png"}

    def refresh_sheets(self, entries: list[dict]) -> None:
        """Frames and sheet entries depend on the review (the clip's real frame
        count and rate, a one-shot's settled frame), which lands after the
        entries were first built: rebuild them before each manifest write, and
        record each sheet's shape beside it for approve.py."""
        for i, e in enumerate(entries):
            if stage_of(e) == "frames":
                cid, action = e["name"].split("-")[0], e["name"].split("-")[1]
                e["frame_count"] = self.clip_frames(cid, action)
                continue
            if stage_of(e) != "sheet":
                continue
            cid, action = e["name"].split("-")[0], e["name"].split("-")[1]
            entries[i] = e = self.sheet_entry(cid, action)
            c = next(ch for ch in self.characters if ch["id"] == cid)
            shape = {"frames": e["frame_count"], **e["layout"], "frame": self.sheet["frame"],
                     "fps": self.fps_of(action, c), "loop": self.loop_of(action)}
            side = self.drafts / "characters" / cid / f"{action}.sheet.json"
            side.parent.mkdir(parents=True, exist_ok=True)
            if not side.exists() or json.loads(side.read_text()) != shape:
                side.write_text(json.dumps(shape) + "\n")

    # ------------------------------------------------------------ per-action
    def loop_of(self, action: str) -> bool:
        if action in ("skill", "burst"):
            return action == "skill"
        return bool((self.actions.get(action) or {}).get("loop"))

    def review_of(self, cid: str, action: str) -> dict:
        path = self.drafts / "characters" / cid / f"{action}.review.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def cut_clip(self, cid: str, action: str) -> Path | None:
        """The clip the frames are cut from: the interpolated one when it
        exists, else the raw one, else nothing yet."""
        for name in (f"{action}_smooth.mp4", f"{action}_hd.mp4", f"{action}.mp4"):
            path = self.drafts / "characters" / cid / name
            if path.exists():
                return path
        return None

    def probe(self, path: Path) -> tuple[int, float]:
        import av
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            rate = float(stream.average_rate) if stream.average_rate else float(self.video["fps"])
            # Count by decoding: the container's frame count is metadata and an
            # interpolated clip's was off by two, which fails the framework's check.
            count = sum(1 for _ in container.decode(stream))
        return int(count), rate

    def clip_frames(self, cid: str, action: str) -> int:
        """How many frames the clip the sheet is cut from really has."""
        path = self.cut_clip(cid, action)
        return self.probe(path)[0] if path else int(self.video["frames"])

    def clip_fps(self, cid: str, action: str) -> float:
        path = self.cut_clip(cid, action)
        return self.probe(path)[1] if path else float(self.video["fps"])

    def ensure_mask_inputs(self) -> None:
        """Write `<action>_maskin.mp4`, a 1024px copy of the clip the frames
        are cut from, for the mask model to read; same frame count."""
        import av
        for c in self.characters:
            cid = c["id"]
            for action in [*self.actions, *(("skill", "burst") if c.get("skill") else ())]:
                cut = self.cut_clip(cid, action)
                maskin = self.drafts / "characters" / cid / f"{action}_maskin.mp4"
                if cut is None or maskin.exists():
                    continue
                # Only the final cut clip may feed the mask: wait until the chain
                # has produced it (the raw clip alone means upscale/interpolate are pending).
                if cut.name == f"{action}.mp4" and self.upscale["enabled"]:
                    continue
                if cut.name == f"{action}_hd.mp4" and int(self.review_of(cid, action).get("hold_period") or 1) > 1 and self.interpolate["enabled"]:
                    continue
                with av.open(str(cut)) as src, av.open(str(maskin), "w") as dst:
                    stream = src.streams.video[0]
                    rate = stream.average_rate or 16
                    out = dst.add_stream("libx264", rate=rate)
                    out.width = out.height = 1024
                    out.pix_fmt = "yuv420p"
                    out.options = {"crf": "18", "preset": "medium"}
                    n = 0
                    for frame in src.decode(stream):
                        img = av.VideoFrame.from_image(frame.to_image().resize((1024, 1024)))
                        img.pts = n; n += 1
                        for packet in out.encode(img):
                            dst.mux(packet)
                    for packet in out.encode():
                        dst.mux(packet)
                print(f"  wrote {maskin.relative_to(self.drafts)}: {n} frames at 1024px for the mask")

    def ensure_unique_clips(self) -> None:
        """Write `<action>_unique.mp4` — only the moving frames, at the drawing
        rate — for every reviewed clip that holds frames, as FILM's input."""
        import av
        for c in self.characters:
            cid = c["id"]
            for action in [*self.actions, *(("skill", "burst") if c.get("skill") else ())]:
                review = self.review_of(cid, action)
                period = int(review.get("hold_period") or 1)
                raw = self.drafts / "characters" / cid / f"{action}.mp4"
                unique = self.drafts / "characters" / cid / f"{action}_unique.mp4"
                if period <= 1 or not raw.exists() or unique.exists() or not review.get("ok"):
                    continue
                phase = int(review.get("moving_phase") or 0)
                rate = max(1, int(round(float(review["fps"]) / period)))
                with av.open(str(raw)) as src, av.open(str(unique), "w") as dst:
                    out = dst.add_stream("libx264", rate=rate)
                    first = next(iter(src.decode(video=0)))
                    out.width, out.height, out.pix_fmt = first.width, first.height, "yuv420p"
                    out.options = {"crf": "12", "preset": "medium"}
                    src.seek(0)
                    n = 0
                    for i, frame in enumerate(src.decode(video=0)):
                        if i % period != phase:
                            continue
                        img = av.VideoFrame.from_image(frame.to_image()); img.pts = n; n += 1
                        for packet in out.encode(img):
                            dst.mux(packet)
                    for packet in out.encode():
                        dst.mux(packet)
                print(f"  wrote {unique.relative_to(self.drafts)}: {n} moving frames at {rate} fps (held x{period})")

    def fps_of(self, action: str, c: dict | None = None) -> int:
        """Playback fps written to the catalog: the clip's own rate, so motion
        plays at the speed it was made, unless the action or a burst says otherwise."""
        if action == "burst":
            return int(((c or {}).get("skill") or {}).get("burst_fps") or self.effect["burst_fps"])
        forced = (self.actions.get(action) or {}).get("fps")
        if forced:
            return int(forced)
        return int(round(self.clip_fps(c["id"], action))) if c else int(self.video["fps"])

    def review_flags(self, action: str) -> list[str]:
        if action == "skill":
            return ["--loop", "--strict-motion"]
        if action == "burst":
            return ["--ends-empty", "--contained"]
        return ["--loop"] if self.loop_of(action) else ["--settle"]

    @staticmethod
    def blank_path(cid: str) -> str:
        return f"characters/{cid}/blank.png"

    @staticmethod
    def small_path(cid: str) -> str:
        return f"characters/{cid}/skill_small.png"

    def flatten_backgrounds(self) -> None:
        """Flatten a reference's background to one exact colour before anything is
        built from it. The image model ignores "no shadow" often enough to matter
        and paints a soft grey ellipse under the feet; the matte would keep it as a
        grey blob, and the video model copies whatever the reference shows. Every
        pixel reachable from the corners within a small colour tolerance is the
        background — a shadow is contiguous with it, the character is sealed off by
        its outline — and is set to the corner colour. Idempotent: a `.flat` marker
        beside the image records that it has been done."""
        from PIL import Image, ImageDraw
        for c in self.characters:
            for name in ("reference.png", "skill_reference.png"):
                path = self.drafts / "characters" / c["id"] / name
                marker = path.with_suffix(".flat")
                if not path.exists() or marker.exists():
                    continue
                with Image.open(path) as im:
                    rgb = im.convert("RGB")
                w, h = rgb.size
                m = max(4, min(w, h) // 25)
                px = [rgb.getpixel((x, y)) for box in ((0, 0), (w - m, 0), (0, h - m), (w - m, h - m))
                      for x in range(box[0], box[0] + m) for y in range(box[1], box[1] + m)]
                colour = tuple(sorted(ch[i] for ch in px)[len(px) // 2] for i in range(3))
                before = sum(1 for v in rgb.getdata() if v != colour)
                # Pillow's floodfill returns at once when the fill colour is within
                # `thresh` of the seed's colour, so fill a copy with a sentinel far
                # from any light background, then set every pixel it reached.
                sentinel = (0, 255, 0)
                marked = rgb.copy()
                for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
                    ImageDraw.floodfill(marked, seed, sentinel, thresh=self.reference["flatten_tolerance"])
                rgb.putdata([colour if m == sentinel and v != sentinel else v
                             for v, m in zip(rgb.getdata(), marked.getdata())])
                after = sum(1 for v in rgb.getdata() if v != colour)
                rgb.save(path)
                marker.write_text("#%02x%02x%02x\n" % colour)
                print(f"  flattened {path.relative_to(self.drafts)}: {before - after} background px "
                      f"set to #{colour[0]:02x}{colour[1]:02x}{colour[2]:02x}")

    def archive(self, cid: str, action: str, stage: str) -> None:
        """Keep every roll. With `archive:` set in the config (a directory,
        relative to the config), a clip that lands is copied into
        `<archive>/<cid>/<action>/roll-NN/` with its review, and the sheet joins
        the same folder when it lands, so the evolution of an animation stays
        visible after the drafts are overwritten."""
        root = self.cfg.get("archive")
        if not root:
            return
        src = self.drafts / "characters" / cid
        dest_root = (self.root / root).resolve() / cid / action
        dest_root.mkdir(parents=True, exist_ok=True)
        rolls = sorted(d for d in dest_root.iterdir() if d.is_dir() and d.name.startswith("roll-"))
        numbers = [int(d.name.split("-")[1]) for d in rolls if d.name.split("-")[1].isdigit()]
        if stage == "video":
            # Folders may be renamed with a suffix by hand (roll-03-notes); number past the highest.
            dest = dest_root / f"roll-{max(numbers, default=0) + 1:02d}"
            dest.mkdir()
            names = [f"{action}.mp4", f"{action}.review.png", f"{action}.review.json"]
        else:
            if not rolls:
                return
            dest = rolls[-1]
            names = [f"{action}.png", f"{action}.sheet.json"]
        for name in names:
            if (src / name).exists():
                shutil.copyfile(src / name, dest / name)
        print(f"  archived {stage} -> {dest.relative_to(self.root.parent)}")

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
        if stage_of(entry) == self.gated_stage:
            review = self.review_path(entry)
            if review.exists() and not json.loads(review.read_text()).get("ok", False):
                return False
        return True

    @property
    def gated_stage(self) -> str:
        """The first paid stage after the video: the review blocks it."""
        return "upscale" if self.upscale["enabled"] else "mask"

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
        """Run one entry, waiting out Replicate's rate limit (429) and its
        transient output-upload failure rather than dying mid-chain: a burst
        of short mask jobs trips the first, and the second is the provider's
        own storage hiccup, which a retry of the same entry clears."""
        delay = 30
        for attempt in range(6):
            result = self.agf_run("generate", name)
            message = (result.get("error") or {}).get("message", "") if "error" in result else ""
            transient = ("429", "error trying to upload output", "Prediction interrupted")
            if not any(t in message for t in transient):
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
        if report.get("settled_frame"):
            print(f"  settled at frame {report['settled_frame']} of {report['kept']}; the sheet keeps "
                  f"{min(report['kept'], report['settled_frame'] + int(self.video['hold']))}")
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
            cid, action = target["name"].split("-")[0], target["name"].split("-")[1]
            for derived in (f"{action}_unique.mp4", f"{action}_smooth.mp4", f"{action}_maskin.mp4", f"{action}.loop.json"):
                (self.drafts / "characters" / cid / derived).unlink(missing_ok=True)
        if target["name"].endswith("-reference"):
            cid = target["name"].split("-")[0]
            (self.drafts / target["output"]).with_suffix(".flat").unlink(missing_ok=True)
            for derived in (self.blank_path(cid), self.small_path(cid)):
                path = self.drafts / derived
                if path.exists():
                    path.unlink()
                    print(f"  removed stale {path.relative_to(self.drafts)}")


def stage_of(entry: dict) -> str:
    return entry["name"].rsplit("-", 1)[1]


def select_entries(plan: "Plan", wanted: list[dict], args) -> list[dict]:
    """The entries this run covers. Rebuilt every loop, because a chain's
    shape depends on what has landed (a reviewed clip that holds frames
    gains an interpolate stage)."""
    entries: list[dict] = []
    for c in wanted:
        entries += plan.entries_for(c)
    limit = STAGES.index(args.stage)
    entries = [e for e in entries if STAGES.index(stage_of(e)) <= limit]
    if args.action:
        entries = [e for e in entries if stage_of(e) == "reference" or e["name"].split("-")[1] in args.action]
    return entries


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
    entries = select_entries(plan, wanted, args)

    if args.regenerate:
        target = next((e for e in entries if e["name"] == args.regenerate), None)
        if target is None:
            raise SystemExit(f"no entry named {args.regenerate!r} in this selection")
        # Everything downstream of it is now stale: delete those drafts so the loop rebuilds them.
        plan.remove_stale(target, entries)
        plan.flatten_backgrounds()
        plan.ensure_blanks()
        plan.refresh_sheets(entries)
        plan.write_manifest([e for e in entries if plan.ready(e)])
        result = plan.agf_run("regenerate", args.regenerate)
        if "error" in result:
            print(json.dumps(result, indent=1))
            return 1
        print(f"regenerated {args.regenerate}")
        if stage_of(target) == "video" and not args.no_review:
            plan.review(target)
        if stage_of(target) == "video":
            cid, action = target["name"].split("-")[0], target["name"].split("-")[1]
            plan.archive(cid, action, "video")
        # fall through into the loop so the chain rebuilds

    while True:
        plan.flatten_backgrounds()
        plan.ensure_blanks()
        plan.ensure_unique_clips()
        plan.ensure_mask_inputs()
        entries = select_entries(plan, wanted, args)
        plan.refresh_sheets(entries)
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
            if stage_of(entry) in ("video", "sheet"):
                cid, action = entry["name"].split("-")[0], entry["name"].split("-")[1]
                plan.archive(cid, action, stage_of(entry))


if __name__ == "__main__":
    raise SystemExit(main())
