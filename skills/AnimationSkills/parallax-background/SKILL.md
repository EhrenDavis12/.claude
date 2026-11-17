---
name: parallax-background
description: Make the layered, horizontally looping background art for a side-view battle scene — sky, clouds, far mountains, mid hills, forest edge, ground, foreground — one image per layer, local and free, in the characters' style.
---

# Parallax battle background

A battle scene's background is a stack of separate images, one per depth, each a seamless
horizontal strip. In the game each layer slides at its own speed, so the far ones barely move
and the near ones move with the ground. This is how shipped side-view games do it: Hollow
Knight, Ori and Cuphead are built of layered painted planes; the GameMaker parallax write-up,
the Slynyrd landscape blogs and the CraftPix cartoon forest packs give the numbers below. Copy
it; do not invent a new structure.

**Local and free only.** Layers start as code blockouts; style edits and seam repair are
Qwen-Image-Edit (`src/LLMs/generate.py edit`), and alpha comes from the blockout's own mask. No paid model without the user's say-so for that job;
when local fails at the budget, the item goes to `blocked` with a question and the run moves on.

## The layer stack — scene 1: daytime forest edge / grassland

Reference height 1080 px. Every strip is **3840 px wide** (2× a 1920 screen, covers a 2400 px
phone) and loops left to right. Factor = how much the layer moves with the ground (0 = fixed to
the camera, 1 = the ground).

| # | Layer | Content | Size | Alpha | Factor |
|---|---|---|---|---|---|
| 0 | Sky | blue gradient, light glow upper left | 3840×1080 | opaque | 0 |
| 1 | Clouds | many separate single-cloud cut-outs, varied sizes, never one continuous strip; the game places them on 2–3 cloud layers (far ones smaller, paler, slower) | one sprite per cloud | cut-out | 0.02–0.08 + slow drift |
| 2 | Mountains | a few separate single-mountain cut-outs, varied shapes, plus paler smaller ones for a back range; soft haze at each base, hidden by hills and trees; never one repeating strip | one sprite per mountain | cut-out | 0.05–0.12 |
| 3 | Mid hills | rolling blue-green hills, small tree clumps | 3840×400 | cut-out | 0.3 |
| 4 | Trees | many separate single-tree cut-outs, varied sizes and kinds, never one continuous strip; the game places them on 2–3 depth layers, and plants some on the ground itself at ground speed so the ground blends into the background | one sprite per tree | cut-out | 0.4–0.7; 1.0 when planted on the ground |
| 5 | Ground | a texture only — soil with fine detail (small stones, pebbles, grain), no grass blades on top. Covers most of the screen: from the horizon down to the bottom, tall enough for a 3-column × 5-row formation on each side; the approved formation layout sets the horizon | 3840 × layout height | opaque | 1.0 |
| 5b | Grass edge | the blades of grass along the top of the ground, its own layer | 3840×100 | cut-out | 1.0 |
| 6 | Shrubbery | many separate cut-outs: bushes of different sizes, weeds, grass patches; those sitting on the ground move with it, only clumps in front of the fighters are foreground | one sprite each | cut-out | 1.0 on the ground, 1.3 in front |

Unity draw order: Sky, Clouds, Far, Mid, Trees, Ground, Grass edge, Characters, FX, Foreground.

## What makes it read as depth (the reviewer checks every one)

- **Atmospheric perspective.** Each layer further back is lighter, less saturated, lower
  contrast, less detailed, and shifted toward the sky colour. Far mountains sit within about 15%
  of the sky's value; mid hills within about 30%. Only ground and foreground use full range.
- **Outline weight falls with distance.** Characters heaviest (black). Ground and foreground
  2 px dark-tinted. Forest edge 1–2 px dark green. Mid hills 1 px tinted at most. Far layers no
  outline. A black line on a far layer pulls it forward and flattens the scene.
- **One light direction** (upper left) on every layer and the characters. No cast shadows baked
  into any layer; contact shadows belong under the characters — drawn above ground props such as
  the grass strip, or the props hide them, and deeper than any ground prop's shadow (about 25–30%
  dark), soft-edged, never a black blot.
- **Palette.** Sky and far layers cool; ground and near layers warm and saturated; the most
  saturated, highest-contrast colours are kept for the characters.
- **Fighter zone stays quiet.** Between about 35% and 75% of the height, where the fighters
  stand, no high-contrast edge, no trunk or vertical line behind a head, no landmark.
- **No landmark that shows the repeat.** Balanced, even content; a strong one-off feature repeats
  every 3840 px and gives the loop away.
