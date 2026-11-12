---
name: idle-breathing-loop
description: Build a character's or enemy's production idle — a longer, slightly varied, seamless breathing loop made from the character's approved AT-THE-READY battle pose with the weapon held as the video model draws it — and layer extra motions (head turn, regrip) on copies of it. Use when a new character or enemy needs its idle, when an idle starts from a relaxed pose or shows a weapon glued on by code, when an idle pops at the loop point, blinks, talks or blurs, or when an extra motion must be added without touching the approved idle.
---

# Idle breathing loop

**The method, for every idle of every hero and enemy:** the idle is made from the character's
approved **at-the-ready battle pose** — never the relaxed design pose — with the weapon held the
way the video model draws it in that picture. That one approved picture (K0) and a short prompt
go to the paid video model (Seedance first), K0 at both ends so the loop closes on it. The
breathing itself is liked and kept; the idle is **longer and a little varied**, not one repeated
breath.

The user's words (2026-11-09, on the skeleton idle): "The idol should be at the [ready] position
... the idols need to be longer a little bit more diverse, but the breathing looks wonderful ...
it needs to be in at the ready at the battle ready position holding their weapon appropriately.
This image is at a relaxed position with the weapon somehow glued to his hand in an awkward
position looks like Code versus the animation itself."

- **No weapon by code in an idle.** A weapon pinned or attached onto a relaxed body reads as code
  and is rejected on sight. A take whose weapon changes type or shape is re-rolled, not pinned.
- **No relaxed key.** If the character has no approved ready pose, making that one picture is the
  only key work (`annie-key-artist`), and it goes to the user first.
- **Paid takes need a yes and a cap.** A Seedance take is $0.06 a second (a 3 s take about
  $0.18); with no yes and no dollar cap in the brief the item goes to `blocked` with that
  question. Local Wan is not a fallback for a ready pose: it reads a weapons-ready key as combat
  in every mode (see "Local Wan, relaxed keys only"). The Replicate token is only in the login
  profile: start every paid command with `source ~/.zprofile >/dev/null 2>&1;` (or `zsh -lc`).
