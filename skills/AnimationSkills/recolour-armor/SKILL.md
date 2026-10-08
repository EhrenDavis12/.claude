---
name: recolour-armor
description: Make a new colourway of an armor a character already wears — same shape, same frames, new colours (the archer's Fire Robes from its Forest Robes). Use when the user asks for a shade, tint, palette or "colour class" of an existing outfit, or when a recoloured body flickers, leaves a patch in the old colour, or tints something it should not. Not for an armor with a new shape (wings, plates, a different hood) — that is `new-armor`.
---

# Recolour armor (repaint the cloth, keep every pixel's place)

A recolour never calls a model. It reads the finished body frames of the base armor and maps colours,
so position, movement, face, camera and scale are the base's **by construction** — nothing has to be
checked for drift, only for colour. Free, local, seconds per action.

Working folder (archer): `src/asset-animation-demo/local_runs/archer/loadout/`. Python:
`src/Asset-Gen-Framework/.venv/bin/python`. Run everything from the loadout folder.

## When this is the right skill

The new armor's outline is the base armor's outline, pixel for pixel. If the user wants anything that
changes the silhouette — a pauldron, a longer cloak, a different hood — stop and use `new-armor`.

## How it works

`recolor.py` picks pixels by **hue band**, not by position, and sends each one through a **luminance
ramp**: shadows to the ramp's dark end, highlights to its light end. One ramp is shared by every sheet,
so an identical base pixel always becomes the identical new pixel — that is what keeps a colourway from
flickering between actions.

| Piece | Where | What it decides |
|---|---|---|
| which pixels | `green_weight` (hue 60–175, saturation and value floors) | near-black outline pixels and everything outside the band are left exactly alone |
| the colours | `ROBE_RAMP`, `GEM_RAMP` | 7 stops dark → light; the lightest stop is where the highlights land |
| brightness scale | `ROBE_NORM`, `GEM_LUM` | fixed numbers, never re-measured per sheet (a per-sheet measure is what made two sheets differ by ~4 levels) |
| small parts in a second colour | `track_gems` + `gems.json` | followed frame to frame, never looked up in a fixed window |

## Steps for a new colourway

1. **Pick the base armor and name the hue band.** Only cloth that owns its hue can be recoloured. On the
   archer the green cloth can; the brown cloak cannot, because it shares its brown with hair, leather
   and the bow. Say this to the user before starting if their idea needs the brown changed.
2. **Write the ramp**: seven stops from the base's darkest shadow to its lightest highlight. Skin never
   changes.
3. **Add the body** beside `fire_body` in `recolor.py`, and to `ROBE_BODIES` and the `bodies` list in
   `install.py` (same `frameSet` as the base — that is what tells Unity it reuses the base's weapon
   sheets, so the bows are already pinned).
4. **Build every action**: `python refire.py` (all actions) or `python refire.py <action> ...`. It prints
   the frames whose second-colour parts changed.
5. **Check**: `python check_gems.py` must exit 0. A failure names the action and frame.
6. **Pin and install**: `recolor.py` is an input of the weapon sheets, so `python pin.py --only <actions>`
   then `python install.py --only <actions> --frameset robes`.
7. **Look at it in motion**, not in stills: the Unity Loadouts scene, the new body, each animation at
   0.25x. A recolour's defects are single-frame flickers, and a contact sheet hides them.

## Defects and their fixes

| Defect | Cause | Fix |
|---|---|---|
| a small part flashes the wrong colour for 1–3 frames | the tracker lost it (a limb crossed, it shrank to a sliver, two blobs merged) | add an anchor for that frame in `gems.json` (`{action: {frame: [[x, y], ...]}}`), then `refire.py <action>` |
| a scrap of cloth takes the small part's colour | a blob bigger than 1.3× the part is part + cloth | nothing to do — the tracker keeps only the blob's opened core; if a human has judged the candidate to be cloth, list it in `SCRAPS` in `check_gems.py` |
| the colourway is a shade off between two actions | a brightness scale was measured per sheet | use the fixed `*_NORM` numbers |
| the outline turns coloured | value floor too low | raise the `wv` floor in `green_weight`; outline pixels must keep weight 0 |
| `install.py` refuses | a recoloured body is older than its base, or `recolor.py` is newer than the weapon sheets | `refire.py`, then `pin.py --only`, then install |

## Scorecard — the last step of every run

Append one row to `scorecard.csv` beside this file, then run the `skill-improver` skill on this skill.

`date,character,colourway,actions,frames,flicker_frames_found,anchors_added,minutes,usd,hand_fixes,note`

- `flicker_frames_found` — frames `check_gems.py` or your own look found wrong before the fix.
- `hand_fixes` — anything done by hand that these steps did not tell you to do. Each one is a missing
  step; `skill-improver` turns it into one.
