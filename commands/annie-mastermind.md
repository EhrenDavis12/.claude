---
description: One mastermind pass over annie's queue when it has no work — tidy Blocked, then make at most one auto job that serves the user's Focus. Also how an auto job is worked
argument-hint: "(none — the runner starts it when the queue is empty and the switch is on)"
allowed-tools: Agent, Bash, Read, Grep, Glob, Skill, WebSearch, WebFetch
---

# Annie's mastermind

The arguments, if any, are: `$ARGUMENTS`

The runner starts this when annie's queue has nothing to work and the user has switched the
mastermind on. It keeps the queue moving one small step at a time while the user is away. It
**follows choices the user has already made and never makes a new one.**

```
Q=.claude/systems/annie/queue/q.py
F=.claude/systems/annie/queue/focus.md
OUT=src/asset-animation-demo/local_runs/auto
```

`$F` is the user's Focus: the **Goal**, what matters **Right now**, and the topics to
**Learn**. It is theirs — read it, never edit it. Every job you make moves us toward the Goal
by way of Right now.

**What to do next is reasoned, not listed.** Work out the gap between where we are and the
Goal: which asset type has no proven method yet, which one a game needs soonest, which is
cheapest to prove, and what a proof would leave behind that the game can use. Pick the step
that closes the most of that gap. What the user has dropped, paused or ruled out is in memory
and in the queue's notes — read it there and steer clear; nobody keeps a list of it for you.

## The rules

1. **Never ask the user anything, and never add to Blocked.** No `AskUserQuestion`, no
   `q.py ask`. A job that would need the user's answer is not made.
2. **Prep and research only.** No clip rendered for the user to approve, nothing approved or
   installed touched, no Unity scene or app code (that is forge's). Work lands under `$OUT`.
3. **Local and free.** No paid model, ever. A web search is fine.
4. **One job per pass.** A pass makes at most one item, `add --auto --bg`. q.py's gate holds
   the daily cap, the cooldown and the pause while auto results wait for the user.
5. **Skills learn; agents and workflows are proposed.** A lesson for a recipe goes in a
   `FOR MAIN LOOP:` note, as `/annie-queue` says. A change to an agent, a command, the
   runner or the pipeline goes in the report under `PROPOSAL:` — never made.
6. **Never answer a taste question** — a colour, a face, a mood, a style, whether something
   looks right. Those stay open, however sure you are.

## A pass

1. **Know what exists — by search, not by reading the board.** You are only useful if you
   never re-make what exists, and the full board is about 100 KB, so never `list` it whole:
   - `python3 $Q list --brief` — one short line per item, every state, done included;
   - `python3 $Q find <word> [<word> ...]` — searches the queue **and** the archive. Search
     for each candidate job's subject before choosing it (`find spark`, `find unity effect`),
     and read an item in full only when a hit could be the same work;
   - `grep` the recipe list in `.claude/skills/AnimationSkills/SKILL.md`, the roster in
     `SYSTEM.md`, the memory index and `$OUT` for the same words — a recipe or agent for a
     thing means that route is already chosen;
   - `$F`, which is short.
   The newest work wins: when the user has moved a kind of asset onto a newer route (a Unity
   build, a new recipe), the older route is closed — research and tests on it are repeats.
2. **Tidy Blocked.** `python3 $Q show <id>` each blocked item from the brief list — only
   those — and for each open question:
   - If a memory, a recipe or a design doc **already states** the answer, and it is not a
     taste question, answer it:
     `python3 $Q answer <id> <n> "Mastermind (<date>): <answer> — from <where it is said>, quoted: '<the words>'."`
     A guess, an inference, or "most likely" is not an answer; leave it open.
   - If a big blocked item has a part that does not depend on the open question, that part
     may be this pass's one job (next step), titled `Split from #<id>: …`.
   Then `python3 $Q list`: if anything is now queued, the runner will pick it up — stop here.
3. **Make one job.** Pick the kind, in this order of preference:
   - **Try one trick** — a researched trick under `$OUT/research/` that has no sandbox test
     yet and serves Right now.
   - **Look back** — when no look-back report from the last 7 days is in `$OUT/lookback/`:
     what has worked and what has not, from the scorecards, rejects and memory, and where
     to use more of what worked.
   - **Research** — the first Learn topic in `$F` with no report in `$OUT/research/`.
4. **Check it before adding.** Every line must be yes, or the job is not made:
   - You searched for it (`find`, `grep`) and read every hit that could be the same work.
   - It moves us toward the Goal by way of Right now, and nothing the user has dropped or paused.
   - It can finish without the user's answer to anything.
   - It is local and free, and touches nothing approved or installed.
   - It produces a report or a sandbox picture, not a clip for approval.
   - Nothing in the queue (done included), the archive, a recipe, an agent or `$OUT`
     already covers it, and it is not on a route newer work has replaced. Name the closest
     existing work in the job's note and say in one clause why this is not a repeat.
   - One worker can finish it in about two hours.
5. **Add it:**
   `python3 $Q add --auto --bg "<Research|Look back|Try> : <title>" --note "Serves: <which part of Right now>. Closest existing: <item or recipe> — not a repeat because <why>. Job: <what to make, where, done when>."`
   Then `python3 $Q render` and publish to the Queue page, as `SYSTEM.md` says.
6. **Report** in two lines: what was tidied, what was made (or why nothing was).

If nothing passes the check, make nothing. An empty pass is a good outcome, not a failure.

**Last step, always:** `[ -n "$ANNIE_WORKER_DONE" ] && touch "$ANNIE_WORKER_DONE"`

## Working an auto job

`/annie-queue` sends an item marked `auto` here instead of through the animation pipeline.
Its note says what to make. The rules above still hold.

- **Research** — search the web for what real studios and good games do, then write
  `$OUT/research/<topic-slug>.md`: what they do; what applies to us, given the Focus and the
  archer method; **one to three cheap tricks** worth a sandbox test, each with how to test it
  and what pass looks like; then any `PROPOSAL:` lines. Short. The tricks are the point.
- **Look back** — read the scorecards under `.claude/skills/AnimationSkills/`, the memory
  files, and the queue's done and rejected notes. Write `$OUT/lookback/<date>.md`: what
  worked, what did not, and the places still done the old way — each one a job a later pass
  could make.
- **Try** — work only in `$OUT/sandbox/<id>/`. Use annie's agents as the trick needs (key
  artist for stills, tool writer for a script), with a brief that says "sandbox test, not
  for any action"; their budgets hold. Never touch a character's real files. End with a
  contact sheet and a one-line pass or fail.

Then: `python3 $Q note <id> "<one line: what it found or showed>"`, a `FOR MAIN LOOP:` note
for any recipe lesson, and park it for the user — `python3 $Q clip <id> <the sheet png>` for
a sandbox test, `python3 $Q move <id> review` for a report. A job that cannot finish says why
in its note and goes to `review` too, never to `blocked`.

$ARGUMENTS
