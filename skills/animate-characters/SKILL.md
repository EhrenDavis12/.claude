---
name: animate-characters
description: Generate a set of game characters as transparent, style-consistent sprite-sheet animations (idle, attack, defend, any action) through Replicate via the Asset-Gen-Framework, review each video before spending on it, matte it with the outline intact, and approve finished sheets into a Flutter app with a drop-in sprite player. Use when a project wants animated characters generated rather than drawn, when a new character or action is added to one that already has them, or when a generated animation looks wrong and someone asks why.
---

# Animating characters

One config file, one command, and a character comes back as three (or more) transparent
sprite sheets that play smoothly in Flutter and match every other character generated the
same way. This is the pipeline that built the Asset Animation Demo (`src/asset-animation-demo`),
made project-agnostic: everything a project decides lives in its `animate.yaml`; everything
that was learned the hard way lives in the scripts and at the bottom of this file.

The scripts run with the framework's python and need `REPLICATE_API_TOKEN` in the environment:

```
PY=../Asset-Gen-Framework/.venv/bin/python
SK=../../.claude/skills/animate-characters/scripts      # from the app directory
$PY $SK/animate.py animate.yaml                          # generate everything
$PY $SK/approve.py animate.yaml --all                    # copy finished sheets into the app
```

## What a project supplies

Copy `templates/animate.yaml` next to the project's `assetgen.yaml` (the framework config: a
manifest path, a drafts folder, a record file) and fill in:

- **the style bible** — one paragraph that every character prompt starts with. It fixes the
  proportions, the shading, the line weight, the pose, the framing, and a flat single-colour
  background. The background must be flat and light: the matte and the outline restoration
  both depend on it.
- **the characters** — an id, a name, a `look` that finishes the bible's sentence, and one line
  per action saying what that character does.
- **the actions** — `idle` (must `loop: true`) and any one-shot actions. Each becomes a button.

The first character in the list is generated from text alone and becomes the **style anchor**:
every later character is generated with that image as an init image and a prompt that says
"match this style, draw a different character". That one reference is what keeps six
characters looking like one artist. If the first one is not loved, regenerate it before
generating anyone else, or point `style_anchor:` at a better one.

For the Flutter side, copy `templates/sprite_sheet.dart` and `templates/character_catalog.dart`
into the app. The player decodes a sheet once, draws one cell per frame with `drawImageRect`
from a ticker, loops or plays once and calls back. The catalog JSON that `approve.py` writes
is what `loadCatalog()` reads. Each character's asset folder has to be listed in `pubspec.yaml`
by hand (Flutter does not bundle directories recursively); `approve.py` adds the line.

## What the pipeline does, per character

1. **Reference image** — `sourceful/riverflow-2.0-pro`, square, 1K, PNG, flat background baked
   in (not transparent: it is only an input to the video model, and a flat background is what
   the matte removes cleanly).
2. **One video per action** — `wan-video/wan-2.2-i2v-fast`, image-to-video from the reference,
   81 frames at 16 fps (the model's minimum), the same reference passed as the last frame so
   the action returns to its pose and an idle closes into a loop. The prompt asks for a brisk
   action, a static camera, a centred character of unchanging size, an unchanged background.
3. **Review** — `review_video.py` measures the video before anything is spent on it. A failing
   video blocks its chain (a `<action>.review.json` beside it says why) and the run moves on;
   `--regenerate <id>-<action>-video` redoes it. Warnings print and do not block; look at the
   `<action>.review.png` contact sheet.
4. **Mask** — `sprited/birefnet-video` (`toonout` variant, `mask` output) gives a grayscale
   alpha video, tracked across frames so the edge does not flicker.
5. **Frames** — the framework's `extract_frames` with `matte:` and `resize:`. The alpha comes
   from the mask, and the outline the matte shaved off is **restored by colour**: the mask is
   grown three pixels and, in that band, only pixels clearly unlike the flat background are
   kept, with alpha from its colour distance and the background's share subtracted from its
   colour. The body is the model's; the edge is decided by colour, identically on every frame,
   and carries no background. Then a premultiplied fit to the cell size.
6. **Sheet** — the framework's `assemble_sheet`: the kept frames (every second one, the last
   six dropped — see the lessons) in a row-major grid, one PNG.

The framework checks every entry's inputs before doing anything, so `animate.py` writes the
manifest with only the entries whose inputs already exist, generates the pending ones, and
repeats until the chains complete. Rerunning is idempotent: it skips whatever is drafted.

Approval is separate and human: `approve.py` copies sheets into the app and rewrites the
catalog. Nothing reaches the app any other way, and the framework can never write there.

## Skills: a projectile and its burst

A character with a `skill:` block (name, `look`, in-place `motion`, optional `noun` and
`burst`) gets two more sheets, drawn in its own style, so a game can show it attacking
across the screen:

