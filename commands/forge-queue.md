---
description: Work the active project's queue — triage Inbox, build Ready items through the forge pipeline, refine Later items, and propose against the Goal — one tick, unattended, questions written to Blocked instead of asked
argument-hint: "[--init] [--one] [--propose] [--on-main] [--dry-run] — omit to drain Ready, then triage, then refine"
allowed-tools: Agent, Bash, Read, Write, Edit, Grep, Glob, Skill
---

# Work the queue, unattended

One **tick** of the forge work queue: read the eight files under `<docsRoot>/queue/`, do the
highest-priority thing they call for, record the outcome in those files, commit, and stop —
**without ever stopping to ask a question.** Run it once by hand, or on a timer with
`/loop 30m /forge-queue`.

The arguments, if any, are: `$ARGUMENTS`

The queue exists so the user can hand over goals and tasks and walk away. Every point where a
normal session would pause — an ambiguity, a failed agent, a decision only the user can make —
becomes a line in a file instead of a question in the terminal.

**The absolute rules, in priority order:**

1. **Never call `AskUserQuestion`. Never end a turn to ask anything.** A genuine question goes
   into `Blocked.md` under its item, and the tick moves on. If you find yourself composing a
   question to the user, you have already broken this command.
2. **Never hold state in conversation memory.** Re-read the queue files from disk before every
   write and write them back immediately after. This is what survives a compaction, a crash,
   or the user editing a file mid-tick — and the reason `/forge-queue` can simply be run again.
3. **One item at a time, fully closed before the next.** Never two live writers.
4. **Never re-dispatch a failed agent more than once.** One retry, then the item goes to
   Blocked with the failure as its question.
5. **Every move is add-to-destination first, then remove-from-source.** A crash between the
   two duplicates the item; the next tick sees the same title in two files and removes the
   copy in the *earlier* section. Loss is impossible; duplication is self-healing.

This command is **project-agnostic**. Nothing in it names a project, a doc, or a feature.

## The write boundary still holds

Under `forge` the main loop never writes a project artifact, and this command does not break
that. The queue files are **coordination state** — the same class as git operations — and
the main loop is their bookkeeper: it moves lines between files, writes notes under Later items
and questions under Blocked ones, and copies `forge-queue-planner`'s report into Proposed. It
never invents a task, never edits a line the user wrote (except to move it), and never touches
the header block above the `---` rule in any file.

Everything else is delegated exactly as `SYSTEM.md` says: design docs through
`forge-doc-writer`, PRDs through `forge-prd-author`, source through `forge-code-writer`, tests
through `forge-test-author`. You are the driver, not an author.

## The files, and who holds the pen

| File | Owner | You may |
|---|---|---|
| `Goal.md` | user | read |
| `Later.md` | user (lines) · queue (the `>` note under each) | rewrite a note in place; remove it when the item leaves |
| `Inbox.md` | user | remove a line as you triage it |
| `Ready.md` | user (order) · queue (tags) | add a triaged line at the bottom, a re-ready Blocked line at the top; remove the line you pick up |
| `Processing.md` | queue | add on pickup; remove on close-out |
| `Blocked.md` | queue (item, `Q:`) · user (`A:`) | add an item with questions; remove it when it returns to Ready |
| `Proposed.md` | queue | replace its rows from the planner's report |
| `Done.md` | queue | add a row on close-out; prune rows older than 30 days |

**Line formats.** Items are `- ` lines after the `---` rule; anything indented belongs to the
item above it. Titles identify items — match them case-insensitively with tags stripped.

```
Inbox / Ready:   - <title> [prd|look|research] [S|M|L]     (tags optional in Inbox)
Processing:      - <title> [prd|look] · started <UTC ISO> · branch <name> · session <link or name>
Blocked:         - <title> [prd|look] · branch <name or none>
                   - Q: <question written for the user — see below>
                     A:
Done:            - <YYYY-MM-DD> · <title> · <Nh Nm> · <sha or none> · <grafana url>
Proposed:        - <title> [prd|look] [S|M|L] — <why the goal needs it>
Later:           - <title>
                   > <the queue's note, three to six lines>
```

## Resolve the scope first

1. Read `.claude/project/active.json` for the slug, then the manifest whose `.name` matches
   it (conventionally `Docs/<slug>/project.json`). Use `docsRoot`, `srcRoots`, `prds`,
   `roadmap`, and `testing` if present. If either file is missing or will not parse, **stop
   and say to run `/set-project`.** This is the one legitimate early stop.
2. `QUEUE = <docsRoot>/queue`. If it does not exist and `--init` was not given, stop and say
   to run `/forge-queue --init`.
3. Note the session identity for Processing lines: the `https://claude.ai/code/session_…`
   link if one is in your context, otherwise the session name if you know it, otherwise the
   pickup timestamp.

## Arguments

