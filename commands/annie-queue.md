---
description: Work annie's queue — take the top queued animation through the pipeline, park it for the user's eyes or on a question, and move on to the next, without ever stopping to ask
argument-hint: "[--one] [--paid] — omit --one to keep going until nothing is queued; --paid: the paid slot"
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
   `python3 $Q next` refuses to claim a second item. The one exception is the paid slot below.
4. **An item already `working` when the run starts is resumed, not restarted.** Check its note
   and the files it names, then pick up from the last stage that finished.
5. **Never wait with `while pgrep -f "<pattern>"`.** The waiting shell's own command line
   holds the pattern, so pgrep finds itself and the loop never ends: a worker sat in two such
   loops for 15 hours (2026-10-27). Wait on the job's PID (`while kill -0 $PID`), a finished
   file it writes, or the background task's own completion notice.
6. **Every note is a promise, and the runner holds you to it.** Under the runner, each
   `python3 $Q note <id> "..."` on the working item buys the stage it starts 90 minutes; a
   stage that will take longer says so up front with `--minutes N` (at most 180 — a longer one
   notes again part way). A worker past its promise with no new note is taken down, whatever it
   looks like it is doing, and the next worker resumes from the note. So note before every
   stage and before every long wait, and say in the note what is running. The runner cannot
   tell a long render from a hung one; only your note can.
7. **Nothing waits open-ended.** A script that may run long goes under a time limit —
   `perl -e 'alarm shift; exec @ARGV' <seconds> <command>` (macOS has no `timeout`) — and a
   wait polls with a limit too. In Python, never use a `multiprocessing` Pool without an
   `if __name__ == "__main__":` guard: Python 3.14 on macOS starts its children by re-running
   the script, so they spawn forever and the pool never returns — a reviewer waited 7 hours on
   two such scripts (2026-10-30). A plain loop is almost always fast enough.
8. **Never end the turn while a subagent you started is still running.** Keep the turn open
   with a polling wait (with a limit, per rule 7) until it returns; a turn that ends early
   leaves the agent's result with nobody to act on it.
9. **The user's word is the only `done`.** A passing sheet review takes the item to `review`
   with its clip attached, never to `done`.

**Every animation, one picture in (user, 2026-11-09, `focus.md` "How every animation is made now"):** the video model gets only the character's approved picture and a short action prompt, no end pose and no in-between keys; it invents the whole action, the game snaps in and out of it, and the only grade is: a solid action, and the same weapon, clothes and face. This overrides any recipe or brief step that draws strike or hit keys or renders first-last.

**Away week (until about 2026-11-09, see `focus.md`):** the user is offline. No question
parks an item unless it needs money: take the default, note it as `Going ahead with:`. A pick
sheet still goes to `review`, with the reviewer's choice in its note as
`PROVISIONAL PICK: <n>, because <reason>`, so the mastermind can queue the next step from it.
A paid call this week follows `focus.md` "Replicate budget" (paid is the worker's call within it,
no asking; `edit_remote.py` for a pose the free tool cannot draw, hand-logged): the total
read before each call, never past $55.52 in `local_runs/replicate_spend.csv`, the item's own cap
($4 an action unless its note says less); a call on a path that writes no ledger line is hand-logged into the ledger the same minute. At the cap, finish locally.
Character and enemy clip takes go to the paid model, never local Wan (user, 2026-11-07: "we
know the local animations don't work that we have to do paid"); weapons stay in hand in every
idle and action. See `focus.md`.
Before claiming with `next`, plan by token usage (`focus.md` "Plan by token usage"): when
usage is near the limit, `python3 $Q up <id>` a long local render job first, so the hours go to
cheap-token work while the window resets. While a render runs, wait cheaply: `kill -0` on its
PID, minutes apart.

## The paid slot (`--paid`)

The runner may run one item marked paid beside the normal worker. With `--paid`, claim with
`python3 $Q next --paid`, which takes only paid items. A paid-slot worker uses remote models
only: it never starts the local model server, a local Qwen or Wan render, or Unity, because the
main worker owns them. Light local steps — matting, ffmpeg, measuring scripts — are fine. When
the next step needs a local render or Unity, note that on the item, then
`python3 $Q move <id> queued` (no `--top`: the local part waits behind the user's other jobs —
user, 2026-10-30: "once the paid part is done, and that same job now becomes lcoal clean up
parts, that can wait behind the other jobs i had in my queue") and `python3 $Q paid <id> off`,
in that order, so the main slot does it in turn. The brief's dollar cap still binds; reaching it parks the item as usual.

## The loop

1. `python3 $Q next` claims the top queued item and prints it, with any answered questions
   under it. The `now` lane always goes first; the background lane only runs when `now` is
   empty. If nothing is queued in either, say so in one line and stop.
2. **An item marked `auto`** was made by the mastermind: work it as
   `.claude/commands/annie-mastermind.md` says under "Working an auto job", not through the
   pipeline, then go to step 4.
   **Otherwise, run annie's pipeline for that one action, exactly as `SYSTEM.md` says** — recipe through
   `animation-skills`, the shot brief, then keys, clips, sheets, each one with its reviewer and
   its budget. Answers already on the item go into the brief verbatim. Before each stage,
   `python3 $Q note <id> "<stage, one line>" [--minutes N]` so the page shows where it is and
   the runner knows how long it may take (rule 6). `note` replaces the whole note, so carry
   any `FOR MAIN LOOP:` text and every `User (<date>): '...'` quote into the new one — on a
   fresh item the user's words live only in the note. Re-read it first: the desk may have
   added words mid-run.
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
