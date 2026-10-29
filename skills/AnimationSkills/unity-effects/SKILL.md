---
name: unity-effects
description: Build an effect or a test scene in the open Unity editor and record it to a captioned mp4 — effect prefabs made of separate, toggleable layers (white flash, drawn core, front and back particles, shockwave, trail, lingering bits, 2D light, bloom), test scenes that play them (Archer vs Archer), all inside annie's sandbox in the Unity project. Use when the user asks for an effect or a scene built, tried or recorded in Unity. Not for drawing the textures the layers use (the image pipeline), code-drawn sheet effects (`effects-overlay`), body animation (`base-action`), or game code (forge).
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

## Driving the editor

- The CLI is `~/.unity/bin/unity`; a non-login shell does not have it on PATH, so call it by that
  path. Prefix every call with `UNITY_NO_BANNER=1 UNITY_NON_INTERACTIVE=1 UNITY_NO_PAGER=1` and
  pass `--project-path <absolute project path>`.
- `unity status` first. No row means the editor is closed: open it yourself with `open -a
  /Applications/Unity/Hub/Editor/6000.6.2f1/Unity.app --args -projectPath <path>` and poll
  `unity status` until it answers — never `unity open` or `unity doctor`, which go through the
  Hub and hang.
- **Close the editor when the job is done** (the user, 2026-10-28: it wastes processing power
  left open). After the last recording and the frames are saved, save the scene, then quit:
  `osascript -e 'tell application "Unity" to quit'`, and if the editor process is still there
  after a minute, `kill -TERM` its PID. Never leave it open for a later job; that job opens it.
- `unity command set_autotick --enable true` before anything else; the editor stalls unfocused.
- Build with the builder pattern: write `AnnieBuild/<Job>.cs` with a static entry, run
  `unity command run_script --file AnnieBuild/<Job>.cs --entry <Class>.<Method>`; `--dry_run
  true` compiles without running. Create assets through `AssetDatabase`, `PrefabUtility`,
  `EditorSceneManager` — never by writing YAML.
- A `.cs` written under `Assets/` triggers a domain reload: `unity command recompile`, then poll
  `recompile_status` until done, tolerating dropped connections. A failed compile is fixed or
  the file deleted before anything else — a project left failing boots into Safe Mode, where
  the CLI cannot connect at all.
- **A command that stops answering is usually a modal dialog.** Check with `osascript` (System
  Events, an `AXDialog` window of the Unity process) and press its button. Never kill the editor.
- Play mode: `unity command editor_play`, then eval `UnityEngine.Application.runInBackground =
  true;` — without it time does not advance between CLI round trips. Leave play mode at the end.
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
- **Start particle sprites larger than looks right** — they read too small at first — and
  brighten dirt dust, which vanishes against the ground.
- **A trail emits from the projectile's first frame**, not once it is in flight.
- **Effects draw in the target's row sort order**, so a back-row hit never covers the front row.
- **A build-up take adds exactly one layer per part.**
- **Bloom**: HDR is already on in `UniversalRP.asset`, so bloom is a Volume profile in the job
  plus post-processing on the camera. It lifts the bright sky even at threshold 0.97, so it goes
  on the effect layers only, or is off by default.
- Every Particle System gets `useAutoRandomSeed = false` and a seed in the entry, so a re-take
  differs only where the fix did.
- The test scene camera has post-processing on and matches the game's framing (iOS landscape).
  Characters in a scene are the game's installed sprites, referenced, unchanged.
- **Scrolling lanes are quads with a wrap-scroll unlit shader**, not Sprites.
- **A crowd's fill order is in the brief.** Front-row-first with 3 a side gives no diagonal shot.

## Shared scripts (`Assets/Annie/Shared/`, written by `annie-tool-writer`)

- `AnnieLayers` — on the effect root: the list of layer children with an on/off box each,
  applied in the inspector at once; `Replay()` to fire the effect again; a loop option so the
  test scene repeats it while the user toggles.
