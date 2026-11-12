---
name: base-action
description: Make a new one-shot or looping action animation for a character or enemy — attack, hurt, defend, run, run stop, death — by giving the video model one approved picture of the character with the real weapon in hand and a short action prompt, keeping the best take and cutting its frames into the sheet. Use when the user asks for a new action, a new version of one, or when an action invents a face, changes the weapon or clothes, or does not read as a solid action. Not for the idle or its extras (`idle-breathing-loop`), a recolour (`recolour-armor`), or the same action on another armor (`new-armor`).
---

# Base action (one picture in, the video model makes the action)

**The method, for every action of every character and enemy:** the paid video model (Seedance
first) gets one approved picture of the character, with the real weapon in hand, and a short
prompt naming the action — the action (at-the-ready) pose for combat actions, the relaxed pose
for runs (see "Which picture each action starts from"). Nothing else: no end pose, no in-between keys, no prompt that
dictates each limb. The model invents the whole action. The game snaps from the idle straight into
the clip and, after the clip's follow-through, snaps back to the idle — so the clip needs no
blend from the idle and no landing on it.

The user's words (2026-11-09): "let the video model go and have fun and make it look good. Create
the whole action. It's a snap straight into the action pose so we don't need it to blend from one
pose to another pose" ... "all we're really checking for is does it look good? Can we work with it
and does it look like the image that it's supposed to look like in other words the store has to
remain the same type of sword to clothes have to remain the same clothes, the face has to remain
the same face generally, we don't want them going crazy with other details" ... "that goes for
every single animation we draw for every character as well as the hurt just let them be hurt."

Drawn strike, wound-up or hit keys and first-last renders between keys are not used: controlling
each pose is what kept actions at 2.3 passes of about two hours each, and the user ruled it out.

Working folders (archer): `src/asset-animation-demo/local_runs/archer/actions/` (clips, body
sheets; shared tools in `tools/`) and `.../archer/loadout/` (hand track, bows, checks, install).
Other classes and enemies work in `local_runs/characters/<class>/work/<action>/`, with class tools
in `local_runs/characters/tools/`. System `python3` has no PIL, so every script here runs on the
`.venv python`: `src/Asset-Gen-Framework/.venv/bin/python`. The long reference for every registry
key and flag is `actions/README.md` — read it when a step below names a key.

## Before starting — say this to the user

- **A Seedance take is $0.06 a second of video** — a 3 s take is about $0.18, a few minutes each.
  Paid calls go only under the user's yes for that job and a dollar cap, carried in the brief; an
  artist that reaches the cap stops and reports. With no yes and no cap the item goes to `blocked`
  with that question, and the run moves to the next job.
- **The Replicate token lives only in the login profile.** A subagent's shell and a runner worker
  do not have it: start every paid command with `source ~/.zprofile >/dev/null 2>&1;` (or run it
  under `zsh -lc`). Give every paid script an absolute prompt path — a relative one sent an empty
  prompt and paid for a random image.
- **Check a paid model is up with one cheap call before planning a ladder around it.**
  nano-banana failed four times with `invalid_grant` (a JWT error) at $0 — that is Replicate's or
  Google's side, not our token, so it means another model or `blocked`, not a retry.
- **The start picture is an approved one**, the weapon its real self in the hand, not erased —
  the action pose or the relaxed pose by the table below, never both. If the approved picture that
  action needs does not exist, making that one picture is the only key work (`annie-key-artist`),
  and it goes to the user first.
- **Basic weapon and basic armor first.** No other weapon, recolour or armor is built from an
  action the user has not accepted.
- **Under the queue runner, resuming an agent with `SendMessage` fails** (no transcript, every
  agent, every round): dispatch fresh each round with a hand-off brief, so the system's resume
  budget does not apply here. Write the brief's path (or its text) into the item's note at every
  stage end: a worker restarted mid-run lost it.
- The Character Chart cell is set as the state changes — `idle-breathing-loop/SKILL.md`, "Keep the
  Character Chart current".

## Which picture each action starts from

Every character has two approved poses: the **action pose** (at the ready, weapon held for the
fight) and the **relaxed pose**. One animation gets exactly one of them. Feeding both made the
Assassin run with his daggers held out in front and his arms not swinging — the user: "It looks
terrible".

