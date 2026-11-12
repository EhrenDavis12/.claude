---
name: unity-effects
description: Build an effect or a test scene in the open Unity editor and record it to a captioned mp4 — effect prefabs made of separate, toggleable layers (white flash, drawn core, front and back particles, shockwave, trail, lingering bits, 2D light, bloom), test scenes that play them (Archer vs Archer), floating damage text, and menu art cut into moving pieces by code, all inside annie's sandbox in the Unity project. Use when the user asks for an effect or a scene built, tried or recorded in Unity. Not for drawing the textures the layers use (the image pipeline), code-drawn sheet effects (`effects-overlay`), body animation (`base-action`), or game code (forge).
---

# Unity effects and test scenes (built in the editor, recorded to mp4)

Annie builds **effects, scenes and recordings** in Unity. Forge writes the game. So everything
here happens inside annie's sandbox in the Unity project, references the game's assets without
changing them, and ends as an mp4 the user watches. Nothing is installed into the game.

`annie-unity-artist` does the building and recording; `annie-sheet-reviewer` reviews the
recording from its contact sheets.

## Where things live

| What | Path |
|---|---|
| Unity project | `src/unity-side-scroler/sideScrollerBattles` (Unity 6000.6.2f1, 2D URP, iOS landscape) |
| The sandbox — annie's only writable area in the project | `Assets/Annie/` |
| One job's folder (the artist's) | `Assets/Annie/<Job>/` — `Prefabs/`, `Scenes/`, `Materials/`, `Textures/` |
| Shared scripts every job uses (`annie-tool-writer`'s) | `Assets/Annie/Shared/` — runtime + `Editor/`, each with its own `.asmdef` |
| Builder scripts, run with `run_script` (outside `Assets/`: no import, no reload) | `AnnieBuild/<Job>.cs` at the project root |
| Recordings, frames, capture log, contact sheets, entry | `src/asset-animation-demo/local_runs/unity/<job>/` |
| Python (captions, contact sheets) | `src/Asset-Gen-Framework/.venv/bin/python` |

Read-only to annie: `Assets/Characters`, `Assets/Scenes`, `Assets/Scripts`, `Assets/Settings`,
`Assets/Spikes`, `Packages/`, `ProjectSettings/` — everything outside `Assets/Annie/`. A change
any of them needs (HDR or post-processing on the URP asset, a package) is reported to the user,
never made.

**On-screen buttons and panels use the house UI style**, the parchment scroll "R04 One Rod"
(the user, 2026-10-29: "apply it to any menue items we create when building in unity"). Take
the pieces from `src/asset-animation-demo/local_runs/scenes/ui_parchment/scroll_v3/R04_OneRod/`
(`buttons.png`, `modal.png`); never Unity's default grey buttons in a recording the user sees.
Text is Eagle Lake option 11 (`menu-map-buildings`, Lettering), and text floating over a fighter
is chibi (Floating text below); the words on those pieces are a stand-in in another font.

## Driving the editor

- The CLI is `~/.unity/bin/unity`; a non-login shell does not have it on PATH, so call it by that
  path. Prefix every call with `UNITY_NO_BANNER=1 UNITY_NON_INTERACTIVE=1 UNITY_NO_PAGER=1` and
  pass `--project-path <absolute project path>`.
- `unity status` first. No row means the editor is closed: open it yourself with `open -a
  /Applications/Unity/Hub/Editor/6000.6.2f1/Unity.app --args -projectPath <path>` and poll
  `unity status` until it answers — never `unity open` or `unity doctor`, which go through the
  Hub and hang. Take the editor's PID from `pgrep -f 'Unity.app.*sideScrollerBattles'`, not
  from `unity status`.
- **An open that hangs: `sample <pid>` first.** The stack names the dialog it is waiting on,
  which can sit on a second monitor where screenshots miss it. "Access token is unavailable" in
  `~/Library/Logs/Unity/Editor.log` is harmless; a good start's log moves to
  `<project>/Logs/Editor.log`.
- **Close the editor when the job is done** (the user, 2026-10-28: it wastes processing power
  left open). After the last recording and the frames are saved, save the scene, then
  `kill -TERM` the editor's PID. An `osascript` quit is refused here (no assistive access) and
  Unity ignores a polite quit while the scene is dirty anyway (see What still fails). Unity
  shows a restore-backup dialog at open whenever `Temp/__Backupscenes` exists, even empty, so
  once the editor is gone move the whole folder out of `Temp/` — never only its contents. Never
  leave it open for a later job; that job opens it.
- **Check the licence before building.** "No valid Unity Editor license found" or
  `LicenseGroupOfflineValidityPeriodIsExpired` in the log means nothing will build: park the item
  at once with that question, never work round it.
- `unity command set_autotick --enable true` before anything else; the editor stalls unfocused.
- Build with the builder pattern: write `AnnieBuild/<Job>.cs` with a static entry, run
  `unity command run_script --file AnnieBuild/<Job>.cs --entry <Class>.<Method>`; `--dry_run
  true` compiles without running; `--args` takes a JSON array. Create assets through `AssetDatabase`, `PrefabUtility`,
  `EditorSceneManager` — never by writing YAML.
- A `.cs` written under `Assets/` triggers a domain reload: `unity command recompile`, then poll
  `recompile_status` until done, tolerating dropped connections. A failed compile is fixed or
  the file deleted before anything else — a project left failing boots into Safe Mode, where
  the CLI cannot connect at all.
- **A command that stops answering is usually a modal dialog.** Check with `osascript` (System
  Events, an `AXDialog` window of the Unity process) and press its button. Never kill the editor.
- Play mode: `unity command editor_play`, then eval `UnityEngine.Application.runInBackground =
  true;` — without it time does not advance between CLI round trips. Leave play mode at the end.
  A recording started right after a play session returns Runtime Error: wait for play mode to
  stop, then 10 s.
- Exit code 2 is a bad command line: fix it. Exit 6 is the editor failing: read the error.

## The layer standard (user-approved)

Every effect prefab is a root with **one child per layer**, named as below, each wired into the
shared toggle component so the user can switch it on and off in the inspector while watching
in play mode. Layers a brief leaves out are absent, not empty.

| # | Child | What it is |
|---|---|---|
| 1 | `L1_Flash` | one-frame white flash |
| 2 | `L2_Core` | the hand-drawn shape: a spark sprite, or a slash — a textured plane/arc swept along the swing + a soft weapon-tip Trail Renderer |
| 3 | `L3_ParticlesFront` / `L3_ParticlesBack` | particles out the front of the hit **and** out the back of the target, so it reads as travelling through |
| 4 | `L4_Shockwave` | ring — optional; built only when the brief asks, for the user to judge |
| 5 | `L5_Trail` / `L5_Linger` | a trail for every attack (dirt from a charge, wind behind an arrow, a beam for fire, ice shards) + lingering bits around the target (dirt puffs, fire, wind or ice motes) |
| 6 | `L6_Light` | URP 2D light burst on the surroundings |
| — | `Bloom` | a Volume with Bloom, in the job's scene, toggled like a layer |

Layer 7 — the push-back and recovery — stays in the sprite animation; the effect never moves the
body. Camera shake is out for now.

- **Particle System**, not VFX Graph: the target is iPhone. Shader Graph for materials. Trail
  Renderer for trails.
- **Textures come from annie's image pipeline as drawn PNGs** (`effects-overlay`'s particle
  textures), imported into the job's `Textures/` with no mipmaps and NPOT scaling off. Never
  Unity's default particle; a missing texture is reported, not stood in for.