- **Greyscale check**: the archer and the assassin placed on the stacked scene, desaturated;
  both must stand out by value alone. Set the separation bar (`gsep` in `shadows.py`) from the
  roster actually placed: 56.9 was archers only; the full v2 roster scores about 27–29.

## Method

1. **Layer by layer from the start; no whole-scene painting.** The local model cannot paint a
   whole scene with level ground — six tries all tilted the ground into the distance. The user's
   call: build each layer on its own. The first layer the user approves sets the style prompt
   and seed family for the rest. Grass blades along the top of the ground are never part of it:
   they are the grass-edge layer. The fine detail on the ground (small stones, pebbles, grain) is
   what makes it work. **Every scene is built like the meadow: each element its own layer**, made
   from its own source parts. Never split a finished, composited strip into layers by colour (a
   join split by R−B < 8 shipped once): the split slices objects across two speeds, and when the
   stage scrolls the user sees them "cut in half".
2. **Code blockout first, never a text prompt.** Text-to-image failed 3 of 3 on every layer tried
   (floating blocks, tilted ground, merged cloud banks, cropped bottoms). Draw each layer as a code
   blockout — periodic over 1920 so it loops by construction (peaks, humps or pebble placement
   wrapped at the ends), one shape per sprite for clouds, mountains, trees and shrubs — and keep
   the blockout's mask as the alpha, eroded 2 px. Then decide per layer whether Qwen paints it:
   - **Painted shapes** (clouds, mountains, mid hills, tree sprites): one Qwen style edit per 1920
     half or per sprite sheet, the blockout as picture 1, "no outline, no black line" in the prompt.
   - **Textures and flat-shaded rock** (ground soil, cave floor, wall, ceiling, shrubs): the
     code-drawn version is the deliverable and Qwen is skipped. Qwen adds nothing there: it draws
     3–4 px near-black outlines a grade cannot thin, turns round discs into glossy beads, and adds
     cracks and vignettes to rock. Shrub finals were drawn fully by code from the blockout labels.
