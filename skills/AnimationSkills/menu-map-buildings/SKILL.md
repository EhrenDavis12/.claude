---
name: menu-map-buildings
description: Make the main-menu map — a top-down 3/4 still map of a town with roads, a pond and fields — and its buildings as separate sprites with shadows and anchor points, plus the game's menus in the map's style (pages, pop-ups, buttons, item icons) as game-ready text-free pieces with a layout.json, local and free. Use when the user asks for a menu map, a town or world map, building props for one, or menu and UI mockups to match it. Not for a side-view battle background (`parallax-background`).
---

# Menu map and buildings (top-down 3/4, still)

A menu map is one still ground image seen from above at a 3/4 angle, plus **each building as its
own sprite** with its own shadow and anchor points, placed on the map by game code. Nothing loops
and nothing scrolls.

**Local and free only.** Shapes are code; Qwen-Image-Edit (`src/LLMs/generate.py edit`) is used
only where it helps. No paid model without the user's say-so for that job.

**Everything is tinted to the approved palette** — every UI piece, icon, map and building
(palette_v4 option 3; the user, 2026-11-13: "Make sure as we go through everything that we do
tinted with our color skin."). An untinted piece is not done.

Working folder: `src/asset-animation-demo/local_runs/scenes/menu_map/` — `k0.py` (the shared code
blockout and masks, `blockout/layout.json`), `styleA.py` (fully code), `styleC_buildings.py`
(flat fills + ink by code), `fullbleed.py`, `runq.py`, `common.py`. Python:
`src/Asset-Gen-Framework/.venv/bin/python`.

## Method

1. **Code blockout first** (`k0.py`): map, roads, pond, and one blockout + mask per building. Every
   style is built from the same blockout, so styles compare like for like. Roads must meet each
   door.
2. **Alpha from the mask, soft-edged** — never keyed. Draw the mask at 3x, erode it 6 px there
   (2 px at 1x), OR the thin parts (poles, flags, fence rails) back at 3x, and area-reduce: the
   alpha is that coverage. Partial pixels outside the old hard edge take the ink colour. Recolour
   with plain `rc`, not `rc_over` — `rc_over` re-solves edge alpha and moves it 5–7 levels
   (`game_ready_v5/map/build_v5.py`). Every attachment touches its body in the mask: each sprite
   is **one connected piece**. Pixel-art poles snap to the pixel grid.
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
8. **Cast shadows are one closed footprint projected from one ground line.** Per building, pick
   ONE ground line (where its front feet meet the ground), take the CLOSED footprint — fill
   between the outermost feet, then `binary_fill_holes` — project that, and cut everything above
   the ground line. Never project per-column bases: gap columns streak and overhangs invent
   grounds. **Shadows fall back and to the right** (the user, 2026-11-13: "For the map the V2
   alternative it looks great use that." — the back set, `ui_parchment/game_ready_v2/map/
   pieces_back`, made by `shadows_v2.py`). A dome or rock prop (the cave) does not fit the flat
   ground line — it turns into a slab — and needs its own method that keeps its silhouette.
9. **Adding buildings to an approved map: rebuild it byte-exact first** (K0, `game_ready_v5/map/
   k0_run.py`) and prove the md5s match before changing anything. Then each new building:
   - clears the old neighbours' flag and pole shadows — a shadow landing on a new roof was a
     review finding;
   - a small hanging sign has a visible link below its arm, or it reads as a bag;
   - side-by-side crates sit on one top line, never stepped — stepped reads as stairs.

## Menus and UI in the map's style

**The house UI style is chosen: Scroll v3 "R04 One Rod"** (the user, 2026-10-29: "R04 One Rode
is our choice for all our menus and buttons. Good design and its not to busy ... apply it to any
menue items we create when building in unity or need a button or menu"). Aged parchment on one
wooden rod with a curled free edge, on the Scroll page layout. Every new page, pop-up and button
— mockup or Unity — starts from it: `ui_parchment/scroll_v3/R04_OneRod/` (`page.png`,
`modal.png`, `buttons.png`, `sheet.png`), drawn by `scroll_v3.py`. Known small fault: the curl is
orange on the panel but dark red on red buttons. To make them one colour in a job, subclass and
take the curl pixels from a same-size aged render (`R04C` in `victory_v1/build_victory.py`); moving
that into `scroll_v3.py` needs `annie-tool-writer`. Other styles below are history; do not offer
them again unless asked. The words on these pieces are mock-up only (see below).

**No word is ever baked into an image.** The game draws every word in code with the approved font
(option 11, see Lettering), so a panel or button with lettering on it cannot go into the game
(the user, 2026-11-12: "Those assets should've been game ready"). A mock-up with words on it is
fine for the user's pick, but it is not the deliverable. A menu or UI job is done only when it
hands over, per screen:

- **Text-free panels** — pages, pop-ups, plates, tabs — as transparent PNGs.
- **Blank buttons**, each in its normal, pressed and selected state.
- **Icons as separate transparent PNGs**, never pasted onto a panel or button.
- **9-slice notes for every panel that stretches**: the four border insets in px, and which
  middle bands may stretch or tile.
- **`layout.json`** per screen: every piece's file and box (x, y, w, h), and every text slot —
  `id`, the words, box, size, colour, alignment.
- **A check sheet rebuilt from the pieces alone**: the PNGs placed by `layout.json` and the words
  drawn by code (`ink_font` or the `bake.py` atlas) into the slots, beside the approved mock-up.
  A slot whose words do not fit its box, or a piece that does not line up, shows here.

**A code-built screen is made game-ready by re-rendering it with the word step off, never by
painting the words out.** Re-run the approved builder with `ink_font.text` / `Ink.paint` wrapped to
record each text slot (words, box, cap, colour, anchor) at the call and skip the ink, and keep
every `s.seed()` call, so the paper, rod and buttons come out pixel for pixel as approved
(`ui_parchment/game_ready_v1/build_pieces.py`, checked by `check_pieces.py`).

- **Compare pieces against the approved picture outside the word ink dilated 3 px.** The approved
  pictures were recoloured after the words were blended in, so word edges on gold and red never
  match the re-render — up to 48 levels, invisible by eye. Inside that band is not a defect.
- **Re-solve the soft-pixel alpha of a recoloured piece against the picture underneath**, not
  against the pre-recolour render, or its edge carries the old colour.
- **A leftover-ink box measure false-flags rod shading, ruled lines and the icons in price boxes.**
  Read its flags by eye before calling any of them ghost ink.
- **Page paper carries the old map's erased path as a pale swirl.** It is in the approved paper,
  not a leftover; say so with the check sheet so nobody cleans it. It cannot be cleaned by
  patching — only 54% of the page is real paper, and two patches failed (a flat silhouette, then
  a chevron). A clean paper gets its warm edges and age back in one step from a per-channel
  low-frequency tone map: multiply each channel by `G_sigma(old) / G_sigma(new)`, Gaussian sigma
  200, old = the approved `paper.png` (`game_ready_v6/paper/paper_v6.py tone 200`). Use that, not
  Qwen re-renders — a fresh Qwen parchment matched by one linear colour map comes out pale, flat
  and edge-less.
- **Only the v1 page paper is approved** until the user approves a newer one. `paper_v3b` is not,
  so every page built on it (the v3 settings, about, shop and character-select `page.png`) never
  ships. `game_ready_v3/paper_measure.py` gives v3b a mid-band ratio of 0.773.

**New UI pieces** follow `ui_parchment/game_ready_v4/build_v4.py`: import `scroll_v3`, `ui_lib`,
`build_pieces` and `unroll_lib` read-only (the `build_pieces` import calls `S3.calibrate()`), and
write the md5 before-snapshot of those files first. Check with `check_v4.py`.

- **Judge the pieces-vs-approved diff on opaque pixels only.** Soft-pixel diffs are invisible.
- **A modal's height fits its slots.** Measure the dead band between the body text and the
  buttons; a confirm panel at 520 tall had to come down to 440.
- **Qwen ink glyphs** (pause and the like): write "two upright bars" plainly, or it adds slashes.
  Pick the render whose red matches the Q1 close X.
- **Unroll gap shadows are a fall-off curve.** Take the profile from the approved unroll as a
  curve, and check the fall-off itself, not only the max alpha — three passed on max alpha as flat
  strips.
- **The unroll's moving strip also carries the panel's bottom-edge shadow beside the rod.** Zeroing
  the gap shadow outside opaque rows leaves a pale gap at rest. Keep the run-to-knob strip, and
  give `panel.png`'s 15 rod-side columns the panel's own bottom-edge shadow, within ~10 luma of
  v3 at 100%.
- **Shadow checks need an at-rest crop**: 100% open, at both knobs — mid-opening stills miss the
  rest-state gap.
- **Palette checks compare with the approved palette screen's own button**, not the option 3 corner
  swatch. Piece-by-piece recolour edges differ by a few levels invisibly, so a 2–4 level limit
  fails good pieces.
- **Character select uses each character's approved relaxed pose, placed on a scroll by the game**
  — no portraits (the user, 2026-11-13). The layout gives each slot a box, a feet anchor and a
  scale (`game_ready_v3/charselect_08/`); characters are not recoloured.

**Removing words from painted art** (no builder to re-run): clean the paper underneath — no
smudge, no ghost letters, the grain and tone carried through — and measure the leftover ink in each
old text box against free paper beside it (dark pixels over the paper's own level). Clean by eye at
full size as well; a ghost the measure misses shows once the code-drawn words sit over it.

**The results pop-ups are chosen: Victory 2 and Defeat 9** (the user, 2026-11-01), `opt2` and `opt9`
in `ui_parchment/victory_v1/build_victory.py`. Victory 2 is a tall scroll with the loot as a written
list: icon, name and amount on each ruled line. Defeat 9 has Retry and Exit on the buttons in the
game's lettering, which was shown as applying to every button. Each opens by code (`unity-effects`,
a scroll that unrolls). `ui_parchment/font_v1/build_frames.py` renders both with every word in the
game font (`frames/victory2.png`, `frames/defeat9.png`), placed by baseline — those are the approved
mock-ups; the game pieces are their text-free panels, blank buttons and icons plus `layout.json`.

**A script importing `scroll_v3` calls `S3.calibrate()` once before its first render.** Without it
`_GAIN` stays 1.0 and the paper goes dark and orange while the rod and red buttons do not, so the
rod stands out and tan buttons sink.

**No phone-size views for now** — on any sheet in this recipe, icons and HUD included (the user,
2026-10-30: "I don't need the mobile examples right now so don't worry about those"). Skip the
phone view and the `at phone size:` lines until they ask again.

**Recolouring menus or the map into a palette: keep the paper warm by default.**
`auto/style_guide/palette_v4/recolour.py IN OUT <option> --paper` keeps warm hues (the parchment,
gold) and moves the rest — lake, red buttons, character colours. A full recolour (no `--paper`)
turns the paper mustard-orange, flattens selected-state highlights (a selected tab, a selected shop
tile) until they are hard to see, and washes out gold coins. Say plainly with the sheet that
kept-warm is close to the original and may read as "not much changed". Show before / full / kept
warm side by side, and check selected states and gold on each. `recolour.py` has no protect mask,
so a portrait's skin and accents shift too (a teal mask turns blue): a per-job mask
(`menus_map_v1/skin.py`) is the stopgap; a `protect_mask` option in `recolour.py` is owed to
`annie-tool-writer`.

Pages, pop-ups and buttons are **all code** on the map's own paper — no Qwen. Working folder:
`src/asset-animation-demo/local_runs/scenes/ui_parchment/` — `paper.py` (the clean paper),
`ui_lib.py` (the shared kit: ink, paper, fonts), `opts_a.py` / `opts_b.py` (one class per
style), `ui_run.py` (renders each option's `page.png`, `modal.png`, `buttons.png`, `sheet.png`,
`measure.json`), `compare.py` (all options on one sheet).

- **An all-ink style still needs one accent** (red) on the primary button, or primary and
  secondary read equal. One red primary per screen and a Buy button on every row of a list shop
  cannot both hold: the brief says which wins.
- **The full OFL copyright line does not fit one line of a scroll at cap 28** — plan it as three
  lines on an about or credits page.
- **Label-to-ornament clearance ≥ 8 px**, measured — rollers, plates and borders crowd labels.
- **Measure every accent colour**: grey drifts in where the style says blue.
- Woodcut stipple reads as flat brown at 1920; shade with bold cross-hatch bands instead.
- **A rolled paper end is drawn side-on at paper height**: tube shading, stepped edges, a strip
  of the paper's back with a gap, and a tangent exit onto the sheet. An end-on ellipse reads as
  a circle.
- **Hatching follows the roll's curve**, over a paper-tone wash. A straight grid reads as basket
  weave and goes solid when dimmed.
- **Variants differ in silhouette, not just stroke pattern.** Curl, stacked turns and hatched
  ends all blur into vertical stripes at thumbnail size — check every option at small size too.
- **The measure script computes modal roll-to-content clearance**, not just the modal's box.
- A key artist and key reviewer dispatched in the background can be resumed with `SendMessage`
  for the fix round. If a resume fails, fall back to a fresh hand-off brief. To see whether one is
  still writing, use `stat -L` on its task output: the path is a symlink.
- **Measure scroll paper in a centre window on free paper.** A whole-paper median reads about 13
  levels low on correct paper (203,167,119 against 215,175,123).
- **Darkening a scroll after calibrate**: `dark=0.30` goes grey-olive; 0.17 stays warm. `dark` and
  `scorch` leave the rod and buttons light, so the rod can read slightly brighter on that paper.
- **A tan button reads about 8 levels lower at 250x100 than at 310x110.** That is shading, not a
  colour error.
- **A silhouette check at small size is a judgement, not a measure.** At 360 px the artist and the
  reviewer chose different pop-ups, the reviewer on the icon row and the taller scroll. Report the
  reviewer's call and its reason.
- **Run a batch of Qwen edits under a chain script** (`lettering_v2/chain1.sh`): its renders survive
  a worker dying and the next worker picks them up from the files. Restarts took about half of
  a 180-minute lettering round.
- **Take the md5 before snapshot at the start of the run.** One written after the work, in the same
  second as the after snapshot, proves nothing.
- **A check widened to pass needs its finding traced.** A pad widened from 3 to 8 px to pass 4 px was
  a 3 px speck of the D, and 5 px was enough.
- **Waiting on subagents, loop for 540 s.** The 10-minute Bash limit moves a 590 s loop to the
  background.

### Icons

Item icons (potions, weapons, armour, food) for menus and buttons. Working folders under
`src/asset-animation-demo/local_runs/scenes/ui_parchment/`: `icons_v1/` — `items.py` (one code
spec per item, unit space 0..100, light upper-left), `blockout.py`, `styles.py` (one Qwen phrase
plus finish settings per style), `qwen_run.py`, `build.py`, `measure.py`, `sheets.py`; and
`icons_v2/` — `traces_v3.py` (outline polygons traced over the paint), `overlay_v3.py` (draws a
trace over its paint to check it), `finish_v3.py` (the chosen finish), `measure_v3.py`,
`pick_sheet_v3.py`. The unsuffixed and `_v2` copies are the earlier round; work in the `_v3` ones.
A set of related icons gets its own folder, `icons_currency/gold/` and `icons_currency/crystal/`,
each a self-contained copy on a 4x4 sheet: `items_<set>.py`, `blockout_<set>.py`,
`qwen_<set>.py <try>`, `traces_v3.py`, `overlay_all.py <out> <src>` (every trace on one sheet),
`finish_v3.py`, `measure_<set>.py`, `pick_sheet_<set>.py`. Gold also has `autotrace_gold.py` (draft
polygons from the paint, checked by eye after) and `GLOW` as a constant in its `finish_v3.py`.

**Route: code blockout → one local Qwen edit → crop the raw paint → trace the mask to the paint
→ light finish.** This is the chosen look for every icon (the user, 2026-10-30, picking boot B1
made this way; all four shields made this way were liked).

1. `python blockout.py` — the same items in the same order for every style, on flat grey 128.
   **Qwen's yellow wash spoils seven cells of a 4x4 sheet**: (col,row) (0,0)–(2,1), (0,2) and
   (1,2). Only about nine cells a sheet come back clean, so from try 1 put the important icons in
   the right column and the bottom row, and throwaways in the washed cells.
2. `python qwen_run.py <style> [try]` — **one** edit per style (4 steps), prompt saved beside the
   result. Run a batch under `perl -e 'alarm shift; exec @ARGV' 2400` per edit. **Pass the next
   unused try number** — a used one silently re-runs that old try (14 minutes lost).
3. **Crop the raw Qwen cell and keep its paint.** Do not run the old heavy finish (`build.py
   finish`: blockout mask, low-pass, despeckle, code boss and buckle, 10 px burn) — on the boot
   and shield it removed planks, rim, arch and buckle the paint already had. When an icon looks
   flat, look at the raw cell before making a new edit: half the boot and shield options came
   from existing paint at no edit cost. Each trace names its own `src`, so one sheet can mix cells
   from different tries.
4. **Trace the outline to the paint by hand** in `icons_v2/traces_v3.py` (`poly` in cell pixels,
   256 a cell; `poly_add` for parts such as a handle; `holes` for real see-through holes, which
   are subtracted) and check it with `python overlay_v3.py`. The mask follows the paint, not the
   blockout, and **leaves cast shadows out**. Starting a trace from the blockout shape fits,
   because Qwen follows the blockout closely, but check notches for slivers of plate grey. **A
   grey gap enclosed by paint (a helmet plume) matches the plate, so check every enclosed gap by
   eye** and trace it as a hole if it is one — the artist missed one.
5. `python finish_v3.py <ids> --cap 5` — alpha from the traced polygon (eroded 1 px, holes
   filled, then `holes` subtracted, one piece), colour bled outward from inside, the I03 burnt
   edge with **the burn capped at 5 px**. No low-pass, no despeckle, nothing pasted or painted
   over the paint. Drawn at 512 a cell, area-reduced to 128. The cap kept the shield's detail
   measure at 16.6–23.3 against 6.1 from the old finish. A cap of 5 still browns thin spike tips:
   set `cap` to 1.5 on that item's trace. Gold needs a glow gain of 0.12, not 0.30, which clipped
   14% of a coin's core to lemon. **The gold check is "matches the shop gold, no lemon wash"**: the
   gold coin sits near 43° hue; 70–95° is lemon.
   **Tint to the palette, then mask cream, teal, gold and purple fields back to the raw paint** —
   the tint clips cream (239,228,198) to near-white and halves purple saturation (0.61 to 0.32).
   **After a light-hide edit the tint pushes the item to gold** (median V 0.73). Recolour it by
   ramp to a sibling icon's brightness, and check its median V against the set's before review.
   The current game set is `icons_game_v1/` (`build_set.py`, `check_A.py`–`check_C.py`). The
   game's icons now live at `Menus/icons/icon_<n>_128.png`, not `OneRod/Icons/`, so
   `icons_items_v1/pick_sheet_items.py`, which reads `OneRod/Icons/<name>.png`, is stale: repoint
   it before using it for the game-icon reference row.
6. `python measure_v3.py [ids]` (writes `I03/measure_v3.json`).
7. `python sheets.py block <style>` — the style **on the One Rod panel and buttons at 128, 64 and
   32 px**; `python sheets.py all` adds `compare_all.png`.

**Option sheets for the user's pick are a quick script paste** over the background — numbered,
side by side. The user prefers that to a Unity scene or a clip for choosing between options.
Label options in a font with lining figures (Palatino): old-style figures made "B1" read as
"BI".

**The chosen icon style is I03 "Scorched Edge"** (soft oil paint with a warm glowing centre; the
user, 2026-10-30: "IO3 the scorched Edge is the way to go here"). New icons are made in it.

- **Name every fill colour in the prompt** ("opaque ruby-red potion") or Qwen washes potions
  toward one colour.
- **Qwen follows the blockout's masks literally.** "Lit side and shaded side" did not shade flat
  armour: it added drop shadows instead.
- **"Burnished highlights" makes Qwen invent gems**; drop the phrase.
- **Metal and wood words swap in Qwen**: "hammered iron bars with square-cut ends" gives forged
  iron, while "forged iron bars" gives planks.
- **Naming a star anywhere in the prompt puts stars on every coin.** Draw a stamp only in the
  blockout, and keep it from the one try that has it.
- **"Every facet violet" gave a cast shadow under every icon.** Drop the phrase.
- **Asking Qwen for a broader scimitar** (twice) only flared the blade near the guard; widen it
  in the blockout spec instead.
- **Qwen adds rivets, dots and strap marks.** Judge them by eye on the raw paint. A despeckle and
  a wood low-pass also strip the planks, rim and grain that make the icon read.
- **A burn cap does nothing for a boxy boot top** — the outline comes from the mask, so fix the
  trace, not the burn.
- **A blockout cuff placed below the boot top** comes back as a band with a stub above it. Put
  the cuff at the top.
- **Qwen paints a fold-over cuff with wood-like streaks.**
- **When a design fails twice, change the design, not the wording.** Two crystals that failed
  twice worked first try once the planner redrew them; the coin pouch stayed wrong through five
  tries of the same route.
- **The bandage and the hide have no edit route.** Eleven Qwen edits across two jobs and four
  designs all failed (birch log, mat, capsule, cigar, tap, chocolate bar). Do not edit them again:
  ask the planner for another way — a code-drawn blockout traced as it stands, or a different
  item for the same meaning.
- **A crest-badge emblem must fill the crest.** About 14 px on a 32 px badge is too small for a
  thin shape to read.
- **The coin pouch has no working method yet.** A neck level with the coins' centres gives a dome
  with horns on every try; raising the coins clear detaches them with a zigzag neck. Try a
  different method, not another edit.
- **Blockout shapes that come back wrong**: a flat base under a pile returns as a slab, so piles
  get no base; ruled panels on a chest paint flat, so draw none; a closed-up pair of lower bars
  merges into one block, so keep the gap and trace it as a hole.
- **Thin parts meeting at one point read as an arrow at every size**, however deep the notches.
  For a crystal cluster use fewer, fatter parts, lopsided, on a shared flat foot, and do not write
  "growing from one point". Isometric cubes and many small gems break up at 32 px. Three fat gems
  hold, but square cushions read as blocks small; use rounder or non-square stones.
- **Measures passed three designs the key reviewer held on its first pass.** Keep that first-pass
  hold; a clean `measure.json` does not stand in for it.
- **Measuring colour**: a two-material icon (brown and gold) averages to the tan panel, so it
  cannot meet a mean contrast rule; measure each material apart and use the edge row. State the
  gold pixel window in the brief (28–62 and 25–65 gave different medians). A yellow measure with
  saturation above 0.35 misses cream: also count hue 15–90 at saturation 0.05–0.35.
- **Acceptance rules that do not work for icons**: a toe flat-run rule (6 px) cannot be met by a
  rounded toe; boot IoU against the old icon is dominated by the shared foot and says nothing of
  the top; on a quartered shield measure boss contrast per quarter, not over the whole field; a
  speck count flags grain ends and rivets, so judge specks by eye; an edge-luma range tracks the
  item's brightness, not its edge; an IoU limit between a disc and its rounded tile cannot pass
  below about 0.79; part contrast against 4 px neighbours misreads cork and bone.
- **After ORing the mask back, fill enclosed holes in the mask**, or see-through holes appear
  where the erosion cut a narrow neck.
- **A dark garment's off-colour patch that survives a darker blockout and a named-colour prompt**
  is fixed by recolouring that region in the raw paint before the finish step — one go.
- **A greatsword in a box-filling diagonal cannot be longer than a sword**, and a 1.7x guard with
  a 30% grip reads as an X at 64 px. Specify the blade width and a shorter guard, and tell it from
  the sword by a ricasso or a longer grip.
- **A garment that fails twice is built on an approved garment's outline**, then given one
  edit. The hide vest read as a sheaf or a pelt in two designs drawn from scratch; on the
  jerkin's outline with a V cut out it passed after one edit.
- **At small size the axe head reads as a flag on a pole in every style** — make the head wider
  and the haft shorter in the spec. Thin blades (scimitar, dagger) also go to hairlines there.

**Scribble and X marks (the close button).** The chosen close button is **Q1, hard slashes, in
red** (the user, 2026-10-31): `icons_v2/I03/round4/items_v4/Q1.png` **placed as-is** — no tan
button behind it and no other X (the user, 2026-11-13). Same route as the icons, with the round-4 scripts in `icons_v2/`
(`items_v4.py`, `blockout_v4.py`, `qwen_v4.py`, `finish_v4.py`, `measure_v4b.py`,
`pick_sheet_v4b.py`); it took 3 Qwen edits of 6.

- **The code blockout**: each arm about 10 units half-width, 3 legs per arm, uneven jitter.
  Never a zigzag across a short arm — it reads as a swastika.
- **Say "strokes of ink"** in the prompt, never "quill": "quill" paints feathers.
- **The mask is paint only** (`finish_v4.py`), which keeps the stroke tails a blockout mask cuts.
- **Measure solidity at 32 px and the outer arm width** (`measure_v4b.py`); those are what
  decide whether the mark still reads small.

### Lettering

**The game's font is approved for all text except damage text: option 11, Eagle Lake with the ink
treatment — font + code ink, not painted** (the user, 2026-11-01: "The font for the rest of the app
is approved"). Every word on a page, pop-up or button is drawn with it by code at run time, into a
`layout.json` text slot — never into the image. Damage text is chibi
(`unity-effects`, Floating text). Do not offer another font, or painted Qwen lettering, unless asked.

**Show lettering in place.** They chose it seeing it on the pop-up sheet, not from the lettering
sheet, where it was one of nine. A font question goes out on the real pop-up.

Working folder: `src/asset-animation-demo/local_runs/scenes/ui_parchment/font_v1/`, reusing
`lettering_v2/` read-only (`cells2.py 11`, `lettering.py`, `plate.png`, `measure.py`, `pick_sheet.py`).

- **Any string, from code**: `ink_font.text(string, cap, x, baseline, anchor, seed, noff=(0, 0))`.
  Tiers: big cap 60 and up, button 28–59, small under 28.
- **For Unity without TextMeshPro**: `bake.py` writes `bake/atlas_<92|44|28|18>.png` and
  `font_<size>.json` (advance and bearing per glyph; three variants a glyph at 92 and 44, one at 28
  and 18). `bake_use.py` rebuilds a line from those alone and `check_bake.py` compares it with
  `ink_font`. Nothing is in Unity or the game yet.
- **Not switched everywhere yet**: Scroll labels in `ui_lib.py` still use Hoefler Text in other
  menus. Caption bands on a sheet, outside the game frames, stay in a plain serif by default.
- **Hand noise follows world position, not seed.** Six seeds gave 9.4–10.6% pale core on VICTORY;
  moving the word changed it. A title moved from its picked spot needs a noise offset (`noff`; 0 keeps
  the picked masks at 0 px) and a pale share check: K under 0.6, trim 2 px, 5% or under
  (`title_search.py`).
- **Centre a title by its measured ink box.** Anchored by the untreated font box, the warp pushes ink
  off centre, 5.5 px on DEFEAT.
- **Set labels on one baseline, never centred by ink box**: a y tail lifts the word, an 11 px step
  between neighbouring buttons. The exception is a step the picked layout already has.
- **Under cap 28, draw at 3x then area-reduce, with a lighter hand** (`SMALL_TIER`). The big-tier
  treatment turned Crystal's y into a v at 11. The agents' read: hard below cap 14, straining at 11,
  worse on red.
- **Do not mirror-tile a paper swatch behind a font panel**: the bands read as a paper fault. Stretch
  one swatch. (`panels.py` still tiles.)
- **Numbers stay as the font draws them; that is approved.** 1 is drawn like a small capital I, so x1
  reads xI and 120 reads i20; 0 is close to O; 3, 5, 7 and 9 hang below the line. Do not swap, redraw
  or flag them. The big size's small y has a gap in its tail in two of three variants, so a big
  lower-case word needs a look.
- **Eagle Lake is SIL OFL 1.1**, so it can ship: licence in `lettering_v2/fonts/eaglelake/`, source
  in `fonts/SOURCES.txt`. The Hoefler Text on Scroll labels (`ui_lib.py`, from
  `/System/Library/Fonts/Supplemental`) and the Palatino in `build_victory.py` are mockup stand-ins,
  likely not licensed to ship.
- **No round ink blots by code** — they read as bullet holes.
- **Pale dry-pen bands across a stem look like tan slabs.** Dry-pen streaks run along the stroke.
- **Lowering rough-edge on font small words** fixes broken hairlines but makes them look like a
  plain font again.
- **Judge the hand-written look by eye.** The "not a font" check (XOR between two copies of the
  same letter) proves warping, not a hand-written look.
- **Trim 1 px from the ink mask before measuring ink-density span** — measured on the full mask,
  the span can pass on stroke edges alone.
- **No measured numbers on a pick sheet** — name, route and font only.
- **`lettering_v2/measure.py`'s `hairlines_ok` compares against an inflated untreated count**; fix it
  before trusting it: count at darkness above 0.25, per word.

### Battle HUD bars

Health and mana bars over a battle scene are all code, drawn over a clean re-render of the scene
base. The current code is `src/asset-animation-demo/local_runs/scenes/battle1/hud_bars/round4/`
(`engine.py` holds the bar sizes and colours, `health.json` the health per unit, `build.py` and
`compose.py` the sheet); earlier rounds sit beside it, read-only.

**The bar system is approved** (the user, 2026-10-30: "1,5,11 thesee are what we want to go with
for the Health bar system."). Build to it; do not offer other placements again unless asked:

- **A side vertical bar**: D5b thickness (columns 8/8/7/7/6 px from front row to back) in D5c's
  bright red and blue (`BR_RED`, `BR_BLUE`).
- **Still**: it does not follow the body through an idle or a weight shift.
- **About 15 px out from its own character**, on the cloak side.
- **Drawn on top of every character**, whatever the stack.
- **No body glow or rim** (panel 1).
- **Where a bar sits on the quiver of the archer in front, leave it as is** (panel 5).
- **On a hit or attack the bar nudges out of the way** (panel 11): 41 px further out on the hit
  and 21 px on the attack in round 4's frames, leaving a 10 px gap. It moves only then.
- A unit at full health shows nothing. A weight shift brings the body within 1–6 px of the still
  bar for a moment; the user has accepted that.

- **Every bar placement lands on a neighbour in a stacked formation.** In the 5-row block an
  over-head bar sits on the torso of the row behind, an under-feet bar on the chest of the row
  in front — there is no clear ground. Say so in the brief so nobody hunts for it.
- **A skill-button row over a stacked formation has two clear spots only**: the top HUD line, or
  the gap between columns.
- **"Show only when hurt" means health below full** — mana does not count. Write that in the
  brief, or the artist ORs in mana and full-health units show bars.
- **A rim or outline on a figure is cut by every layer in front of it, scenery included.**
  Compute it from the figure's visible pixels in the final frame, not its sprite mask minus
  other figures — that version paints the rim over foreground bushes and grass.
- **A rim is sourced from named body parts**, not the whole figure. Excluding only weapons and
  gear leaves the tunic, which cloak and arms cover, so a full-body rim shrinks to hood and boots
  and its variants look alike. A rim cut to a height band still traces whatever sits in the band
  — the bow as red curls, the quiver's arrows.
- **A rim dilated from alpha > 128 and then cut by alpha > 4 comes out about 1 px thin.** Dilate
  by the width + 1 and print the measured width on the sheet.
- **An opened mask stops at the fist and the bow grip**, so a distance "from the cloak" measured
  on it is wrong: measure cloak distance from the cloak's colour.
- **Exclude small pieces by position or colour, not size alone.** The green gems read as clothing
  and grow a rim arc by the knee; a size-based speck rule also drops real hood pieces up to 17 px
  on head-turn frames. Check any speck rule against the head turn as well as the idle.
- **A minimum fill flattens low health**: a 7 px floor makes 6–9% health one look. Say so on the
  sheet when the floor is set.
- **Check a contrast limit against the ground's real range first.** The battle ground is grey
  120–157, so no bright blue gets 40 grey levels from it: judge the bar against the ground by hue
  (ΔE76) and say so on the sheet. Muted tones make red and blue hard to tell apart on the back row.
- **A gap is the empty pixels between mark and figure**, never measured from the mark's edge
  column — that reads one pixel short.
- **A halo's gap is the bar's gap minus the halo width.** A brief cannot promise both "position
  unchanged" and a fixed gap on a shadow or halo option — pick one and write which.
- **Clamp every slice start at 0.** A negative start gives an empty slice in numpy, and an overlap
  check on it reports a false "no overlap".
- **A check that subtracts the same zone as the rule it tests cannot see that rule fail.**
  Mutation-test every new check: run it on the old code, or with the rule turned off, and see it
  fail before trusting its pass.
- **Review strips include every row the acceptance table names.**
- **When the planner's brief is lost, write the brief's text or its path into the queue note**, so
  the next worker resumes against the same brief.

## Hand-off to forge

The last step of a menu or UI job the user has approved. Annie never writes into the game; forge
copies the folder in.

1. **One folder, grouped by piece**: `local_runs/handoff/UI/` — `map/`, `icons/`, `popups/<name>/`,
   `party_pick/`, `battle_hud/`, `loading/`, `widgets/`, `unroll/<set>/`, `results/`, `charselect/`,
   `settings/`, `about/`, `shop/`, and `_review/` for preview stills only. Forge copies every folder
   except `_review/` and the README into the game's `Assets/Resources/Menus/` under the same names
   and keeps every file name — each `layout.json` names its pieces by file.
2. **Byte copies, md5-checked.** Every file is a copy of the approved source; list the md5 of
   both and report the mismatch count, which must be 0. No `.meta` files are shipped.
3. **The v1 page paper wherever a newer paper is unapproved** — see the page paper rule above. A
   layout that still names `paper_v3b` keeps the note; the README says the shipped file is v1.
4. **The README explains every path in the layouts**: which are the piece's own, which point into
   another shipped folder, and which are annie's provenance notes (`auto/...`, `scenes/...`,
   `nowords.png`) that are not shipped and not needed. Map each game screen to its pieces.
5. **md5 the game's current stills against the approved roster** and list every one that is not
   approved — this caught an unapproved Brute portrait.

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
| Curled paper corners read as a fancy ticket border | corners drawn as concave quarter-discs; failed twice in the same spot | needs a different method of drawing the curl — do not patch the quarter-disc |
| Icon armour flat, or with drop shadows | "lit side and shaded side" in the Qwen prompt; or the heavy finish stripped the paint | drop the phrase; crop the raw cell, trace the mask to the paint, burn capped 5 px |
| Gems on icons nobody asked for | "burnished highlights" in the prompt | drop the phrase; shade by code |
| Added rivets and dots on icons | Qwen detailing | judge by eye on the raw paint; no despeckle or low-pass, which strip real detail |
| See-through holes in an icon | enclosed mask holes after ORing thin parts back | fill enclosed holes in the mask |
| Grey plate showing inside an icon (a helmet plume gap) | a gap enclosed by paint matches the plate, so no measure sees it | check enclosed gaps by eye; trace it in `holes` |
| Pale facets on a Qwen sheet wash to cream or yellow | a yellow beam over cells (0,0)–(2,1), (0,2), (1,2); rewording and a darker blockout facet did not move it in three edits | important icons in the right column and bottom row, throwaways in the washed cells (red minus blue 3.6 or under on every used cell); move the item, do not reword |
| Cream fields go near-white, purple goes dull after the palette tint | the tint clips (239,228,198) and halves purple saturation | mask cream, teal, gold and purple back to the raw paint |
| Off-colour patch on a dark garment | Qwen; survives a darker blockout and a named colour | recolour the region in the raw paint before the finish |
| Gold icon reads lemon | hue pushed past ~70° | keep the coin near 43°; check against the shop gold |
| Stars on every coin | a star named in the prompt | no star in the prompt; stamp in the blockout only |
| Potions all one colour | fill colours not named | name each colour in the prompt |
| Ink spots read as bullet holes | round blots drawn by code | no round discs |
| Menu art cannot go into the game | words baked into the panel or button image | text-free pieces + `layout.json` text slots; words drawn by code |
| Smudge or ghost letters where words were removed | words painted out without cleaning the paper | code-built: re-render with the word step off; painted: carry grain and tone through, measure leftover ink against free paper beside it |
| Pieces-vs-approved check fails at word edges on gold and red | approved pictures recoloured after the words were blended in | measure outside the word ink dilated 3 px |
| A recoloured piece's soft edge does not match the approved picture | soft-pixel alpha solved against the pre-recolour render | re-solve alpha against the picture underneath |
| Building shadow streaks, or a second ground under an overhang | shadow projected per column from each column's lowest pixel | one ground line per building; closed footprint (fill between outer feet, `binary_fill_holes`); cut above the line |
| Building edges hard or stair-stepped | alpha from a 1x mask, or `rc_over` re-solved the edge | 3x mask coverage eroded 6 px, area-reduced, partial pixels in ink colour, plain `rc` |
| New building wears a neighbour's flag shadow | placed without checking old pole and flag shadows | move it clear of them |
| Small sign reads as a bag; crates read as stairs | no link below the sign's arm; crates on stepped tops | draw the link; crates on one top line |
| Cave or rock shadow reads as a flat slab | flat ground-line projection on a dome shape | its own silhouette-keeping method; not the building projection |
| Pale gap beside the rod at rest | the moving strip carried the panel's bottom-edge shadow; zeroing it outside opaque rows removed it | keep the run-to-knob strip; give `panel.png`'s 15 rod-side columns the bottom-edge shadow, within ~10 luma of v3 at 100% |
| Clean paper is pale, flat and edge-less | linear colour match, or a Qwen re-render | per-channel tone map `G_200(old)/G_200(new)` |
| Trees look off beside the buildings | side-view battle trees used on a top-down map | draw map trees top-down 3/4 |

## Scorecard — the last step of every run

Append one row per pass to `scorecard.csv` beside this file, then run `skill-improver` on this
skill.

`date,scene,layer,generations,edits,passes,minutes,usd,user_verdict,note`