- **Projectile trails are thin and faint.** An arrow trail must not look like a missile (the
  user, 2026-10-28): width about 0.02 of screen height, alpha about 0.35, puffs 0.10–0.26 —
  the rejected first take had 0.10 H, full alpha and puffs to 1.3. Particles stay small, about
  60% of what looks right in a still. Brighten dirt dust, which vanishes against the ground.
- **Melee hit settings that passed review** (the Assassin's knife): ground dust draws behind
  the body; particles start wide with a small emit radius; the core fades on a low last alpha
  step, not a cut; the trail dies with the tip; the core runs from the fist to past the tip.
- **A drawn cut is specified by angle and maximum bulge**, its tip anchored on the weapon head
  every frame. Briefed loosely, the crescent bulged sideways and the tip came off the cleaver.
- **A burst gets its own drawn flipbook**, made before the build: small core → lopsided bloom →
  scraps, ending bright on a clear centre, and its last cell fades rather than cuts. A core of N
  identical radiating wisps reads as a daisy. Tint the flipbook's white centre cells down, or
  they read as a second flash.
- **A charge is wisps orbiting a glow, tips trailing round it** — upright wisps read as a torch.
- **Strand particles off a projectile end by impact + 2 frames**: clamp their life, or they
  outlive the head.
- **A tint blended thin over warm ground turns neutral.** Check the core's own channel margin
  (green over red for a ghost green) on its pixels, not only the median colour.
- **Match the stack to the hit.** The full layer stack suits a dramatic hit; a plain arrow hit
  wants fewer layers going on.
- **A trail emits from the projectile's first frame**, not once it is in flight — except a
  steep shot, where it starts once the arrow is clear of the body.
- **A steep arrow starts on the arm line**, then eases to its path's tangent. Rotated to the
  tangent from frame one, its tail sits on the torso and it reads as launched from the belly.
- **Check a brief's path numbers against arrow speed at planning.** Distance, flight time and
  launch angle cannot all hold at a fixed speed; say which one gives.
- **Ground hits (a miss):** a mound of `dirt_clump` reads as a rock; `dust_puff_white` tinted to
  the ground reads as soil. Clods fade from about 82% of life — fading at 45% they dissolve in
  the air — and check on the frames that they land. Vary each clod's rest height: one collision
  plane lines landed clods up in a flat row.
- **Effects draw in the target's row sort order**, so a back-row hit never covers the front row.
- **Lingering bits never cross the target's figure.** Draw `L5_Linger` behind the target (sort
  order) or spawn it outside the target's outline mask: a spawn ring sized by radius still lands
  motes on the head when the hit pose leans.
