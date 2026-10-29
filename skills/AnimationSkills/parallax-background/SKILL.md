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
  into any layer; contact shadows belong under the characters.
- **Palette.** Sky and far layers cool; ground and near layers warm and saturated; the most
  saturated, highest-contrast colours are kept for the characters.
- **Fighter zone stays quiet.** Between about 35% and 75% of the height, where the fighters
  stand, no high-contrast edge, no trunk or vertical line behind a head, no landmark.
- **No landmark that shows the repeat.** Balanced, even content; a strong one-off feature repeats
  every 3840 px and gives the loop away.
- **Greyscale check**: the archer and the assassin placed on the stacked scene, desaturated;
  both must stand out by value alone.

## Method

1. **Layer by layer from the start; no whole-scene painting.** The local model cannot paint a
   whole scene with level ground — six tries all tilted the ground into the distance. The user's
   call: build each layer on its own. The first layer the user approves sets the style prompt
   and seed family for the rest. Grass blades along the top of the ground are never part of it:
   they are the grass-edge layer. The fine detail on the ground (small stones, pebbles, grain) is
   what makes it work.
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
   back. Check by tiling it three times side by side. The shared `runq.py` adds scene 1's
   `ref_D.png` as a reference unless `NOREF=1` is set, and Qwen then copies its boulders — set
   `NOREF=1` for any layer that is not scene 1's ground.
5. **Alpha**: from the blockout mask; far layers keep a hard-cut edge (soft edges fringe). Opaque
   layers (sky, ground fill) need no key. A trunk 2–4 px wide goes half-transparent when
   downscaled — force its alpha to 255 and regrade it.
6. **Tint by code is allowed** — a still background layer has no body; lightening, desaturating
   and shifting a far layer toward the sky colour is a colour grade, not a pose. Each tree depth
   is graded on its own: a far trunk is a lighter grey than a mid one, never darker.
7. **Trees beside the fighters.** Where a trunk would stand beside a fighter's head, lift the tree
   so its foot sits on the hill in the band between the hill's solid line and the back row's head
   box (battle 1: y 340–346) — never fade the trunk, which leaves ghost stubs beside the hoods. Each
   trunk ends in a tuft tinted from its own layer, never in hill colour. Lifting costs size, and
   that thins the edge: say so with the clip, and bring density back by spacing, not scale. A
   "changed trunk pixels" check counts any nearer layer's alpha as cover.
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
10. **Preview**: stack the layers, slide each by its factor across two loops, render an mp4 (and a
   still with both characters on it) for the user. That clip is what the user judges. Encode at
   1280 wide, crf 20, with one keyframe for the whole clip
   (`-x264-params keyint=<frames>:min-keyint=<frames>:scenecut=0`) — at crf 26 with the default
   keyint, figures fixed to the camera over the scrolling scene shimmer at every keyframe. A
   whole-frame flicker number hides that: measure neighbour-frame change inside the figure masks.
   Over 16 MB it cannot go on the Queue page. `preview.py` truncates
   `ground/v2/preview/measure_preview.txt` in any mode, so copy it (and the scripts it calls) into
   the run's own folder before running it. A preview with a crowd of fighters idling and attacking is
   `effects-overlay`, step 6; a top-down menu map is `menu-map-buildings`.

**Acceptance rows must be reachable.** Before a figure-against-ground contrast row goes into a brief,
measure what the flat ground colour alone scores: with scene 1's soil D, archer minus its ring is
−36, so a row asking for ≤ −40 can never pass and needs another threshold or metric.

**The formation is a mirror — measure before rebuilding.** When the user says one side still looks
wrong, run `scenes/battle1/formation/measure.py` (per-column centres for both groups) first. A
pixel-exact mirror can still read differently, so ask which line looks crooked — heads, quivers,
bows, or the stagger direction — before changing anything.

Unity wiring (a parallax script per layer, Tiled SpriteRenderer with Full Rect + Repeat, one PPU,
no Pixel Perfect camera for this painted art) is application code — not annie's; report it.

## Scorecard — the last step of every run

Append one row per layer pass to `scorecard.csv` beside this file, then run `skill-improver` on
this skill.

`date,scene,layer,generations,edits,passes,minutes,usd,user_verdict,note`
