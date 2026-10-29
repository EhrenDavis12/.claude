---
name: effects-overlay
description: Make a body-free effect overlay for a character's action — a hit spark, landing dust, footfall puffs — drawn by code as a short transparent sheet that game code places and plays on top of the body animation (the archer's hit spark), and the drawn particle and trail textures Unity effects use. Use when the user asks for an effect, impact, spark, dust or puff to go with an action, or when an effect shows a dark hole, a pale rim or the wrong size in the battle scene. Not for the body movement itself (`base-action`), the idle (`idle-breathing-loop`) or a background (`parallax-background`).
---

# Effects overlay (code-drawn, placed by game code)

An effect is **never part of a body animation**. The body sheets carry body movement only; an
effect is its own small sheet, made separately, with no body in it, and the game places it (an
anchor on the target, a spawn tick) and plays it on top. So an effect run never touches an
approved body, weapon or scene file.

Effects are **drawn by code, not by a model**: flat fills, no glow, no gradients, a dark outline
matching the character's. That makes them free, deterministic, and rebuilt by one command.

Working folder (archer): `src/asset-animation-demo/local_runs/archer/effects/<effect>/`. The hit
spark there is the worked example — copy its scripts and change the shapes:

| Script | Job |
|---|---|
| `hit_spark_key.py` | the peak key: three code-drawn candidates `K1_A/B/C.png` + `K1_candidates_sheet.png` + `measure.json` |
| `hit_spark.py` | the sheet `f0..f5` (6 × 512, one row, 16 fps, no loop), `_sheet.json`, `_measure.json`, `_review.png`; asserts f1 equals the picked key pixel for pixel |
| `hit_spark_preview.py` | TEST preview in battle scene 1: strips per shot, 1280 mp4, quarter-speed mp4, 2× target crop, `preview/preview_log.json` |
| `hit_spark_check.py` | timing and composite checks on `preview_log.json`; prints PASS / FAIL, never forces |
| `hit_spark_edgecheck.py` | edge ring on the scene-1 ground and the cave still: no pale rim |
| `<effect>.entry.json` | the rebuild commands, the settings found by trial, the anchor, `installed` |

Python: `src/Asset-Gen-Framework/.venv/bin/python`. Every script runs with no arguments.

## Before starting

- **Take an md5 baseline of the approved files** the preview reads — the installed body and
  weapon sheets, the scene stills, `scene1_preview.py` — and check it again at the end. Nothing
  approved may change.
- The mode is local and costs nothing: no model call is made. A run has taken about 40 minutes.

## Steps

1. **Peak key first.** Draw three candidates of the peak frame in the brief's colours
   (`*_key.py`). The key reviewer picks one; the sheet's peak frame is that key, asserted equal.
2. **Draw it the house way**: draw at 4×, reduce with premultiplied alpha, save straight RGBA.
   Flat fills only — tip colour, body colour, a small core — and a **~3 px dark outline grown
   outward** with round joins, in the character's own outline colour. No glow, no soft halo.
3. **Build the sheet** (`<effect>.py`): a short burst — a small flash, the peak, a broken-up
   frame, shards, smaller shards, specks, then nothing. Every number is in the script; no
   randomness.
4. **Measure after the outline**, not before: tip angles (target ≥ 30°), bbox against the idle
   height, centroid drift on the early frames, border clearance, last-frame area against the
   peak. The outline blunts tips, so a tip measured on the raw shape lies.
5. **Preview inside battle scene 1** (`scenes/battle1/preview_scene1/`), never on grey alone, with
   several shots: same row, diagonal to the far back row, and the enemy side (mirrored). Play the
   *installed* action sheets unchanged; the effect spawns on the target's anchor on the arrival
   tick and is scaled by the target's row scale. Label every output TEST. A hit cuts cleanly only
   when the target is on idle frame 63, 0 or 1 at its start: slide the attacker's start to fit,
   never the target's idle phase. Attack and hit frame 19 return to idle frame 0 only. Compose
   each sheet frame once and cache only the resized frames the shots use — caching everything
   ran to about 5 GB.
6. **A full-scene preview needs a varied crowd.** The user wants the idles visibly varied: every
   figure starts its base idle at its own random frame, and head turns and weight shifts are
   peppered in often — about 2–3 extras per figure per 36 s (8 over 24 s for 30 figures was too
   few to notice, rejected). Head turns read at 1280; a weight shift peaks at about 3 px against
   about 2 px of idle sway, so shifts barely read and head turns carry the variety. Seed the
   schedule so it rebuilds the same. Brief the "at most N figures in an extra at once" cap as
   about half the crowd (18 of 30): a cap of 16 for 30 figures, 6 shots and 2 extras each over
   36 s cost about 25 min for 3000 attempts and failed every time. A re-run starts its schedule
   search at the level the last run reached. Keep the search log beside the outputs, not in
   scratch. The background layers themselves are `parallax-background`.
7. **Composite every effect frame over the target in the scene** and run the checks
   (`*_check.py`, `*_edgecheck.py`). The cave background still is
   `scenes/battle2/preview/stal_TEST_still.png` — the approved one; `wall2/still3_C.png` is not.
8. **Review**, then show the user the 1280 mp4 and the quarter-speed mp4, labelled TEST. A
   reviewer waiting on a long job waits on that job's own completion, never on a timer.

## Intro and scroll scenes

- **A battle intro (armies run in) is very quick**: the user asks for about 2 s from the first
  frame to everyone idling — 14 s and 8.5 s both felt sluggish. Tap-to-skip is game code, not
  part of the clip. **Its floor is the stop sheet plus the skid-start spread**: the Archer's run
  stop is 72 ticks, and the spread of skid starts that idle-frame variety needs is 42–45 ticks,
  so about 3.25 s with that stop. Say so before rendering; under it needs a shorter stop sheet
  or less variety, the user's call.
