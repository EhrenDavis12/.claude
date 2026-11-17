---
name: sound-effects
description: Make game sound effects and music loops locally and free on this Mac — short action sounds (bow release, arrow hit, miss, block), voices (hurt grunts, battle cries), menu sounds (clicks, paper, scroll, pen) and coins from MOSS-SoundEffect v2.0, layered and pitch-varied with ffmpeg so a crowd of 30 fighters does not repeat, looping music from ACE-Step 1.5 cut on the bar, and full songs from Lyria 3 Pro when the user approves the spend. Use when the user asks for a sound, a pool of sound variants, sorted sound sets for random play, or background music. Not for effects you see (`effects-overlay`, `unity-effects`) or putting sound into game code (forge).
---

# Sound effects and music loops (local, free)

**Read this before starting:**

- **The user's ears are the only gate.** No agent can hear. Every number below only throws
  away takes that are plainly broken; whether a take sounds like a bow, or the music has the
  right mood, is the user's call, every time. Every listen clip says so on screen.
- **Worked inline, by the main loop or the queue worker.** No annie agent owns sound, and
  `annie-sheet-reviewer` is skipped because it cannot hear. The write boundary still holds:
  everything is made in a sandbox folder, nothing installed, nothing approved touched.
- **One big job at a time.** MOSS peaks around 20 GB and ACE-Step around 37 GB on this 32 GB
  Mac. Close ComfyUI first (`llms stop`; restart with `llms start` after) and run nothing
  else. `llms` is not on PATH: run it as `src/LLMs/llms`. The swap rule for local renders applies: check swap before and after, never stop a
  render because swap spiked.
- **Local, $0, for sound effects.** Stable Audio 3 is gated behind a click-through the user has
  not made; do not use it or an ungated mirror of it. **Music has a paid route that works**
  (Lyria 3 Pro on Replicate, about $0.24 a job of three songs) — only with the user's yes and a
  dollar cap for that job, asked by the main loop.

## What the user has said