- **When the take budget is spent, a still placeholder is the cheap exit**: 64 copies of K0 in
  the installed format (8×8, 16 fps, as the archer's `versions.json` entry), so game code is
  unchanged and a moving idle can replace it later. Label it a placeholder to the user.
- Approved idles made the older way (the archer's relaxed PROD idle v2) stay as they are; a new
  version from the ready pose is a new job, never an edit of the approved one.

Working folder per character: `src/asset-animation-demo/local_runs/<character>/` (classes and
enemies: `local_runs/characters/<class>/work/`); the approved keys live in its `approve/`
subfolder with a README the user reads. **Never a grey displacement map on the still key** — it
was tried in Unity and rejected by the user ("The gray pattern idea did not work on the
characters"); do not offer it for an idle. Run the shared scripts with the agf venv python
(`src/Asset-Gen-Framework/.venv/bin/python`); `gen.py --mode fast` has no hosted start-only path,
and its `edit` only calls Qwen. Every local matte path (`generate.py matte`, `gen.py matte`, agf's
model matte) reaches ComfyUI on 8188, so inside a paid slot with no server use the flood matte.

**The Assassin's (rogue) main idle is `rogue/work/idle_v6/g0`, approved:** 6 s, the bob from
`idle_v4` slowed to 4 s, then a 2 s still rest (step 6b), no wind. There is no Assassin install
route yet, so it is not in Unity. The user accepted that it rises as one piece like a bob ("it does
look like a bob but it looks good"). **Wind on him can come later, and no route tried makes it.** He
wears nothing loose and his hood is a stiff stub, about 30 px at 640. Asked for wind, the video
model invents something to blow — Wan a teal cape, Seedance a black tail — and "breeze" or "blows"
draws rings on the floor. A head-only crop does not help: Seedance slid the whole head 7–11 px at
640 and left the stub rigid, even on "large flapping". An image edit swells the stub (+32%, +70%
length) rather than bending it and repaints the crown highlight, which steps at any mask. One pin
gives one lean, never a flap, so judge a pin fallback before paying for it. Wind needs loose cloth
in the key, and that is a new look for the user to approve, so do not spend another take on this
hood. If a flap ever exists, `rogue/work/idle_v6/attach_hood.py` is the attach: replace inside one
fixed mask on a sub-pixel head track, proved on a static hood at under 0.6 px at the seam and 0 px
changed outside the mask. A head turn, or another variation, is still wanted for him later — every
method tried so far (Wan i2v, Qwen, nano-banana) failed, so the next attempt needs a new method, not
another seed of an old one.

## Three modes — where each model job runs

Every model job goes through `scripts/gen.py`, which takes the same commands and flags as
`src/LLMs/generate.py` plus a mode. Scripts call `gen.py`; the mode comes from `--mode` or from
`GEN_MODE` in the environment, and with neither it is `local`.

```
GEN_MODE=fast ./render_hit.sh 7                          # a whole script in one mode
python3 gen.py --mode fast edit K0.png "..." --seed 71 -o key.png
python3 gen.py --mode fast --dry-run keyframes ...       # where it would run and the cost; no call
```

| Job | Local time | `local` | `fast` | `100fast` |
|---|---|---|---|---|
| `edit` — key pose (Qwen-Image-Edit 2511) | ~8 min | local | Replicate, ~10 s, $0.03 | Replicate |
| `keyframes` — in-between (Wan 2.2 first-last-frame) | 13–40 min | local | Replicate, ~25 s, $0.05 | Replicate |
| `matte`, video (BiRefNet) | ~1 s a frame | local | local | Replicate, ~8 s, ~$0.01 |
| `upscale`, video (Real-ESRGAN) | minutes | local | local | Replicate, ~75 s, ~$0.10 |
| `matte` / `upscale`, one image | 5–12 s | local | local | local |
| `interpolate` (FILM) | ~30 s | local | local | local |
| face lock, post, sheet (our scripts) | ~2 min | local | local | local |

- **`local`** — free, and the only mode for unattended overnight runs. One job at a time,
  `src/LLMs/llms free` after each Wan render (`llms` is not on PATH).
- **`fast`** — for sitting at the desk: the two jobs that are 95% of the wait leave the Mac. One
  action (about six key seeds, two in-betweens) is about $0.30 and two minutes of model time against
  ninety. Nothing is loaded locally for those jobs, so the swap and close-Unity rules do not apply.
- **`100fast`** — `fast` plus video matte and upscale. FILM and single-image jobs stay local in every
  mode because local is the faster side: FILM on Replicate took ten minutes and $0.60 a clip.

Every paid call prints its cost and adds a line to
`src/asset-animation-demo/local_runs/replicate_spend.csv`. The hosted Wan makes 81 to 121 frames:
`gen.py` asks for 81 and samples the whole move down evenly to the count asked for (first and last
frames kept, so the clip still lands on its end key), then sizes it to the width and height asked for.
The hosted models are different builds from the local ones — a seed does not give the same picture
in two modes, so a re-roll of an approved seed stays in the mode that made it.

## Keep the Character Chart current — part of every run

The user tracks and reviews all animation work on one page, the Character Chart
(https://claude.ai/artifact/VMw7tr3gNogpx2efw9ozsZ). Its record is
`src/asset-animation-demo/local_runs/chart/chart.json`: a table per character, a row per body or
weapon, a column per animation. A run is not finished until the chart says what the run did.

Update the cell **at the moment its state changes**, not at the end of the session:

| When | Command (from `local_runs/chart/`) |
|---|---|
| work is planned but waiting | `python3 build_chart.py set <character> <row> <column> inqueue --note "..."` |
| the first model job for it starts | `... set <character> <row> <column> working` |
| a clip is ready for the user to judge | `... set <character> <row> <column> review --clip <gif or video> --note "Attack v4."` |
| the user says it is approved | `... set <character> <row> <column> done` |

Then publish `chart.html` to the same link: the Artifact tool with `url` set to the link above,
`root` set to the chart folder, and `files` set to what `python3 build_chart.py files` prints.

- **`done` is the user's word only.** A clean check, a passing guard or your own liking is `review`.
- A body's animation usually changes several rows at once (both robes share frames; every bow is
  pinned onto it) — set each row the run really rebuilt, and leave the others alone.
- The note is one short line: the version, and which figure to look at when the clip shows several.
- A new character, body, weapon or animation is a new entry in `chart.json` (`characters`, `rows`,
  `columns`); add it the first time it is touched.

## The result this produces

A 16 fps sprite sheet (512 px cells, transparent), about 6–9 s long: the character in the
at-the-ready battle pose, weapon in hand as the model drew it, breathing — several breaths that
are not all the same (a deeper one, a shallower one, a small settle of the grip or weight), feet
planted, face the same face on every frame, loop seam no bigger than a normal frame step. One
breath repeated reads as too short and too plain (the user).
**Idles never snap.** The idle and its extra motions (a weight shift, a head turn) are seamless
loops: the last frame flows into the first and the pose comes back to K0 exactly, because they
play back to back in the game (the user). Only actions — attack, hurt, defend — may
snap into or out of the idle and need only their place to match. Give the video model K0 and
the motion's approved keys in the order they play. Only the
character and their own weapon are in frame — no other figure, no effect, no projectile.
Unity: `Assets/Characters/<character>_versions/idle_vN.png` + an entry in that folder's
`versions.json` with `"loop": true`, `"status": "prod"`.

## Steps, in order — each one earned its place

1. **One approved base key, K0, transparent, at 1024: the at-the-ready battle pose**, weapon
   drawn in the hand by the image model, never attached by code. Cut from the approved reference with
   BiRefNet + the agf matte, then **clean enclosed pockets by hand**: white or plate-coloured
   regions the source art itself carried (the archer had a white gap between glove and bow and
   between the arrow shafts). Measure the edge ring (should be dark, ~0 bright pixels) and show the
   user the key on dark / checkerboard / light — Preview draws transparency as white and misleads.
   The user approves K0 in `approve/README.md` before anything else is rendered. For a new class
   or enemy, K0 is a byte copy of the user-approved battle stance (the ready pose, not the relaxed
   design) (check its sha1 against the approved file —
   a stale `keys/K0_<class>.png` from an earlier design round has passed for it once); a true gap
   in the silhouette, outlined on both sides and grey in the source, stays transparent.
2. **Lay K0 on a flat grey plate, #7f7f7f, at 640 px** (`K0_plate.png`). Grey, not magenta:
   magenta tinted every white highlight pink through the matte. Resize the RGBA first
   (Pillow's RGBA resize already premultiplies — premultiplying by hand first blows out the faint
   edge pixels), then composite on the grey; compositing at 1024 and then a Lanczos resize
   leaves a 1 px light rim round the outline (1073 rim px against the archer's 55).
   For any character but the archer, also write `keys/K0_<class>.ref.json` at 640: face box (eyes,
   brows, mask), head box, pocket boxes, enclosed gaps, a box and tip per weapon, a sole band
   **per boot** (feet are rarely level in a battle stance), the bbox, and the alpha threshold any
   piece count uses (dust sits at alpha ≤ 6; a spider's fang tips are not leg tips) — `face_lock.py`,
   `pose_guard.py`, `finish_key_body.py` and `build_v5.py` hard-code the archer's K0 and its bow
   and quiver boxes; a rogue-aware version that reads the `.ref.json` is owed by
   `annie-tool-writer` before any non-archer key is guarded.
3. **Render K0 → K0 takes with hosted Seedance** (`archer/actions/tools/render_remote.py
   --model seedance --start K0_plate.png --end K0_plate.png --duration 2|3`, which writes
   `replicate_spend.csv` itself; `edit_remote.py` does not, so log its spend by hand). The prompt
   is short: standing ready for battle, breathing slowly, holding the weapon, static camera, flat
   grey background — no wording for each limb. Seedance holds the boots at 0 px with a clean drawing
   and follows wording strongly — far better than Wan on the rogue crouch — but there is no middle:
   rise wording stands him up (+45 px), still wording freezes him (0 px). **Find a small move by
   slicing the start of a too-big take**, not by asking for less: the rogue's approved breath is
   frames 5–10 of a rise take, FILM-densified, retimed with `retime_progress --axis vertical`, then
   mirrored back to K0. Pinning a small rise does not work either: two Seedance K0 → peak takes
   wandered far through the middle (one sank 34 px, eyes shut for 16 frames) and snapped to the
   pin in the last frames — slicing is the only route that has worked. Never pin a take's end to a frame harvested from another take if that frame
   has its eyes closing — the eyes close on the way in and the take overshoots anyway (+30 px).
   `edit_remote.py` resizes its result to `--size` square and nano-banana returns 1344×768, so for
   a wide plate pad or scale uniformly and keep the raw; a fix is owed by `annie-tool-writer`.
   Seedance returns **1920×1088, not 16:9: scale uniformly** and crop; squeezing to 1280×720
   (a 0.74% stretch) moved the boots 1.3 px. Seedance's first 2–3 frames can be a crisp K0 beside
   soft frames: drop them, or the mirrored loop flickers at the seam. A slice passes when the
   figure rests into the band over 4 or more raw frames, not when 4 frames sit inside it.
   **When pinned K0 → K0 fails, a start-only take sliced from frame 0** made the fighter's idle: a
   3 s start-only take stays on-model only about 0.4 s (then a blink, a smile fading, a sword
   swing), so cut from frame 0 and expect about one take in five to be usable; play a deep and a
   shallow slice there and back, FILM 8×, then `retime_uniform` — `retime_progress` skips frames
   on a breath that wobbles back. A downward settle needs `clean.py retime_progress --direction
   down`; never reverse, retime and reverse again (that puts the ease at K0 and an un-eased V at
   the low point), and expect the end ease to leave a few near-identical cells at the bottom of a
   mirrored settle.
3b. **Make it longer and varied by chaining takes.** `render_remote.py` gives 3 s at most, so the
   length comes from two or three different K0 → K0 takes (other seeds, or wording for a deeper
   breath, a shallow one, a small grip or weight settle) cleaned one by one and played back to
   back: each starts and ends on K0, so every join closes like the loop seam (step 6 at each join).
   Rests (step 6b) go between them, not one long freeze at the end. Keep only takes that hold the
   weapon, clothes and face of K0; a take that swings the weapon or stands up is dropped.
4. **Lock the face** (`scripts/face_lock.py`): paste K0's face (eyes, nose, mouth, chin; rows
   150–240, cols 268–392 at 640) onto every frame at the tracked head position — SSD template
   match, ±10 px, 1 px steps, offsets median-filtered over 5 frames so the patch never jitters,
   7 px feather, per-frame tone shift from the blend ring. No blink, no mouth, no blur; the head
   still rides the breath. **On a slow idle use `scripts/facelock_smooth.py <in.mp4> <out.mp4> --k0
   <plate> --ref K0_<class>.ref.json`** instead: a whole-pixel paste hops visibly when the head
   moves under 1 px a cell (the weight shift hid it); this one tracks the head box sub-pixel, makes
   the offsets monotone and smoothed, and resamples the face cubic. It leaves a 13–15% eye
   sharpness pulse at 512 from the sub-pixel resample — say so to the user. Because it forces
   monotone offsets it cannot lock a there-and-back loop or a head that moves more than 10 px; its
   search window must be at least the measured depth + 5 px, and it crashes on float ref boxes
   (round them) — a fix is owed by `annie-tool-writer`. Face lock pastes plate grey into gaps
   (between fangs): run `enclosed_plate` after the lock, before the flood matte. (For segments where the face must move, use `scripts/mouth_fix2.py`
   instead: same tracking, lower face only — the model talks whenever the head is still, a
   negative prompt does nothing at cfg 1, and only a patch fixed it.)
5. **Post, per frame** (`scripts/build_v5.py`): flood-fill matte from the plate colour (no model
   needed — anything the flood from the corners cannot reach is the figure). **Key the matte against
   each frame's measured plate** (median of the frame border), never a fixed #7f7f7f: a hosted
   render's plate drifts (Seedance's was about (116,116,121)), and measuring it cut the fringe from
   228 to 14 px (`characters/rogue/work/idle_v4/s3_final/post_s3.py` does it; build_v5 still keys
   #7f7f7f). Skip the face and the blades in any plate-grey drop or eye whites go transparent. A grey colour-key
   inside fixed pocket boxes applied to the mask *before* the agf matte (grow 3, erode 1), colour
   match to K0 (per-channel mean/std over the character's pixels), downscale 640 → 512 in
   premultiplied space. **No 4× upscale** — it buys nothing at this size and costs 2/3 of post time.
6. **Close the loop**: drop the duplicate last frame (it equals the first), 2-frame premultiplied
   crossfade across the seam (last → first). Do not paste the crisp K0 into the sheet — a sharp
   frame inside soft frames reads as a flash.
6b. **Rests, when a steady bob reads as constantly rising**: after the loop's cells, repeat cell 1
   (the rogue: floor cells 001–064 byte for byte, then 32 copies of 001). Add no ease or drift by
   code: an eased bob already arrives with no position corner (under 0.2 px a cell at 640), and if
   the rest reads frozen, shorten it, which is a free re-cut. Count the freeze from the cells, since
   the floor's last cells can already equal cell 1: the rogue's 63 and 64 do, so his 32-cell rest
   freezes 35 frames. Tell the user nothing at all moves in it.
7. **Sheet + Unity**: cells in a near-square grid, sidecar `.sheet.json`, copy into
   `<character>_versions/`, add the `versions.json` entry (fps 16, loop true), run
   `Characters/Import Animation Versions`, capture play mode to a GIF and *look at it*.

## Local Wan, relaxed keys only

This route made the archer's relaxed PROD idle v2 and is kept for re-rolls of idles made that way;
it is not used for a new idle, because a ready pose reads as combat to Wan in every mode —
first-last K0 → K0, start-only, local and hosted. The Assassin's 8 takes swung or thrust the
daggers, stood up, or cut to another figure, and no take held a clean breath; a prompt with no
combat words at cfg 3.0 with a negative prompt did no better (daggers retracted 94 px, eyes closed
for 12 frames, a gold glow on the outline, the hood rose 2 px).

One segment K0 → K0 with Wan 2.2 14B first-last-frame (`scripts/render_breathe.sh`):
65 frames, 640×640, 16 fps, seed 7, 4-step lightx2v. The prompt asks for *one slow deep breath,
chest and shoulders only, head and face do not move, eyes open, no blinking, mouth closed,
feet planted, same shading throughout, static camera, flat grey background*. Pinning K0 at both
ends is what makes the loop close. **Close Unity first**: 65 frames with Unity open hung the
server at the decode twice (swap 27 GB). 49 frames is the ceiling with Unity open. The server
gives one model at a time — never queue Qwen edits while Wan runs.

## Keeping in-betweens clean (`scripts/clean.py`)

Every Wan clip goes through these before it is composited; each one answers a defect that crept in:

| Defect | Cause | Rule |
|---|---|---|
| grey inside the bow, arrow gaps, glove gap | Wan paints the plate into any enclosed gap; a flood fill cannot reach it | `enclosed_plate`: drop plate-coloured pixels (grey, sat < 26, lum 90–175) within 12 px of anywhere K0 is transparent. Leaves the buckle alone. Replaces fixed pocket boxes. On low-saturation figures (the spider's lavender highlights, ~127,111,129) it eats real highlights: drop only plate blobs that touch the flooded background (`characters/spider/idle_v1/compose_idle_v1.py` `encl()`) |
| ghost double cape, fuzzy edge | crossfading two different shapes | never crossfade shapes. Render the clip **from the idle's own frame** (`idle16_plate.png`, frame 16 of the locked loop) so it joins exactly; drop each pinned frame 0 (a pure texture pop, ~7 vs a typical step of 1). |
| body wobbles, then lunges and snaps at the key | Wan's motion is not monotonic, and it **overshoots a pinned key** — the key frame can sit *behind* the model's own extreme, so forcing the clip to end on the key makes the peak dip | `retime_progress`: measure the body's real travel (horizontal centroid of a row band, running maximum so backward wobble is skipped), end on the furthest frame not the key, eased targets (0.7 cosine / 0.3 linear) so the mirrored reversal has no snap, a 5-frame hold at the extreme, and the raw anticipation frames before the move skipped; then `bridge_jumps` FILMs the one pair the skip leaves (jump = > 3× the *mean* step; the median is useless after a retime). Shift hips went 0→12.7→0 in a clean bell, 1.6 px per 2 frames max. |
| a retime stops short of the top (8.6 of 9.0 px) | the pinned end frames are dropped | `retime_progress --keep-pinned` reaches the top |
| a slowed loop stops hard at the top | slowing retimes only the middle: arrival at the top went from 51% to 71% of mid-rise speed | ease needs more source frames near the top, not a slower retime |
| a vertical move (a breath rise) retimes into bursts | the centroid measure is horizontal only; a top-edge measure is locked by one outlier through the running max (a 5.2× step) | `clean.py retime_progress <in> <out> --cells N --axis vertical`: progress is the row-profile shift of the upper 60% against the first kept frame, sub-pixel, so a rise of a few px still gives distinct cells (worst step 2.19×); it prints the source frames and any duplicates. |
| snap mid-move (head) | Wan moves in bursts | `generate.py interpolate` twice (FILM 4×) then `retime_uniform` (motion measured on a 4× downsample so pixel noise does not count) → every frame carries equal motion. Head turn's worst step 7.2 → 4.0, shift's 5.5 → 3.5, evenly spread. |
| distorted face mid-turn | at 640 the face is ~60 px; Wan smears a 3/4 face | **render face motion as a close-up**: crop the head box (rows 22–262, cols 180–480 at 640) from the idle frame and from the key, scale 1.6× to 480×384, run Wan on that, then `closeup_to_full.py` pastes it back. 4× the face pixels; the turn came out crisp first try. Same trick as the hand close-up for Qwen keys. |
| texture pop at internal joins (out→hold→back) | different renderings of the same pose | `crossfade_joins`, 3 frames each side. |
| pasted head jumps | tracking a mid-turn face against two keys | don't track the source: a static-camera clip pinned to K0's body already has its head where K0's is. Track only the idle's own head bob. |
| blink / mouth flicker | model habit | `face_lock` where the head is still; `still_face` (temporal median) only where the head is still. A blink *during* a turn stays — every patch across a turning head ghosts the eyes. |

Measure, don't eyeball. Track a part by its own pixels or its outer mask edge — a fixed-box
centroid under-reads a fist or claw that moves out of its box by half. On a hanging-arm body gate
the arms with the head: the outer fist and elbow edge must not move before the head top has moved
2 px; the goblin's arms pulled out at frame 5–6 of every sink. Render every review mp4 on a dark
background as well as grey — grey hid plate bits at a cape hem — and have the reviewer check the
face on every frame for blinks; an artist's blink windows have been wrong. Also: per-frame mean |diff| profile (whole figure and head region), plate-coloured pixel count
inside the figure, edge-ring colour, and the pose guard. A lint that runs these before Unity is the next step.
Run each take's quick gate before cleaning it — on a bad take it saves the whole clean. Captions
go in a strip outside the picture: `compose_idle_v4`'s caption bar over rows 0–26 hid the hood's
rise. A reviewer never runs the artist's compose script to read its checks — even with `--no-video` it
rewrites the sheet. A face-box check read under sub-pixel offsets scores high on its own (a
perfect moved K0 scores 11.81), so judge the face on paired-frame strips, not that number. A
tip-travel number passes on a rigid slide: judge cloth motion registered on the face and rim, by
shape change and reversals.

## Keys for extra motions (head turn, regrip) — on a COPY of the idle, never on it

- Keys are **whole-body edits of K0 with local Qwen-Image-Edit** (3–4 seeds), finished with
  `scripts/finish_key_body.py` (hardened BiRefNet mask, plate pixels dropped, colour-matched).
  No head graft — the graft made the body rigid. Control comes from `scripts/pose_guard.py`
  instead: feet, bow, quiver and size measured against K0; the body may breathe, not walk.
- Qwen turns the whole body on "look behind him" every time; left/right is a coin flip per seed.
- Wan segments between adjacent keys, 33 frames, breathing in the prompt; a return segment
  played as the out-bound reversed is seamless and cannot talk.
- The extra motion is layered onto idle frames (head region tracked and composited) so the body
  under it is the PROD idle, and the clip starts and ends on idle frames. Play idle 6/10,
  idle+head-turn 2/10, idle+regrip 2/10.

- **A head turn turns the whole body.** The hood, shoulders and torso turn with the head; a face
  sliding inside a still hood is rejected — the motion must read as fluid and natural, never one
  part on its own. So a head turn is a whole-body edit of K0, not a head crop.
- **A head turn under a hood** (rogue): local Qwen edits from K0 cannot rotate this hooded body —
  16 edits over three methods (head crop, code-guided crop, whole body, chained from a turned-head
  plate) only redrew the face while the hood and body stayed put, and hosted nano-banana (2 tries)
  kept the hood still and redrew both fists, or copied K0. **Wan i2v from K0 alone** couples any
  turn with a teal cape growing down the back and both fists drifting, in every frame of every
  take, whatever the wording; a Qwen clean-up of such a frame flattens the torso 3× and Qwen cannot
  pull back one arm (it draws a third). No route tried so far turns this hood, so the Assassin's head
  turn waits for a new method. A key reviewer checks every weapon, the back dagger too, not only the one the brief
  names.
- **A breath-in key** (rogue crouch): Qwen edit cannot make a small whole-upper-body rise.
  Strong wording raises or spreads the arms (daggers overhead, a T-pose), mild wording moves
  nothing and bloats the torso, an upper-body crop loses the sash and dagger handle, and "shift
  up" redrew a standing figure — 6 of 6 failed, one of them hosted. Hosted nano-banana also failed
  6 of 6: nothing moved, the legs lengthened, or the whole figure slid. Do not spend edits on it;
  the breath comes from a K0 → K0 Seedance render (step 3), which needs no breath key.
- **Measure a turn by NCC patch tracking** of torso, sash and hood top against K0 — a real turn
  moves them; row widths do not show it. A take whose body below the head scores NCC ≥ 0.88 against
  K0 and whose hood top moves under 5 px while the eye band moves 45 px or more is a face slide,
  not a turn.

## What still fails at the ready pose

The video model replaces the pose instead of adding a breath on these bodies; do not plan another
take of the same route for them without a new method:

- **A big winged quadruped** (the dragon): K0 → K0 from a seated and from a ready start, 6 takes
  on 2 models and 3 pin modes, reared, prowled or folded the wings; pinned Seedance snaps out to
  another pose and races back to the end key, so there is no early rise to slice. Measure such a
  body with a silhouette tool (per-foot sole bands, crest top with wings excluded) — patch NCC
  fails once a take re-poses.
- **A staff or haft held upright in a fist, or a hand resting on a planted weapon** (Star Sage,
  brute, porter): the staff fist drifts first and the body pivots on it; a hanging arm rides its
  shoulder at about 0.9×, so the fist slides 7–10 px along a still haft.
- **A three-quarter body** (the hobgoblin) turns toward camera on every model and wording tried.
- **A non-human body** (the spider): image edits will not shift its weight (6 wordings returned
  K0), and Wan K0 → K0 closes the eyes and nods; Seedance K0 → K0 keeps the eyes and sinks straight
  down — slice its start.
- **Hanging arms on a bulky monster** swing out on any sink (goblin, skeleton), and a "do not
  spread" clause does nothing on Seedance; a sink through the knees with no arm wording (Seedance
  pinned) moved the skeleton as one piece.

## Numbers (M1 Max 32 GB, server alone)

| Step | Time |
|---|---|
| Qwen key edit, 1024 | 4.5–5 min per seed |
| Wan 14B FLF, 640, 33 frames | ~13 min; 65 frames ~40 min |
| face lock / mouth patch | seconds |
| post, flood matte, 64 frames | ~2 min |

## Scorecard — the last step of every run

Append one row per pass to `scorecard.csv` beside this file, then run the `skill-improver` skill on
this skill.

`date,character,action,frames,passes,key_edits,inbetweens_local,inbetweens_remote,hand_fixes,new_tools,minutes,usd,user_verdict,note`