- `AnnieCapture` — in the test scene: sets `Time.captureFramerate` (30), renders the camera into
  a 1920×1080 RenderTexture each frame, writes `frames/f0000.png…`, then `capture.json` with the
  frame rate, frame count, seeds, and **every `AnnieLayers` toggle as the scene had it**; exits
  play mode when done. Bloom works through it; no Recorder is needed. **It shows tick n+1 on
  frame n**, so a scene's director starts its tick early (−1 for Archer vs Archer, −2 for battle
  scene 1): check frame 0 against tick 0 on the first capture.

## Recording

1. Baseline: md5 of every file outside the sandbox the scene reads (character sprites, controllers,
   backgrounds), into `<job>/baseline.md5`.
2. Capture the **all-layers** take first; that is the one the user judges. A solo take per layer
   is made only when the brief asks — the user toggles layers by hand themselves. A hit's second
   shot waits for the target's idle to cycle back to frame 63, 0 or 1, so a two-shot take runs
   about 225 frames.
3. Encode with **one keyframe for the whole clip**: `ffmpeg -framerate 30 -i frames/f%04d.png
   -c:v libx264 -x264-params keyint=<frames>:scenecut=0 -pix_fmt yuv420p -crf 18`. The default
   250-frame keyframes pulse every ~5 s, which shows in a side-by-side. Encode the quarter-speed
   copy from the raw frames too, with its own caption.
   **Keep the raw frames until the reviewer has run** — without them determinism and full-size
   sharpness cannot be checked, and an encode fix needs a re-capture.
4. **Caption from `capture.json`, never typed.** The local ffmpeg has no `drawtext`, so draw the
   caption — "TEST · layers on: Flash, Core, …" — onto a transparent PNG with PIL and lay it over
   with ffmpeg's `overlay` filter. Every recording carries it, the quarter-speed one too.
5. Contact sheet of every frame (or every second frame past 60) and a paired-frame strip of the
   hit, for the reviewer.
6. Check the baseline again. `<job>.entry.json` holds the builder command, the seeds, the
   settings found by trial and the layers built.

## Acceptance — before the user sees it

| Check | Pass |
|---|---|
| Caption | names exactly the layers `capture.json` says were on |
| Each layer | visible on the frames the brief gives it, absent when its toggle is off |
| Flash | white on one frame only |
| Through-travel | back particles leave the far side of the target, not the front |
| Textures | every particle and core uses an imported drawn texture; no default particle |
| Determinism | two captures with the same seed match frame for frame |
| Match to an approved clip | compared against the lossless render, never the approved mp4 — the mp4's own compression floor (mean ~3.4) sits on a pixel-mean limit of 4 |
| Keyframes | one I-frame in the encode |
| Outside the sandbox | md5 baseline unchanged; `git -C src/unity-side-scroler status` shows changes under `Assets/Annie/` and `AnnieBuild/` only |
| Compile | `recompile_status` clean at the end |

## What still fails

- `AnnieCapture` renders into an sRGB RenderTexture, which forces linear blending: soft edges
  come out about 5 levels brighter than the sprite pipeline. It needs a render-texture format
  option, and a log of scene state such as a scroll switch — ask `annie-tool-writer`.
- `annie-unity-artist` could not be resumed with `SendMessage` after its first round. Plan a fix
  round as a fresh dispatch with a hand-off brief: the files, the findings, what passed.

## Scorecard — the last step of every run

Append one row per pass to `scorecard.csv` beside this file, then run the `skill-improver` skill on
this skill.

`date,job,layers,frames,passes,hand_fixes,new_tools,dialogs,minutes,usd,user_verdict,note`

- `job` is `<effect or scene>_v<n>`; `layers` is the count built; `frames` the all-layers take.
- `dialogs` counts modal dialogs met — each one is a recipe fix waiting to be written.
- `hand_fixes`, `new_tools`, `passes` and `minutes` are what this skill exists to drive down.
- `user_verdict` stays `pending` until the user has judged it; backfill it when they rule.