1. **Effect reference** — the same image model, the effect style bible plus the `look`, with
   the *character's own* reference as the init image and a prefix that says "match this
   style, draw only this effect, no character". `--action skill --stage reference` makes
   just these; look at them before spending on video. Six came back right first time.
2. **`skill` video** — a loop, like idle: the effect animates *in place*, centred, pointing
   right. The app supplies the travel, flips it for the other direction and rotates it to
   the flight angle, so the review runs `--loop --strict-motion` and **fails** a clip whose
   effect drifts or changes size instead of warning.
3. **`burst` video** — one-shot, from the same reference: the effect bursts apart into
   solid shards and vanishes. Its `last_image` is `characters/<id>/blank.png`, a flat frame
   in the reference's background colour that `animate.py` writes locally the moment the
   reference lands, so Wan is pulled to an empty frame. The review runs `--ends-empty
   --contained`: no end-flash check (the end *is* a change), it fails if the last kept
   frame still holds foreground or the first holds none, and it fails any frame whose
   foreground touches the border — a cell cuts the burst off there, and the cut reads as
   a square box on screen. The prompt asks for a compact burst within the middle two thirds
   of the frame. The sheet keeps its trailing empty frames; the catalog plays it at
   `effect.burst_fps` (32) so the burst reads as a hit, not a clip.
4. Mask, frames and sheet as for an action, with one difference: the frames step runs the
   framework's **effect matte** (`matte: {effect: true}`, from `effect.matte` in the config).
   A burst is hundreds of small shards and the mask model loses most of them, so outside the
   mask body the frame is keyed by colour alone — a narrow ramp around the threshold, the
   background share un-blended — and inside the body only exact background is dropped (the
   model fills holes between dense shards). Characters never use it: silver armour is too
   close to the grey background to survive a colour key. Drafts: `skill_reference.png`,
   `blank.png`, `skill.*`, `burst.*`; `approve.py` copies `skill.png` and `burst.png` beside
   the action sheets and writes `skill: {name, spin, animation, impact}` into the catalog.

A `hurt` action (the character flinches and returns to pose) is what the target plays when
the burst lands; it is an ordinary action, one motion line per character, and the motion
should say "half a step" and "staying in place" so the character stays in frame.

Every `look` for an effect says solid, opaque, chunky, no glow or transparency: the matte
turns anything see-through into a white blob (see the lessons), so glows belong in code. A
thrown weapon is never asked to spin: give it a subtle in-place motion and `spin: true`, and
the app rotates the sprite in flight (see the lessons).

## Judging the result

Look, do not assert. After approving, build a review strip (frame 0, 5, 10 … of every sheet
composited on green) and read it as an image; then run the app and record a tap through the
playtest skill. What to look for:

- **A pale line outside the outline** is background left in the edge pixels. Check on the
  darkest background the game uses; a light one hides it. The difference key removes it when
  the background is flat and known — if it is back, the background was not flat (check the
  review's corner std) or `mask.threshold` is far from the outline's distance.
- **Outline weight** should be identical from frame to frame. If it breathes, the matte is
  eating it: raise `mask.grow` by one, or lower `mask.threshold` if the outline colour is
  close to the background.
- **A brightness step** in the last frames means `video.trim_end` is too low for that clip.
- **A white blob** where a translucent effect should be (a barrier, a glow) is the matte
  flattening it: a matte cannot carry half-transparency. Put see-through effects in code or in
  their own layer, not in the character's video.
- **Loop closure**: a `loop_gap` warning on an idle means the last kept frame differs from the
  first. Usually harmless at 16 fps; if the loop visibly pops, regenerate that video.

## Cost and size

Per character with three actions: one image call, three video calls, three mask calls, and
local work — a few dollars for six characters, about ten minutes each, run sequentially
(the framework holds one lock per record). A 256px, 7x6 sheet is 1.5–2 MB as PNG; six
characters came to 33 MB of assets.

## Lessons — keep this section current

**This skill improves itself.** When a run teaches a better strategy — a threshold that was
wrong, a model that does a step better, a failure the review did not catch, a prompt phrase
that fixed a recurring defect — update the script or the default that embodies it *and* add a
dated line here saying what changed and what it cost to learn. The next run must start from
the best known way, not rediscover it. Entries are newest first.

- **2026-09-23 — A burst that reaches the frame edge plays as a square.** The first six
  bursts flew their shards past the cell border in most frames; on screen the cut-off
  edge drew a box around every impact. The prompt now keeps the burst within the middle
  two thirds with an empty margin, and the review's `--contained` gate fails any frame
  with foreground in the outer 4% of the frame before a mask is paid for. Cost: six
  videos regenerated.
- **2026-09-23 — A burst needs its own matte.** The character matte trusts the mask body and
  colour-keys a three-pixel band around it. On a burst of hundreds of shards the mask model
  loses most of the small ones (a band cannot reach them), fills the holes between dense
  ones with flat background (which rides along at full alpha), and its shrunken ring makes
  the "fully foreground" measure wrong, so edges un-blend into pale rims. Two dead ends
  first: keying the whole body proportionally dimmed every light colour (a white band, a
  pale centre, steel blades at 22 colour-distance from the grey), and a hard cutoff inside
  the body alone fixed nothing visible. What works is `matte: {effect: true}`: keep the
  body, drop only exact background inside it, and outside it key every pixel by colour with
  a narrow ramp around the threshold. Then the late frames came out fully opaque: `auto`
  background was read per frame from the corners, and shards were in the corners. The
  framework now measures it once from the first frame. Cost: three framework rounds and
  four local rebuilds; no video was regenerated for any of it.
- **2026-09-23 — Do not ask the video model to spin a thrown weapon.** A dagger and an axe
  asked to "spin one full turn" came back turning slowly, off-centre, short of a full turn,
  and the dagger wandered a sixth of the frame. A spin is the one motion code does perfectly:
  the clip now shows a subtle in-place motion, `spin: true` goes into the catalog, and the
  app rotates the sprite in flight. Cost: two videos regenerated.
- **2026-09-23 — "Blades glint" paints a white halo.** Asked for a glint, the axe came back
  with a soft white glow around it, which is a see-through effect the matte cannot carry.
  The motion now says "no glow, no shine and no glint". Cost: one video.
- **2026-09-23 — The review's motion gates were tuned on characters; effects broke them
  three ways.** A burst's shards cross the corners, so the flatness check read them as an
  unflat background: in `--ends-empty` mode it now judges only the first frame and the empty
  tail. A thin arrow doubles its bounding-box *height* by tilting a few degrees, so size is
  now measured on the box's longer side. And a flapping tassel changes size without moving,
  so `--strict-motion` escalates only drift; size stays a warning. Three false blocks, each
  found by looking at the contact sheet before regenerating anything.
- **2026-09-23 — A light rim around the outline means background is still in the edge.**
  Two causes, both in the frames step. Every edge pixel of the video is a blend of outline
  and background, so keeping it at full alpha paints the blend as a pale line; and resizing
  straight RGBA lets the (background-coloured) transparent pixels bleed into their neighbours.
  The matte is now a difference key against the flat background — alpha in the edge band is
  the pixel's colour distance relative to a fully-foreground pixel, and the colour is
  un-blended by subtracting the background's share — transparent pixels are forced to black,
  and the resize is premultiplied. No feather: antialiasing comes from the key and the
  downscale. Seen on the mage's hat on the app's dark background; invisible on a light one,
  so check edges on the darkest background the game has.
- **2026-09-23 — A burst of short jobs trips Replicate's rate limit.** Eighteen mask jobs in
  a row got a 429 on the fourth, which killed the run mid-chain. `animate.py` now waits
  30 s, then 60, 120, 240, and retries the same entry before giving up.
- **2026-09-23 — The last six video frames brighten; drop them.** Wan's first-and-last-frame
  conditioning blends toward the last image over the final frames. Measured on 18 clips: 13
  brightened by +4 to +14 luminance in the last four frames, which played back as a flash
  at the end of every action. `video.trim_end: 6` removes it on every clip; the review's
  `end_flash` check fails a video where it does not. Cost: a full day's sheets rebuilt.
- **2026-09-23 — The matte shaves the outline; restore it by colour.** BiRefNet reads a thick
  charcoal outline against light grey as shadow and cuts one or two pixels into it, differently
  per frame, which reads as a flickering edge. Growing the mask three pixels and keeping only
  non-background-coloured pixels in that band gives a constant outline. This is why the style
  bible insists on a flat, light, single-colour background: the fix needs to know what
  background looks like. Built into the framework as `matte:` on `extract_frames`.
- **2026-09-23 — Review the video before the matte, not the sheet after.** Every defect above
  was found on the finished sheet, after three paid steps. The review now runs on the raw video
  and blocks the chain. Its thresholds were first set too tight (every clip failed: actions
  legitimately move, glows legitimately brighten) and were recalibrated on all 18 clips:
  end-flash and a non-flat background fail; spikes, loop gap, drift and size only warn.
- **2026-09-23 — Community models need a pinned version.** `sprited/birefnet-video` 404s on
  the models endpoint; name it `owner/name:<version>` and the framework routes it correctly.
- **2026-09-23 — Wan will not make fewer than 81 frames.** Ask for 81 and keep every second
  frame; the doubled pace reads as snappy, not as dropped frames.
- **2026-09-23 — The image model wants its references as a list.** `init_images` is an array;
  the framework's `input_files` now accepts a list of references for exactly this.