- **A code-drawn particle texture carries its own colour under alpha 0**, never black: Unity's
  bilinear sampling pulls the black into a dark fringe. A single white glow tinted cyan loses its
  white centre — stack two (a white core over a tinted glow).
- **A build-up take adds exactly one layer per part.**
- **Bloom**: HDR is already on in `UniversalRP.asset`, so bloom is a Volume profile in the job
  plus post-processing on the camera. The Bloom component must be saved into the profile asset,
  or bloom silently does nothing: measure a take with it on against off before the caption names
  it. It lifts the bright sky and pale bones even at threshold 0.97, so it goes on the effect
  layers only, or is off by default.
- Every Particle System gets `useAutoRandomSeed = false` and a seed in the entry, so a re-take
  differs only where the fix did. Give every renderer its own sort order within the layer: two
  renderers on equal order draw in no fixed order and break determinism. A script that emits
  particles takes one random stream per layer from the seed, or toggling a layer reshuffles the
  others.
- The test scene camera has post-processing on and matches the game's framing (iOS landscape).
  Characters in a scene are the game's installed sprites, referenced, unchanged.
- **Scrolling lanes are quads with a wrap-scroll unlit shader**, not Sprites. Wrap the uv with
  `frac` **and** sample with `SAMPLE_TEXTURE2D_GRAD` on the unwrapped uv's `ddx`/`ddy`: `frac`
  alone makes the mip pick jump at the wrap, a 2 px seam line down the lane.
- **A battle opens on an empty battlefield, and nobody just appears** (the user, 2026-10-31).
  Over 4 s the camera scrolls with parallax, the player's side runs in at run pace with normal
  legs, each runner on at a random time, and the enemies scroll in from off screen right, as if
  approached (the user, 2026-11-01: "Battle scene intro is approved"; 3 s was too short). A scene
  that starts with the armies already standing is rejected on the opening alone.
- **A crowd's fill order is in the brief.** Front-row-first with 3 a side gives no diagonal shot.
- **A run cycle always plays at its approved rate — never sped up.** Legs at ×2.4–3 to keep up
  with a fast scroll read as "having seizures" (the user, 2026-10-31). Play the cycle at normal
  speed and accept foot slide: the user prefers sliding feet over frantic legs.