- **The planner computes the skid-start table** and the search starts from it: random annealing
  misses a fit that tight, and the seeded table was found on the first attempt at level 0.
  Get the speed by starting the armies near the meeting point, not by faster run art: the run
  speed is fixed by the sheet, so a shorter intro comes from less camera travel and a shorter
  hold, never a faster scroll. Hold about 1 s after the last figure settles, inside that total.
- **A shorter ease needs its smoothness limit scaled**: peak slope = 1.5·G0/(ease·fps). A limit
  set for a long ease fails a short one that is smooth.
- **A crowd "neighbour" no-lockstep rule covers the outer pair in a row (c0–c2) and diagonals**,
  not only figures one column apart, or a looser search level hides lockstep there. Frames half a
  run cycle apart (8 of 16) read as nearly in step, and a phase-difference rule cannot see it —
  ban a run-phase gap of exactly 8. A strict 3-tick skid ladder keeps same-column figures two
  rows apart only 1 frame apart, so the rule covers column pairs two rows apart as well.
- **Spread the left army's final idle frames across the whole idle cycle**, not within 15 frames
  of each other, or the crowd lands in near-step.
- Brief contact slip as a share of the **run speed**, not of the ground speed: the ground-speed
  ratio blows up as the camera eases to 0.
- Encoded with one I-frame (keyint = frame count), the keyframe-pulse check is just "I-frame
  count = 1".
- `footspeed.py` needs a `.sheet.json`, which the installed run sheet lacks — write one beside it
  first.
- A ground-locked army stops later than the camera unless every skid start ends by
  T_land − 1.0 s.

## Shaping an effect (studio practice)

- **Dust and footfall**: one horizontal and one upward sheet, each small and big, mirrored for
  the other side — not one sheet per action.
- **A slash**: one crescent, thick at the tip and thin at the tail, laid along the tracked
  weapon-tip arc, at its peak for 1–2 frames.
- **Hitstop and the white flash are game code**, not sheet frames; preview them together with the
  effect.
- **Vary a hit spark** by rotating or mirroring it per hit: free, and it passes every spark
  check.

## Particle textures for Unity

Particle and trail textures for `unity-effects` are made here too: one PNG per family plus a
white copy for tinting, each with its `.json`, built by code and finished by Qwen-Image-Edit
only where painting helps (dirt, smoke, ice, fire). The worked example is
`effects/particles_v1/` — `build_code.py`, `model_blockouts.py`, `finish_model.py`,
`contact.py` (light and dark contact sheets), `particles_check.py` (PASS / FAIL per row, no
arguments).

- **Qwen drifts neutral greys to sky-blue**, and the resize blends quantised tones back: remap
  the tones *after* the resize, then measure the grey's hue.
- **Qwen adds cartoon faces to round clumps.** "No face" in the prompt makes it worse; pits and
  chips cut into the blockout remove it.
- **A slash or trail strip has its thick end at u = 0**, overriding edge padding there, or a gap
  shows at the cap.
- **A 64 px snowflake carries one branch pair per arm, at about 0.6 r.** Finer detail turns to
  mush and pinholes.
- **The tip detector reports "no tip found"** rather than passing a cell it could not measure.
- **Tint samples on the contact sheet match the sprite's own hue**, or the user reads the tint as
  its colour.

## Defects and their fixes

| Defect | Cause | Fix |
|---|---|---|
| A black disc in the middle of a frame, in motion | a see-through hole inside the shape shows the target's dark clothes; a grey review sheet hides it | no hole inside any effect shape — fill the centre opaque (the spark's f2 has an opaque yellow centre inside a dark ring); check centre alpha on the scene composite of the filled-centre frames |
| Tips blunter than measured | angles measured before the outline was grown | measure on the final RGBA |
| A pale rim on dark ground | semi-transparent edge pixels lighter than the outline | edge colour = outline colour; `*_edgecheck.py` composite ring ≤ max(background, outline) |

## Acceptance — before the user sees it

| Check | Pass |
|---|---|
| Centre of each filled-centre frame (spark f0–f2) on the scene composite | alpha ≥ 0.999 over 7×7 px — no hole; the later shard frames are empty in the middle by design and are not checked |
| Edge ring | straight edge colour = outline colour; composite never lighter than both background and outline |
| Tip angles, after the outline | ≥ 30° on every frame |
| Timing in the scene | effect f0 on the arrival tick = target hit frame 0; each effect frame lands with its hit frame |
| Approved files | md5 baseline unchanged |

## What still fails

- `scene1_preview.py` is not importable: the preview `exec`s its source with string replacements
  (and redirects its measure file to a scratch path written into the preview script — change that
  path to the current scratchpad before running). A shared scene-setup module is owed; ask
  `annie-tool-writer` for it the next time an effect is previewed.
- The spark check scripts build scene paths from their own folder depth, so a copy run from
  another folder needs a path fix. Keep the GROUND / CAVE paths in one constant or an env var
  when copying them.
- Effects not made yet: death landing dust, run footfall puffs. Same method.

## Scorecard — the last step of every run

Append one row per pass to `scorecard.csv` beside this file, then run the `skill-improver` skill on
this skill.

`date,character,action,frames,passes,key_edits,inbetweens_local,inbetweens_remote,hand_fixes,new_tools,minutes,usd,user_verdict,note`

- `action` is `fx_<effect>_v<n>`; `frames` counts body frames made, so it is `0` for an effect.
- `hand_fixes`, `new_tools`, `passes` and `minutes` are what this skill exists to drive down.
- `user_verdict` stays `pending` until the user has judged it; only their word makes it `approved`.
  When the user rules, backfill `user_verdict` on that row — a `pending` left behind reads as
  still waiting.
