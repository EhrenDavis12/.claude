---
name: new-armor
description: Give a character a new armor or outfit (the archer's Nightmare Cloak, Heavenly Armor) and animate every action for it — made the way the base armor was made, from the outfit's own approved base image — its idle from the outfit's at-the-ready battle pose by the `idle-breathing-loop` method, every other action from one approved picture of the outfit with the real weapon in hand, the video model making the whole action — so its motion may differ from the base's while the camera, scale, ground line, rest pose and pinned weapons stay the same. Use when the user asks for a new armor, outfit or skin, a new animation for one, or a fix to one (a still-looking idle, a hit that reads as a kick, an invented face, a bow that does not turn with the hand). A same-shape colour change is `recolour-armor` instead.
---

# New armor (its own animation, made the base's way)

**The promise to the user:** each outfit gets its own animation, made exactly the way the base armor's
(Forest Robes) was made: the idle from the outfit's own approved at-the-ready battle pose (its K0, weapon drawn in hand), and every other
action from one approved picture of the outfit, the video model making the whole action. The outfit may move differently from the base — the user's
words: "the animations don't have to be perfect or match what we have for the green cloak they could be
their own thing" — but the idle loops on the outfit's K0 pixel for pixel, the weapon, clothes and face stay the
outfit's own, there is no halo, and the images are clean.

**Why not copy the base's motion:** every way of putting a second outfit on the base's frames redraws
each frame, and the redraw shimmers and leaks the base outfit's parts. See "Methods that lost" — the
user agreed that even a perfect shared grey base body would not make the other armors good.

Cost and time, said before work starts: the idle is two or three paid Seedance K0 → K0 takes,
about $0.18 each. An action is paid Seedance takes, about $0.18 a 3 s take — minutes and
cents, but it needs the user's yes and a dollar cap.

## What the user has already rejected — do not ship these again

| Rejected | Their words | So |
|---|---|---|
| an idle that only breathes (one code breath key, FILM ping-pong) | "looks like a still image ... the cloak doesn't move ... It's just not alive" (face, hands and stance were "perfect") | an idle needs a visible breath **and** cloak motion, "life ... wind", not overdone — watch the base idle for the amount |
| a hit with no pain and a lifted boot | "looks like a small knockback versus he got hurt"; "more like he's trying to kick dirt than he is getting hit" | a hit that reads as really hurt — the take is graded on that by eye; the prompt names the hurt, not each limb |
| a bow that turns less than the hand | "needs a little bit more rotation to follow the hand ... around the Z axis" | the bow turns 1.0x with the located fist; no `angleOverrides` scaling it down |
| held frames (12 picked frames, holds baked in) | "it's choppy ... doesn't matter if it's not glitchy it doesn't look good anyway" | keep every in-between frame |
| one shared grey body that every outfit is drawn over | "These results are just terrible" | each outfit is its own animation |
| a face pasted onto moving frames | "The face is all glichy… slow it down and you will see it" | a face is held only where the head does not move (a code-warped idle) — never pasted per frame; a take that changes the face is replaced by another take |
| a different camera angle | "the death scene created a different camera angle" | own poses are fine; the camera, scale, ground line and facing stay the base's |
| torn edges, holes, loose fragments | "let's make sure these are crisp clean images" | look at 4x on a light background before anything is sent |

## Before any frame is made

1. **The outfit's K0 is approved by the user** (`<outfit>/approve/K0_<outfit>.png`, the
   at-the-ready battle pose with the weapon drawn in the hand, the base's size). It is read-only for every action.
2. **Check K0's own matte first.** The cloak's K0 had ~166 px of transparent pinholes in the grey
   buckle frame and a +15 edge ring of its own; rebuilt frames are solid there, so a pinned end cell
   pops. Measure every later frame against K0's own numbers, in the same resize: a premultiplied box
   1024→512 (`own/K0n_512.png`). A straight-alpha LANCZOS resize reads K0 itself +26 on the ring.
3. **Colour-match to the pinned cell**, not to the approve image (they differ by ~2.4 levels), or every
   seam steps: `nc_build.py --colour-ref <K0n_512>`.

Tools for the archer's cloak are in `local_runs/archer/nightmare_cloak/tools/`; a new outfit copies them
and swaps the mask and K0. Python: `src/Asset-Gen-Framework/.venv/bin/python`.

## Idle — the `idle-breathing-loop` method

The outfit's idle is made exactly as `idle-breathing-loop/SKILL.md` says: K0 is the outfit's
approved at-the-ready battle pose with the weapon drawn in the hand, Seedance K0 → K0 takes
chained into a longer, slightly varied breathing loop. The cloak's code-warp idle (`own/idle/v3/`:
a breath warp and a masked cloak sway on an empty-fist K0, the bow pinned by code) is not used for
a new idle: a relaxed body with a weapon attached by code reads as code (the user, 2026-11-09:
"relaxed position with the weapon somehow glued to his hand in an awkward position looks like
Code"). Its masked, cloak-only sway (`nc_cloak_sway.py`; whole-figure MLS sway brought a new
cloak-edge defect every try) is still the tool if a held moment needs cloth motion added.

