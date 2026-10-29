---
name: menu-map-buildings
description: Make the main-menu map — a top-down 3/4 still map of a town with roads, a pond and fields — and its buildings as separate sprites with shadows and anchor points, plus the game's menus in the map's style (pages, pop-ups, buttons), local and free. Use when the user asks for a menu map, a town or world map, building props for one, or menu and UI mockups to match it. Not for a side-view battle background (`parallax-background`).
---

# Menu map and buildings (top-down 3/4, still)

A menu map is one still ground image seen from above at a 3/4 angle, plus **each building as its
own sprite** with its own shadow and anchor points, placed on the map by game code. Nothing loops
and nothing scrolls.

**Local and free only.** Shapes are code; Qwen-Image-Edit (`src/LLMs/generate.py edit`) is used
only where it helps. No paid model without the user's say-so for that job.

Working folder: `src/asset-animation-demo/local_runs/scenes/menu_map/` — `k0.py` (the shared code
blockout and masks, `blockout/layout.json`), `styleA.py` (fully code), `styleC_buildings.py`
(flat fills + ink by code), `fullbleed.py`, `runq.py`, `common.py`. Python:
`src/Asset-Gen-Framework/.venv/bin/python`.

## Method

1. **Code blockout first** (`k0.py`): map, roads, pond, and one blockout + mask per building. Every
   style is built from the same blockout, so styles compare like for like. Roads must meet each
   door.
2. **Alpha from the mask**, eroded 2 px — never keyed. Thin parts (poles, flags, fence rails) are
   ORed back into the alpha after the erosion, and every attachment touches its body in the mask:
   each sprite is **one connected piece**. Pixel-art poles snap to the pixel grid.
3. **Buildings are drawn by code in every style**: flat fills, lit face upper-left, windows and
   trim drawn. Qwen on a building sheet drops windows and trim and adds bevels or brick texture,
   and the result reads as the code version with less detail.
4. **Ink, when the style has it, is drawn by code after the 2 px erosion** — erosion eats a Qwen
   outline.
5. **The ground is code by default; Qwen only for paper or texture.** A Qwen ground wash bakes
   shadows under bushes on most seeds, and adding "no shadow" makes it worse. Qwen parchment draws
   side-view bush fans: erase its painting and keep only the paper. A parchment prompt adds a torn
   border on every seed: `fullbleed.py <src> <dst> 36 110` crops 36 px and stretches the outer band back
   out by code. That stretch widens bushes at the edge about 1.5× — say so with the still.
6. **Shading never wraps at the frame edge** — a shadow or gradient must not reappear on the
   opposite side.
7. **Per building**: `<name>.png`, `<name>_shadow.png`, and its anchor points in `anchors.json`.
   Composite them on the map and on grey for review.

## Menus and UI in the map's style

Pages, pop-ups and buttons are **all code** on the map's own paper — no Qwen. Working folder:
`src/asset-animation-demo/local_runs/scenes/ui_parchment/` — `paper.py` (the clean paper),
`ui_lib.py` (the shared kit: ink, paper, fonts), `opts_a.py` / `opts_b.py` (one class per
style), `ui_run.py` (renders each option's `page.png`, `modal.png`, `buttons.png`, `sheet.png`,
`measure.json`), `compare.py` (all options on one sheet).

- **Decorative fonts (Trattatello, Luminari) for headers and drop caps only**; labels and body
  in a plain serif. Trattatello misreads letters ("Archer" as "Arcber"), Luminari's H and N read
  as other glyphs.
- **An all-ink style still needs one accent** (red) on the primary button, or primary and
  secondary read equal.
- **Label-to-ornament clearance ≥ 8 px**, measured — rollers, plates and borders crowd labels.
- **Measure every accent colour**: grey drifts in where the style says blue.
- Woodcut stipple reads as flat brown at 1920; shade with bold cross-hatch bands instead.
- The key artist dispatched in the background could not be resumed with `SendMessage` twice
  running: plan the fix round as a fresh hand-off brief.

## Defects and their fixes

| Defect | Cause | Fix |
|---|---|---|
| Buildings lose windows and trim, gain bevels or brick | Qwen run on the building sheet | draw buildings by code; Qwen for the ground only |
| Outline missing or broken | ink drawn before the 2 px erosion | ink by code after erosion |
| Torn parchment border | the parchment prompt, every seed | `fullbleed.py` crop 36 px + stretch the outer band |
| Baked clump shadows on the map | Qwen ground wash; "no shadow" in the prompt makes it worse | code ground; shadows are per-building sprites |
| A pole, flag or rail missing or floating loose | 2 px erosion ate it, or it does not touch the body in the mask | OR thin parts back after erosion; gate: connected pieces = 1 per sprite |
| Side-view bush fans on the parchment | Qwen paints on the paper | keep only the paper, erase its painting |
| Jitter differs between runs | `gen.py` seeded jitter with `hash(name)`, which varies per process | seed with a fixed value |
| Trees look off beside the buildings | side-view battle trees used on a top-down map | draw map trees top-down 3/4 |

## Scorecard — the last step of every run

Append one row per pass to `scorecard.csv` beside this file, then run `skill-improver` on this
skill.

`date,scene,layer,generations,edits,passes,minutes,usd,user_verdict,note`