| Action | Start picture |
|---|---|
| idle, attack, hurt, defend, death and every other combat action | the action pose |
| run loop, run start | the relaxed pose |
| run stop | not settled — try the action pose and a frame taken from the run itself, and show the user both |

## Making the design stills (a new character's picks)

When the character has no approved poses yet, the picks come first: each design as a relaxed and
an at-the-ready still, shown as one numbered side-by-side sheet.

- **Budget about 32 edits** for five designs (ten stills) plus fixes; 26 ran out. Split the round
  into two queue items — the five relaxed stills, then the five at the ready — or one worker hits
  its six-hour limit mid-round.
- **A chibi human starts from an approved body, never a text-only grey canvas.** From grey alone
  the model draws a flat default cartoon — dot eyes, wrong outline weight, plain — on every seed.
  An existing character's body on grey, with its head box painted grey, gave house-grade eyes and
  outline on the first seed. A text-only start is for monsters only.
- **A prop's length cannot be steered by prompt.** Every "shorter spyglass" edit came back as a
  sword, a second tube or longer, and "a dagger 1/5 of his height" came out at 42% of his height.
  Cut one clean prop from the best still and pin it by code from the start (`pin_weapon.py`, step
  5's rules), not after edits fail. A model-drawn dagger that is too long is shortened by code:
  keep the drawn grip and pin only the blade part.
- **Size props in pixels against the head** (the head is about 290 px on these stills), and word a
  dagger against the fist that holds it — never as a share of height, and never "head-tall".
- **Put the prop-and-hand sentence first in the prompt.** Later in the prompt the dagger was not
  drawn at all.
- **Keep the grip stub in the start picture.** A bare-fist start put the dagger in the wrong hand.
- **Name the hand by its image side.** Placement wording names the left or right of the picture
  where the grip stub left in the start picture sits — "the hand on the image's left, holding the
  stub" — never the character's left or right; wording without it swapped hands three times.
- **Name a hair colour by the colour it should render.** "Ash-blond" renders grey; say "warm
  pale-yellow blond".
- **The at-the-ready crouch is built into the start picture, not worded.** The local edit model
  holds the head top at the relaxed still's row on every crouch, whatever the crouch words, and on
  three of five designs moved the dagger to the far arm crossing the chest. Re-wording made a new
  arm defect twice (a third arm). Start the ready edit from a picture that already crouches — an
  approved crouch body, flattened — and check on the sheet that the head sits lower than relaxed
  and the weapon is still in the same hand.
- **Rank the picks by the design, not by which still came out cleanest.** A pick's defects are
  fixed after it is chosen; the user passed over the cleanest still because its shape was the
  closest to an existing character's. Treat a likeness to another character as the heavier caveat.
- **Say the fix as what is there, never as the defect.** In a local Qwen edit a negative clause
  draws what it names ("no orange skin smeared into it" smeared it). For skin blotches use "The
  cheeks, nose and forehead are one single flat skin colour, exactly as in picture 1." — it
  cleared the cheeks on both seeds.
- **A two-hand staff ready pose starts from the relaxed pose**, with the whole two-hand diagonal
  grip worded in one edit. Asking a hip fist on an existing pose to take the staff came back
  unchanged or with a stretched staff.
- **The low fist lands about 75% down the staff**, never near the tip: set the brief's bar there,
  not at a pixel row near the tip.
- **Judge relaxed → ready by the staff head's travel, not the fists'.** The fists moved 110–145 px
  while the orb moved about 270 px; the head of the weapon is what reads as the change.
- **A whole-figure edit cannot change one arm's job.** Whole-figure edits that
  turned one arm to a palm on the chest or a cupped hand failed, and each re-roll added blotches
  or an extra hand.
- **Turning a fist to a fixed haft angle is a method failure, and paying does not fix it.** Paid
  qwen-image-edit-plus behaved like local Qwen 2511 on a gauntlet's knuckle row: it redrew the
  whole crop window (losing the arm) or left the fist unchanged, and a rotated upright window gave
  a thumb-side fist (palm view). A bigger model of the same family is not a new method — ask the
  planner for one. Paste back only the low-saturation glove pixels, or the model's recoloured
  shield comes along.
- **A head part's size (horns, crest, ears) cannot be steered by prompt either** — the model sizes
  a new part to the mass it replaces. Strip the old part first with a bare-head edit (it passed
  first try), then add the part from a swatch holding only that part at the target scale. The
  swatch must hold no extra spike or crest, or it is drawn as another horn.
- **Take only the new part's pixels.** Adding a part also redraws the eye angry. Composite along a
  minimum-cost seam through flat colour, with the eye and brow protected, and take the part's base
  and the outline under it from the model's result. Never run the seam along an outline. There is
  no shared "take only the new part" script yet — an `annie-tool-writer` ask.

## The grade — the only thing judged

| Rule | Means |
|---|---|
| a good, solid action | it reads as a real attack, hurt, block or run at game size, by eye. A clean, subtle take reads as nothing happening |
| it still looks like the character | the same weapon (same type and shape), the same clothes, the same face — eye style, shape, size. No new details: no invented trim, armor, second weapon or expression the picture does not have |
| only he and his own weapon are in frame | no other person (enemies come from the game), no effect of any kind — particles, sparks, dust, smoke, glow, blood — and no projectile, not even an arrow in flight. Effects and projectiles are separate overlays |
| send mp4, never GIF | and label a test clip loudly as a test — an approved action is not touched, and nothing that could pass for a new version of it is sent |

Nothing else is measured against a plan: no travel numbers, no hip angles, no pose match to a key,
no end pose match to the idle. Where he ends is not graded; the game snaps him back to the idle.
Death is the one action that holds its last frame instead of snapping back.

Standing user rules that still hold inside the model's take: knees bend outward only, never
inward — never ask for inward knees in a prompt; a weapon is gripped at the handle's end, not
choked up.

## Steps

**1 — Plate the start picture.** The approved picture, matted, on the flat grey plate (127) at
1280×720, boots on row 704, room for the action on every side. `tools/plates.py key` makes only
the 640 square plate; for 1280×720 copy `characters/rogue/work/death_v8/plate.py` (pastes the
picture onto the plate and prints where it landed). A shared 1280×720 plate tool is an
`annie-tool-writer` ask. Seedance returns 16:9 (1920×1088) or 4:3 only — a 3:2 plate is paid for,
comes back a 4:3 centre crop and aborts — so plate 16:9 or 4:3. Speck-check the plate before any
paid call (nothing more than 3 levels off grey more than 6 px outside the figure): a faint dashed
streak in a plate grew into speed lines on hosted Wan.

**2 — Takes.** Start-only, hosted, Seedance first. Run `--dry-run` once; it prints the input and
the plate's aspect. Every paid call is logged to the spend ledger, and a returned aspect off the
plate's aborts. A failed prediction writes no ledger line; refusals are billed $0.

```
.venv python tools/render_remote.py --model seedance --start work/<name>_plate.png \
      "<short action prompt>" --duration 3 --seed 7 -o <action>/work/<name>_s7.mp4 --dry-run
```

The prompt names the action and nothing more: "a powerful sword attack", "he gets hit hard and
reels back", "he raises his shield and braces". Roll a few seeds and two or three wordings, then
keep the best take. Wan (`--model wan`, no `--end`) is the second model to try.

The face is what breaks first, and it breaks when the head moves. Pick action wording that keeps
the head level: a defend that sinks the whole body with the weapon held in front ("whole body
sinks ... head stays level ... eyes open") held the fighter's face, where every lean-back hurt on
the same picture turned his eyes to lines or doubled his face. A hurt is a flinch and a stagger
with the head kept level, not a fall backward; "hit hard" reads as an attack.

Moving the action over from another clip does not save the face — the face breaks where the head
moves, whichever model draws it, so start from the picture. Kling v3 Motion Control refuses the
3-head chibi figure as a driver ("No complete upper body detected"), even on his own footage, and
wants 3 s of continuous real motion (held frames do not count). Wan 2.2 Animate can sit in
`starting` for 10–25 min: cancel at 10 min, billed $0. Seedance 2.0 reference mode accepts the
cartoon picture and copies a lean, but shut the eyes for the whole lean and leaned too far. A grey
mannequin stand-in drawn by Seedance turns to face left on any hurt wording.

What the prompt must not say, because the model draws it:

- **No attacker, no blow, no hit source on a hurt.** Describe only his own flinch and stagger.
  "struck by a blow coming from the right edge" drew a black arrow, and "hit hard by an unseen
  enemy off-screen to the right; nothing enters the image" drew an enemy arm with daggers on every
  seed. Naming the knock-back direction by image sides ("reels toward the left edge") keeps it
  away from the enemy.
- **No outfit details the picture does not show** — on the rogue, "black boots with grey cuffs"
  invented the cuffs. Name image sides, not body sides.
- **No "back", no chin, no step.** "back" reads as the body's own backward — a backbend with the
  hips thrust forward; "chin lifting" draws an upward eye roll; "takes one short step toward the
  left edge" walks. Use image directions and keep the feet planted.

A run starts from the relaxed pose: upright, side-profile, the arms already opposed (one forward,
one back). The action pose's ready crouch reads as an attack, arms-down pictures flap both arms
together, and a three-quarter picture turns the head. The rogue's approved run came from such a
picture, start-only, hosted.

**3 — Look at every take.** A contact sheet of each take (`tools/contact.py <clip> <out.png>
--step 2`; it breaks on 1280×720 frames, so until `annie-tool-writer` fixes it use the rogue
hurt's `local_runs/characters/rogue/work/hurt/v9/sheet_R1.py`), then every fast frame at 4× for
the defects below. Grade against the table above; pick the take; cut its window — drop still
lead-in frames, and stop before a long take's tail starts inventing. A 2 s Seedance take moves on
twos and stays on-model for only about frames 7–21: cut there, and stop before the expression
changes. Check the face on every picked frame for doubled edges — a doubled face shows at modest
head speed, so head speed is not the test.

**4 — Cut and build.** A per-action `compose*.py` picks the window and sets the timing (copy
`hit/compose2.py`) and writes the plate as `.npy`; `build_action.py` mattes it, colour-matches,
cuts cells and records the recipe in `loadout/actions.json`.

```
.venv python tools/build_action.py <plate> <action> "<Label>" --fade 0 --register [--loop]
      [--drop-grey-pockets]
.venv python tools/build_action.py <action>                     # a rebuild: every option from the entry
```

**5 — Weapon pin, only as a fallback.** The model's own weapon stays when it passes "same weapon".
When it forks, flips, vanishes or changes shape, render that action again from the same picture
with empty fists and pin the approved weapon art on by code: `../loadout/finish.sh <action>
[--no-install] [--no-locate] [--force]` for the archer's bows (tracks the hand, pins, runs the
checks, writes the review files; stops before install on any failure); on another class
`characters/tools/attach_blade.py` for a still and `attach_blades_track.py <frames_dir> <out_dir>
--labels labels.json` (run with the `.venv python`) per cell; for a hammer or mace in one fist `characters/tools/pin_weapon_1fist.py` (eases the
angle by fist travel, not frame number), for a two-handed haft or glaive `pin_weapon_2fist.py
--glaive`, for one still `pin_weapon.py` (each prints its usage with no arguments). Pin onto empty
fists only: pinning over a model-drawn weapon chokes the grip or doubles an edge, so erase the drawn
one first. Measure the fist width on the figure — the finger-mask default sat a cleaver 28 px off —
and make the skin cover follow the arm's own outline, not a box, or straight-edged tabs show over
the shaft. A punch fist (fingers stacked upright) cannot hold a level haft; the picture needs a
hammer grip. A closed fist holds the blade across
the palm: the angle follows the finger row (about forearm −85°), never the elbow-to-fist line.
Code attaches a weapon or prop to a tracked point and nothing more — **a body pose is never built
by code**; cut pieces, warps and limb rigs read as a paper puppet and were rejected.

**6 — Watch it, then show it.** The review mp4 at full and quarter speed; for a run, the whole
chain (`../loadout/review_chain.py`). A sheet judged from stills is not judged. Use `--no-install`
until the user has seen it. Render the review mp4 on a dark background as well as grey — grey hid
plate bits at a cape hem and a grey shard in a spider's fangs — and wrap the action in idle cells
on both sides, so the user judges the real snap. Captions: write them from the measured numbers,
never the brief's targets; plain hyphens (the caption font has no en dash); this ffmpeg has no
`drawtext`, so the TEST label also goes in the filename. A class with no install route yet (the rogue): at install, set the
sheet's pivot so the feet do not drop at the idle cut.

## Defects and their fixes

| Defect | Cause | Fix |
|---|---|---|
| a new face, a "shocked" or open-mouthed expression, blinks | the video model invents faces | another seed or wording; a face that changes fails the grade. Never paste a face over moving frames — the user found it "horrible" and it glitches at the head's edge |
| the weapon changes shape, forks or doubles mid-swing | the model redraws a fast-moving weapon | another seed; then the weapon pin fallback (step 5) |
| an enemy, an arrow, an arm or a second figure appears | attacker or hit wording in the prompt, or a long take's tail | no attacker wording; cut a long take before its tail |
| a blood puddle, dust or glow | the model's own effects; "no blood" did not stop one | another seed |
| a backward hop or a big travel off his spot | start-only takes over long durations overshoot (paid Wan 81 frames moved one step 750 px, off the edge) | a 2–3 s take; a take that leaves the frame is a weak take by eye |
| a face smear on most frames at 4n+1 of a hosted take | likely the hosted model's chunk artefact | pick the window's frames around it; another prompt does not fix it |
| the first frames hold still before the action | the paid model starts moving a few frames in (from f5 on Wan) | drop the still frames at compose; the snap from the idle needs the action from cell 0 |
| a half-transparent double of a swinging limb (doubled bracer bands) | the model blends two limb positions | swap in the neighbouring frame of the same take; found only by looking at fast-swing frames at 4× |
| a ghost limb on one frame | the model's own | drop the frame; FILM only between two consecutive good frames |
| hosted frames sit about 10% darker than the picture | the hosted model's own tone | match the take's tone to the start picture before compose |
| the take brightens across the action (about 7% on Seedance) | the hosted model drifts | ramp the gain over the first cells, not one gain for the whole take |
| fur, boots or face pop at the idle cut though the figure's tone passes | a whole-body colour match averages regions out (+16% on the brute's fur) | match by region (mantle, boots, face) to the idle with 12 px blurred masks; never the legs |
| steel highlights inside a grey-steel figure go transparent (visor, knee) | the plate colour key takes light grey steel | refill enclosed holes under 2000 px from the raw before the colour match (`characters/tank/defend_v1/refill_holes.py`) |
| a dotted light fringe round a matted hosted clip | the plate's halo round the outline; it shows only on black | review mattes on black; `characters/tools/ch_edge.py` plus smear removal |
| a matte clean-up eats real trim (a hem, a pauldron) or misses a chip | a smear rule bites trim and light steel touching transparency; its luminance floor misses dark chips | scope the smear rule to the regions that smear (cape, legs); diff every cleaned cell against the first matte |
| grey wedge between limbs | an enclosed pocket of plate | `--drop-grey-pockets`, then put back the silver-rimmed pockets it also drops (hair strands, blade fullers, knee highlights) |
| a grey shard blinks inside the outline on a few cells | a fully enclosed near-neutral blob the pocket rule skips | also drop enclosed blobs of chroma spread under 14, brightness 110–165, 25–3000 px; seen only on a dark review |
| enclosed transparent holes, 1–2 px cracks to 300 px slits | the matte | count every enclosed transparent component at any size, at alpha 128 and at 250; fill cracks with outline black |
| earlier frames change by a few grey levels after a recompose | re-encoding an mp4 of another length | the compose script writes the plate as `.npy` |
| `finish_key.py` turns the rogue olive | it colour-matches to the archer | a flat-grey flood-fill matte (`characters/rogue/work/run/r9/key_flat_matte.py`) |
| a loop drifts in scale or position | the model's framing wanders | pick the best-closing pair with `tools/runstat.py <clip> --loop`, stabilise head x and ground line (`run/compose_run.py`) |
| a run stop keeps running and never brakes | from a mid-stride frame neither Seedance nor Wan brakes (3 of 3) | prompt the brake hard on the run-frame option; a start picture already in the skid also worked, with a pop at the cut into it the user passed ("I think we're good") — show it, say it is there |
| pinned weapon: the tracker loses the hand (bracer, crossed arms, far swing) | the fist changes shape or leaves the search band | hand-label `locateSeeds`, widen `locateCols` / `locateRows`, set `angleOverrides` |
| pinned weapon: bow lies flat or whips | the bow turns 1:1 with a forearm that swings wide | `maxTurnDeg`, or an eased `angleOverrides` |
| pinned weapon: floats beside the body or swaps hands on a run | the fist is hidden behind the torso | `hiddenFrames` + `weaponBehind`; check with `../loadout/checks_behind.py` |
| pinned weapon: hangs in the air after a fall | rigid pin to a limp hand | `bowRelease` in the entry |
| pinned blade: a slit between fist and guard | the art sits off its own blade axis | `attach_blade.py` measures the axis from the steel and exits 1 on a new enclosed hole |
| pinned blade: a grip step slips or jumps a frame | window agreement let a weak match through | an NCC floor of 0.35 on every tracked grip step; hand-choose steps where the fist turns |
| `install.py` refuses | a hand track older than its body or than shared code | `finish.sh <action>`; after editing `pin.py`, `newaction.py <a> --locate` for each action, then a full `pin.py` |

## Acceptance — before the user sees it

| What | Pass |
|---|---|
| action | reads as a solid action at game size, by eye on the contact sheet and the mp4 |
| same character | the start picture's weapon, clothes and face on every frame; no new details |
| frame | only he and his own weapon; no other figure, no effect, no blood, no projectile |
| tone | the take's mean figure brightness within 3% of the start picture's, and each region (cloth, fur, boots, face) without a visible step at the idle cut |
| matte | clean on black and on a light background at 4×; no pockets, holes or fringe |
| rebuild | `build_action.py <action>` alone reproduces the sheet |
| pinned weapon (fallback only) | `finish.sh` prints no failure verdict and finds the hand on every frame; `--force` is never how an action ships |
| in motion | watched at 1x and quarter speed as mp4, on grey and on dark, wrapped in idle cells |

## What still fails

- **The video model's faces and weapons are a seed lottery**: the grade rejects a changed face or
  weapon, and the answer is another seed or wording, not a repair.
- **A staff held in a fist leads every move.** Seedance makes the staff arm do the action on a
  hurt (the Star Sage 3 of 3 takes, the porter 2 of 2: fist up 80–340 px, staff over the hat) and
  collapses a two-hand staff grip to bunched hands whatever the wording. Next to prove: a body-only
  take with empty fists and the staff pinned by code (step 5).
- **Only the archer has a build and check route.** `build_action.py`, `finish.sh` and
  `actions.json` are archer-only; every other class and enemy writes its own compose and check
  script per action. A shared body-only build-and-check is an `annie-tool-writer` ask.
- **A run stop does not brake** from a mid-stride picture on either video model, and which
  picture it starts from is not settled: the action pose or a frame from the run, shown side by
  side.

## Run loops must match the ground speed (no ice-skating)

In a battle scene the run plays in place while the ground scrolls under it. The foot on the
ground must slide backward at exactly the ground's speed, or the character skates.

- **The even slide comes from the take itself**, never after: judge it at clip review with
  `tools/footspeed.py`'s CV, and rate legs clean by eye.
- **Measure every run loop's foot speed**: during each contact, track the planted foot (sole x per
  frame, in sheet pixels) — pixels per frame and the stride per cycle. A foot that stops, jumps or
  speeds up skates at any playback speed: another take, never moving the body in code.