- Bow and arrow sounds, and the 30-archer variety mix: **approved** ("Sounds awesome. I love
  the variety in the arrow shots.").
- Arrow sound sets: **approved** ("The sounds effects sound good just make sure you
  catigorized them."). **Every sound set is categorised** — one folder per category the game
  picks from at random. For arrows: **release** (on fire), **hit** (arrow strikes a body),
  **miss** (whoosh past, thunk in the ground), **blocked** (wooden knock, metal clank).
- **All music is Celtic and sea shanty**: traditional Celtic instruments, a traditional Celtic
  scale (major, Mixolydian, Dorian, Aeolian, pentatonic). **Never an Arabian scale** ("that
  awkward flat note") and never Middle-Eastern instruments. The sea-shanty crew chanting
  voices are loved. **Keep strings a violin, not a fiddle** — no folksy fiddle-reel sawing
  (user, approving the extra battle songs: "be carful not to turn the violin into a fiddle"):
  ask for bowed violin or strings, and never name "fiddle" or "reel" in a prompt.
- Battle music: the first upbeat epic loops were **rejected** as too happy and cheerful. What
  is wanted: "medieval type of song ... Celtic background music" — frame drums or bodhran,
  fiddle, harp; a minor or modal key (Dorian, Aeolian); driving, not cheerful. Loops that
  kept a held high tone were called ear-piercing. The three Lyria battle songs are
  **approved** ("all three amazing"), and so are the three light-hearted menu songs — but all
  three battle songs have an Arabian feel, the war chant most, so they are not the model for
  a new song's scale.
- Knife sound sets (attack, hit, miss): **approved**. The user wants every sound set
  categorised — folders plus a list file — so the game can pick at random later.
- **Which set plays on which event is the user's call, after listening** ("we'll designate which
  kind of bucket of sound effects should be used for which action"). Name a set for what it
  sounds like, and assign nothing to a button or event.
- Menu sounds: **all the paper and click sounds approved** ("I approve all the paper sounds and
  click sounds we can designate 2pools of sounds and which pool a button or menu will pull from").
  So there are **two pools**, `sandbox/73/sets/paper_rustle` (12 sounds) and `sandbox/73/sets/click`
  (19): each button or menu names one pool and pulls from it at random. Which pool goes on which
  button has not been said. Pen scratches were not judged, and the scroll unroll and roll-up sets
  were not named.
- Hurt voices: **only the short ones approved** ("For hurt voices I approve only the short ones the
  longer one don't sound right."), then the set split at 0.80 s approved — 5 distinct takes a
  voice. They want the shortest grunts and do not pick them by sound name ("uhh", "ugh"): sort by
  length, not by prompt. Battle cries **approved as made** ("Just approve the sound effects for
  now").

## Where things live

| What | Path |
|---|---|
| One job's sandbox (venv, weights, takes, report, clip) | `src/asset-animation-demo/local_runs/auto/sandbox/<id>/` |
| MOSS setup, generator, checks (the working copy) | `sandbox/62/install.sh`, `gen.py`, `check.py`, `run_render.sh`, `sheet.py` |
| Front+body variants, crowd mix, captioned clip | `sandbox/63/mix.py` |
| Category sets: trim, thud cut, body check, variants, list.json | `sandbox/66/sort_sets.py`, `crowd_and_sheet.py` |
| Paid songs on Lyria 3 Pro: generator with cap, piercing-tone, outside-scale, flat-second and tempo measures, clip (the working copy) | `sandbox/80/`: `gen.py`, `tonal.py`, `scale.py`, `flat2.py`, `tempo.py`, `clip.py`; older `sandbox/79/`, `sandbox/61/paid/`, `sandbox/70/` |
| Knife sets: trim, start limit, drop, level, de-dupe, list (the working copy) | `sandbox/67/sort_sets.py`, `finish.py` — run with `sandbox/62`'s venv python |
| Voice sets: first-burst cut, pitch-only variants, pitch reading, crowd test | `sandbox/72/sort_sets.py`, `gen.py` — its de-dupe covers model takes only, not variants |
| Split a set at a length with no re-render: moves rather than deletes, rebuilds both list files | `sandbox/72/keep_short.py` (`CUT_SECONDS`) |
| One-at-a-time sets, no crowd test: a start and a length limit per bucket, variant de-dupe, faint takes listed (copy this for menu-like sets) | `sandbox/73/sort_sets.py`, `gen.py`; coins `sandbox/78/` |
| ACE-Step generator, loop cutter, waveform sheet (the working copy) | `sandbox/61/celtic/gen.py`, `loop.py`, `run_render.sh`, `sheet.py` — not the older `sandbox/61/loop.py` |
| Research behind the model choice | `local_runs/auto/research/sound-effects-and-music.md` |

Copy the nearest job's scripts into the new sandbox and change the prompts, seeds and counts.
Run every script with `sandbox/62/.venv/bin/python` — system `python3` has no numpy.
`mix.py` imports `check.py` from `sandbox/62` by path, so point that import at the copy.

## Sound effects with MOSS-SoundEffect v2.0

**Setup** — none for a new job: point `run_render.sh` and `gen.py` at `sandbox/62`'s venv and
`models/` by path rather than reinstalling 12 GB. A fresh install, if 62 is gone, is about
12 GB with 10 GB of weights. The model is
`OpenMOSS-Team/MOSS-SoundEffect-v2.0` — not the older `MOSS-SoundEffect` repo, which is an 8B
token model. It runs on MPS through the
`https://github.com/VladimirTalyzin/MOSS-SoundEffect_v2.0_MPS_ROCm` wrapper, cloned to
`<sandbox>/moss`. `install.sh` makes a Python 3.12 venv with uv inside the sandbox (managed
Python kept in the sandbox too), installs torch and the wrapper's requirements, checks MPS,
then runs `download_model.py`.

**Render** with `run_render.sh`: it sets `PYTORCH_ENABLE_MPS_FALLBACK=1
TOKENIZERS_PARALLELISM=false TORCHDYNAMO_DISABLE=1`, runs `gen.py` under a time limit, and
logs memory and swap to `mem.csv` every 5 s. Under the queue runner `Monitor` is refused, so wait
in foreground loops of 540 s; the 10-minute Bash limit moves a 590 s loop to the background. `gen.py` loads with
`mps_compat.load_pipeline(MossSoundEffectPipeline, <models/MOSS-SoundEffect-v2.0>,
torch.bfloat16, "mps")`, 2.0 s of audio, 50 steps, CFG 4.0, one seed per take, and skips takes
already on disk so a stopped run resumes.

| Measured on the M1 Max, 32 GB | |
|---|---|
| Load | 22 s |
| One take, 2 s of audio, 50 steps | 140–157 s — 16 takes is about 40 min |
| Peak memory | 20–21.5 GB at most; `mem.csv` reads `ps` RSS, which has read as low as 11.4 GB on the same model, so it is no footprint measure. Swap peaked 6.6–11.9 GB and fell back |
| Output | mono, 48 kHz |

Prompt one sound, close up and dry: "A single sharp bow string release: one quick taut twang
and a short whoosh of an arrow leaving the bow, close up, dry, no music, no voices." Make 6–8
takes a sound. Takes kept: voices 38 of 40, metal knocks 6 of 6, coins 31 of 35, menu sounds 38
of 52, bow and arrow about 3–4 of 8. A seed can give silence — peaks of -66 and -51 dB — so drop
that take rather than gaining it up.

**Asking for a short sound does not make it short.** MOSS fills the 2 s: "short" and "very
brief" paper and pen prompts gave 4–21 bursts, "a single coin" gave 4–6, and a pour or slide
always reaches the length limit. Cut after the render, by the set's purpose: a limit per bucket
ending on a 60 ms fade (`limit_length`, `MAX_SECONDS` in `sandbox/73`, `sandbox/78`), and tell
the user which sets were cut, to listen for an abrupt end. What each prompt gives:

- **Clicks** prompt well, under 0.11 s.
- **Paper crinkle** swelled late on all 4 seeds, 270–490 ms, and all were thrown out; ask for a
  rustle or a flick instead.
- **Pen** comes out faint, peak 0.007–0.06, and is lifted 20–30+ dB. Keep it and list it for
  hiss (`QUIET_RAW_DB`). Scribbles start slowly: 1 of 4 survived.
- **Voices**: MOSS makes voiced sounds from "A grown man/woman ... a short low pained uhh ...
  close up, dry, one voice only, no words, no music, no echo, no crowd", but says them two or
  three times. Cut each to its first burst (`keep_first_burst`, `sandbox/72`; 44 of 76 sounds
  needed it), limit cry 1.8 s, and list whatever still holds two. A hurt voice has to be short:
  a limit of 1.2 s let through the long ones the user rejected. `sandbox/72/sets` holds
  0.29–0.76 s, split at 0.80 s where both voices have a natural gap (men 0.76 to 0.87 s, women 0.66
  to 0.81 s), with the rest in `sets_long_hurt`. Among men "ugh" ran 0.33–0.61 s and "uhh"
  0.87–1.26 s, so any limit under 0.87 s loses every male "uhh", and a new one needs a prompt or a
  cut that ends sooner. To shorten a set already made, run `keep_short.py` with a new
  `CUT_SECONDS`: no re-render, longer sounds moved, both list files rebuilt. Half of a set is
  pitch copies, so count distinct takes, not files (12 files a voice were 5 takes), and say so.

**Trim and level** with `check.py`. The sound lands anywhere in the 2 s, up to 1.4 s in, so
every take is cut: leading silence off below -40 dB under the take's peak, 2 ms pre-roll,
10 ms fade at the end. Gain is the lesser of what reaches -20 LUFS and what keeps the peak
under -1 dBFS. **A thud (ground, wood) is over in 100–400 ms**, and the rest of its 2 s is a
quiet noise floor the gain boosts until the take fails tail and length: end it where it falls
-40 dB under its peak, with a 30 ms fade (`sort_sets.py`; this rescued 4 takes). **A short sound cannot reach -20 LUFS under that peak limit** — arrow hits land
at -24 to -27 — so a short sound's loudness is set by its peak, and that is expected, not a
failure.

**Short knife sounds** (swish, stab, slash, scrape) follow the same trim, with these limits
(`sandbox/67/sort_sets.py`, `finish.py`): cut every one at -40 dB under its peak; a stab
starts within one action frame (62 ms); drop a variant whose peak is under -12 dB; scale
crests to -1 dB; drop a variant over 90% alike to one already kept. 4 of 24 variants went
this way, and 30 attacks crowd-mixed to -5.38 dBFS. **The -12 dB floor is for hits only:** a held
sound levelled to -20 LUFS peaks low and is still loud, so voices, menu sounds and coins use
-24 dB.

## Variants and crowds with ffmpeg (no model, seconds)

`mix.py` makes 8 variants a sound from the survivors:

- **Front + body.** The sharp front of one take crossed into the body of another with an 8 ms
  equal-power crossfade (`afade curve=qsin`). Split at 80 ms for a bow release (its attack
  climbs for about 70 ms), 30 ms for an arrow hit.
- **Pitch and volume.** `asetrate=<48000 × (1 + pct/100)>,aresample=48000` over pitches from
  -6% to +6%, and volume 0 to -2 dB, shuffled per sound.
- **Voices, menu sounds and coins: pitch only**, one ±5% copy of each survivor, no front+body
  splice. Run the de-dupe on the variants too: a 5% copy of a click can stay over 90% alike its
  source.
- **Distinctness.** Normalised cross-correlation between every pair. Front+body swaps work for
  the bow (closest pair 57% alike) and barely for arrow hits (90%), whose energy is all in the
  front: **variety for a short hit needs more distinct fronts**, so make more model takes
  rather than more swaps.
- **The crowd test.** 30 shots over 10 s at random times, mixed offline through one fixed bus
  of **-8 dB set before measuring**, never normalised after. 30 releases plus 30 hits peaked at
  -5.4 dBFS, so -8 dB leaves headroom for 30 fighters. Render the single-file version on the
  same schedule beside it, so the only difference the user hears is the variety. **Voices are
  held and stack higher:** 30 hits plus 10 cries reached +0.18 dBFS at -8 dB and -1.82 to -2.1 at
  **-10 dB**, so a voice set takes -10 dB. Sounds that never play 30 at once (menu, coins) skip the
  crowd test.

**Sorted sets for random play.** Every sound set is one folder per category (for arrows:
`release`, `hit`, `miss`, `blocked`), each holding its WAVs and a `list.json` of name, seconds
and loudness that the game picks from at random each shot. A category with fewer than about 4
good sounds gets new MOSS takes and the same variant step: whoosh-past and thunk-in-the-ground
for miss, wooden knock and metal clank for blocked. The crowd test draws its 30 shots at random
from the sets; arrows peaked at -5.45 dBFS, no clipping.

## Music loops with ACE-Step 1.5

**Setup.** Clone ACE-Step 1.5 into the sandbox, a Python 3.11 venv beside it with ACE-Step,
MLX and PyMusicLooper, and download the `ACE-Step/Ace-Step1.5` checkpoints plus
`ACE-Step/acestep-5Hz-lm-0.6B` (about 11 GB). **Use the 0.6B language model**, never 1.7B: one
M1 Max report hit about 42 GB with it.

**Render** (`gen.py`): DiT `acestep-v15-turbo`, LM over `backend="mlx"`, no CPU offload; 60 s
instrumental at a set BPM and key, 8 inference steps, guidance 1.0, one seed a take. Pass
`use_cot_caption=False`, or the LM rewrites the caption and the asked instruments and mood
drift. Three captions (instrument sets, BPMs, keys) of two seeds each gives the user six takes
to pick from; each takes 33–37 s.

| Measured on the M1 Max, 32 GB | |
|---|---|
| Load | 56 s (DiT 21 s, LM 35 s) |
| One 60 s take | 33–55 s |
| Peak footprint | **37 GB** — the research's 15 GB is far too low; swap peaked 18.8 GB and recovered |

**Run it alone**, with ComfyUI closed and nothing else open that holds memory.

Takes wind down by about 56 s even with "no ending" in the prompt, so cut the loop before
that.

**Cut the loop** with `loop.py`: PyMusicLooper's candidate points, kept to loops of at least
30 s within 20 ms of a whole number of bars, then a whole-bar grid of its own (start and end
whose next 2 s match best on a mel spectrogram), closed with a 40 ms equal-power crossfade. It
walks the ranked points until one holds all three: under 1 LU across the join, a crossfade step
no bigger than the neighbouring samples', and an unbroken beat — the tracked beat gap at the
join within 10% of the loop's usual spacing. The beat test is there because an on-bar looper
point can hold every other number and still break the beat (gaps of 0.70–0.74), and the grid is
there because half the takes had no on-bar looper point at all.

`loop.py` also prints a best-fit major and minor key. It is a hint that the take is in a minor
key, and says nothing about mood: only ears judge that.

## Songs on Lyria 3 Pro (paid, with the user's yes)

`google/lyria-3-pro` on Replicate: $0.08 a file, a full song up to 3 min, so a job of three is
$0.24. `gen.py` refuses to pass its `CAP` and skips takes already on disk. The prompt is a
style line, a **timestamped form** (`[0:00 - 0:20] soft start ... [2:30 - 3:00] keeps going at
the same level to the very end`) and a closing line that bans the piercing sounds by name —
"no tin whistle, no flute, no piccolo, no high fiddle, no shrill bagpipes ... no whistle, no
shrill". That passed first round with no re-rolls for both intense battle songs and
light-hearted menu songs. **An asked key does not hold**: Lyria tends to sit on D whatever key
is asked, and spelling the notes out in the prompt did not hold it either. Name the scale
plainly instead — "G major pentatonic" in the style line cut outside-scale sound from 21.6% to
14.7%. A tempo in the prompt does hold: ~120 BPM tracked 117–123 on `tempo.py`. Lyria can
refuse a request with E005 "sensitive" (2 of 10 in each of two jobs); a new seed passes. `elevenlabs/music` at $0.0083 a
second is too dear for a $2 cap, and the ElevenLabs key on file is invalid.

**Piercing is a held narrow tone, not broad high energy.** `tonal.py` measures it: a narrow
tone standing 18 dB over its neighbours at 1.5–8 kHz, held 0.25 s or more, weighted by its
share of the frame. The approved battle songs scored 0.7–3.4% against 5.8–27.2% on the loops
called ear-piercing, while their broad energy above 2.5 kHz was no lower — so judge by
`tonal.py`, not by a high-band level. True peak lands up to +0.7 dB; say it.

**An Arabian scale shows as sound outside one seven-note scale.** `scale.py` finds the
best-fitting seven-note scale (any mode of a major scale) and measures the share of pitched
sound outside it. Battle songs the user heard as Arabian scored 17.8–23.0%, in the order they
ranked them; approved menu songs scored 8.9–13.5%. Drop a take over about 15% before showing
it, until the user's ears disagree with that bar.

**`scale.py` cannot see Phrygian.** A tune with a flat second still fits one seven-note family
(Phrygian is a mode of a major scale), so it scores low; and its bin count leans uneven — white
noise leans C, and every song read F. Run `flat2.py` beside it: it finds the home note and
reports the share a semitone above it against a whole tone above. On synthetic tunes D
Aeolian/Dorian scored 0.7% and Phrygian/Hijaz 8.6%. It did not rank the user's three
Arabian-feeling battle songs in their order, so both scripts are hints and ears decide. A
synthetic test tune built from random notes can skip the very note under test: cycle every
scale note. The listen clip for a job of five songs fits
the queue page's 15 MB clip limit at 120 kbps audio.

## Captioned listen clip

- This Homebrew ffmpeg has **no `drawtext`**: draw each caption card with matplotlib (Agg) and
  loop the still for its sound.
- A looped still with `-shortest` overran the audio by 3.7 s and left silent video: give the
  card **`-t <sound length>`** instead.
- Run every ffmpeg in a script with **`-nostdin`**, or it eats the script's input.
- Each sound plays once with its name and its check result on screen, so the user can
  overrule a failure. A loop plays once, then about 6 s past its join.
- A sound for an action goes on a **copy** of the approved action's mp4; the approved file is
  never touched.
- Show a waveform sheet beside the clip for the look; the clip is what gets judged.

## Defects

| Defect | Cause | Fix |
|---|---|---|
| Take fails "slow start" | the sound sits late in the 2 s | trim from the take's own peak, not the file start |
| Clipping reported on a clean take | takes touch 1.0 for a sample or two | judge clipping as a flat run of 3+ samples at full scale, not a touch |
| A thin tick passes every check | the checks see onset, tail, clip and tone, not body | body check (`sort_sets.py`): RMS from peak + 20 ms on, against the peak; under -40 dB is a tick — list it, and never use it as a front |
| Woody ring or knock failed as a stuck tone | the tone limit (one bin holding half a frame's energy for 60% of frames) is a starting number; knocks ring | list a ring on a knock for the user, never fail it |
| Thud fails tail and length | boosted noise floor after a 2 s take's short thud | cut at -40 dB under peak, 30 ms fade |
| Whoosh, voice, paper or pen fails "slow start" | they swell in | their start limit is 200 ms |
| 6 of 8 roll-ups and 4 of 8 unrolls fail "slow start" | a 1–2 s scroll slide swells for longer | its start limit is 400 ms; list anything past 200 ms for the ears |
| Voice says it two or three times | MOSS repeats a voiced sound | cut to the first burst (`keep_first_burst`) |
| Held shout dropped as too quiet | -20 LUFS peaks low on a held sound | variant floor -24 dB, not -12 |
| Crowd of voices clips | held sounds stack higher | bus -10 dB, not -8 |
| Pitch copies of a click sound the same | 5% barely moves a very short sound | de-dupe variants at 90% (`sandbox/73`) |
| Take is silent | a bad seed (MOSS 6805 peaked -66 dB) | drop it, new seed |
| Bow release sounds doubled | 2–3 bursts in one take | list burst counts for the user; prefer one-burst fronts |
| Arrow variants sound alike | the hit is all front | more distinct model takes, not more front+body swaps |
| Loop join loud or late | top-ranked point off the bar or over 1 LU | walk ranked on-bar points (`loop.py`) |
| Beat stumbles at the join, every number passing | an on-bar looper point that breaks the beat | hold the beat gap within 10% (`loop.py`) |
| No loop point for a take | PyMusicLooper finds none on the bar | the whole-bar mel grid (`loop.py`) |
| Caption's instruments or mood drift | the LM rewrites the caption | `use_cot_caption=False` |
| Song sounds Arabian ("that awkward flat note") | a scale outside the Celtic set | name the scale in the prompt ("G major pentatonic"); drop takes over about 15% on `scale.py` |
| Lyria refuses with E005 "sensitive" | its filter on a prompt or seed | a new seed |
| Song in the wrong key, notes spelled in the prompt | Lyria leans to D | name the scale, not the key or its notes; check with `flat2.py` |
| Silent video tail on the clip | `-shortest` with a looped still | `-t` |

## Acceptance

| Check | Pass |
|---|---|
| Sound starts after the cut | within 30 ms; a whoosh, voice, paper, pen, or coin pour or slide within 200 ms; a scroll slide within 400 ms, past 200 listed |
| Tail at the end | under -60 dB over the last 50 ms (-58 is likely inaudible; say so) |
| Clipping | no flat run at full scale |
| Stuck tone | under the limit, or listed for the user (a knock's ring is always listed) |
| Body | RMS after peak + 20 ms over -40 dB under the peak, or listed as a thin tick |
| Survivors | at least 3 a sound, about 4 a sorted set |
| Crowd mix, 30 shots in 10 s, bus -8 dB (voices -10 dB) | peak under 0 dBFS |
| Length | under the bucket's limit; sets cut there are named for the user |
| Music take | no crash, swap recovers, a take under 5 min |
| Song (paid) | held high tone (`tonal.py`) under about 10% of the song; outside-scale sound (`scale.py`) under about 15%; flat second (`flat2.py`) listed for the user; spend under the job's cap |
| Loop | at least 30 s, a whole number of bars at the asked BPM, join step no bigger than normal neighbouring samples, under 1 LU across the join, beat gap at the join within 10% |
| The sound or the music itself | **the user listening** — nothing else passes it |

## What still fails

- **Arrow-hit variety rests on few distinct fronts.**
- **Male and female voices may not separate.** Male cries read about 340 Hz against 374 for the
  women. The reading is a hint for the ears, never a reason to drop a take: it tops out at its
  500 Hz limit, and a held "raah" can read as one flat note for the full 1.8 s.
- **One clean short texture.** A single coin clink or a single pen stroke is not proved, and
  a pour keeps hitting its limit. Rendering under 2 s, or allowing a longer limit, is untried.
- **Scale is a hint, not proof.** `scale.py`'s 15% bar rests on one job's ranking; outside-scale
  sound also counts drums and voices, and it is blind to Phrygian. `flat2.py` sees the flat
  second on synthetic tunes but has not matched the user's ranking. Trust their ears over both.
- **Holding a key on Lyria.** Neither an asked key nor spelled-out notes held it.
- **Local music's mood.** The ACE-Step loops hold every number but kept piercing held tones;
  the approved songs are paid. A free route with the same result is not proved.
- **What the music does across the join.** A loop can pass every number and still jump from a
  full section to a thinner one, or join two passages that match poorly; point the user's ears
  at those takes.

## Scorecard

Append one row to `scorecard.csv` per job:

```
date,job,kind,model,takes,survivors,variants,render_minutes,peak_gb,hand_fixes,new_tools,usd,user_verdict,note
```
