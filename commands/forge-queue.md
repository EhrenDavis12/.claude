---
description: Work forge's queue — take the top queued item through the forge pipeline, park it for the user's eyes or on a question, and move on to the next, without ever stopping to ask
argument-hint: "[--one] — omit to keep going until nothing is queued"
allowed-tools: Agent, Bash, Read, Grep, Glob, Skill, SendMessage, WebSearch, WebFetch
---

# Work forge's queue

The arguments, if any, are: `$ARGUMENTS`

The queue keeps forge building while the user is away. One item is worked at a time, and
anything that needs the user parks the item rather than the run. The runner
(`.claude/systems/forge/queue/run.sh`) starts a fresh session per job with `--one`; by hand,
run it once, or keep it going with `/loop /forge-queue`.

This is annie's queue, ported: the same script, the same promises, the same parking. What
differs is the work — the forge pipeline in `SYSTEM.md`, not an animation one.

Every queue change goes through the script, never by hand — it is the only writer. After
every change that moves an item, `python3 $Q render` and publish what it prints to the Queue
page (the link is in `SYSTEM.md`), so the user sees it from wherever they are:

```
Q=.claude/systems/forge/queue/q.py
python3 $Q list
```

## Resolve the scope first

Read `.claude/project/active.json` and the manifest whose `.name` matches it. Use `docsRoot`,
`srcRoots`, `prds`, `roadmap`, `stack` and `testing` if present. If either file is missing or
will not parse, **stop and say to run `/set-project`** — the one legitimate early stop. The
queue only hands out the active project's items, so an item from another project never
reaches you.

## The rules

1. **Never ask the user anything during a run.** No `AskUserQuestion`, and no ending the turn
   on a question. A question is `python3 $Q ask <id> "<question>"` — `--blocker` when the
   item cannot move without it — and the run moves on to the next item. Word it the way
   `CLAUDE.md` says a question to the user must be worded: answerable without opening a file —
   what happens on screen, the concrete options, how hard each is to change later.
2. **Re-read the queue before every change.** The user may have reordered it from the desk, so
   trust what the file says, not what you remember.
3. **One item working at a time.** Two live writers in one srcRoot is two builds stepping on
   each other. `python3 $Q next` refuses to claim a second item.
4. **An item already `working` when the run starts is resumed, not restarted.** Check its note,
   its branch in each srcRoot (`git -C <srcRoot> log queue/<id>-<slug>`) and any PRD it names,
   then pick up from the last stage that finished.
5. **Never wait with `while pgrep -f "<pattern>"`.** The waiting shell's own command line holds
   the pattern, so pgrep finds itself and the loop never ends: an annie worker sat in two such
   loops for 15 hours (2026-10-27). Wait on the job's PID (`while kill -0 $PID`), a finished
   file it writes, or the background task's own completion notice.
6. **Every note is a promise, and the runner holds you to it.** Under the runner, each
   `python3 $Q note <id> "..."` on the working item buys the stage it starts 90 minutes; a
   stage that will take longer says so up front with `--minutes N` (at most 180 — a longer one
   notes again part way). A worker past its promise with no new note is taken down, whatever it
   looks like it is doing, and the next worker resumes from the note. So note before every
   stage and before every long wait, and say in the note what is running. The runner cannot
   tell a long build from a hung one; only your note can.
7. **Nothing waits open-ended.** A test run, a build or a script that may run long goes under a
   time limit — `perl -e 'alarm shift; exec @ARGV' <seconds> <command>` (macOS has no
   `timeout`) — and a wait polls with a limit too. In Python, never use a `multiprocessing`
   Pool without an `if __name__ == "__main__":` guard: Python 3.14 on macOS starts its children
   by re-running the script, so they spawn forever and the pool never returns (2026-10-30).
8. **Never end the turn while a subagent you started is still running.** Keep the turn open
   with a polling wait (with a limit, per rule 7) until it returns; a turn that ends early
   leaves the agent's result with nobody to act on it.
9. **The user's word is the only `done`.** A green suite and a passing review take the item to
   `review` with its picture attached, never to `done`. Only the desk moves an item to `done`,
   on the user's approval, and only then is its branch merged — **unless the Focus carries the
   user's Standing approval**, their word given in advance (see "Park it").
10. **Everything `SYSTEM.md` says still holds.** You never write source, tests, design docs or
    PRDs yourself — the owning agent does. The review budget, the 250k bound, the escalation
    triggers and the no-docs-during-the-build rule are all in force. A worker is the main loop
    for its one job.

## The loop