- **Record it with the action**: `footSpeedPxPerFrame`, `stridePx`, `fps` in the sheet's
  `.sheet.json` / registry entry, at the scale the sheet is installed.
- **The game sets one ground speed for everyone**; each character's run playback speed is
  `groundSpeed / footSpeed`. Stay within about ±20% of 1.0, or the run needs a longer or shorter
  stride.
- **Loop length is one measured cycle**, never a frame count written ahead (the rogue's hosted
  run stepped every 7.6 frames). Pick the window by the hood's series and foot speed as well as
  the seam: the best-seam window can hide a whole-body hitch.
- **Every run plays at the Archer's run pace**: a 1.00 s cycle (the rogue's 22 frames play at
  22 fps).
- A character standing still (idle, the enemy side) is parented to the ground and travels with it.

## Scorecard — the last step of every run

Append one row per pass to `scorecard.csv` beside this file, then run the `skill-improver` skill on
this skill.

`date,character,action,frames,passes,key_edits,inbetweens_local,inbetweens_remote,hand_fixes,new_tools,minutes,usd,user_verdict,note`

- `passes` — how many times the action has been shown to the user, this one included.
- `key_edits` — edits to make the start picture, usually 0; `inbetweens_remote` — paid takes rolled.
- `hand_fixes` — anything done by hand that these steps did not tell you to do; `new_tools` — scripts
  written mid-run. These, `passes` and `minutes` are what this skill exists to drive down.
- `user_verdict` stays empty until the user has judged it; only their word makes it `approved`.
