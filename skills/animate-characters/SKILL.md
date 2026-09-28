---
name: animate-characters
description: Generate game characters as transparent, style-consistent sprite-sheet animations (idle, attack, defend, hurt, a projectile and its burst) through Replicate via the Asset-Gen-Framework — reference image on a chroma backdrop, Kling image-to-video with a negative prompt, held-frame detection and FILM interpolation, anime upscale, mask and colour-keyed matte, per-action sheets with settle trimming and loop closing — then approve finished sheets into a Flutter app or hand them to Unity. Use when a project wants animated characters generated rather than drawn, when a new character or action is added, when an animation looks wrong (fuzzy edge, halo, flicker, talking face, choppy or bouncing motion, loop pop) and someone asks why, or when a new video model is being tried.
---

# Animating characters

One config file, one command, and a character comes back as transparent sprite sheets that
play at real speed, match every other character generated the same way, and survive a
dark game background without a halo. This is the pipeline that built the Asset Animation
Demo (`src/asset-animation-demo`) and the Unity showcase (`src/unity-side-scroler`), made
project-agnostic: everything a project decides lives in its `animate.yaml`; everything
that was learned the hard way lives in the scripts and at the bottom of this file.

The scripts run with the framework's python and need `REPLICATE_API_TOKEN` in the environment:

```
PY=../Asset-Gen-Framework/.venv/bin/python
SK=../../.claude/skills/animate-characters/scripts      # from the app directory
$PY $SK/animate.py animate.yaml                          # generate everything
$PY $SK/animate.py animate.yaml --character knight --action idle          # one chain
$PY $SK/animate.py animate.yaml --character knight --stage reference      # just the reference
$PY $SK/animate.py animate.yaml --regenerate knight-idle-video            # re-roll one clip
$PY $SK/approve.py animate.yaml knight                   # copy finished sheets into the app
```

**Iterate one character, one action at a time.** A roll costs a dollar and four minutes of
video plus a quarter of an hour of upscale, interpolation and matte. Get the reference
right (look at it), then the idle right (measure it, look at it in the engine), then the
one-shots. Every roll is archived (see below), so nothing is lost when the next roll wins.

## What a project supplies

Copy `templates/animate.yaml` next to the project's `assetgen.yaml` (the framework config: a
manifest path, a drafts folder, a record file) and fill in:

- **the style bible** — one paragraph every character prompt starts with. It fixes the
  proportions, shading, line weight, stance, framing and the `{background}` placeholder,
  which `animate.py` fills from `background:` (chroma green by default: the matte keys by
  colour distance and silver armour sits only ~50 from a light grey but ~300 from green).
  Say which way the character faces in image terms; models read body-relative left and
  right the wrong way round often enough that the reference is mirrored afterwards when
  needed (a mirror is deterministic; a re-roll is not).
