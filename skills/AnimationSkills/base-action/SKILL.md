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
Other classes work in `local_runs/characters/<class>/work/<action>/`, with class tools in
`local_runs/characters/tools/` (`ch_measure.py`); there is no per-class `measure.py`, so a clip is
measured with `loadout/clipmeasure.py`. A floor clip's box, hood drop and ground sink come from
`characters/rogue/work/death_v7/acc.py <take.mp4> <ground_row>` (reads the take's `_f/` frames);
the `measure.py` in older death folders has a hard 1.6 row scale and misreads any other plate.
System `python3` has no PIL, so every script here runs on the `.venv python`.
Python for post and analysis: `src/Asset-Gen-Framework/.venv/bin/python` (`.venv python` below).
The long reference for every registry key and flag is `actions/README.md` — read it when a step
below names a key.

## Before starting — say this to the user

- **An action has taken 2.3 passes on average** (attack 5, run stop 5, hit 2, death 2), and a pass
  made locally averages about 1 h 55. A local key edit is ~8 min, a local 33-frame in-between
  18–23 min; the same in-between on Replicate is ~30 s and ~$0.05. Quote these, not a hope.
- **Modes** (`local` / `fast` / `100fast`) are in `idle-breathing-loop/SKILL.md`, "Three modes"; the
  scripts here call its `scripts/gen.py`, so `GEN_MODE=fast <script>` moves the key edits off the Mac
  — but **not an i2v render**: for that `gen.py` silently runs local. A hosted clip goes through
  `tools/render_remote.py` only. The user has said yes to Replicate for the in-between while they are
  iterating at the desk — report the spend. Any other paid call needs their yes; unattended runs stay
  local.
- **The base idle is approved** and the bow-less base key exists (`approve/K0_forest_nobow.png`, made
  by `tools/make_k0_nobow.py`). An action starts and ends on the idle's frame 0.
- **Floor poses (death, a fall): the planner asks the user's open questions about the leg
  arrangement before the first edit**, not after a spent budget — a death once took 17 edits on a
  lie the user had not settled.
- **Basic weapon and basic armor first.** No other bow, recolour or armor is built from an action the
  user has not accepted.
- **Local model jobs run one at a time**, each wrapped in `tools/memlog.sh "<what>"` and
  `tools/memlog.sh after "<what>"`. Exit 1 means stop: swap is over 8 GB. No local in-between over
  33 frames. Never let key edits and in-betweens share the queue.
- **Under the queue runner, resuming an agent with `SendMessage` can fail** (no transcript): continue
  with a fresh dispatch and a hand-off brief instead.
- The Character Chart cell is set as the state changes — `idle-breathing-loop/SKILL.md`, "Keep the
  Character Chart current".

## What the user judges

| Rule | Means |
|---|---|
| the body must really move | a clean, subtle result reads as nothing happening. Hit: a stumble or lean back, not a wince. Measure hip and hand travel; do not trust "checks pass" |
| no anticipation — action and follow-through only | every action has three parts: anticipation, action, follow-through. The anticipation is what makes an action feel slow, so, as AAA games do, it is cut. The action starts on its already-wound-up pose: idle cuts straight to it, with no in-between from the idle and no wind-up key to draw. Brief, key and judge the action and the follow-through; that is where the time goes. That cut is the only snap: the action and the follow-through back to the idle play smooth, with enough frames, and "snap" is never a reason for few frames there |
| the whole body moves together | nothing moves on its own: when the head turns, the hood, shoulders and torso turn with it. A single part sliding on a still body is rejected — fluid and natural is the point |
| the weapon behaves like a real object | attack: no draw — it starts at full draw with the bow bent and the hand at the string's centre, then a quick release, the bow snaps back, and a follow-through; no arrow; a small chest puff |
| it ends near the idle pose | the game snaps back to the idle, and with no anticipation that snap reads as expected, not jolting. So the last frame need not match the idle frame exactly; never spend renders chasing an exact match. Death is the exception: it holds its last frame |
| it stays on its spot | his place comes back even when his pose need not. Anything that moves him off his spot — a push-back, a lunge, a stumble — moves him back to it by the last frame; a hurt that leaves him standing where the hit pushed him is a reject. A death lies down where he stood. Make a real attempt in the generation itself — prompt, start and end keys, plate placement — so the take is already in place; re-centring whole frames by code afterwards is a fallback, not the plan, because every clip that needs it is an edit the user did not want to pay for. A knock-back that must end in place is briefed with a stepping return by default — a bridge render to the idle key at the start x — because easing a whole-frame offset back over a standing tail always skates. Only he and his own weapon are in the frame: no other person (enemies come from the game), no effect of any kind — particles, sparks, dust, smoke, glow, blood — and no projectile, not even an arrow in flight. Effects and projectiles are made separately and laid over in the game |
| the AI gets the keys in order | give the video model the start image, and the approved keys in the order they play, so it makes the in-betweens — and a loop where one is needed — itself |
| the face is the base key's face | same eye style, shape, size; only the pose changes |
| knees bend outward only | standing to horse stance; never ask for inward knees in a prompt |
| a run is two clips | the idle cuts straight into the loop, then a stop back to idle with a little flare (a skid; dust is a separate effect). No run start is made for now |
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

**What the local edit model will not do from the base key — plan another start picture before the
first edit, because no wording gets there:**

- **swap which arm does the action** against the base key's arm roles (a mirror-swap key). Every
  take used the base key's own stabbing arm. A swapped key needs a start picture whose arms are
  already in those roles — the planner names it in the brief.
- **lower the head** — a kneel or crouch started from the standing key is drawn at full standing
  height. Start from a picture whose head is already low (an approved sit or kneel plate).
- **change the legs while the upper body is kept "exactly"** — that pins the waist and bends only
  the thighs. Asked to throw the upper body back, it does, and copies the base key's legs.
- **both weapons forward with running legs** — it adds a third arm. Start from a pose reference
  whose arms are already right, back arm hidden behind the body.
- **a chibi floor pose (sit, lie)** — it draws its own sit or lie and floats the body with only a
  hand on the ground. Pin the ground contact on the heel, bottom or hood, never a hand; a
  spread-knee lie failed 17 of 17.
- **step a hurt pose back** — with leg edits spent, a knocked-back hit needs a start picture whose
  legs are already stepped back: a user sketch, or another character's pose as picture 2 only, its
  facing checked.

**Tidy edits on a picked frame** (a clip frame used as a key): the picked frame alone is picture 1.
Adding the base key as picture 2 snaps the figure back to standing.

Prompts describe only what the base key shows: on the rogue, no "black boots with grey cuffs" (its
boot tops are black, and the cuffs get invented). Leaning a hooded head back swells the hood.

Look at every result before the guard's numbers mean anything. Budget about six edits a key; past
that, stop and report it blocked; the run moves to the next job. Paid models (`tools/edit_remote.py`,
`tools/render_remote.py`) only with the user's say-so for that job and a dollar cap. **Never
build a body pose by code** — cut pieces, warps, slides and limb rigs all read as a paper puppet
and were rejected on the rogue's attack and run ("not how a human moves"). Code only attaches a
weapon or prop to a tracked point.

**Redrawing one limb on an approved pose** (a class battle stance's weapon arm, until a stance
recipe exists): erase the limb to plate, then a whole-figure edit with an existing drawing whose
arm already looks natural as picture 2 (a rejected stance, the design final). Composite only the
limb region onto the approved body, swap the weapon by code (the approved head scaled, a straight
handle on the fist's axis, butt 10–30 px past the fist), and after the finish re-matte put the
approved body's pixels back outside the limb region so the body diff is 0. Before writing a pose
into a brief, check it fits: fist point + handle length + head size inside the 16 px margin and
above the ground row.

**2 — In-betweens.** First-last-frame, key to key, 33 frames, on a grey plate.

```
.venv python tools/plates.py key <key.png> work/<name>_plate.png
<action>/render_<action>.sh <seed>                              # copy hit/render_hit.sh
.venv python tools/render_remote.py "<prompt>" --start work/a_plate.png --end work/b_plate.png \
      --seed 7 -o <action>/work/<name>_remote_s7.mp4 --take 33 --keep-raw      # the same call, hosted
.venv python tools/contact.py <clip.mp4> <out.png> --step 2 ; .venv python tools/measure.py <clip.mp4>
```

`contact.py` breaks on 1280×720 frames; until `annie-tool-writer` fixes it, cut those contact sheets
with the rogue hurt's `local_runs/characters/rogue/work/hurt/v9/sheet_R1.py`.

Look at the contact sheet of every clip. Hosted suits a short, plain move between two close poses,
and three seeds cost less time than one local render. A long move between far-apart poses (a drop to
the floor) is not rendered hosted first-last: the hosted model must fill 81 frames and overshoots,
then comes back (a hosted start-only death works — below).
The end pose takes over only in the last tenth of a clip unless the prompt describes it.
First-last between a wound-up key and a lunge key finishes the stance change before it rotates the
arm, at 33 and at 17 frames, whatever the wording: a stab that moves legs and arm together needs a
middle key (legs half slid, fist half up), or a wound-up key whose stance is already near the
lunge. Never render between two near-identical keys (key-to-key mean change under about two frame
steps): at 33 frames the model invents walking and arm swings, at 13 it holds and then snaps.
Treat the pair as a hold, or drop one key. The return
to the idle is usually the out-bound clip reversed.

When the edit model cannot make a key, **Wan 2.2 TI2V 5B from the start frame alone** runs locally in
about 65 s at 640 (33 frames, 4 steps, swap under 7 GB) and follows the start picture — but it
ignores direction words ("knocked left" travelled toward the enemy and grew 1.15×), so it suits a
move whose direction the start pose already implies. It adds nothing the start pose does not
already lean into: from a hurt pose already leaning back it holds the start picture and adds no
step, and mirroring the start changes nothing. For a fall, name image sides in the prompt (falls
toward the left edge, hood left, boots right) and place the key low on the plate so no floor shows
in front of him: together they turn the landing from a 3/4 top view to nearly side-on — keep both.
Locally it still invents its own landing every seed: the face smears in the tip-over frames, the
body hangs in the air before it drops, and it ends face-up with the dagger still in the fist. Its
cfg and shift are hard-coded in `src/LLMs/generate.py`.

**Choosing the method.** A whole-body move with no set end spot (a death) tries one-go video
before keys. A move that must end on its start spot, or must not bring in other figures (a hurt),
is not one-go as-is.

**A one-go death from K0 alone, hosted, is the method that shipped** (rogue death, approved):
Replicate `wan-2.2-i2v-fast`, start-only, 720p, 81 frames, $0.11 a take, on a 1280×720 plate with
K0's boots on row 704. `render_remote.py` with no `--end` does this; run `--dry-run` first. With or without
`--end` it keeps a non-square plate, logs every paid call to the spend ledger and aborts on a
returned aspect off the plate's. The paid
model is smoother than local but adds a backward hop and invented "shocked" eyes on every seed —
"never jumps or leaves the ground" did not stop the hop, and "no blood" did not stop a dark
puddle on one seed. Cut an 81-frame paid take before its tail: the last frames can invent a
second figure. The user judged the epic take over the controlled one — the free and paid takes
both passed by eye with floats measured, and they took the paid one.

A **hurt** one-go (start-only from K0, local A14B 33 frames) knocks back away from the enemy on
every seed when the direction is named by image sides — keep that. **Describe only his own
flinch and stagger — no attacker, no blow, no hit source.** Any enemy or hit wording draws one in:
locally "struck by a blow coming from the right edge" drew a black arrow, and on the paid model
even "hit hard by an unseen enemy off-screen to the right; nothing enters the image" drew an
enemy arm with daggers on every seed. Start-only always turns front-on by the end, local and paid
alike, and paid start-only over 81 frames overshoots a knock-back about 5× (one step became
750 px, off the edge) — so a hurt that recovers is first-last onto an end key (K0 a step left),
about 33 frames. Hosted first-last with start = end on the idle plate is no fix either: it plays
"run out and run back" (about 770 px of travel), never a small knock-back. **The method that lands
on the start spot**: take a frame from a liked take as the lean key (matted, one local eye edit),
and have the video model play only the return home, lean key → the idle key at the start x. It
lands exactly, side-on, stepping. An 81-frame return over-falls past the lean first (309 px; shift
6 only trims it to 234 px) — pick an earlier, smaller lean frame or a shorter clip.
The paid snap starts at f5 with f1–4 still: drop f2–4 at compose. The face
smears locally in the same fast frames on every seed, so that smear is the method, not the seed —
another seed does not fix it.

**Before composing, look at every fast-swing frame of every clip at 4×** for a half-see-through
second copy of the moving limb (doubled bracer or cuff bands). It passes every measure check. The
fix is a neighbouring frame from the same clip — never a bridge or a paint-out.

**3 — Compose and build.** A per-action `compose*.py` picks frames and sets the timing (copy
`hit/compose2.py`): the cut into the first key, a smooth action with enough frames, hold, eased
return. It writes the plate; `build_action.py` mattes it,
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
| the edit model cannot make the pose at all (a lean-back skid, legs passing in a stride) | outside what it draws from this key | reword with picture sides, within the budget; then blocked for the user — no paid model without their say-so, never build the body by code |
| in-between opens the mouth, blinks, shuts an eye | the video model invents faces | another seed first, then drop the bad frames and bridge them. Pasting the key's mouth or face over the frames (`tools/patch_mouth.py`, `tools/patch_face.py`) is a last resort for one or two frames with a still head: on the defend the user found the pasted face "horrible", and a paste that spans a moving head glitches at its edge |
| a ghost limb on one frame | the model's own | drop the frame; bridge with FILM only between two consecutive good frames — across four frames or a real rotation FILM ghosts too |
| a half-transparent double of the swinging forearm mid-swing (doubled bracer bands) | the in-between blends two limb positions; measure checks pass it | swap in the neighbouring clip frame; found only by looking at fast-swing frames at 4× |
| the clip keeps doing the old motion (keeps running, never skids) | the end pose is too far for one segment | make the first frames by code (`run_stop/lead_in.py`) and render only the settle |
| a ghost hand on the last frames | a crossfade onto the idle over a pose that has not arrived | `--fade 0`, and make the tail arrive: a short hosted render from the last good frame to the base key (worst step 49 px → 22 px) |
| earlier frames change by a few grey levels after a recompose | re-encoding an mp4 of another length | the compose script writes the plate as `.npy` (`run_stop/compose_skid4.py`) |
| a loop drifts in scale or position | the model's framing wanders | pick the best-closing pair with `tools/runstat.py <clip> --loop`, stabilise head x and ground line (`run/compose_run.py`) |
| grey wedge between limbs | an enclosed pocket of plate | `--drop-grey-pockets`, then put back the silver-rimmed pockets it also drops (hair strands, blade fullers) |
| a dip or sink asked for between two keys never appears, or the arm drops with it | the video model only moves between its end keys; a pose in neither key is not drawn — an over-crouch, nothing, or a frozen split render from a video frame (3 of 3 takes) | draw the dip into a key, or drop it from the brief |
| a figure hops between two keys that stand still | the pinned boot sits higher in one key than its neighbour | compare boot rows across all keys at key review, before any clip |
| the scarf or cloak tail pops on a snap start | the picked frames do not follow the tail growing into the action's first key | pick frames where the tail grows in step |
| head travel measures wrong on a hooded figure | the 'head' track follows the scarf centre | measure from the hood top |
| hip travel measures wrong on the rogue | trouser centroid moves with the legs | measure hips from the sash centroid |
| feet skate after in-place tracking (whole frames re-centred on the body) | the take's feet stay planted while the body travels | in-place tracking only on a take whose feet move with the body. When it is used: track the chest by a colour region (scarf, sash), not the bounding box; take ground contact per segment; smooth or freeze the offsets once the body settles; matte to the largest figure before shifting so the frame border never shows |
| a planted foot measures as sliding or lifting | boot row vs ground lies when the raw figure floats | measure contact from sole stability frame to frame |
| the blood test fires on skin | `r > g+40, r > b+40` catches skin tones | `r > 140, g < 80, b < 80`, against an idle-key baseline |
| a snap start lingers before it moves | the first frame held three frames before the snap | hold the first frame once |
| `pose_guard.py --run` crashes on the rogue | it finds the hood by the archer's green | judge the run key by eye until it has a dark-hood mode |
| `clipmeasure.py` numbers jump mid-clip | its matte fails when the plate brightens partway through | check the plate's brightness across the clip first; judge that clip by contact sheet, or re-plate before measuring |
| `ch_measure.py` fails a hurt or death K1, or misreads dagger length | its K1 gates are the attack's; fist touching blade merges them | read its K1 verdict only on an attack; check the blade by eye where it meets the fist |
| the edit draws the weapon as a long staff gripped mid-handle, or a hammer, whatever the wording or picture 2 | the edit model's own idea of a mace (10 of 10 tank edits) | keep the drawn arm and fist, swap the weapon by code; paste back only glove and cuff pixels over the new handle (exclude the old wood by colour, r−b > 40) and keep the glove's bottom outline inside the paste box, or a stub of the old staff and a flat glove edge show at 2× |
| a whole-figure edit keeps picture 1's legs | picture 2 was a code-drawn prop | picture 2 = picture 1 gave the wider stances; a prop picture 2 left the legs unchanged |
| the first key of an action, already wound up, needs the weapon arm pulled back and code warping squashes the forearm | a rigid 100% forearm cannot retract past the back silhouette (rogue: reach 137 vs 70 wanted) | check retraction against forearm length before briefing; a pulled-back arm needs new upper-arm art from the edit model, not a code warp |
| a crushed tunic flap and doubled hem after a knee slide | the knee group pinned points on the hem and upper thigh while the block moved, shearing the cloth | put knee handles on the knee rows only; let the hem interpolate between block and knee |
| 1–2 px transparent cracks where hood, scarf and glove meet after a lean warp | the 3–60 px pinhole check does not count them | list every enclosed transparent component of any size and fill with outline black |
| a model-drawn blade with no outline over the background, a hollow slit, or flecks | grey blade shading keyed out as plate by the matte | swap the blade for the base key's own blade art, rotated rigidly onto the drawn crossguard; repaint the old outline the fill leaves behind |
| run legs built by code from rigid base-key pieces read as a paper puppet at 2× (sliced shaft ends, a break at the ankle, unoutlined edges) | rigid pieces cannot bend at the knee or ankle | don't build stride legs from pieces; a legs crop clean-up with picture 1 = picture 2 redraws a standing pose and drops a lifted leg |
| the edit model never draws a run passing pose (jump or stride instead) | it draws strides from a standing key; a passing pose from the base key, or the archer's airborne pose as picture 2, comes out as a hop | key the loop contact to contact (two contact keys) and let the video model draw the passing frames. Never pose legs by a limb warp |
| ground props (dropped daggers) sit on top of a fallen body, or under a kneeling leg | pasted above the body layer, or at another key's x | paste ground props under the body layer; check where the kneeling leg is before reusing another key's prop x |
| planting the trailing toe of a drawn stride turns it into a knee-down lunge | the drawing had the rear foot in the air | let the trailing foot lift; only the front heel sits on the ground row |
| a redrawn arm is a stiff straight tube | the edit copied a code-drawn guide arm faithfully | never give the model a code-drawn limb as the pose; picture 2 = a drawing with a natural arm |
| whole-figure edit of an erased-limb plate draws a stub limb, a second weapon, or turns the body front-on and drops the shield | nothing in the pictures shows the pose | picture 2 = a pose source with that limb; composite only the limb region back |
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
| travel | hips and hand visibly move — numbers stated next to the previous version's. A death's drop is measured by hood-top travel; a sash-drop bar of 200 px is unreachable for a chibi, which lies about 100 px tall. A measured float on a death is reported, not a reject: the user passes it by eye |
| units | every px bar names its pixel unit — the 832 plate's px and the artist's key px differ by about 1.6×, so an unnamed bar is read at the wrong scale |
| on the spot | body centre (torso and hips, not the bounding box) on the last frame within a few px of the first, horizontally, end x measured on the sash, not on all teal; no other figure and no blood in any frame. A take that needs re-centring by code is reported as such |
| face | the base key's face on every frame; no invented expression |
| rebuild | `build_action.py <action>` alone reproduces the sheet |
| in motion | watched at 1x and quarter speed as mp4 |

## What still fails

- **The first pass is usually too subtle or mechanically wrong** — that is where the 2.3 passes come
  from. Read "What the user judges" against the key before rendering anything.
- **The edit model cannot draw some poses**, and the video model's faces and extra limbs are a seed
  lottery. Past budget the item is blocked for the user; a code-made body key is never the fallback.
- **Hand seeds are labelled by hand** on most actions.

## Run loops must match the ground speed (no ice-skating)

In a battle scene the run plays in place while the ground scrolls under it. The foot on the
ground must slide backward at exactly the ground's speed, or the character skates. Games solve
it this way, and so do we:

- **The even slide is made in the original stride render, never after.** It cannot be retrofitted
  into a finished run: FILM in-betweens ghost where the legs cross, a Wan first-last render over one
  contact runs 2–3 strides in 17 frames and crowds the end key, and spare frames from another
  stride do not line up once stabilised. Judge it at clip review with `tools/footspeed.py`'s CV,
  and rate legs clean by eye — Laplacian variance does not catch speckled ghost legs.
- **Measure every run loop's foot speed**: during each contact, track the planted foot (sole
  x per frame, in sheet pixels) and record how fast it travels back, in pixels per frame, plus
  the stride (pixels per full cycle). The sliding must be steady through the contact — a foot
  that stops, jumps or speeds up skates whatever the playback speed; that is a clip defect for the
  clip reviewer, fixed by another take, never by moving the body in code.
- **Record it with the action**: `footSpeedPxPerFrame`, `stridePx`, `fps` in the sheet's
  `.sheet.json` / registry entry, at the scale the sheet is installed.
- **The game sets one ground speed for everyone**; each character's run playback speed is
  `groundSpeed / footSpeed` (Unity Animator speed). Stay within about ±20% of 1.0 or the legs look
  too fast or slow — if a character falls outside, its run needs a longer or shorter stride.
- A character standing still (idle, the enemy side) is parented to the ground and travels with it.

## Scorecard — the last step of every run

Append one row per pass to `scorecard.csv` beside this file, then run the `skill-improver` skill on
this skill.

`date,character,action,frames,passes,key_edits,inbetweens_local,inbetweens_remote,hand_fixes,new_tools,minutes,usd,user_verdict,note`

- `passes` — how many times the action has been shown to the user, this one included.
- `hand_fixes` — anything done by hand that these steps did not tell you to do; `new_tools` — scripts
  written mid-run. These, `passes` and `minutes` are what this skill exists to drive down.
- `user_verdict` stays empty until the user has judged it; only their word makes it `approved`.