1. `python3 $Q next` claims the top queued item and prints it, with any answered questions
   under it. The `now` lane always goes first; the background lane only runs when `now` is
   empty. If nothing is queued in either, say so in one line and stop.
2. **An item marked `auto`** was made by the mastermind: work it as
   `.claude/commands/forge-mastermind.md` says under "Working an auto job", not through the
   pipeline, then go to step 5.
3. **Answers first.** If the item carries answered questions and any answer settles a design
   question — a rule, a contract, a behavior — run `Skill(forge-tidy-docs)` with the answer
   text in its prompt before anything is built, so the answer lands in the design docs. The
   queue never becomes the only place a decision lives. Answers that are only preferences for
   this build go into the first dispatch verbatim.
4. **Run the forge pipeline for that one item**, below. Before each stage,
   `python3 $Q note <id> "<stage, one line>" [--minutes N]` so the page shows where it is and
   the runner knows how long it may take (rule 6). `note` replaces the whole note, so carry
   the branch, any `FOR MAIN LOOP:` text and every `User (<date>): '...'` quote into the new
   one — on a fresh item the user's words live only in the note. Re-read it first: the desk
   may have added words mid-run.
   **On a background item, run `python3 $Q check` after each stage too.** On `yield`, put it
   back with `python3 $Q move <id> queued --top` — its note says where it stopped, and the
   branch stays where it is — and go to step 1. Never stop an agent mid-dispatch to yield; the
   check is between stages.
5. Put what the run taught about the process in the note, starting `FOR MAIN LOOP:` —
   **under the runner, writes into `.claude/` are refused** (unattended mode protects that
   folder), so the desk saves lessons and runs `forge-retro-planner` when they repeat. One
   refused command never means every command is refused — keep going.
6. With `--one`, stop here. Otherwise go back to step 1. A parked item never stops the run.

## The pipeline for one item

### Decide the path, out loud

The title may carry a path tag — `[prd]`, `[look]` or `[research]` — and a size `[S|M|L]`. A
tag the user wrote wins. An untagged item gets the triage call now: read the design docs and
code it touches, then decide by the cost of a wrong guess — `[prd]` for rules, engine
semantics, persistence, money, or a contract other features depend on; `[look]` for layout,
animation, menus, settings, theming, copy; `[research]` when the item asks a question rather
than for a change. **Say the cost sentence** in the conversation, exactly as `SYSTEM.md`
requires, and put the tag in the note.

If the item cannot be built without a decision only the user can make, `ask` it now, before
any branch exists, and move on.

### Branch

Items build on each other before the user has approved them — the second screen needs the
first one's project — so every queue branch starts from **`queue/build`**, the stack of
everything built so far. In each srcRoot the work will touch:

```
git -C <srcRoot> rev-parse --verify queue/build || git -C <srcRoot> branch queue/build
git -C <srcRoot> checkout -b queue/<id>-<slug> queue/build
```

and name the branch in the note. When the item parks in `review`, merge it into the stack
(`git -C <srcRoot> checkout queue/build && git -C <srcRoot> merge --no-ff queue/<id>-<slug>`),
so the next item builds on it. A blocked item is not merged in. A resumed item checks out its
existing branch instead. A `[research]` item has no branch. The checked-out main branch is the
desk's: only approved work reaches it.

### Run the path

`SYSTEM.md` is the authority on each stage; this is the sequence, with the checkpoints:

**`[prd]`:** `forge-prd-author` → `forge-prd-reviewer` (a blocking finding goes back to the
author once; a second blocking finding is a `--blocker` question) → `forge-test-author` →
`forge-test-auditor` → `forge-code-writer` → **tests pass** (the manifest's `testing.command`)
→ `forge-code-cleaner` → **tests still pass** → `forge-code-reviewer` → `forge-code-prd-alignment`
→ `forge-harvest-planner` for this PRD → `forge-doc-writer` → `git rm` the PRD once the
planner's **Ready to delete** line reads clean.

**`[look]`:** built-in `Plan` agent → `forge-test-author` and `forge-test-auditor` only if
there is behavior worth pinning → `forge-code-writer` → **tests pass** → `forge-code-cleaner`
→ **tests still pass** → `forge-code-reviewer`.

**`[research]`:** no code. Answer the question the item asks, with sources: read the design
docs and code first, then `WebSearch`/`WebFetch` for anything outside the repo — or dispatch
the built-in `general-purpose` agent when the reading is broad enough to crowd the context.
Write the findings to `<docsRoot>/queue/reports/<id>-<slug>.md`: what was found, the options,
the recommendation and why, what each option would mean for the game. A recommendation is a
decision only the user can make, so the item **always parks on questions**: one `ask` per
decision. If the findings contradict a design doc, say which passage and leave the doc
alone — the answer lands there through `forge-tidy-docs` when the user answers.

Every path: one dispatch per stage, in sequence, each finished before the next. A reviewer
finding that is a defect goes back to `forge-code-writer`, within the review budget. Any
agent that returns **Needs your call** with a question you cannot settle by reading is an
`ask`.

### Show it

Before parking a built item, **look at it**: run the app or the scene the way the project's
run skill says (`Skill(playtest)` for the app; the `unity-cli` or `unity-pipeline` skill for a
Unity scene), and capture what the user would judge — a screenshot, or a short mp4 when the
change moves. Save it under the scratchpad and attach it with `python3 $Q clip <id> <path>`.
Appearance is checked by eye, never asserted. A change with nothing on screen (an engine rule,
a save format) attaches the test run's summary as a `.txt` instead, and says so in the note.

### Park it

- **Built and reviewed:** commit the code in each touched srcRoot on its branch
  (`queue(<project>): <slug>`), and the docs at the root (below). Then `clip` the picture —
  the item goes to `review` — and `note` it: the branch, what changed in one line, what the
  user should look at, and `took <Nh Nm> · http://localhost:3000/d/claude-agents?from=<start ms>&to=<end ms>`.
  Put anything still open in the note.
- **Under a Standing approval** in the Focus, a built and reviewed item does not wait in
  `review`: after the steps above, merge it into the checked-out main branch of each srcRoot
  (`git -C <srcRoot> checkout <main> && git -C <srcRoot> merge --no-ff queue/<id>-<slug>`, then
  back to `queue/build`), commit the moved pointers at the root (`git add <srcRoot>`), and
  `python3 $Q move <id> done` with `APPROVED under the user's standing approval` first in the
  note. Its picture stays attached so the user can look later. A merge that conflicts is
  aborted and the item stays in `review`, with the conflict in the note.
- **A question that has a cheap default does not park.** When an agent names what it would do
  anyway ("going ahead with …"), and that default is cheap to change later and touches
  nothing approved, record it with `python3 $Q ask <id> "<question> Going ahead with:
  <default>."` (no `--blocker`), move the item back to `working` if `ask` moved it, and carry
  on with the default. The user judges the result when they look; a run that parks on every
  soft question sits idle.
- **A question only the user's intent can settle,** or a loop budget spent: commit what exists
  on the branch, `python3 $Q ask <id> ...` — it goes to `blocked` — and the run moves to the
  next job. Leave the branch and any PRD in place; partial work is the normal state of a
  blocked item.

## Committing — the checkpoints

Docs at the repo root, after every stage that changed them:

```
git add -A <docsRoot>
git commit -m "queue(<project>): <what changed>"
```

Scoped to `docsRoot` on purpose: it picks up tidy edits, PRD creation and deletion, research
reports and the roadmap, and it cannot pick up a submodule pointer or `.claude/`. Code is
committed inside each srcRoot on its queue branch, never on the checked-out main branch — the
desk merges it on the user's approval. The queue itself is not in git: `queue.json` is local
state, and `q.py` is its record.

If nothing is staged, skip the commit. If a commit fails, retry once, then say so in the note.
Never `--no-verify`, never `--force`, never `git reset` or `git checkout --` anything, never
rewrite history.

## The end of a run

One short report: what moved, and what is waiting on the user. **Never end on a question.**
Nobody reads a worker's window: a question goes into the queue with `python3 $Q ask <id> ...`
so it reaches the user through the desk.

**Under the runner, the very last step is the finished mark** — after the report, whatever
happened, even when other commands or writes were refused, and with nothing queued too:

```
[ -n "$FORGE_WORKER_DONE" ] && touch "$FORGE_WORKER_DONE"
```

The runner starts each worker as an interactive session so it shows in Remote Control, and an
interactive session does not end by itself: this mark is the only thing that closes it. Never
write it earlier — the runner closes the session half a minute after it appears.

## What this command never does

- **Never asks.** Restated because it is the whole point.
- **Never writes a design doc, a PRD, source, or a test.** Only the owning agent does.
- **Never moves an item to `done`, and never merges a queue branch.** That is the user's word,
  through the desk.
- **Never turns research into a decision.** Findings end as questions; the user answers, and
  the answer reaches the docs through the tidy pipeline.
- **Never touches `.claude/`**, `project.json`, or another project.
- **Never deletes a branch** and never rewrites history.
- **Never runs `/set-project` or `/set-system`.** If the wrong project is active, stop and say
  so before the first dispatch.
