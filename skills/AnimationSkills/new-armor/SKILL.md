---
name: new-armor
description: Give a character a new armor with a new shape (the archer's Heavenly Armor — winged pauldrons, white hood, short cloak) and re-create every one of its animations so they are identical to the base armor's — same position, same movement, same face, same camera, same scale, frame for frame — so the weapons pinned to the base still sit in the hand. Use when the user asks for a new armor, outfit or skin that changes the silhouette, or when an armor's animation drifts from its base (different expression, size jump, arm doing something else, armor details changing mid-clip). A same-shape colour change is `recolour-armor` instead.
---

# New armor (same animation, new outfit)

**The promise to the user:** an armor animation is the base animation wearing other clothes. Same frame
count; on frame *i* the head, hands, feet and chest are where the base has them on frame *i*; the face
is the base's face. People pay for armors, so this is the skill that has to be reliable — and it is not
yet. Read "What still fails" before promising a date.

Working folders (archer): `src/asset-animation-demo/local_runs/archer/heavenly_armor/` (the armor's own
frames; `motion_copy/` holds the tools) and `.../archer/loadout/` (bows, checks, install). Python:
`src/Asset-Gen-Framework/.venv/bin/python`. Paid calls need the user's yes and a cap in dollars.

## Before any armor frame is made — three gates

1. **The base animation is approved by the user.** An armor copies its base frame for frame, so every
   later change to the base throws the armor copy away. The Character Chart says which base cells are
   Done; anything else is a moving target. If the user wants the armor anyway, say what it will cost
   when the base changes.
2. **The armor has an approved reference set, not one picture.** One front view is why bracers, wings
   and the quiver get re-invented whenever the body turns. Before the first animation, make and get
   approved: front (the base idle key re-dressed), side-on, back, and one with the arms raised.
3. **The armor's idle is made by the same method as its actions.** A hand-made idle key is drawn thinner
   than the model's frames, and every action that starts and ends on it jumps in size at both ends.

## The method that works today: motion copy

A video model (`wan-video/wan-2.2-animate-replace` on Replicate, ~$0.05 per second of clip at 720p, ~1
minute) re-draws the character from the armor reference while following the base video. It holds pose,
timing and camera. It does **not** hold the face, and it re-invents what it cannot see.

Per action, from `heavenly_armor/motion_copy/`:

| Step | Command | What to check |
|---|---|---|
| 1 driver | `mc_prep_crop.py <a>` (base body frames on grey, cropped in to the character so the model gets ~1.3× the pixels; anything that would be copied as an object is removed first — dust, a quiver's contrasting arrows recoloured to the armor's) | the driver is the base **before** its effects (dust, sparks) |
| 2 model | `run_model.py wan-video/wan-2.2-animate-replace ... seed=11`, then a second seed | two takes; a third only if both fail the numbers |
| 3 pick | `mc_cut.py` + `compare.py` + `pairs.py` | see "Picking a take" |
| 4 recipe | `mc_recipe.py <a> <take> --fade 0 --head 0 ...` | writes the action's entry; every option of the base's own track is copied, not retyped |
| 5 build | `../actions/rebuild_hv.sh <a> --no-install` | replays everything with no paid call |
| 6 judge | `mc_accept.py <a>`, `mc_flicker.py <a>`, then **watch it** | see "Acceptance" |
| 7 install | `../../loadout/install.py --only <a> --frameset heavenly` | always `--only`; a bare install ships every half-built action |

### Picking a take

- Score against the base **without its effects** (`COMPARE_FOREST_DIR`), or dust counts as a pose error.
- Use **head position and the outline's edges**, not the centre of mass: a white hood and short cloak
  against a wide brown cloak move the centre 10–40 px on frames where the pose is identical.
- No crossfade at the joins. Measure the first and last step against the base's own; only act when the
  armor's is clearly above it.

### The face

The model's face is never shipped. `mc_face.py` puts the base frame's face onto the armor frame
(`faceFollow` — work in the base face's own coordinates — is on for every action whose head moves more
than 10 px). It is the weakest step: the face is resampled, so it is soft, and the fit is ~0.75–0.85.
Always rebuild before re-running it; it edits the sheet in place.

### Things the model re-invents, and what removes them

| It draws | Remove with |
|---|---|
| its own expression (smile, shut eyes, open mouth) | `mc_face.py` |
| the base outfit's coloured parts as loose objects | recolour them in the driver (step 1), not afterwards |
| the base's dust or debris as specks | drive from the pre-effects sheet; add effects back as post steps on the base's frame numbers |
| a raised arm where the base's arm hangs under a cloak | the model's, not the driver's — more seeds do not fix it; re-draw those frames (in-between from the idle, then a single-image edit) |
| a glow or smear where an arm crosses the chest | single-image edit of that frame; a two-image "look + pose" edit ignores the pose |
| grey left inside the hood or between limbs | `mc_hoodfill.py`, `mc_hazefix.py`, `mc_despeckle.py` |

## Acceptance — every action, before the user sees it

| What | Pass |
|---|---|
| frame count | equals the base's |
| head position vs the base, same frame | within 8 px on every frame |
| outline edges vs the base | within 15 px, or explained by the outfit's own shape |
| first and last frame | byte-equal to the cell they join (idle 0, or the linked action's frame) — `install.py` refuses otherwise |
| join step | no larger than the base's own first/last step |
| face | the base's expression on every frame, checked on the paired face sheet at full size |
| armor identity | hood, gem, pauldrons, wings, bracers, cloak, quiver the same on every frame where they are visible |
| weapons | every bow in the fist and the string at the string hand, on the frames the base uses |
| **in motion** | watched in the Unity Loadouts scene at 1x and 0.25x beside the base. A sheet judged from stills is not judged |

## What still fails — the honest state

- **Faces are soft and sometimes smudged**, because they are warped and pasted.
- **Size jump at the first and last frame** on every action that joins the hand-made idle.
- **Armor details drift** on turned or crossed poses (plain bracers on edited frames, a wing that comes
  and goes).
- **Every action has needed at least one fix nobody had needed before.** Until that stops, the recipe
  is not finished.

## The next method to prove: repaint only the clothes

Keep the base video and mark face, hair and skin as "do not touch", so those pixels stay the base's —
face, position, camera and scale are then the base's by construction instead of by repair. The model
fills only the clothing region from the armor reference (a masked video fill with a reference image).
Untested here. The open risk is shape: parts that reach outside the base outfit's outline (wings, a
bigger hood) need the mask grown, and it is not known how well the design holds. Prove it on one
action, beside the motion-copy result, scored on the table above, before changing the method.

## Scorecard — the last step of every run

Append one row to `scorecard.csv` beside this file, then run the `skill-improver` skill on this skill.

`date,character,armor,action,method,frames,takes,head_px_worst,frames_passing,face_fit,size_jump_ratio,frames_hand_fixed,new_fix_tools,minutes,usd,user_verdict,note`

- `frames_hand_fixed` and `new_fix_tools` are the numbers this skill exists to drive to zero.
- `user_verdict` stays empty until the user has judged it; only their word makes it `approved`.