3. **Code-drawn shapes that pass**: flat two-tone shading with the lit face upper-left (say "lit
   face upper-left" in a brief, not "split upper left to lower right"), soft seams of about 3 px
   and −24 luma rather than outlines, every corner 60–70° or wider (sharper cusps read as horns or
   spikes), and boxy shapes re-rolled. Blur-only softness reads as sky or fog, and a flat blockout
   plus grain reads as sky over sea — rock needs slabs or chips with two flat tones.
4. **Make it loop**: a periodic blockout already loops. Where a painted half meets the next, shift
   the strip half its width on x so its two ends meet in the middle, repair a tapered band at
   least 32 px wide there with a Qwen edit of a crop around the seam (pic1 = pic2 = the crop,
   "continue the landscape across the join, change nothing else"), paste back only the band, shift
   back. Check by tiling it three times side by side.
   **Mirror tiling is the fallback for a strip whose ends will not meet** (the user, 2026-10-29):
   in the scrolling scene, every other copy is flipped on x — start→end, end→start, start→end —
   so each join puts an edge against its own mirror and always lines up. In Unity it is one
   setting (Mirrored wrap on the texture, or a flipped copy beside it). The cost: every feature
   comes back flipped once per two widths, so a distinctive rock or a light coming from one side
   gives it away — fine for plain soil and grass, wrong for anything lit from one side. The shared `runq.py` adds scene 1's
   `ref_D.png` as a reference unless `NOREF=1` is set, and Qwen then copies its boulders — set
   `NOREF=1` for any layer that is not scene 1's ground.
5. **Alpha**: from the blockout mask; far layers keep a hard-cut edge (soft edges fringe). Opaque
   layers (sky, ground fill) need no key. A trunk 2–4 px wide goes half-transparent when
   downscaled — force its alpha to 255 and regrade it.
6. **Tint by code is allowed** — a still background layer has no body; lightening, desaturating
   and shifting a far layer toward the sky colour is a colour grade, not a pose. Each tree depth
   is graded on its own: a far trunk is a lighter grey than a mid one, never darker. A grade
   that keeps a layer off the wall's palette shifts hue and warmth and never darkens: darkening
   made near-black specks.
7. **Trees beside the fighters.** Where a trunk would stand beside a fighter's head, lift the tree
   so its foot sits on the hill in the band between the hill's solid line and the back row's head
   box (battle 1: y 340–346) — never fade the trunk, which leaves ghost stubs beside the hoods. Each
   trunk ends in a tuft tinted from its own layer, never in hill colour. Lifting costs size, and
   that thins the edge: say so with the clip, and bring density back by spacing, not scale. A
   "changed trunk pixels" check counts any nearer layer's alpha as cover.
   **Many cards from one approved tree set**: vary each copy by scale (±8%) and luma (±6%) only,
   keeping far trees lighter. Never mirror-flip a card shaded for the upper-left light — the flip
   puts the light on the upper right. Order the copies at random with no same source side by
   side and a cap on runs of one shape; picking each next tree "most unlike the last" makes a
   pine/round/pine/round beat that the eye catches even when neighbour-difference numbers pass.
8. **Speed and colour per layer.** Never put wall-coloured pixels in a layer that moves at floor
   speed: it drifts against the slower wall and shows a step at the join. A prop that hangs from or
   stands on a layer moves at that layer's factor: stalactites move at the ceiling's 0.85, never
   1.0, or they slide off the ceiling. Draw their roots 24 px above the ceiling's edge and order
   them under the ceiling layer, so the join is seamless.
9. **Sparse sprite props are spaced per screen, not per loop.** A loop-wide gap CV passes while one
   screen still shows an even beat (stalactites: loop CV fine, an even 5–6 sprite run at the wrap
   scored 0.08 in its window). Before key review, measure centre-spacing std/mean over every
   1920 px camera window across the loop, wrap included; every window needs 0.25 or more. Get there
   by pairing some sprites at 120–180 px gaps and opening others to 450–700 px. Code-drawn sprites
   pass this way with no Qwen.
10. **Foreground occluders need room.** With a full 15-a-side roster and a 16 px no-go box round
   each fighter, edge occluders shrink below readable (under 1% coverage). The foreground look
   needs either some overlap of the fighters' lower legs or cards that run past the frame edge —
   say which with the still. An occluder drawn after a vignette must be tinted darker than the
   darkened layer under it, or it lightens into a ghost — so measure it against the ceiling
   after the vignette is applied, never before.
11. **Preview**: stack the layers, slide each by its factor across two loops, render an mp4 (and a
   still with both characters on it) for the user. That clip is what the user judges. Encode at
   1280 wide, crf 20, with one keyframe for the whole clip
   (`-x264-params keyint=<frames>:min-keyint=<frames>:scenecut=0`) — at crf 26 with the default
   keyint, figures fixed to the camera over the scrolling scene shimmer at every keyframe. A
   whole-frame flicker number hides that: measure neighbour-frame change inside the figure masks.
   **Check every package in motion**, hand-offs included: the scrolling mp4 plus a shift-vs-y
   profile on frame pairs (each row's measured shift must match its layer's factor, with no row
   split between two). `profile_v2.py` reads opaque strips only: on a sparse sprite layer its
   90 px pairs find no shift, so it needs a sparse-layer mode (an `annie-tool-writer` job) before
   it can judge one. A still at scroll 0 is not enough — the game pans the stage in its intro.
   Over 16 MB it cannot go on the Queue page. `preview.py` truncates
   `ground/v2/preview/measure_preview.txt` in any mode, so copy it (and the scripts it calls) into
   the run's own folder before running it. A preview with a crowd of fighters idling and attacking is
   `effects-overlay`, step 6; a top-down menu map is `menu-map-buildings`.

**Acceptance rows must be reachable.** Before a figure-against-ground contrast row goes into a brief,
measure what the flat ground colour alone scores: with scene 1's soil D, archer minus its ring is
−36, so a row asking for ≤ −40 can never pass and needs another threshold or metric.

**The battle ground needs no tile set** — one looping strip plus free props already is "one big
tile". Tiles are for top-down maps, ledges and cave floors, and a tile set's tile size comes from
the character's on-screen height, never from the screen width.

**The formation is a mirror — measure before rebuilding.** When the user says one side still looks
wrong, run `scenes/battle1/formation/measure.py` (per-column centres for both groups) first. A
pixel-exact mirror can still read differently, so ask which line looks crooked — heads, quivers,
bows, or the stagger direction — before changing anything.

Unity wiring (a parallax script per layer, Tiled SpriteRenderer with Full Rect + Repeat, one PPU,
no Pixel Perfect camera for this painted art) is application code — not annie's; report it.

**Hand-off to forge** — a drop-in folder (`local_runs/handoff/BattleCave/`): the layers,
`scene.json` (depth, factor and order per layer), the fighter slots and a loader. Annie builds it;
forge copies it in.

- **Ship it under a `Resources/` path** — the loader loads by path, and nothing else is found.
- **Guard the import size**: set each texture's max size to its real width or above, and check it
  after import — the default cap shrinks a 1920+ strip.
- **Blend masks are data, not colour.** The game's importer treats only `M1_`-prefixed files as
  data textures, and its iPhone override ASTC-compresses masks. Say in the forge note which files
  are masks so they import linear and uncompressed.
- **One layer, one depth.** A layer that spans two depths (a wall at 0.8 and a floor at 1.0) is
  split, so each part moves at its own factor.
- **Check at the game's aspect (~19.5:9)**, not only 16:9: a card duplicated off-frame for the
  wrap shows at the wider edges. Drop any duplicate the wider frame does not need.
- **Preview in Gamma colour space** — the game uses Gamma, not Linear, so a check judged in
  Linear does not hold in the game.

## Scorecard — the last step of every run

Append one row per layer pass to `scorecard.csv` beside this file, then run `skill-improver` on
this skill.

`date,scene,layer,generations,edits,passes,minutes,usd,user_verdict,note`

## Ground and wall variety: one blend method, not tiles

Tile sets are not used for the battle ground (the user, 2026-10-29: a tiled ground showed its
grid through repeating pebble clusters). **Every blended surface in every scene is built one way**
(the user, 2026-11-15: "we should just have the one method of how to build these things"): a
white-slot texture, a black-slot texture and a grey mask, mixed by the game's `GbMix` shader —
m = saturate(mask.r × MaskMul + MaskAdd), MaskMul 1, MaskAdd 0, blended in linear under Gamma and
premultiplied by the white slot's alpha. The meadow is grass + soil; the cave floor is dirt +
stones, its back wall two rock types, its join edge J1 + J1 recoloured in the floor-rock tones.
A new pattern on the mask changes the look without redrawing either picture. No new generation:
the surfaces are built from approved textures.

`local_runs/scenes/_shared/gbmix.py` is the shader's twin in Python, the one tool for this (run it
with `src/Asset-Gen-Framework/.venv/bin/python`): `mix --white --black --mask [--scroll --window]`
composites exactly what the game draws, `mask --w --h --segments --seed [--labels ids.npy --grow 2]
[--light-below Y]` makes a pattern, `selftest` checks it against the formula. The meadow's blend is
in the Unity sandbox (`Assets/Annie/BattleScene1GroundBlend`, masks M1–M3).