- **Entries are per runner at random times, never per column.** Columns read as arriving in lines.
  Pick the entry ticks from a seed, hill-climb them against the checks, and hard-code the table:
  `battle_scene1_full/plan_opening_f.py` spreads 15 runners from tick 13 to tick 106 of a 192-tick
  scroll, and that table passes both the lines and the arrivals checks.
- **Random entries take longer to fill the screen, and that pace is approved.** The approved take's
  arrivals ran about 2.3 times the earlier staggered take's, and the user did not call them slow, so
  do not shorten them or offer a faster take on that fear. Put these in the brief beside the lines
  count, so the time is known: runners fully on at 1.5 s and at 2.5 s, the army's right edge, and the
  time with 5 or more cut by the screen edge.
- **Measure arrivals on the frames.** First visible is each frame's own opaque edge, not the widest
  run cell (reads up to 4 ticks early) and not the planner's simulation. The artist measures the
  fully-on ticks: the simulation was off by 1, because the leg frame changes the edge.
- **The Archer's normal run is 16 fps, a 1.00 s cycle**: exactly 3 ticks per sheet frame at the
  scene's 48 fps capture. Checking legs against that, count holds from the tick the frame formula
  starts, not from the figure's entry, or a partial hold off screen reads as a short one.
- **A run-on from off screen costs distance ÷ leg speed.** At the approved 303–395 px/s an
  800 px run-on takes 2.5–3 s, so a shorter one needs a closer start, or the slide above — say
  which in the brief, before building. A crowd intro's floor is the stop sheet's length plus
  the spread of skid starts: keeping fixed skid ticks while compressing the run-on packs a row
  to 21–60 px apart, so the skid spread sets crowd spacing.
- **A camera faster than about ⅔ of a figure's leg speed leaves it crawling on screen**, and a
  figure that plants while the camera still moves rides back with the ground. State that
  ride-back in the brief, from the plan (the plant is skid start + 12) rather than by hand at a
  tick near it, and count it from the figure's furthest screen point, not from the plant: the
  same runner reads 62 px against 53.
- **Measure a foot-slip limit on the approved sheet first.** The run's own sole falls behind
  16–30 px a stance, so a 3 px limit can never pass; set the limit from that measurement.
- **Redo one part of a scene by a wholesale tick shift of the rest.** A fight kept by shifting
  every tick by a constant needs no re-solve and its frames match the kept take within the noise
  floor (see Acceptance), so a new opening rebuilds and captures in about 13 minutes, not a full
  fight re-plan. Brief it at that size.
- **No two characters breathe or run in step.** Spread the final idle frames across the cycle,
  never leave a run-phase gap of exactly 8 between neighbours, and check every pair — diagonal,
  one row apart, as well as side by side. Skid starts squeezed into a short window cap the
  cross-row idle gap at the start spacing; that is what let in-step pairs through.
- **A fight plan spaces hits on one target.** A hit lands only a few ticks after the previous
  hit's reaction has ended, so a fatal third hit cannot land early; plan the kill times from
  that, not from the arrow's flight alone.
- **Pooled effects: a new shot claims its slot and the stale shot releases it.** A shot still
  holding a reused slot blanked three impacts while the impact log read 33 of 33.

## Dissolving a sprite into particles (enemy death)

The reusable sequence is `Assets/Annie/EnemyDeath/` (`EnemyDeath.Play(targets, seed)`), built on
the hurt pose so enemies need no death sheets. The user approved `EnemyDeath_v1` as the death for
any character with no death animation of its own; its settings are the approved look.

- **One order map per call, over the union of the targets' world bounds.** The shader samples it
  by world position and the particles emit from the same map, so body and weapon cut as one and
  each fleck leaves where the cut is.
- **Read the sprite by blitting its rect to a RenderTexture**: sheets are not readable, so
  `GetPixels` fails. The Particle System Shape module's sprite emission fails on FullRect sheets;
  emit from script.
- **Long-wavelength noise only tilts the cut into a straight slice.** It takes short octaves too:
  wavelength/amplitude as fractions of height 0.55/0.17, 0.22/0.10, 0.09/0.05, 0.035/0.02.
- **Tying islands to the feet by weakest link tears the edge but takes heads and hands in a
  burst**, 3–4 frames on small figures. At blend 0.6 that trade is still open.
