---
description: Work annie's queue — take the top queued animation through the pipeline, park it for the user's eyes or on a question, and move on to the next, without ever stopping to ask
argument-hint: "[--one] — omit to keep going until nothing is queued"
allowed-tools: Agent, Bash, Read, Grep, Glob, Skill, SendMessage, WebSearch, WebFetch
---

# Work annie's queue

The arguments, if any, are: `$ARGUMENTS`

The queue keeps annie busy while the user is away. One item is worked at a time, and anything
that needs the user parks the item rather than the run. Run it once, or keep it going with
`/loop /annie-queue`.

Every queue change goes through the script, never by hand — it is the only writer. After
every change that moves an item, `python3 $Q render` and publish what it prints to the Queue
page (the link is in `SYSTEM.md`), so the user sees it from wherever they are:

```
Q=.claude/systems/annie/queue/q.py
python3 $Q list
```

## The rules

1. **Never ask the user anything during a run.** No `AskUserQuestion`, and no ending the turn
   on a question. A question is `python3 $Q ask <id> "<question>"` — `--blocker` when the
   item cannot move without it — and the run moves on to the next item. Word it the way
   `CLAUDE.md` says a question to the user must be worded: answerable without opening a file.
2. **Re-read the queue before every change.** The user may have reordered it from another
   session, so trust what the file says, not what you remember.
3. **One item working at a time.** This is annie's one-artist rule, nothing more.
   `python3 $Q next` refuses to claim a second item.
4. **An item already `working` when the run starts is resumed, not restarted.** Check its note
   and the files it names, then pick up from the last stage that finished.
5. **The user's word is the only `done`.** A passing sheet review takes the item to `review`
   with its clip attached, never to `done`.

## The loop

1. `python3 $Q next` claims the top queued item and prints it, with any answered questions
   under it. The `now` lane always goes first; the background lane only runs when `now` is
   empty. If nothing is queued in either, say so in one line and stop.
2. **An item marked `auto`** was made by the mastermind: work it as
   `.claude/commands/annie-mastermind.md` says under "Working an auto job", not through the
   pipeline, then go to step 4.
   **Otherwise, run annie's pipeline for that one action, exactly as `SYSTEM.md` says** — recipe through
   `animation-skills`, the shot brief, then keys, clips, sheets, each one with its reviewer and
   its budget. Answers already on the item go into the brief verbatim. After each stage,
   `python3 $Q note <id> "<stage, one line>"` so the page shows where it is.
   **On a background item, run `python3 $Q check` after each stage too.** On `yield`, put it
   back with `python3 $Q move <id> queued --top` — its note says where it stopped, and the
   files stay where they are — and go to step 1. Never stop an artist mid-render to yield;
   the check is between stages.
3. **Park it** when it reaches a point the user has to settle:
   - The sheet reviewer passes it, or its review budget is spent:
     `python3 $Q clip <id> <the mp4>`, then the Chart cell goes to `review`. Put what is still
     open in the note.
   - A **keys-only** item stops once `annie-key-reviewer` approves its keys: attach the keys
     sheet with `python3 $Q clip <id> <the png>`. No clip is rendered for it.
   - **A question that has a free, local default does not park.** When the planner or an agent
     names what it would do anyway ("going ahead with …"), and that default needs no paid model
     and touches nothing approved, record it with `python3 $Q ask <id> "<question> Going ahead
     with: <default>."` (no `--blocker`), move the item back to `working` if `ask` moved it, and
     carry on with the default. The user judges the result in the morning; an all-night run that
     parks on every soft question sits idle (user, 2026-10-26).
   - A planner or agent question that only the user's intent can settle, a step that would
     need a paid model, or local failing at its budget: `python3 $Q ask <id> ...` — it goes to
     `blocked` and the run moves to the next job. Every job is local and free; never switch to a
     paid model without the user's say-so for that job.
4. Run the end-of-run steps that do not wait on the user: the scorecard row and
   `skill-improver`, as `SYSTEM.md` says. **Under the runner, writes into `.claude/skills/` are
   refused** (unattended mode protects that folder). Do not try: put the scorecard row and what
   the run taught in the item's note instead, starting `FOR MAIN LOOP:`
   (`python3 $Q note <id> "FOR MAIN LOOP: scorecard <file>: <row> | lesson: ..."`), and the main
   loop saves them. One refused command never means every command is refused — keep going.
5. With `--one`, stop here. Otherwise go back to step 1. A parked item never stops the run.

At the end, one short report: what moved, and what is waiting on the user. **Never end on a
question.** Nobody reads a worker's window: a question goes into the queue with
`python3 $Q ask <id> ...` (or `note` on a done item) so it reaches the user through the main
session. A worker that stopped to ask in its own window sat idle all night (2026-10-22).

**Under the runner, the very last step is the finished mark** — after the report, whatever
happened, even when other commands or writes were refused, and with nothing queued too:

```
[ -n "$ANNIE_WORKER_DONE" ] && touch "$ANNIE_WORKER_DONE"
```

The runner starts each worker as an interactive session so it shows in Remote Control, and an
interactive session does not end by itself: this mark is the only thing that closes it. Never
write it earlier — the runner closes the session half a minute after it appears.

## When the user answers, in a normal session

This part runs outside the command, whenever the user speaks:

- **An answer** — `python3 $Q answer <id> <n> "<their words>"`. With no open question left, the
  item goes back on top of the queue.
- **"Approved"** on a clip — install, engine import, Chart cell to `done` (the steps
  `SYSTEM.md` lists), then `python3 $Q move <id> done`.
- **A rejection** — their words go on the item as an answered question, so the next brief
  carries them verbatim, and the item goes back to the top with `move <id> queued --top`.
- **New work, reorder, drop** — `add`, `up`, `move`, `drop`. Long batch work the user wants
  done "when nothing else is on" goes in with `--bg`; `lane <id> now|background` moves it.
