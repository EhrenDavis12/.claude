---
name: new-armor
description: Give a character a new armor or outfit (the archer's Nightmare Cloak, Heavenly Armor) and animate every action for it — made the way the base armor was made, from the outfit's own approved base image, with its own key poses and in-betweens, so its motion may differ from the base's while the camera, scale, ground line, rest pose and pinned weapons stay the same. Use when the user asks for a new armor, outfit or skin, a new animation for one, or a fix to one (a still-looking idle, a hit that reads as a kick, an invented face, a bow that does not turn with the hand). A same-shape colour change is `recolour-armor` instead.
---

# New armor (its own animation, made the base's way)

**The promise to the user:** each outfit gets its own animation, made exactly the way the base armor's
(Forest Robes) was made: key poses drawn from the outfit's own approved base image (its K0), the motion
filled in between them, every frame kept. The outfit may move differently from the base — the user's
words: "the animations don't have to be perfect or match what we have for the green cloak they could be
their own thing" — but every action starts and ends on the outfit's K0 pixel for pixel, the bow follows
the outfit's own fist, there is no halo, and the images are clean.

**Why not copy the base's motion:** every way of putting a second outfit on the base's frames redraws
each frame, and the redraw shimmers and leaks the base outfit's parts. See "Methods that lost" — the
user agreed that even a perfect shared grey base body would not make the other armors good.

Cost and time, said before work starts: local and $0 is the default. A local Qwen edit takes about
9–10 minutes, a local Wan segment 7–8 minutes once Docker Desktop is closed (see "Machine"). The
approved idle took about three hours of agent time; a hit with a pain face takes most of a day locally.
A hosted render is minutes and cents, but needs the user's yes and a dollar cap.

## What the user has already rejected — do not ship these again

| Rejected | Their words | So |
|---|---|---|
| an idle that only breathes (one code breath key, FILM ping-pong) | "looks like a still image ... the cloak doesn't move ... It's just not alive" (face, hands and stance were "perfect") | an idle needs a visible breath **and** cloak motion, "life ... wind", not overdone — watch the base idle for the amount |
| a hit with no pain and a lifted boot | "looks like a small knockback versus he got hurt"; "more like he's trying to kick dirt than he is getting hit" | a pain face for a split second at impact, the back knee bending and turning a little (outward only), more torso bend with the cloak flowing |
| a bow that turns less than the hand | "needs a little bit more rotation to follow the hand ... around the Z axis" | the bow turns 1.0x with the located fist; no `angleOverrides` scaling it down |
| held frames (12 picked frames, holds baked in) | "it's choppy ... doesn't matter if it's not glitchy it doesn't look good anyway" | keep every in-between frame |
| one shared grey body that every outfit is drawn over | "These results are just terrible" | each outfit is its own animation |
| a face pasted onto moving frames | "The face is all glichy… slow it down and you will see it" | a face is held only where the head does not move (a code-warped idle), or painted into a key the motion is rendered from — never pasted per frame |
| a different camera angle | "the death scene created a different camera angle" | own poses are fine; the camera, scale, ground line and facing stay the base's |
| torn edges, holes, loose fragments | "let's make sure these are crisp clean images" | look at 4x on a light background before anything is sent |

## Before any frame is made

1. **The outfit's K0 is approved by the user** (`<outfit>/approve/K0_<outfit>.png`, empty fist, the
   base's stance and size). It is read-only for every action.
2. **Check K0's own matte first.** The cloak's K0 had ~166 px of transparent pinholes in the grey
   buckle frame and a +15 edge ring of its own; rebuilt frames are solid there, so a pinned end cell
   pops. Measure every later frame against K0's own numbers, in the same resize: a premultiplied box
   1024→512 (`own/K0n_512.png`). A straight-alpha LANCZOS resize reads K0 itself +26 on the ring.
3. **Colour-match to the pinned cell**, not to the approve image (they differ by ~2.4 levels), or every
   seam steps: `nc_build.py --colour-ref <K0n_512>`.

Tools for the archer's cloak are in `local_runs/archer/nightmare_cloak/tools/`; a new outfit copies them
and swaps the mask and K0. Python: `src/Asset-Gen-Framework/.venv/bin/python`.

## Idle — code only, no model

The approved idle (`own/idle/v3/`) is a per-frame code warp of K0, so the face, hands and stance are
K0's own pixels and nothing is invented.

| Step | What | Check |
|---|---|---|
| 1 breath key | `nc_pose_key.py` handle mode: head block lifted ~9 px at 1024, shoulders, chest, belt, belly, hips tapering to 0, legs, boots and hem pinned | measure the delivered lift by sub-pixel block match — MLS blends a rigid block toward its neighbours (asked -8, got -7); height ratio ~1.015 |
| 2 cloak sway | `nc_cloak_sway.py K0 out --gl g --gr g`: a masked rotation field swings only the two cloak panels; the body is composited back from K0 unwarped, cloth pinned to the body over 24 px | `--gl 0 --gr 0` returns K0 byte for byte; body pixels changed: 0; left flare 12–16 px at 512, right peak ~6; no hinge, no glow-line ripple at 8x |
| 3 clip | `own/idle/v3/warp_clip.py`: cell t = breath warp at b(t) over sway(K0, g(t), g(t−4)), breath curve plus three gust curves, 64 cells at 16 fps | cell 0 byte-equal K0n_512; the last gust runs into the loop point, so something is still turning at frame 0 |
| 4 build | the idle's own compose script → 8x8 sheet; loadout entry `test_only`; `finish.sh <entry> --no-install`; `nc_hands.py --self --weapon` | no failure verdict; 2 hands on every cell |
| 5 bow | where cloth swings under the forearm the hand tracker's angle follows the cloth (±1.4° rocking with a still fist): set `angleOverrides` to the fist's own measured turn | rendered bow turn = the fist's |

Whole-figure MLS sway was tried six times per key and brought a new cloak-edge defect every time
(pins beside edge handles hinge it, dense handles ripple the glow line, carried pivots drag the body).
Cloth sway is a **masked, cloak-only** deformation.

The same cloak layer is the first candidate for the other held moments: a defend brace, end settles,
the head turn and weight shift.

## Actions — keys, then the motion between them

| Step | What | Check |
|---|---|---|
| 1 brief | from the base action's direction and the user's rules (`base-action/SKILL.md`), never from the base outfit's frames | the user's rejected list above is in it |
| 2 keys | local Qwen from K0 with K0 as picture 2; 2–3 seeds per key, up to 6 edits a key | look at every result; mouth closed, rune and glyphs unchanged, quiver on its side |
| 3 key by parts | when a whole-figure edit fails twice (a hit's lean-back came back airborne on 6 of 6 seeds): a code pose for the planted leg (`nc_pose_key.py`, length-preserving rotation), then close-up edits of one region at a time — lower body, off arm, face — with `nc_closeup.py extract` / `paste` | the pasted window changes 0 px outside itself; the seam is invisible at game size |
| 4 expression | a pain face is a close-up edit of the head pasted into **the key only**; the motion is then rendered from that key | reads as pain at game size; K0's skin and line style |
| 5 motion | local Wan first-last-frame between neighbouring keys, every frame kept; a fast impact may be a 2–3 frame snap instead | the clip reviewer's paired strips: no invented face, no ghost limb, no plate inside the figure |
| 6 ends | first and last cell are K0n_512 exactly | byte-equal |
| 7 build | `nc_build.py <plate> <action> --colour-ref K0n_512 --close-holes 150`; loadout entry with no `angleOverrides`; `finish.sh --no-install` | ring within K0's own ±3; pockets cleared; `nc_hands --self --weapon` PASS; bow clear of the face |
| 8 Unity | `nc_unity.sh <action>` between model jobs, never during one; full and quarter speed beside the base | sent to the user as mp4 |

## Defects and fixes

| Defect | Cause | Fix |
|---|---|---|
| Wan invents a grimace, teeth or shut eyes | Wan K0→K0 has no key to hold the face; worst where the head nearly stops (75% of a 33-frame breathing idle) | give it a key that already carries the face; fewer, faster frames; lead and close the prompt with the face line |
| a whole-head lock slides or wobbles | the lock follows the face inside a static hood | hold the face only in a code-warped clip; a lock tracks ±10 px at most |
| a lean-back key comes back flying, quiver flipped | the edit model rotates the whole figure | key by parts (actions step 3) |
| a redraw of a code key snaps back to K0's pose | K0 as picture 2 pulls the result toward K0 in proportion to how far the pose is | redraw only a cropped region, never the whole posed figure |
| a code pose squashes the body ~8% | vertical displacement knots | length-preserving rotation handles |
| a fist or boot ghosts | FILM across a fast limb | FILM only where limbs are near-still; for a strobing face on a fast frame take only the head region from a FILM midframe, shifted and feathered inside the hood |
| motion lands on every 16th frame | FILM chained x16 then x16 | pick frames by measured travel with a mostly linear ease; `gen.py interpolate` caps the multiplier at 16 and its mp4 output is lossy — save PNGs |
| the bow grips 20 px toward the elbow | the hand core counts the cloak's grey sleeve as hand | `locateCols` round the fist |
| a grey wedge inside the figure | plate shaded darker than 127±10 | `--close-holes`, a second pocket pass at 127±22 within 2 px of transparent |
| the loop holds a beat every cycle | every curve reaches rest before the seam | let the last gust run into frame 0 |

## Machine

- One model job at a time; Unity closed during model jobs and recorded between them.
- `actions/tools/memlog.sh` stops at 8 GB of swap. Stale swap trips it with memory 85% free. On this
  Mac Docker Desktop's VM held most of it — quitting Docker took swap from 9.4 to 5.5 GB and halved a
  Wan segment's time. Quit it before a run (it only runs the Claude Code usage tracker). Restarting the
  model server (`src/LLMs/llms stop` / `start`) frees little.
- A HOLD flag one agent sets for another stalls the queue unless the setter releases it; time Unity
  from the artist's hand-back instead.

## Acceptance — every action, before the user sees it

| What | Pass |
|---|---|
| ends | first and last cell byte-equal to K0n_512 (a loop wraps onto its own cell 0) |
| frames | every in-between frame kept; no held-frame trimming |
| face | two eyes, the K0 style, mouth closed unless the action's key calls for an expression |
| halo and edges | ring within ±3 of K0n_512's own; no specks or plate pockets at 4x on a light background |
| body | neighbouring-frame strips: no swelling, thinning, or cloak detail popping in and out; glow lines keep colour and thickness |
| bow | in the fist on every frame, turning 1.0x with it; step no bigger than the fist's own plus 8 px; never across the face |
| life | the idle visibly breathes and the cloak moves; a hit reads as a hit (face, knee, torso) |
| in motion | the user watches the Unity mp4 at 1x and 0.25x beside the base — the only gate that makes it done |

## What still fails

- **Keys that leave rest by a long way.** Local Qwen draws a grounded lean-back airborne and a bow fist
  as a pointing hand (six tries on the attack draw key); the string hand will not rise to the chin. Key
  by parts is the working route for the hit; the attack draw is unsolved.
- **Wan between an expression key and K0** still invents teeth and a slow ease-in on the way into a
  hit. The next method to prove is a 2–3 frame snap into the key with Wan on the recovery only.
- The hand tracker reads cloak cloth as hand; a cloak-aware hand core does not exist yet.

## Methods that lost

- **Redrawing the outfit over each base frame** (Heavenly Armor, all actions): fine detail differs in
  every drawing, so the armor changes ~1.9x as much between frames as the base does; never approved.
  The worked build is in `heavenly_armor/clothes_fill/` and in this file's git history.
- **Motion copy** (`wan-2.2-animate-replace`): the pose sits 13–20 px off the base and the face is
  invented.
- **Armor keys with video in-betweens taken from the base's poses**: 1.86–2.05x the base's change.
- **A grey mannequin body animated over the base, every outfit to go on top**: rejected on sight; it
  would not have removed the per-frame redraw.
- **Held frames** (8–12 per action): smooth to the eye but "choppy".

## Scorecard — the last step of every run

Append one row to `scorecard.csv` beside this file, then run the `skill-improver` skill on this skill.

`date,character,armor,action,method,frames,takes,head_px_worst,frames_passing,face_fit,size_jump_ratio,frames_hand_fixed,new_fix_tools,minutes,usd,user_verdict,note`

- `head_px_worst`, `face_fit` and `size_jump_ratio` measure a copy of the base; leave them empty for an
  outfit's own animation.
- `frames_hand_fixed` and `new_fix_tools` are the numbers this skill exists to drive to zero.
- `user_verdict` stays empty until the user has judged it; only their word makes it `approved`.