- **Scale by the square root of body height**, `k = sqrt(h / 218)`, h being the tallest single
  target's opaque extent: rim 3.5 px × k, sweep 1.4 s × k. A rim scaled with height itself reads
  as a plank at dragon size.
- **A particle texture with a baked grey outline darkens its tint.** Run the fleck shader flat
  (`_Lift` 1) with its shape from the PNG's alpha, and a shard quad at 1.4 of its visible size.
  Flecks on dirt need a brightness floor to show.

## Floating text (damage numbers, Miss, Blocked)

The job is `Assets/Annie/DamageText/`, with its baking and checks in
`src/asset-animation-demo/local_runs/unity/damage_text/`: `bake_v2.py`, `check_v2.py` (sprites),
`check_c.py` (frames against a text-free take), `popmodel.py` (rebuilds a pop; game and chibi
branches), `finish_v2.py <take folder>` (reads the font from that take's `pops.json`),
`sheet_v2.py` (the pick sheet).

- **Bake the text to sprites by code; no TextMeshPro.** Its essentials import outside the sandbox.
- **Text floating over a fighter is chibi at half its first size** — approved (the user,
  2026-11-02: "The damage numbers are good, approved"): Titan One size 40, `textures_chibi_half`,
  font set `chibi_half`. The approved take is `take_c_chibi_half` in the battle, with Miss, Blocked
  and heal on the take A2 chibi half bench. The settings stand as recorded: a hit reads plain `27`,
  no minus sign; Miss is pale cream; Blocked is pale steel blue; the drift stays. All other text is
  the game font (Eagle Lake, ink treatment; `menu-map-buildings`, Lettering), baked in
  `textures_game`. Both sets stay on file. Do not re-bake, re-colour or offer another font unasked.
- **A font swap is never one setting.** The font has been hard-coded in the record script
  (`rec_a2_all.sh`), typed into the finish step, defaulted in the directors (to full-size chibi) and
  assumed by the pop model, and a kept take lacked Miss and Blocked. The planner reads every script
  the swap passes through — bake, directors, record, finish, pop model, checks — and lists the font
  in each before sizing it. Finish writes into a new take's folder, never into the kept take.
- **Chibi's counters are dark slits, not see-through holes**: the bake fills the outline mask, so a
  0, 6, 8 or 9's counter is a slit in the outline colour. That is the approved look; do not "fix" it.
- **Lay the game font out by advance plus bearing, baked to JSON**, with three variants per digit so
  repeats are not twins.
- **The font's atlases cannot take an outline by tinting.** Build it: colour = outline + (fill -
  outline) x D inside the mask, alpha = outline coverage. At cap 28 and under, D is near flat, so
  the ink look is gone and only the warp carries.
- **`SpriteRenderer.sortingOrder` is a short.** `kind*1000` overflows and draws behind the scene;
  `kind*400` fits 32 slots.
- **A full field needs a 32 slot pool.** With 8, the 9th pop kills the first.
- **Leave mipmaps off.** With trilinear they smooth a pop's first frames but soften settled text
  (Laplacian about 3x lower), and mip bias -1 does nothing. The first frame stays rough; say so.
- **An outer outline stroke can seal a letter's mouth and leave see-through flecks.** Fill holes in
  the outline mask (`binary_fill_holes`) and count enclosed pockets on every sprite.
- **Text at the target's head top lands on the face of the figure behind in stacked rows** (22 of
  33 pops in the battle formation; 21 of 30 at half size, and shorter travel ends on more faces).
  Plan where it starts against the formation, and put that count in the brief, before building.
- **A paste sheet for a text pick matches Unity within 0.2% only with bilinear sampling and linear
  blending**, and it must include open ground, or the colour on the real ground is never seen.
  Compare a paste by the text's pivot, not the canvas centre: by canvas centre a reviewer overstated
  a gap as -22% where it was about -6%. Its zoom gets one tile per item, each asserted whole.
- **Check each pop by rebuilding it** from its PNG and formulas over a text-free reference. That
  still works where pops overlap each other or the figures.

## Cutting flat art into moving pieces (a scroll that unrolls)