Parse `$ARGUMENTS`; with none, run the full priority order below.

| Argument | Effect |
|---|---|
| `--init` | Create `QUEUE` by copying every file from `.claude/systems/forge/queue-templates/` that does not already exist there. Never overwrite. Commit, print the folder, stop. |
| `--one` | Build at most one Ready item, then stop. Without it a tick drains Ready. |
| `--propose` | Run the goal engine now, regardless of the empty-queue trigger. Required for a goal's *first* proposal run. |
| `--on-main` | Commit code to the srcRoot's checked-out branch instead of a `queue/<slug>` branch, and move the root's submodule pointer to follow it. |
| `--dry-run` | Do everything except dispatch a writing agent, write a queue file, or commit. Print what each step *would* do. |

Unrecognised arguments: say so and run the default. Never stop over an argument.

## Every tick: housekeeping first

1. **Heal duplicates.** A title present in two files keeps the copy in the *later* section
   (order: Proposed < Later < Inbox < Ready < Processing < Blocked < Done) and loses the other.
2. **Flag stale claims.** A Processing item whose branch has had no commit in 24 hours, or
   whose branch is missing, is listed in the summary as possibly abandoned. **Never re-pick
   it.** The user decides whether to delete the branch and requeue.
3. **Prune Done.** Remove rows dated more than 30 days ago. Git keeps them.
4. **Return answered Blocked items to Ready.** An item whose every `A:` has text moves to the
   *top* of Ready. If any answer settles a design question — a rule, a contract, a behavior —
   run `Skill(forge-tidy-docs)` first so the answer lands in the design docs, and put the
   answer text in that skill's prompt so `forge-doc-planner` sees it. The queue never becomes
   the only place a decision lives.

## Then the priority order

Do the first that applies, then continue down the list until the tick has nothing left:

1. **Ready has items** → build the top one (below). Repeat unless `--one`.
2. **Inbox has items** → triage each (below).
3. **Later has items without a current note** → refine up to three (below).
4. **Goal is set, and Ready and Inbox are both empty** → run the goal engine (below), but
   only if `Proposed.md` already has rows, or the goal text changed since Proposed was last
   written (`git log -1 --format=%ct -- <file>` on each), or `--propose` was given. A goal's
   first run is on request only, so the user can judge the engine before it is armed.
5. Nothing applies → print the summary and stop.

## Building one Ready item

### 1. Claim it

Add the item to Processing with `started <UTC>`, `branch queue/<slug>`, and the session
identity; then remove it from Ready. Commit (`queue(<project>): claim <slug>`).

In each srcRoot the work will touch: `git -C <srcRoot> checkout -b queue/<slug>` from the
currently checked-out branch. With `--on-main`, stay on the checked-out branch instead.

### 2. Decide the path, out loud

An untagged line gets the triage call now (see Triage). Then **say the cost sentence** in the
conversation, exactly as `SYSTEM.md` requires: *"PRD: this changes X, a wrong guess is Y"* or
*"Look: a wrong guess here is visible on screen and cheap."* Record the tag on the Processing
line.

### 3. Run the path

`SYSTEM.md` is the authority on each stage; this is the sequence, with the checkpoints:

**`[prd]`:** `forge-prd-author` → `forge-prd-reviewer` (a blocking finding goes back to the
author once; a second blocking finding sends the item to Blocked) → `forge-test-author` →
`forge-test-auditor` → `forge-code-writer` → **tests pass** (the manifest's `testing.command`)
→ `forge-code-cleaner` → **tests still pass** → `forge-code-reviewer` → `forge-code-prd-alignment`
→ `forge-harvest-planner` for this PRD → `forge-doc-writer` → `git rm` the PRD once the
planner's **Ready to delete** line reads clean.

**`[research]`:** no code and no branch. Answer the question the item asks, with sources:
read the design docs and code first, then `WebSearch`/`WebFetch` for anything outside the
repo — or dispatch the built-in `general-purpose` agent when the reading is broad enough to
crowd the main loop. The output is a recommendation, and a recommendation is a decision only
the user can make, so a research item **always closes into Blocked**: the findings as an
indented block under the item (what was found, the options, the recommendation and why,
what each option would mean for the app), then one `Q:` per decision. If the findings
contradict a design doc, say which passage and leave the doc alone — the answer lands there
through `forge-tidy-docs` when the user answers, like any Blocked answer.

**`[look]`:** built-in `Plan` agent → `forge-test-author` and `forge-test-auditor` only if
there is behavior worth pinning → `forge-code-writer` → **tests pass** → `forge-code-cleaner`
→ **tests still pass** → `forge-code-reviewer` → `Skill(playtest)`: run the app and look at
the result yourself. Appearance is checked, never asserted.

Both paths: one dispatch per stage, in sequence, each finished before the next. A reviewer
finding that is a defect goes back to `forge-code-writer` once. Any agent that returns
**Needs your call** with a question you cannot settle by reading sends the item to Blocked.

### 4. Close out, or block

**Done:** commit the code in each touched srcRoot on its branch (`queue(<project>): <slug>`).
Compute the duration from the Processing line's `started`. Build the Grafana link:
`http://localhost:3000/d/claude-agents?from=<start ms>&to=<end ms>`. Add the Done row, then
remove the Processing line. Commit the queue and docs at the root (below).

**Blocked:** add the item to Blocked with its branch and each question, then remove the
Processing line. Leave the branch and any PRD in place — partial work is the normal state of
a Blocked item. Commit. Then go to the next Ready item.

**Writing a question for the user** — every `Q:` must be answerable without opening a file:
no requirement numbers, no `file:line`, no heading names. Say what happens on screen or what
gets saved, give the concrete options and what each means in the app, and say how hard it is
to change later. One question per `Q:`.

## Triage (Inbox → Ready or Blocked)

For each Inbox line, in order: read the design docs and code it touches. Decide the path by
the cost of a wrong guess — `[prd]` for rules, engine semantics, persistence, money, or a
contract other features depend on; `[look]` for layout, animation, menus, settings, theming,
copy; `[research]` when the line asks a question rather than for a change. A tag the user
already wrote wins. Size it `[S|M|L]`.

If it can be built without a decision only the user can make → add it to the **bottom** of
Ready with its tags, then remove it from Inbox. Otherwise → add it to Blocked with its
questions and `branch none`, then remove it from Inbox. Commit once after the whole Inbox.

Triage is research, not a build: no agent is dispatched for it. Dispatch
`forge-queue-planner` for an Inbox item only when sizing it honestly needs the whole doc set
read — a large `[prd]` candidate — and pass the line as a Later-style target.

## Refining Later items

A Later item is current when it has a `>` note and the docs have not changed since the note was
written (compare `git log -1 --format=%ct` on `Later.md` against the design docs). For up to
three items that are not current, dispatch once:

```
Agent(subagent_type: "forge-queue-planner", prompt: "Target: Later item. Refine these items, one Note each, verbatim as written: <the lines>. Queue: <QUEUE>. Design docs: <docsRoot>. Source: <srcRoots>.")
```

Rewrite each item's note in place from the report's **Note** sections — never append a second
note, never edit the item line. Commit.

## The goal engine (Proposed)

```
Agent(subagent_type: "forge-queue-planner", prompt: "Target: the goal in <QUEUE>/Goal.md. <'The goal text changed since the last run — rewrite Proposed wholesale.' | 'Refine the existing Proposed rows.'> Queue: <QUEUE>. Design docs: <docsRoot>. Source: <srcRoots>. PRDs: <prds>.")
```

Replace everything below the `---` rule in `Proposed.md` with the report's **Proposed**
section, verbatim. Print **Dropped**, **Already covered**, and **Needs your call** in the
summary; a **Needs your call** entry that blocks the goal itself also becomes a Blocked item
titled `decide: <the question>` with `branch none`. Commit.

## Committing — the checkpoints

Queue and docs, at the repo root, after every state change:

```
git add -A <docsRoot>
git commit -m "queue(<project>): <what changed>"
```

Scoped to `docsRoot` on purpose: it picks up the queue files, tidy edits, PRD creation and
deletion, and the roadmap, and it cannot pick up a submodule pointer or `.claude/`. Code is
committed inside each srcRoot on its branch. With `--on-main`, also `git add <srcRoot>` at the
root so the pointer follows, matching the repo's existing practice.

If nothing is staged, skip the commit. If a commit fails, retry once, then record it in the
summary. Never `--no-verify`, never `--force`, never `git reset` or `git checkout --` anything.

## Then print the summary — the only report

```
Queue tick — <project>
Built: <n> · Blocked: <n> · Triaged: <n> · Refined: <n> · Proposed: <rewritten|refined|skipped>

| Item | From → To | Outcome |
|---|---|---|
```

Then, in at most five lines: stale claims, commit failures, and every question now waiting in
Blocked, each in one line the user can answer from the terminal.

## What this command never does

- **Never asks.** Restated because it is the whole point.
- **Never writes a design doc, a PRD, source, or a test.** Only the owning agent does.
- **Never turns research into a decision.** Findings end as a question in Blocked; the user
  answers, and the answer reaches the docs through the tidy pipeline.
- **Never edits a file's header block**, a user's item line, or Goal.md at all.
- **Never re-picks a stale Processing item**, and never deletes a branch.
- **Never runs the goal engine on a fresh goal without `--propose`.**
- **Never touches `.claude/`**, `project.json`, or another project.
- **Never rewrites history** — no amend, no rebase, no force, no reset.
- **Never runs `/set-project` or `/set-system`.** If the wrong project is active, stop and
  say so before the first dispatch.
