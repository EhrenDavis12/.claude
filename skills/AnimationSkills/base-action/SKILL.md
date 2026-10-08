---
name: base-action
description: Make a new one-shot or looping action animation for a character on its base armor — key poses, in-betweens, the body sheet, then every weapon pinned to the tracked hand (the archer's hit, defend, attack, run, run start, run stop and death on Forest Robes). Use when the user asks for a new action, a new version of one, or when an action pops at the join to the idle, invents a face, loses the weapon from the hand, or reads as "nothing happening". Not for the idle or its extras (`idle-breathing-loop`), a recolour (`recolour-armor`), or the same action on another armor (`new-armor`).
---

# Base action (key poses, in-betweens, weapons in the hand)

An action is drawn once, on the base armor with an **empty hand**; the weapons are pinned onto the
tracked fist afterwards, so one body sheet serves every bow and every recolour. Every other armor
copies this sheet frame for frame, so this is the animation that has to be right first.

Working folders (archer): `src/asset-animation-demo/local_runs/archer/actions/` (keys, clips, body
sheets; shared tools in `tools/`) and `.../archer/loadout/` (hand track, bows, checks, install).
Python for post and analysis: `src/Asset-Gen-Framework/.venv/bin/python` (`.venv python` below).
The long reference for every registry key and flag is `actions/README.md` — read it when a step
below names a key.

## Before starting — say this to the user

- **An action has taken 2.3 passes on average** (attack 5, run stop 5, hit 2, death 2), and a pass
  made locally averages about 1 h 55. A local key edit is ~8 min, a local 33-frame in-between
  18–23 min; the same in-between on Replicate is ~30 s and ~$0.05. Quote these, not a hope.
- **Modes** (`local` / `fast` / `100fast`) are in `idle-breathing-loop/SKILL.md`, "Three modes"; the
  scripts here call its `scripts/gen.py`, so `GEN_MODE=fast <script>` moves the slow jobs off the Mac.
  The user has said yes to Replicate for the in-between while they are iterating at the desk — report
  the spend. Any other paid call needs their yes; unattended runs stay local.
- **The base idle is approved** and the bow-less base key exists (`approve/K0_forest_nobow.png`, made
  by `tools/make_k0_nobow.py`). An action starts and ends on the idle's frame 0.
- **Basic weapon and basic armor first.** No other bow, recolour or armor is built from an action the
  user has not accepted.
- **Local model jobs run one at a time**, each wrapped in `tools/memlog.sh "<what>"` and
  `tools/memlog.sh after "<what>"`. Exit 1 means stop: swap is over 8 GB. No local in-between over
  33 frames. Never let key edits and in-betweens share the queue.
- The Character Chart cell is set as the state changes — `idle-breathing-loop/SKILL.md`, "Keep the
  Character Chart current".

## What the user judges

| Rule | Means |
|---|---|
| the body must really move | a clean, subtle result reads as nothing happening. Hit: a stumble or lean back, not a wince. Measure hip and hand travel; do not trust "checks pass" |
| the weapon behaves like a real object | attack: the hand comes to the string at its centre, then pulls; the bow bends on the draw and snaps back; no arrow; slow draw, quick release; a small chest puff |
| it returns to the idle pose | so clips stitch. Death is the exception: it holds its last frame |
| the face is the base key's face | same eye style, shape, size; only the pose changes |
| knees bend outward only | standing to horse stance; never ask for inward knees in a prompt |
| a run is three clips | start (short, idle into the loop's frame 0), loop, stop (back to idle with a little flare: a skid, some dust) |
| a held object stays in one hand | on a side-on run it passes **behind** the body, at the angle of the fist |
| send mp4, never GIF | and label a test clip loudly as a test — an approved action is not touched, and nothing that could pass for a new version of it is sent |

## Steps (from `actions/`)

**1 — Keys.** Whole-body edits of the bow-less base key, one seed at a time. Copy `hit/make_key.sh`
to `<action>/make_key.sh` and change the wording; name sides as the picture's ("the arm on the right
of the image").

```
<action>/make_key.sh <seed> [prompt-file]
.venv python tools/finish_key.py <edit.png> <key.png>          # matte + colour match to the base key
.venv python tools/pose_guard.py --hit|--guard|--attack|--knock|--run <key.png> ...
.venv python tools/key_candidates.py <action>/preview/key_candidates.png "label=path" ...
```

Look at every result before the guard's numbers mean anything. Budget about six edits a key; past
that, build the key by code from one that works (see the defect table).

**2 — In-betweens.** First-last-frame, key to key, 33 frames, on a grey plate.

```
.venv python tools/plates.py key <key.png> work/<name>_plate.png
<action>/render_<action>.sh <seed>                              # copy hit/render_hit.sh
.venv python tools/render_remote.py "<prompt>" --start work/a_plate.png --end work/b_plate.png \
      --seed 7 -o <action>/work/<name>_remote_s7.mp4 --take 33 --keep-raw      # the same call, hosted
.venv python tools/contact.py <clip.mp4> <out.png> --step 2 ; .venv python tools/measure.py <clip.mp4>
```

Look at the contact sheet of every clip. Hosted suits a short, plain move between two close poses,
and three seeds cost less time than one local render. A long move between far-apart poses (a drop to
the floor) is rendered locally: the hosted model must fill 81 frames and overshoots, then comes back.
The end pose takes over only in the last tenth of a clip unless the prompt describes it. The return
to the idle is usually the out-bound clip reversed.

**3 — Compose and build.** A per-action `compose*.py` picks frames and sets the timing (copy
`hit/compose2.py`): snap out, hold, eased return. It writes the plate; `build_action.py` mattes it,
colour-matches, cuts 640 → 512 cells and records the recipe in `loadout/actions.json`.

```
.venv python tools/build_action.py <plate> <action> "<Label>" --fade 0 --register [--loop]
      [--drop-grey-pockets] [--first-idle|--first-cell a:i] [--last-idle|--last-cell a:i]
.venv python tools/build_action.py <action>                     # a rebuild: every option from the entry
```

Effects drawn onto the finished sheet (dust, a still tail) go in the entry's `postSteps` and run only
through `tools/poststeps.py`, never by hand — that is what stops dust being drawn twice.

**4 — Weapons, checks, install** — one command, 30–76 s:

```
../loadout/finish.sh <action> [--no-install] [--no-locate] [--force]
```

It tracks the hand, pins the bows, runs the checks for that action, installs and writes the review
files; it stops at the first failure and before install on any failure verdict. Use `--no-install`
until the user has seen it. An action another one starts or ends on (run, for run start and run stop)
takes those along. After any change to the body, run it again: the hand track and every weapon sheet
depend on the body. The full `pin.py` / `checks.py` are only for a change to shared code or the idle.

**5 — Watch it, then show it.** The review mp4 at full and quarter speed, beside the previous
version; for a run, the whole chain (`../loadout/review_chain.py`). A sheet judged from stills is not
judged.

## Defects and their fixes

| Defect | Cause | Fix |
|---|---|---|
| key raises the wrong arm, mirrors the figure, loses the quiver, adds a ground shadow, speed lines or a jump | the edit model re-poses freely | reword and take another seed; if it draws a weapon in the empty hand, a second "remove it" edit of that result |
| the edit model cannot make the pose at all (a lean-back skid, legs passing in a stride) | outside what it draws from this key | build the key by code from one that works (`run_stop/make_brake_key.py`, `attack/lock_aim.py`, `attack/puff.py`), or edit a close-up crop and paste it (`attack/v4/fist4.py`) |
| in-between opens the mouth, blinks, shuts an eye | the video model invents faces | `tools/patch_mouth.py` (`--box eyes --only <frames>` for a blink); `tools/patch_face.py` when the head travels; or skip those frames |
| a ghost limb on one frame | the model's own | drop the frame; bridge with FILM only between two consecutive good frames — across four frames or a real rotation FILM ghosts too |
| the clip keeps doing the old motion (keeps running, never skids) | the end pose is too far for one segment | make the first frames by code (`run_stop/lead_in.py`) and render only the settle |
| a ghost hand on the last frames | a crossfade onto the idle over a pose that has not arrived | `--fade 0`, and make the tail arrive: a short hosted render from the last good frame to the base key (worst step 49 px → 22 px) |
| earlier frames change by a few grey levels after a recompose | re-encoding an mp4 of another length | the compose script writes the plate as `.npy` (`run_stop/compose_skid4.py`) |
| a loop drifts in scale or position | the model's framing wanders | pick the best-closing pair with `tools/runstat.py <clip> --loop`, stabilise head x and ground line (`run/compose_run.py`) |
| grey wedge between limbs | an enclosed pocket of plate | `--drop-grey-pockets` |
| the tracker loses the hand (bracer, crossed arms, a far swing) | fist changes shape or leaves the search band | hand-label `locateSeeds`, widen `locateCols` / `locateRows`, set `angleOverrides` in the entry |
| bow lies flat or whips | the bow turns 1:1 with a forearm that swings wide | `maxTurnDeg`, or an eased `angleOverrides` |
| bow floats beside the body, or swaps hands on a run | the pinned fist is hidden behind the torso | `hiddenFrames` + `weaponBehind`; seeds from `run/far_arm_seeds.py`; check with `../loadout/checks_behind.py` |
| bow hangs in the air after a fall | rigid pin to a limp hand | `bowRelease` in the entry |
| fist art does not sit on the handle, or the face shows through the bow | the rest-fist cut-out is the wrong drawing | `gripShift`, `fingerMask` |
| `install.py` refuses | a hand track older than its body or than shared code | `finish.sh <action>`; after editing `pin.py`, `newaction.py <a> --locate` for each action, then a full `pin.py` |
| swap still over 8 GB after a job | the server holds the models (Unity open makes it worse) | stop local model jobs; `GEN_MODE=fast`, or close Unity |

## Acceptance — before the user sees it

| What | Pass |
|---|---|
| key | `pose_guard.py` PASS, or each REJECT line explained by the pose |
| join to the idle or the linked action | checks 8n "within 0.5 px / 0.5 deg" on the first and last frame, every bow |
| hand found | check 8o reports no frame with the hand or the string hand missing |
| checks | `finish.sh` prints no failure verdict; `--force` is never how an action ships |
| steps | no step above 3× the clip's mean (`tools/measure.py` flags it); a loop's seam step no larger than its median step |
| travel | hips and hand visibly move — numbers stated next to the previous version's |
| face | the base key's face on every frame; no invented expression |
| rebuild | `build_action.py <action>` alone reproduces the sheet |
| in motion | watched at 1x and quarter speed as mp4 |

## What still fails

- **The first pass is usually too subtle or mechanically wrong** — that is where the 2.3 passes come
  from. Read "What the user judges" against the key before rendering anything.
- **The edit model cannot draw some poses**, and the video model's faces and extra limbs are a seed
  lottery. Every action so far has needed a code-made key, a face patch, or both.
- **Hand seeds are labelled by hand** on most actions.

## Scorecard — the last step of every run

Append one row per pass to `scorecard.csv` beside this file, then run the `skill-improver` skill on
this skill.

`date,character,action,frames,passes,key_edits,inbetweens_local,inbetweens_remote,hand_fixes,new_tools,minutes,usd,user_verdict,note`

- `passes` — how many times the action has been shown to the user, this one included.
- `hand_fixes` — anything done by hand that these steps did not tell you to do; `new_tools` — scripts
  written mid-run. These, `passes` and `minutes` are what this skill exists to drive down.
- `user_verdict` stays empty until the user has judged it; only their word makes it `approved`.