- **the characters** — an id, a name, a `look` that finishes the bible's sentence, and one
  line per one-shot action. The `look` should describe the pose in image terms too ("the
  shield is on the LEFT side of the image, held out in front").
- **the actions** — `idle` (`loop: true`, usually `end_frame: false`, see below) and the
  one-shots. Each becomes a button or an animator state.
- **`archive:`** — a directory where every roll is kept: raw clip, review, finished sheet,
  a `notes.md` you write. The evolution of an animation stays visible after the drafts are
  overwritten. The Unity project keeps its under `Automation_animation_drafts/`.

The first character in the list is the **style anchor**: every later character is generated
with that image as an init image and "match this style, draw a different character".

For the Flutter side, copy `templates/sprite_sheet.dart` and `templates/character_catalog.dart`
into the app; `approve.py` copies sheets, rewrites the catalog and adds the pubspec line.
For Unity, copy the action sheets into `Assets/Characters/<id>/`, put the shape from each
`<action>.sheet.json` into `characters.json`, and run Characters/Import Sheets; the importer
reads pixels-per-unit and the grid per sheet, allows 8192px sources, imports sprites with a
tight mesh, and packs the atlas at high quality (BC7 / ASTC 4x4) — default-quality block
compression greys the outline's antialiasing.

## What the pipeline does, per character

1. **Reference image** — `sourceful/riverflow-2.0-pro`, square, 1K, PNG, the flat backdrop
   baked in. The moment it lands, its background is flattened: every pixel reachable from
   the corners within `reference.flatten_tolerance` becomes the exact corner colour, which
   removes the ground shadow the model paints regardless of the prompt and leaves the
   outlined character untouched (`.flat` marker beside it). Look at it; mirror it if it
   faces the wrong way; re-roll it only if the pose is wrong.
2. **One video per action** — `kwaivgi/kling-v3-video` (pro, 5 s, 1440px square, 24 fps)
   from the reference as the start frame, with a **negative prompt** ("talking, speaking,
   mouth opening, grimace, squinting, bouncing, hopping …"). The video model is configurable
   (`video.model`, `video.keys` naming its first/last-frame inputs, `video.inputs`); Wan 2.2
   fast is the cheap path but has no negative prompt and animates the mouth no matter what.
   The reference is also the **end frame** unless the action says `end_frame: false`: pinned
   to end where it started, Kling barely moves; unpinned it lives, and the sheet closes the
   loop itself (step 8). One-shots keep the pin so they return to pose.
3. **Review** — `review_video.py` measures the raw clip before anything else is spent: a
   brightness step at the end, a background that stops being flat (per channel — a
   saturated colour has a huge spread across channels), the loop gap, drift and size for
   loops, the border for bursts, the **settled frame** of a one-shot (`--settle`), and the
   **hold period** — Kling draws 8 frames a second and repeats each one three times. A
   failing clip blocks its chain (`<action>.review.json` says why); warnings print; the
   `<action>.review.png` contact sheet is what to look at.
4. **Unique frames** — when the review found held frames, `animate.py` writes
   `<action>_unique.mp4`: only the moving frames, at the drawing rate (8 fps). Local.
5. **Upscale** — `lucataco/real-esrgan-video` (`RealESRGAN_x4plus_anime_6B`, `2k`) on the
   unique clip (or the raw one when nothing was held): 2560px with hard line-art edges.
   The clip is sent inline (`inline_inputs`); the model fails on Replicate file URLs. It
   also dies on a long clip — 161 frames, every time — which is why it runs before the
   interpolation, on 41 frames.
6. **Interpolate** — `zsxkib/film-frame-interpolation-for-large-motion` fills four frames
   per drawn one at full resolution (15 minutes a clip), so the 8 fps drawing plays back
   at 32 fps with even motion instead of a jump every third frame. Skipped when the clip
   holds no frames.
7. **Mask and frames** — `sprited/birefnet-video` (`toonout`, mask output) reads a local
   1024px copy of the cut clip (`_maskin.mp4`: the interpolated one is 100 MB, over the
   upload limit, and the model infers at 1024 anyway). Then the framework's
   `extract_frames` with the matte: the mask body is eroded three pixels (its edge sits in
   the background blend outside the outline) and grown twelve; in that band alpha comes
   from colour distance to the backdrop, saturating at twice the threshold; every band
   pixel below full confidence takes the colour of the nearest body pixel (its own colour
   carries background and, un-blended, noise — this is what killed the halo); a premultiplied
   fit to the 512px cell antialiases. Measure the ring of pixels just outside the opaque
   outline: its mean luminance should be within a few points of the outline's.
8. **Sheet** — the framework's `assemble_sheet`, one PNG, a grid as square as the count
   allows. Every frame is kept at the clip's own rate, so motion runs at real speed. A
   one-shot is cut `video.hold` frames after the review's settled frame. A loop that was
   not pinned is **closed**: the best-matching early/late frame pair bounds it and
   `video.loop_blend` frames are crossfaded across the join (`<action>.loop.json` records
   the choice); the seam ends up smaller than an ordinary step. Each sheet's shape goes to
   `<action>.sheet.json`, which `approve.py` and the Unity catalog use.

The framework checks every entry's inputs before doing anything, so `animate.py` writes the
manifest with only the entries whose inputs already exist, generates the pending ones, and
repeats until the chains complete — rebuilding the chain each pass, because a reviewed clip
that holds frames gains stages. Rerunning is idempotent; `--regenerate <entry>` deletes
everything downstream of one entry (unique, smooth, mask input, loop choice included) and
rebuilds. Transient Replicate failures (429, output-upload errors, "Prediction interrupted")
are retried with backoff.

Approval is separate and human: `approve.py` copies sheets into the app and rewrites the
catalog. Nothing reaches the app any other way, and the framework can never write there.

## Skills: a projectile and its burst

A character with a `skill:` block (name, `look`, in-place `motion`, optional `noun` and
`burst`) gets two more sheets, drawn in its own style, so a game can show it attacking
across the screen:

1. **Effect reference** — the same image model, the effect style bible plus the `look`, with
   the *character's own* reference as the init image and a prefix that says "match this
   style, draw only this effect, no character". `--action skill --stage reference` makes
   just these; look at them before spending on video.
2. **`skill` video** — a loop, like idle: the effect animates *in place*, centred, pointing
   right. The app supplies the travel, flips it for the other direction and rotates it to
   the flight angle, so the review runs `--loop --strict-motion` and **fails** a clip whose
   effect drifts or changes size instead of warning.
3. **`burst` video** — one-shot, from the reference shrunk to 42% (`skill_small.png`): the
   effect bursts apart into solid shards and vanishes. Its end frame is `blank.png`, a flat
   frame in the backdrop colour, so the clip is pulled to empty. The review runs
   `--ends-empty --contained`: it fails if the last kept frame still holds foreground, the
   first holds none, or any frame's foreground touches the border (a cell cuts it off there
   and the cut reads as a square box). The catalog plays it at `effect.burst_fps` (32).
4. The rest as for an action, with the framework's **effect matte** (`matte: {effect: true}`):
   a burst is hundreds of shards the mask model loses, so outside the mask body the frame is
   keyed by colour alone and inside it only exact backdrop is dropped.

A `hurt` action (the character flinches and returns to pose) is what the target plays when
the burst lands; its motion should say "half a step" and "staying in place".

Every `look` for an effect says solid, opaque, chunky, no glow or transparency: the matte
turns anything see-through into a white blob, so glows belong in code. A thrown weapon is
never asked to spin: give it a subtle in-place motion and `spin: true`, and the app rotates
the sprite in flight.

## Judging the result — measure, then look

Numbers first, from the sheet frames (a script in the session, or the review), then the
engine. What each means and what fixes it:

- **Edge halo** — mean luminance of the ring of pixels just outside the opaque outline vs
  the outline's own (about 5). Above ~10 on a dark outline is a visible grey rim on a dark
  background and it sparkles because it differs per frame. Fix is in the matte, never in
  the engine: the band colour rule, the erosion, or a backdrop too close to a body colour.
- **Flicker** — the count of opaque pixels in a waist-high band, frame to frame. Under 0.1%
  change on a calm idle. Larger means the mask is losing a low-contrast region: change the
  backdrop colour, not the threshold.
- **Choppiness** — the share of all frame-to-frame change carried by the busiest 10% of
  frames. A clip with held frames measures ~40%; interpolated, ~24%; real footage 10–15%.
- **Life** — horizontal sway of the body's centre and vertical bob of the helmet top across
  the clip, in pixels of the raw frame. On the 1440px knight: 2 px is dead, 44/52 alive,
  81/70 bouncing, 53/38 calm and ready. Steer with words ("small, slow, controlled",
  "knees bend with each breath") and negatives ("bouncing, hopping, excited").
- **Face** — mean change per second in the head region; a sealed mouth stays under ~10 on
  the 1440px clip. Look at a face strip (every 9th frame, head crop) regardless.
- **Loop seam** — difference between the last and first sheet frames vs a typical step.
  After loop closing it should be below a step; if it is not, the clip has no two frames
  that match and needs a re-roll.
- **A brightness step** in the last frames means `video.trim_end` is too low for that clip.
- **A white blob** where a translucent effect should be is the matte flattening it; put
  see-through effects in code.

Then look: a strip of every 20th frame on the darkest background the game uses, a face
strip, the join frames of a loop, and the sprite running in the engine. Never judge from the
engine alone — it may still be showing the previous build.

## Cost and size

Per character with one idle and three one-shots: one image call, four video calls (Kling
pro about a dollar each), four upscales, four interpolations (the slow part, 15 minutes
each), four masks, and local work, run sequentially. A 512px sheet is 11x11 to 13x13 for a
five-second clip at 32 fps, 6–30 MB as PNG, and needs an 8192px source texture in the
engine; a 512px cell renders at native size on a 1080p screen where the old 256px cell was
scaled up two to three times.

## Lessons — keep this section current

**This skill improves itself.** When a run teaches a better strategy — a threshold that was
wrong, a model that does a step better, a failure the review did not catch, a prompt phrase
that fixed a recurring defect — update the script or the default that embodies it *and* add a
dated line here saying what changed and what it cost to learn. The next run must start from
the best known way, not rediscover it. Entries are newest first.

- **2026-09-28 — Close the loop in the sheet, not the prompt.** With no end frame the idle
  never returns to its first frame and the loop popped (the review's gap 23 where 8 warns).
  Pinning it back costs the motion. Instead the sheet keeps the stretch between the
  best-matching early and late frames (search j in the first quarter, i at least 70% later)
  and crossfades ten frames across the join, in premultiplied space, from the frames that
  would have followed the end. Measured on the sheet: the jump at the loop point went from
  3.4 to 1.2 while a typical step is 2.7, and the join frames show no double image. The
  choice is stored in `<action>.loop.json` and redone when the clip is re-rolled. Cost: one
  local rebuild.
- **2026-09-27 — Kling draws 8 frames a second and holds each one three times; interpolate,
  do not play it.** The Kling 3 clip is 24 fps on paper, but every third frame moves and the
  two between are copies (frame-to-frame difference 7 / 1 / 1 / 7 …), so on screen it is an
  8 fps animation and reads as choppy. The review now measures the hold period and which
  phase moves; `animate.py` writes `<action>_unique.mp4` (the moving frames at the drawing
  rate), upscales *that* short clip, and `zsxkib/film-frame-interpolation-for-large-motion`
  fills in four frames per drawn one at full resolution, played at 32 fps. Order matters:
  the upscaler died every time on the 161-frame interpolated clip and never on the 41-frame
  one, and FILM handles 2560px frames (15 min a clip). The interpolated clip is 100 MB, over
  Replicate's upload limit, so the mask reads a local 1024px copy (`_maskin.mp4`); the mask
  model infers at 1024 anyway. RIFE on Replicate is retired (410); ST-MFNet was bursty. Cost:
  five failed upscales and a day's iteration to find the order.
- **2026-09-27 — Kling 3 pro holds the face still when told the character is a silent,
  solitary sentinel, and no end frame is what gives the body life.** Wan 2.2 fast has no
  negative prompt and animated the mouth in every roll. Kling 3 takes one; with "talking,
  speaking, mouth opening/moving, grimace, squinting …" and a prompt framing the knight as a
  lone sentinel who never speaks, the mouth stays sealed in most frames. Pinning the last
  frame to the reference made Kling barely move (2 px of sway); dropping the end frame
  (`end_frame: false` on the action) gave a living body at the price of a loop seam the
  review warns about. Motion is steered by words like "small, slow, controlled", "knees bend
  with each breath", and negatives like "bouncing, hopping, excited"; measured as sway and
  helmet-bob in pixels per roll, kept in the archive notes. Every roll is archived under the
  config's `archive:` path so the evolution stays visible.
- **2026-09-26 — The image model draws a ground shadow no matter what the prompt says.** Two
  rolls of the knight reference, both asked for "no floor, no ground shadow or drop shadow of
  any kind", both came back with a soft grey ellipse under the feet, and one faced the wrong
  way. The shadow would have gone through the whole chain: the video model copies it, the
  matte keys it as a grey blob. `flatten_backgrounds` now flood-fills from the corners
  (tolerance 300 as a sum of channel differences: a shadow's darkest core is ~200 from the
  background, the outline ~600) and sets everything reached to the corner colour. Two Pillow
  traps cost three attempts: `floodfill` returns without doing anything when the fill colour is
  within `thresh` of the seed, so fill a copy with a far-off sentinel and copy the reached set
  back; and its `thresh` is a sum over channels, not a per-channel bound. Facing is now in the
  bible ("the weapon hand toward the viewer's right") because "facing three-quarter toward the
  viewer's right" alone was read the other way once. Cost: two image rolls.
- **2026-09-25 — Every second frame reads as twitching, and the model talks unless told not
  to.** Keeping every second frame made every clip play at double speed; on a body that reads
  as snappy, on a face it reads as a seizure, and the video model animates the mouth on its
  own, so the character also seemed to be talking. Two changes. Every prompt now says the
  face stays calm and steady with the mouth closed, never talking — it reduces the mouth
  motion a lot but does not remove every grimace. And every frame is kept and played at
  16 fps, real speed; because a one-shot then spends most of its five seconds holding the
  final pose, the review reports `settled_frame` (the last frame that still moves, measured
  like the loop gap) and the sheet stops four frames after it. Sheets became per-action
  grids (idle 9x9 at 512px is 4608px wide, so Unity's source-texture cap went to 8192 and
  sprites import with a tight mesh so the atlas packs silhouettes, not full cells). Head
  motion per second of playback fell from 166 to 105 on the idle. Cost: six clips re-rolled.
- **2026-09-24 — A pale rim survives the upscale; it is two things, both at the edge.** After
  the 2560px rebuild the knight still showed a faint light band outside the outline on a
  dark background, plainest in a zoomed Scene view. Measured on the sheet: the opaque
  outline ring was pure black, but the antialiasing pixel just outside it averaged
  luminance 73 at alpha 64. Two causes. The band's un-blend `(rgb - (1-a)*bg)/a` amplifies
  codec chroma noise at low alpha into light grey, so band pixels now take the colour of the
  nearest body pixel instead (the framework fills it outward from the mask body). And the
  mask model's body edge lands a pixel or two outside the outline, in the background blend,
  at full alpha; `mask.erode: 3` shrinks the body before the key so those pixels are judged
  by colour — luminance outside the outline went 61 → 0.5 on the test frame, at a cost of
  0.2% of opaque pixels. Unity added a third: its sprite-atlas pages were block-compressed at
  default quality (DXT5 on desktop, ASTC 6x6 on iOS), which greys the outline's antialiasing
  again; the atlas now packs at high quality (BC7 / ASTC 4x4, quality 100). Measure the ring
  of pixels just outside the opaque outline — its mean luminance should be near the outline's
  — rather than eyeballing; at normal zoom this rim hides.
- **2026-09-24 — A soft outline is a resolution problem, not a matte problem.** The knight
  was called out for fuzzy edges in Unity. The matte was fine: the clip was drawn at 480p
  (624px square) through a lossy codec, cut to a 256px cell, and then scaled up two to three
  times on screen — every step blurred the line. Tested on one frame and one clip before
  changing anything: an anime-tuned Real-ESRGAN pass (`anime6B`) turns the codec blur into
  hard line art, and the video variant keeps the frame count and rate, so it drops in as a
  stage between the review and the mask. The pipeline now generates at 720p, upscales to
  2560px, mattes there (`mask.grow` 3 → 12 to match the thicker outline), and cuts 512px
  cells. Review still runs on the raw clip so a bad roll is never upscaled. `approve.py`
  now reads the cell size off the sheet itself, so characters built before the change keep
  a true catalog entry. Two more things the run taught: the upscaler fails ("error trying
  to upload output files", twelve of twelve) when its input arrives as a Replicate
  file-endpoint URL and works when the clip is inlined as a data URI, so the framework
  grew an `inline_inputs: true` entry field and the upscale entry sets it; and Unity's
  importer capped sheets at 2048 with a per-platform iOS override that the default setting
  never touched, so a 3584-wide sheet was silently downsampled until the importer cleared
  it. Cost: one image call and one video call to test, twelve failed upscale calls before
  the URL cause was isolated, one video re-rolled for a glowing blade, then the knight
  rebuilt.
- **2026-09-23 — A burst that reaches the frame edge plays as a square.** The first six
  bursts flew their shards past the cell border in most frames; on screen the cut-off
  edge drew a box around every impact. Prompting "stay inside the frame" alone did not
  fix it: a burst that starts from an effect filling two thirds of the frame has nowhere
  to expand. The burst now starts from `skill_small.png`, the reference shrunk to 42% on
  its own background (with the shrunk image's background flattened to the exact colour,
  or the paste leaves a seam the model keeps), and the app draws the burst larger. The
  review's `--contained` gate fails a frame whose border is more than 2% solid foreground
  after a 2-pixel erosion — a cut shard, not the spray of dots every burst throws. Cost:
  seven videos, one of them a wasted roll before the shrunken start.
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
- **2026-09-23 — Wan will not make fewer than 81 frames.** Ask for 81. (Keeping every second
  frame was the first answer; it reads as snappy on a body and as twitching on a face — see
  2026-09-25. Every frame is kept now and one-shots are cut where they settle.)
- **2026-09-23 — The image model wants its references as a list.** `init_images` is an array;
  the framework's `input_files` now accepts a list of references for exactly this.