## Actions — one picture in, the video model makes the action

Every action other than the idle is made by `base-action/SKILL.md`'s method on the outfit: the
outfit's approved action pose with the real weapon in hand (its relaxed pose for run and run
start; never both), a short action prompt, no end pose and no in-between keys. The game snaps
from the idle into the clip and back.

| Step | What | Check |
|---|---|---|
| 1 brief | the action named in a short prompt and the user's rules (`base-action/SKILL.md`), never from the base outfit's frames | the user's rejected list above is in it |
| 2 takes | start-only hosted Seedance from the outfit's approved picture (`render_remote.py --model seedance`, no `--end`), a few seeds and wordings, the best kept | a solid action; the outfit's own weapon, clothes and face on every frame, no new details |
| 3 build | `nc_build.py <plate> <action> --colour-ref K0n_512 --close-holes 150`; the weapon pinned (`finish.sh --no-install`) only if the model's own fails "same weapon" | ring within K0's own ±3; pockets cleared; a pinned bow passes `nc_hands --self --weapon` and stays clear of the face |
| 4 Unity | `nc_unity.sh <action>` between model jobs, never during one; full and quarter speed beside the base | sent to the user as mp4 |

## Defects and fixes

| Defect | Cause | Fix |
|---|---|---|
| Wan invents a grimace, teeth or shut eyes | Wan K0→K0 has no key to hold the face; worst where the head nearly stops (75% of a 33-frame breathing idle) | give it a key that already carries the face; fewer, faster frames; lead and close the prompt with the face line |
| a whole-head lock slides or wobbles | the lock follows the face inside a static hood | hold the face only in a code-warped clip; a lock tracks ±10 px at most |
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
| idle ends | first and last cell byte-equal to K0n_512 (a loop wraps onto its own cell 0) |
| frames | every frame of the kept window; no held-frame trimming |
| same outfit | the outfit's own weapon, clothes and face on every frame; no new details |
| halo and edges | ring within ±3 of K0n_512's own; no specks or plate pockets at 4x on a light background |
| body | neighbouring-frame strips: no swelling, thinning, or cloak detail popping in and out; glow lines keep colour and thickness |
| pinned bow (fallback only) | in the fist on every frame, turning 1.0x with it; step no bigger than the fist's own plus 8 px; never across the face |
| life | the idle visibly breathes and the cloak moves; an action reads as a solid action |
| in motion | the user watches the Unity mp4 at 1x and 0.25x beside the base — the only gate that makes it done |

## What still fails

- The hand tracker reads cloak cloth as hand; a cloak-aware hand core does not exist yet, which
  matters only when a weapon has to be pinned.

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
- **Drawn action keys with Wan first-last in-betweens** (local Qwen keys, key by parts, a pain face
  pasted into a key): Qwen drew a grounded lean-back airborne and a bow fist as a pointing hand, and
  Wan invented teeth between an expression key and K0; the user ruled pose control out for every
  action.

## Scorecard — the last step of every run

Append one row to `scorecard.csv` beside this file, then run the `skill-improver` skill on this skill.

`date,character,armor,action,method,frames,takes,head_px_worst,frames_passing,face_fit,size_jump_ratio,frames_hand_fixed,new_fix_tools,minutes,usd,user_verdict,note`

- `head_px_worst`, `face_fit` and `size_jump_ratio` measure a copy of the base; leave them empty for an
  outfit's own animation.
- `frames_hand_fixed` and `new_fix_tools` are the numbers this skill exists to drive to zero.
- `user_verdict` stays empty until the user has judged it; only their word makes it `approved`.
