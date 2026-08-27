---
name: generate-asset
description: Generate one of the active project's assets through the Asset-Gen-Framework CLI, then surface the draft for the user to approve. Use when the user asks for an image, sound, music, sprite sheet, or video that their project's asset manifest already describes — or asks what assets a project declares, or what one was last asked for. Does not write prompts, choose models, approve anything, or move a file out of drafts.
---

# Generating an asset

The framework lives at `src/Asset-Gen-Framework` in this mono repo. It is a CLI, and running
it is a `Bash` step — no agent, for the same reason there is no test-runner agent: running a
command needs no judgment, and this one needs less than most, because the framework already
checks what came back.

**It works from whatever project is active.** Project scoping governs what may be *written*,
not what commands may be *run*, so a tic-tac-toe session generates tic-tac-toe's assets
without switching anything. What the active project supplies is its own config file, which
names its manifest, its sample and base assets, its drafts area, and its record.

## Before the first run

The framework needs a Replicate credential in the environment, and it reads it from there
only — never from a flag, a file, or a prompt. If it is missing, say so and stop; do not ask
the user to paste a token into the conversation.

The active project needs a config file and a prompt manifest under its own source root. If
neither exists, that project has no assets declared yet — say so rather than inventing one.
**Writing them is that project's work**, so under a system with a write boundary it goes
through whichever agent owns that project's source, and it needs that project active.

## Running it

Read the four commands, then run one:

```
agf list              what entries the manifest holds
agf record <name>     what an entry was last asked for
agf generate <name>   generate one entry into the drafts area
agf regenerate <name> generate it again, replacing the draft that is there
```

Each prints exactly one JSON document, on success and on failure alike, and says what failed
and what to change. Read that document rather than guessing from the exit code alone.

**Generating spends real money.** Every `generate` and `regenerate` is a paid API call. So:

- **One entry per invocation, named explicitly.** There is no bulk command by design; do not
  build one out of a loop unless the user asked for exactly those assets.
- **Never rerun a failed generate hoping it works.** The framework reports what was wrong,
  and almost every failure is a manifest mistake that costs nothing to fix and everything to
  retry blindly.
- **`agf record <name>` before regenerating.** It says what was last asked for, so a new
  request is a change from it rather than a fresh guess.

## What you may not do

- **Never write or edit a prompt, a model id, or any manifest entry.** Those are the calling
  project's, hand-written by the user. A prompt an agent invented gets recorded as provenance
  and read back later as a decision — which is how a guess becomes a requirement.
- **Never approve an asset, and never move one out of the drafts area.** Approval is the user
  saying yes, and the move is theirs. The framework cannot write where approved assets live,
  which is what makes a rerun safe; doing the move on their behalf destroys that guarantee.
- **Never edit the framework itself.** That is its own project — changing it means switching
  to it, deliberately.

## Reporting back

Say what landed and where, and give the user what they need to judge it:

- The path of each file written, so they can open it.
- What the framework checked and what it could not. A returned sprite sheet is verified
  against its declared dimensions, but nothing verifies how many cells actually hold art.
- The two-stage shape, if this is their first asset: it is a draft, nothing ships until they
  say so, and discarding it costs nothing.

**Do not tell the user an asset looks right.** They approve by looking at it. Report what was
generated and what was verified; the judgment is theirs, and a confident "this matches the
prompt" from an agent that cannot see what they intended is worse than silence.

If a run fails, relay what the framework said it wanted changed. Fix a manifest mistake only
if the user asks, and only through whoever owns that project's source.