- **Chained, white-ended patterns.** To hide any repeat along a long strip, chain 3 or more
  segments of unequal width (no two within 15%), each starting and ending all white, so every join
  is seamless (the user, 2026-10-29: "each sade patter ends and start with a all white on the ends.
  So diffrent patters remove visable patterns"). Column 0 must equal column 3839. The meadow's own
  M1 is not white-ended (edge columns about 138) — report that gap, do not copy it. Make three
  patterns a surface, overlapping under 0.5 IoU; the game picks one per battle.
- **Hard-edged objects snap whole.** The soft grey alone cannot show slabs or stones whole: the
  meadow's mask over the cave stones drew 91% of stone pixels half-faded, and more contrast only
  reached 11% whole while cutting stones in half. So each stone or slab takes one value, 0 or 1,
  from the grey at its centre (`--labels`, from the approved per-object label map, each object
  grown 2–3 px); the loose dirt between objects keeps the soft grey. Pass: at most 1% of object
  pixels at 0.05 < m < 0.95. Masks are full size: a quarter-size mask cannot hold an edge under
  12–16 px. Show the meadow-exact version beside it on the sheet. Snapped stones keep their dark
  outlines, so the floor behind the fighters gets busier than any soft-mask version (about 6× the
  edge count in the fighter zone on the cave): say so with the first still, not after.
  `gbmix.py`'s snap has no threshold/bias or cluster-aware option yet — an `annie-tool-writer`
  job; until then expect to set some slabs by hand (11–14 of 39 on the cave wall).
- **Slab clusters**: an outline with no thin horn, hook or hammer point and corners of 60° or
  wider; no slit of the other rock inside a cluster. A 30 px morphological opening removing
  nothing is not enough — it misses a slanted horn — so also run a corner-angle test (the share of
  a small ring round each boundary point that is inside the shape, read as an angle; pass at 60°
  or wider) on every rock-type boundary. Slabs on the front row alone drop coverage below 35%. Scan
  for rock-type edges from y 280, not 340, along slanted runs as well as columns: a column-only
  detector misses slanted slab sides and dashed seams, and a slab side that starts above the head
  tops still slides behind them.

**The join between ground and back wall is its own piece.** Design it on its own and show it to
the user before it ships; a quick fix (a soil lip in front of the wall) was not approved: "The
land between the ground and the back wall doesn't look quite right". J1 is the approved join top.
Its top matches the old cave's luma within about 5 in the band behind the back row's faces
(y 381–410) — a light, level ribbon there was rejected — and breaks the level line by dipping
down, never up; only about 18 px of dip fits above the floor line.