**A pop-up opens this way, by code; it needs no drawn animation.** The approved look is take A: the
rod rolls while the writing stays still on the paper, 0.8 s each way (the user, 2026-11-01: "The
scroll animation is amazing approved"). At 60 fps it is frames 24–71 opening, held to 131, frames
131–178 closing.

The job is `Assets/Annie/ScrollUnroll/`, take `A` in `SuDriver.cs`, settings in
`src/asset-animation-demo/local_runs/unity/scroll_unroll/scroll_unroll.entry.json`, with its pieces
in `scroll_unroll/pieces/`. The approved art stays unchanged: the held and closed frames are compared
against it exactly.

- **Get the matte by rebuilding from the drawing script on black and on white**, not by cutting
  the flat image.
- **Separate a shadow baked beside a moving part**: take the min of its profile and the alpha, then
  unpremultiply. Moved with the part, it carried the paper's shadow along. Zeroed, it left a pale
  slit.
- **Round a part's pivot and width together.** Rounded separately, a still rod's edge wobbles 1 px.
- **Record with `AnnieCapture.blendSpace` set to Gamma** (see What still fails) when the frames are
  compared against art drawn in PIL.

## Grey-pattern displacement — scenery only

A grey map that pushes pixels in a shader moves **scenery**: the ground blend, wind through
trees and grass. **Never a character's idle or body motion.** A still character made to breathe
by a grey pattern was tried and rejected (the user, 2026-10-29: "The gray pattern idea did not
work on the characters"). Character motion stays model-drawn keys + video (`idle-breathing-loop`,
`base-action`); do not offer the pattern for it.

- **Wind sways side to side — x only.** Tops sway, bases stay planted (the user, 2026-10-29);
  the push grows with height above the base and is 0 on the base row. An up-and-down push, like
  the breathing test's, is wrong. Measure every take's vertical motion on the trunks and stems:
  it must be 0.
- **Wind is strong: tree tops lean about 15.7 px at 1080 height.** That is the approved battle
  scene 1 wind (the user, 2026-10-30: "For the wind I prefer the strong version otherwise its
  almost un noticiable"). A gentle ~10 px take is too subtle. Brief every scenery sway at the
  strong value by default; go gentler only when the user asks.
- **The height ramp starts at the highest base row in the band**, not the band's bottom row. A
  ramp from the bottom gives the taller plants' roots a push, and the roots slide.
- **Tell a bush from a grass tuft by solidity** (area ÷ convex-hull area), not by bbox fill. A
  tuft's blades fill their bbox about as much as a bush does; only the hull separates them.
- **Record subtle scenery motion with the camera and parallax still first**, the scrolling take
  second. The user could not see the wind while the scene scrolled (2026-10-29: "I can't tell
  the difference when the scene is moving"). A still take is checked against a still reference
  — the same scene, effect off, scroll off — never against the scrolling approved frames.
- **Measure sway by tracking the outline**, not by shift-fitting the top rows. A shift fit reads
  low on wide or overlapping sprites (7.2 against a true 16 px, 0.2 against 8).
- **A screen-space wind pattern over scrolling lanes beats**: the lane moves under the pattern,
  so a plant sees the gust faster than the pattern's own period. State the beat with scroll on
  in the brief — period and scroll speed together — not the pattern's period alone. A frozen
  pattern may also lean a canopy as it scrolls under (8 px over about 32 ticks, unproven), so do
  not promise "wind still" during a scroll.
- **Judge bend against swell in motion, not by a bar.** A canopy push-spread limit cannot hold
  with a 400 px gust: the gust's width spreads the push across the whole canopy by design. Watch
  whether the canopy bends or just swells.
- **Ground blend** is `lerp(grass, soil, mask)` on a copy of the lane. Keep the grass tint noise
  low (×8; ×20 blotched), and let a mud mask's gradient cap reach 4.0 (2.5 lost the mud).
  Masks do not chain end to end with all-white ends: white at the join is full soil top to
  bottom, a straight dirt road under any ramp. Use one pattern when the camera travels less
  than a pattern's width; a long scroll needs a different join method, not yet found.
- **Never force a mask region with a hard box.** It leaves a 1 px cliff in the mask that tears
  the picture at the peak push; shorten the neighbouring ramp instead.
- **A caption's measured peak names the part it was measured on** — "peak 6 px, canopy top" —
  never a bare number.

## Shared scripts (`Assets/Annie/Shared/`, written by `annie-tool-writer`)

- `AnnieLayers` — on the effect root: the list of layer children with an on/off box each,
  applied in the inspector at once; `Replay()` to fire the effect again; a loop option so the
  test scene repeats it while the user toggles.
- `AnnieCapture` — in the test scene: sets `Time.captureFramerate` (30; a full battle scene 48, so
  a 16 fps sheet frame is exactly 3 ticks), renders the camera into
  a 1920×1080 RenderTexture each frame, writes `frames/f0000.png…`, then `capture.json` with the
  frame rate, frame count, seeds, and **every `AnnieLayers` toggle as the scene had it**; exits
  play mode when done. Bloom works through it; no Recorder is needed. **Its tick offset is not
  fixed** — it has read n+1 and n+2 on frame n, and it can shift between runs — so a scene's
  director derives its tick from the frames written, never from a hard-coded offset, and frame
  0 is checked against tick 0 on every capture.

## Recording

1. Baseline: md5 of every file outside the sandbox the scene reads (character sprites, controllers,
   backgrounds), into `<job>/baseline.md5`, and `git -C src/unity-side-scroler status --short` into
   `<job>/git_status_before.txt`.
2. Capture the **all-layers** take first; that is the one the user judges. A solo take per layer
   is made only when the brief asks — the user toggles layers by hand themselves. A hit's second
   shot waits for the target's idle to cycle back to frame 63, 0 or 1, so a two-shot take runs
   about 225 frames. A scene copy still points at its source's output folders, so override them
   at Awake.
3. Encode at the capture's own rate with **one keyframe for the whole clip**: `ffmpeg -framerate
   <capture fps> -i frames/f%04d.png
   -c:v libx264 -x264-params keyint=<frames>:scenecut=0 -pix_fmt yuv420p -crf 18`. The default
   250-frame keyframes pulse every ~5 s, which shows in a side-by-side. Encode the quarter-speed
   copy from the raw frames too, with its own caption — and that caption's fps is the quarter
   copy's own, never the full-speed number.
   **A side-by-side at 2/3 scale shrinks the motion** a third, so lead with the stronger take
   full size and put the comparison second.
   **Keep the raw frames until the reviewer has run** — without them determinism and full-size
   sharpness cannot be checked, and an encode fix needs a re-capture.
4. **Caption from `capture.json`, never typed.** The local ffmpeg has no `drawtext`, so draw the
   caption — "TEST · layers on: Flash, Core, …" — onto a transparent PNG with PIL and lay it over
   with ffmpeg's `overlay` filter. Every recording carries it, the quarter-speed one too. Wrap a
   long caption and check its bounds on the PNG, or it runs off the 1920 frame.
5. Contact sheet of every frame (or every second frame past 60) and a paired-frame strip of the
   hit, for the reviewer. The reviewer's own sheets and measurements go to its scratch folder,
   never into the take folder.
6. Check the baseline again. `<job>.entry.json` holds the builder command, the seeds, the
   settings found by trial and the layers built, and points at the take being shown — update it
   on every re-take, or it names a stale one. Its wind line moves with a tick shift too.

## Acceptance — before the user sees it

| Check | Pass |
|---|---|
| Caption | names exactly the layers `capture.json` says were on |
| Each layer | visible on the frames the brief gives it, absent when its toggle is off |
| Flash | white on one frame only |
| Every impact | a pixel check on each impact's frames shows its effect — an impact log counting hits is not proof |
| Through-travel | back particles leave the far side of the target, not the front |
| Textures | every particle and core uses an imported drawn texture; no default particle |
| Determinism | two captures with the same seed match frame for frame, run on **every** frame: a take against its own copy reached 13 levels and 42 px on the whole clip, where its first 480 frames gave 1 level and 23 px |
| Match to an approved clip | compared against the lossless render, never the approved mp4 — the mp4's own compression floor (mean ~3.4) sits on a pixel-mean limit of 4. The limit is the older take's whole-clip floor from the row above; a frame over it may be that take's own noise, so check it before calling it a change. A take whose two captures are byte-identical has no noise of its own, so noise against an older take is the older take's |
| Match to approved art under a dim | an opaque reference cannot pass an all-pixels match while a dim is ramping: word the row for opaque pixels only until the dim is full |
| Dissolve edge | deviation of the cut from a fitted line, against the brief's number, measured in round 1 — a straight slice passes every other row |
| Dissolve pieces | floating pieces counted per frame with the largest kept in — a metric that drops them misses the piece the user sees |
| Keyframes | one I-frame in the encode |
| Outside the sandbox | md5 baseline unchanged; `git -C src/unity-side-scroler status --short` at the end, saved to `<job>/git_status.txt`, matches `git_status_before.txt` outside `Assets/Annie/` and `AnnieBuild/` — name both files in the hand-back. The repo carries other work's uncommitted changes, so a clean status is never the bar. `Assets/Annie/` is not in that repo's git index: git shows it as one untracked folder and keeps no history of it |
| Face or colour box | a channel rule ("G never rises more than R") is worded for unclipped pixels: under a white flash R clips at 255 and the rule fails on a clean frame |
| Frame numbers | every finding and hand-back states frames 0-based, as the capture writes them |
| Compile | `recompile_status` clean at the end |

A background task's `.output` file is a symlink: check its size and age with `stat -L`, or a
live job reads as silent. A measuring script that uses `multiprocessing` needs an `if __name__ == "__main__":` guard on
macOS. Without it every worker re-imports the script, the output fills with "safe importing of
main module" errors and the job sits silent for hours. If the reviewer reports that no brief
reached it, though the dispatch held it whole, the main loop checks the brief's acceptance rows
itself before the user sees the clip.

## What still fails

- The dissolve's fleck brightness floor (V 0.93) with its saturation cap (0.45) washes a dark
  enemy's bits to pale cream. Its flipX facing was only read in code, never rendered: render a
  flipX take before relying on it.
- `AnnieCapture.blendSpace = BlendSpace.Gamma` blends on sRGB bytes (0 levels off PIL, measured).
  It needs sRGB-off sprite textures and a sprite background, not a camera clear colour. The mode
  is written to `capture.json` as `blendSpace`.
- `Destroy()` of an unused effect leaves a dead `AnnieLayers` in `AnnieCapture`'s list, and
  `capture.json` is never written. Use `DestroyImmediate` in Awake until `AnnieCapture` skips
  nulls — ask `annie-tool-writer`.
- `AnnieCapture` logs layer toggles only. Scroll on/off and scene parameters such as the wind's
  peak push are typed into the caption by hand, which is where a caption goes wrong. Ask
  `annie-tool-writer` for AnnieCapture to write scroll state and the scene's parameters into
  `capture.json`, so the caption reads them.
- `AnnieCapture` leaves the scene dirty. The artist has to open a scene additively and
  `CloseScene(false)` to drop the approved scene's changes, and the unsaved-changes prompt is
  why Unity ignores the quit and needs `kill -TERM`. Ask `annie-tool-writer` for AnnieCapture to
  clear the dirty flag (or discard the scene) when it exits play mode.
- `AnnieCapture` does not expose its frame index, so a director cannot tie its tick to the
  frame written and the offset drifts between runs. Ask `annie-tool-writer` for AnnieCapture to
  expose the frame index it is writing.
- An artist resumed late had `Bash` refused with "running in don't ask mode", though its earlier
  encodes had worked; the cause is unknown, and that run's joined review clip was never made.

## Scorecard — the last step of every run

Append one row per pass to `scorecard.csv` beside this file, then run the `skill-improver` skill on
this skill.

`date,job,layers,frames,passes,hand_fixes,new_tools,dialogs,minutes,usd,user_verdict,note`

- `job` is `<effect or scene>_v<n>`; `layers` is the count built; `frames` the all-layers take.
- `dialogs` counts modal dialogs met — each one is a recipe fix waiting to be written.
- `hand_fixes`, `new_tools`, `passes` and `minutes` are what this skill exists to drive down.
- `user_verdict` stays `pending` until the user has judged it; backfill it when they rule.
