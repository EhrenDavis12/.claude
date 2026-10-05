---
name: idle-breathing-loop
description: Build a character's production breathing idle — a seamless, face-still loop generated locally from one approved transparent key — and layer extra motions (head turn, regrip) on copies of it. Use when a new character needs its base idle, when an idle pops at the loop point, blinks, talks or blurs, or when an extra motion must be added without touching the approved idle. This is the recipe that produced the archer's PROD idle v2 on 2026-10-04; every step here contributed to that result.
---

# Idle breathing loop (the archer idle v2 recipe)

Everything runs locally on the M1 Max through `src/LLMs` (ComfyUI). No Replicate call was used.
Working folder per character: `src/asset-animation-demo/local_runs/<character>/`; the approved
keys live in its `approve/` subfolder with a README the user reads.

## The result this produces

A 64-frame, 16 fps sprite sheet (512 px cells, transparent): one slow breath, chest and shoulders
only, feet planted, face identical on every frame, loop seam no bigger than a normal frame step.
Unity: `Assets/Characters/<character>_versions/idle_vN.png` + an entry in that folder's
`versions.json` with `"loop": true`, `"status": "prod"`.

## Steps, in order — each one earned its place

1. **One approved base key, K0, transparent, at 1024.** Cut from the approved reference with
   BiRefNet + the agf matte, then **clean enclosed pockets by hand**: white or plate-coloured
   regions the source art itself carried (the archer had a white gap between glove and bow and
   between the arrow shafts). Measure the edge ring (should be dark, ~0 bright pixels) and show the
   user the key on dark / checkerboard / light — Preview draws transparency as white and misleads.
   The user approves K0 in `approve/README.md` before anything else is rendered.
2. **Lay K0 on a flat grey plate, #7f7f7f, at 640 px** (`K0_plate.png`). Grey, not magenta:
   magenta tinted every white highlight pink through the matte.
3. **Render one segment K0 → K0 with Wan 2.2 14B first-last-frame** (`scripts/render_breathe.sh`):
   65 frames, 640×640, 16 fps, seed 7, 4-step lightx2v. The prompt asks for *one slow deep breath,
   chest and shoulders only, head and face do not move, eyes open, no blinking, mouth closed,
   feet planted, same shading throughout, static camera, flat grey background*. Pinning K0 at both
   ends is what makes the loop close. **Close Unity first**: 65 frames with Unity open hung the
   server at the decode twice (swap 27 GB). 49 frames is the ceiling with Unity open. The server
   gives one model at a time — never queue Qwen edits while Wan runs.
4. **Lock the face** (`scripts/face_lock.py`): paste K0's face (eyes, nose, mouth, chin; rows
   150–240, cols 268–392 at 640) onto every frame at the tracked head position — SSD template
   match, ±10 px, 1 px steps, offsets median-filtered over 5 frames so the patch never jitters,
   7 px feather, per-frame tone shift from the blend ring. No blink, no mouth, no blur; the head
   still rides the breath. (For segments where the face must move, use `scripts/mouth_fix2.py`
   instead: same tracking, lower face only — the model talks whenever the head is still, a
   negative prompt does nothing at cfg 1, and only a patch fixed it.)
5. **Post, per frame** (`scripts/build_v5.py`): flood-fill matte from the plate colour (no model
   needed — anything the flood from the corners cannot reach is the figure), a grey colour-key
   inside fixed pocket boxes applied to the mask *before* the agf matte (grow 3, erode 1), colour
   match to K0 (per-channel mean/std over the character's pixels), downscale 640 → 512 in
   premultiplied space. **No 4× upscale** — it buys nothing at this size and costs 2/3 of post time.
6. **Close the loop**: drop the duplicate last frame (it equals the first), 2-frame premultiplied
   crossfade across the seam (last → first). Do not paste the crisp K0 into the sheet — a sharp
   frame inside soft frames reads as a flash.
7. **Sheet + Unity**: cells in a near-square grid, sidecar `.sheet.json`, copy into
   `<character>_versions/`, add the `versions.json` entry (fps 16, loop true), run
   `Characters/Import Animation Versions`, capture play mode to a GIF and *look at it*.

## Keeping in-betweens clean (`scripts/clean.py`) — added 2026-10-04 after the first two extras

Every Wan clip goes through these before it is composited; each one answers a defect that crept in:

| Defect | Cause | Rule |
|---|---|---|
| grey inside the bow, arrow gaps, glove gap | Wan paints the plate into any enclosed gap; a flood fill cannot reach it | `enclosed_plate`: drop plate-coloured pixels (grey, sat < 26, lum 90–175) within 12 px of anywhere K0 is transparent. Leaves the buckle alone. Replaces fixed pocket boxes. |
| ghost double cape, fuzzy edge | crossfading two different shapes | never crossfade shapes. Render the clip **from the idle's own frame** (`idle16_plate.png`, frame 16 of the locked loop) so it joins exactly; drop each pinned frame 0 (a pure texture pop, ~7 vs a typical step of 1). |
| snap mid-move | Wan moves in bursts | `generate.py interpolate` twice (FILM 4×) then `retime_uniform` (motion measured on a 4× downsample so pixel noise does not count) → every frame carries equal motion. Head turn's worst step 7.2 → 4.0, shift's 5.5 → 3.5, evenly spread. |
| distorted face mid-turn | at 640 the face is ~60 px; Wan smears a 3/4 face | **render face motion as a close-up**: crop the head box (rows 22–262, cols 180–480 at 640) from the idle frame and from the key, scale 1.6× to 480×384, run Wan on that, then `closeup_to_full.py` pastes it back. 4× the face pixels; the turn came out crisp first try. Same trick as the hand close-up for Qwen keys. |
| texture pop at internal joins (out→hold→back) | different renderings of the same pose | `crossfade_joins`, 3 frames each side. |
| pasted head jumps | tracking a mid-turn face against two keys | don't track the source: a static-camera clip pinned to K0's body already has its head where K0's is. Track only the idle's own head bob. |
| blink / mouth flicker | model habit | `face_lock` where the head is still; `still_face` (temporal median) only where the head is still. A blink *during* a turn stays — every patch across a turning head ghosts the eyes. |

Measure, don't eyeball: per-frame mean |diff| profile (whole figure and head region), plate-coloured pixel count
inside the figure, edge-ring colour, and the pose guard. A lint that runs these before Unity is the next step.

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

## Numbers (M1 Max 32 GB, server alone)

| Step | Time |
|---|---|
| Qwen key edit, 1024 | 4.5–5 min per seed |
| Wan 14B FLF, 640, 33 frames | ~13 min; 65 frames ~40 min |
| face lock / mouth patch | seconds |
| post, flood matte, 64 frames | ~2 min |
