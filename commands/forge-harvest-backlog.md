---
description: Harvest the archived PRD backlog into the active project's design docs, unattended — one topic per loop, a commit per topic, questions written to a file instead of asked
argument-hint: "[--only NN] [--from NN] [--retry-failed] [--dry-run] — omit to run every topic not yet done"
allowed-tools: Agent, Bash, Read, Write, Edit, Grep, Glob, Skill
---

# Harvest the backlog, unattended

Drive `forge-harvest-planner` → `forge-doc-writer` → `git rm` across a fixed list of topics
until the archived PRD backlog is empty, **without ever stopping to ask a question.**

The arguments, if any, are: `$ARGUMENTS`

This command exists because the harvest is a long unattended run. The user starts it and walks
away, so every point where the normal flow would pause — an ambiguity, a contradiction, an
agent that fails — has to become a line in a file instead of a question in the terminal.

**The absolute rules, in priority order:**

1. **Never call `AskUserQuestion`. Never end a turn to ask anything.** A genuine question goes
   into `REVIEW-ME.md` and the loop moves on. If you find yourself composing a question to the
   user, you have already broken this command.
2. **Never hold state in conversation memory.** Re-read `progress.json` from disk at the top of
   every iteration and write it back at the bottom. This is what survives a compaction, a
   crash, or a restart — and the reason `/forge-harvest-backlog` can simply be run again.
3. **Never re-dispatch a failed agent more than once.** One retry, then record the failure and
   move to the next topic. A stuck topic must not consume the weekend.
4. **Stop only when every topic is either done or failed.** Then run the final sweep, the final
   tidy, and print the summary.

This command is **project-agnostic**. Nothing in it names a project, a doc, or a sprint — the
topic list is project data, read from disk.

## The write boundary still holds

Under `forge` the main loop never writes a project artifact, and this command does not break
that. What it writes are **maintenance and coordination artifacts**, which are neither design
docs nor PRDs:

- `<docsRoot>/maintenance/harvest/*` — the planner reports, `REVIEW-ME.md`, `progress.json`.
  `maintenance/` is a subfolder of `docsRoot`, so by the manifest's own definition it holds no
  design docs and no tidying ever touches it.
- **git operations** — `git rm`, `git add`, `git commit` are coordination, explicitly the main
  loop's under `SYSTEM.md`.

Every change to a design doc still goes through `forge-doc-writer`, and every decision about
*what* changes still comes from `forge-harvest-planner`. You are the driver, not an author. If
a planner report is thin or wrong, that is a finding for `REVIEW-ME.md` — never a licence to
write the doc yourself.

## Resolve the scope first

1. Read `.claude/project/active.json` for the slug, then the manifest whose `.name` matches it
   (conventionally `Docs/<slug>/project.json`). Use `docsRoot`, `srcRoots`, `roadmap`.
   If either file is missing or will not parse, **stop and say to run `/set-project`.** This is
   the one legitimate early stop, and it happens before any work.
2. Resolve, from the manifest, and use only these:
   - `ARCHIVE  = <docsRoot>/Archived_for_deletion`
   - `HARVEST  = <docsRoot>/maintenance/harvest`
   - `TOPICS   = <HARVEST>/topics.json`
   - `PROGRESS = <HARVEST>/progress.json`
   - `REVIEW   = <HARVEST>/REVIEW-ME.md`
3. If `TOPICS` does not exist, stop and say so — the topic list is authored, never generated.
   If `PROGRESS` does not exist, create it with empty `done[]`, `failed[]`.
4. Confirm the working tree is clean enough to checkpoint: `git status --porcelain -- <docsRoot>`.
   Uncommitted changes under `docsRoot` are fine — they get folded into the first topic commit —
   but say so in the summary so nothing looks like it came from a harvest.

## Arguments

Parse `$ARGUMENTS`; with none, run every topic that is in neither `done[]` nor `failed[]`.

| Argument | Effect |
|---|---|
| `--only NN` | Run just topic `NN` (a topic `id`), even if it is already in `done[]` or `failed[]`. Still commits, still updates progress. This is the dry run before the long run. |
| `--from NN` | Start at topic `NN` and continue to the end, skipping topics already in `done[]`. |
| `--retry-failed` | Also run topics in `failed[]`, clearing each from `failed[]` on success. |
| `--dry-run` | Do everything except `forge-doc-writer`, `git rm`, and `git commit`. Write the planner reports and print what *would* have been applied and deleted. Nothing is staged. Use it to inspect the 20% filter. |

Unrecognised arguments: say so and run the default. Never stop over an argument.

## The loop

For each topic to run, **in `topics.json` order**:

### 1. Re-read progress, then dispatch the planner

Re-read `PROGRESS` from disk. If the topic is now in `done[]` (and `--only` was not given),
skip it — another run may have covered it.

Build the prompt from the topic's fields and dispatch:

```
Agent(subagent_type: "forge-harvest-planner", prompt: "<the prompt below>")
```

The prompt must state, in this order:

- **Target** — `<docsRoot>/<target>`, plus `section` when the topic names one: "Harvest into
  `<target>`, `<section>` only — leave the rest of the file alone."
- **Create** — when `create` is true: "This doc does not exist yet. Plan its full contents as a
  CREATE finding, in house style: `# Title`, a `> **Status:**` blockquote, content sections,
  and `## Open Questions` last."
- **Feeders** — the topic's `feeders`, each joined to `ARCHIVE` so the agent gets real paths.
  Add: "These are where to look first, not a limit — grep the rest of the archive for the tags
  below if a claim points outside them."
- **Tags** — the topic's `tags`: "Grep these decision tags across the archive. Several are
  prefixes — match them as prefixes, not exact strings."
- **The topic's `note`, verbatim.**
- **The standing instruction, verbatim:**

  > This is a 20% harvest. The code under `srcRoots` is the authority on what the system does;
  > chronology settles what the code cannot show; the PRD text is the weakest source. Older
  > PRDs are suspect — a `Done` stamp is a hint, not proof, and `Draft` PRDs were sometimes
  > built anyway. Not built means not harvested, and it goes under **Dropped**. Ignore
  > `old Prototype/` entirely.
  >
  > **The code is the source of truth, and reconciling the docs to it does NOT require a PRD.**
  > The user has ruled this directly, and it overrides the trace-to-a-PRD rule in both
  > directions:
  >
  > - **A design doc asserts something the code does not do → write a REVISE that removes it**,
  >   even when no PRD, sprint or decision entry covers the change. A column that was dropped, a
  >   table that was renamed, a gate that was deleted — the doc is simply wrong, and leaving it
  >   standing because the paperwork is missing is how it stayed wrong. Quote every passage to
  >   delete, exactly.
  > - **The code does something the docs are silent about → write a REVISE that adds it**, if
  >   and only if it is knowledge a maintainer needs (a contract, an ownership or migration
  >   rule, an invariant, a non-obvious *why*). The 20% rule is unchanged: do not restate code
  >   a reader gets faster by opening the file.
  >
  > **A code-refuted claim usually appears in more than one design doc.** Grep every `.md`
  > directly under `docsRoot` for it and quote each occurrence in the same REVISE — your REVISE
  > format already allows superseded passages in another file, and `forge-doc-writer` may edit
  > any design doc. Removing it in the target doc while leaving it asserted in two others is
  > worse than leaving it alone, because the docs then disagree with each other as well as with
  > the code.
  >
  > **Contradicts the code** is now reserved for what it is actually for: a place the *code*
  > looks wrong — a suspected bug, a stale comment, an unsafe behavior. Plain doc rot is not a
  > contradiction to report, it is a REVISE to write.
  >
  > ---
  >
  > **THE SOT CARRIES NO HISTORY. This is the rule most often broken, and breaking it is how the
  > docs became unreadable.** A design doc states, in the present tense, exactly what the system
  > does and how it is expected to keep operating. Nothing about how it got that way.
  >
  > Never write, and **actively delete on sight** in any section you touch:
  >
  > - **Dates and stamps** — `RECORDED 2026-08-19`, `added 2026-06-24`, `as of <date>`,
  >   `(post-2026-06-10)`, `RETIRED <date>`, `USER-APPROVED <date>`.
  > - **Sprint numbers, PRD names, decision tags** — `sprint_28`, `PRD-usage-schema.md`,
  >   `[TESTCASEBOOKS/naming-v2]`, `XC3`, `RSU-1`, `AC-K5`, `UM10 D5.1`.
  > - **Supersession ledgers** — `⛔ Retained with its date`, `Retained, not deleted`,
  >   `this supersedes X`, `previously Y`, `the earlier Z was dropped`, `Superseded order
  >   (history)`, `NEWLY DANGEROUS`, `reverses the prior decision`, struck-through old wording.
  >   **Delete the old claim outright and state the new one as simple fact.**
  >   ⛔ Never soften this into a note. There is no correct amount of ledger.
  >   A stacked run of dated banners on one topic **collapses into one present-tense passage**
  >   that says what is true now; everything the banners disagreed about is simply gone.
  > - **Rollout and status chatter** — `now implemented`, `not yet built`, `pending`,
  >   `wave 1 has passed its code gate`, `still Draft`, `to land with the migration`.
  >   Either the code does it (state it plainly) or it does not (say nothing at all).
  >
  > **Git is the audit trail** — `git log -p <doc>` already records when X became Y, and it does
  > it without drifting. A hand-maintained ledger duplicates git, contradicts it within weeks,
  > and turns every settled question into something a reader has to re-litigate.
  >
  > **The one thing that survives:** a rejected alternative whose *reason* prevents a regression,
  > stated inline, present tense, in the section it governs — *"this column is plain `text` with
  > no CHECK, because the offered model set churns faster than a deploy does."* That is a reason,
  > not a ledger entry. It names no date, no sprint, and no prior decision. If you cannot phrase
  > it without reaching for the past tense, it does not belong.
  >
  > **This applies to what you REMOVE as much as what you add.** When a topic lands in a section
  > that is already carrying dated banners, retained supersessions or status chatter, plan the
  > REMOVE findings that strip them. Harvesting into a section without de-historicising it leaves
  > the doc worse: newer prose stacked on the ledger that made it unreadable.

- **The no-questions notice, verbatim:**

  > This run is unattended — nobody will answer you. Settle everything the code or the docs can
  > settle, and put anything genuinely needing the user's intent under **Needs your call**. It
  > will be collected in a review file, not answered mid-run. Do not block on it.

- **The report contract reminder:** numbered CREATE/REVISE findings, then **Dropped /
  superseded**, **Ready to delete**, **Contradicts the code**, **Needs your call** — and that
  **Ready to delete** must account for *every* doc a PRD owes, marking anything else **Still
  owed** with the doc it owes.

**If the planner fails** (error, or a report with none of the expected sections): re-dispatch
it **once**, with the same prompt plus "The previous run did not return a usable report."
If the second attempt also fails, append to `failed[]`:

```json
{ "id": "NN", "slug": "...", "stage": "planner", "reason": "<one line>", "at": "<UTC>" }
```

write `PROGRESS`, and go to the next topic. Do not retry a third time. Do not try to do the
planner's job yourself.

### 2. Write the report verbatim

Write the planner's report, **unedited**, to `<HARVEST>/NN-<slug>.md`, prefixed with a two-line
header naming the topic, the target, and the UTC timestamp. Verbatim matters: this file is the
user's only view of the judgment that was applied before the PRDs were deleted.

If the file exists (a re-run), overwrite it — `progress.json` and git hold the history.

### 3. Apply, if there is anything to apply

If the report has at least one **CREATE** or **REVISE** finding, hand the report **verbatim**
to the writer:

```
Agent(subagent_type: "forge-doc-writer", prompt: "<the full planner report, unedited>")
```

Pass the whole report through. `forge-doc-writer` applies CREATE and REVISE literally and is
instructed to ignore the other sections — do not pre-filter it, do not summarise it, do not
reorder it. It also regenerates the manifest's `roadmap` as its final step.

If the writer fails, retry **once**. On a second failure, record `"stage": "writer"` in
`failed[]` — **and do not delete anything for this topic**, because the decisions did not land.
Skip straight to step 5 (the review file), then the next topic.

"No findings" is a valid outcome. Record it, skip the writer, and still honour step 4 — a
planner that found nothing worth keeping may still have cleared PRDs for deletion.

### 4. Delete exactly what the report named

Take **only** the paths under **Ready to delete**. For each, check all of the following, and
skip any path that fails one (recording the skip in the review file):

- it resolves inside `ARCHIVE` (join it to `ARCHIVE` if the report gave it relative to the
  archive; reject anything containing `..` or resolving outside)
- it exists on disk
- it is tracked by git — `git ls-files --error-unmatch <path>`

Then `git rm -r --quiet` the survivors. Paths under **Still owed** are left alone — that is the
normal state of a partial harvest, not a failure.

**Never delete `ARCHIVE` itself, `old Prototype/`, or anything outside `ARCHIVE`**, whatever a
report says. A report naming one of those is a finding for the review file.

### 5. Collect the questions instead of asking them

Append to `REVIEW`, creating it with a `# Harvest review` heading if absent:

```
## NN — <slug> → <target>

### Contradicts the code
<the section verbatim, or "none"> — under the ruling above this is suspected *code* defects, not
doc rot; doc rot was fixed by a REVISE and needs no entry here.

### Needs your call
<the section verbatim, or "none">

### Skipped deletions
<any path from Ready to delete that failed a safety check, with why — or omit>
```

Never answer, resolve, or soften either section. They are the user's, and nothing in the SOT
was written from them.

### 6. Commit — the checkpoint

```
git add -A <docsRoot>
git commit -m "harvest(<project>): <slug>"
```

Scoped to `docsRoot` on purpose: it picks up the doc edits, the deletions, the report file and
`progress.json`, and it cannot pick up `src/` submodule pointers or `.claude/`.

If there is nothing staged, skip the commit and record `"commit": null` — a topic that changed
nothing is a real outcome.

If the commit fails (a hook, a lock), retry once; if it still fails, record the topic in
`failed[]` with `"stage": "commit"` and continue. Never `--no-verify`, never `--force`,
never `git reset` or `git checkout` anything.

### 7. Mark it done, then go straight to the next topic

Append to `done[]`:

```json
{ "id": "NN", "slug": "...", "target": "...", "commit": "<sha or null>",
  "findingsApplied": <count>, "filesDeleted": <count>, "questions": <count>,
  "contradictions": <count>, "at": "<UTC>" }
```

Write `PROGRESS`, print one line — `NN <slug>: N findings, N files deleted, N questions` — and
**start the next topic in the same turn.**

⚠️ **The sha is written *after* the commit, so it necessarily lands in the *next* topic's
commit.** Do not amend to fold it in — amending changes the sha you just recorded, and the
reference dangles. One topic's `progress.json` entry trailing its own commit by one is the
correct, stable outcome. Do not summarise, do not check in, do not ask. The
next dispatch is the next thing that happens.

## Final sweep

After the last numbered topic, and only if none of `--only` / `--dry-run` was given:

1. **List what is left.** Every `sprint_*` folder still under `ARCHIVE`, excluding
   `old Prototype/`, `maintenance/`, the top-level bookkeeping `.md` files, and `service.md`.
2. **One planner run per remaining folder**, with the target: "Whichever design doc under
   `<docsRoot>` fits — name it in the finding. If nothing in this folder survives the 20% rule,
   say so in one line and list the folder under **Ready to delete**." Same standing instruction,
   same no-questions notice. Same one-retry rule. Apply, delete and collect exactly as in steps
   3–5. Report files are named `21-sweep-<folder-slug>.md`.
3. **Remove the non-PRD leftovers** — these were never harvest inputs and hold no decisions:
   every `*/service.md` under `ARCHIVE` (derived per-service summaries), the top-level
   `DECISIONS-pending-approval.md`, `IMPLEMENTATION-PROGRESS.md`, `README.md`, `project.md`,
   `roadmap.md`, the `maintenance/` folder, and `old Prototype/` — whose verdict already lives
   in the project's parking-lot audit doc. `git rm -r` each, with the same safety checks.
4. **Anything still left is listed, not deleted.** Record it in `progress.json` under
   `sweep.remaining` and in the summary. Deleting something nobody harvested is the one
   irreversible mistake available here, and an unexplained leftover is cheap by comparison.
5. Commit: `git commit -m "harvest(<project>): sweep"`. Record `sweep.done`.

## Final tidy

Once the archive is empty (or its remainder is listed), run the tidy pass **once**, scoped to
the docs this run changed:

```
Skill(forge-tidy-docs)
```

`forge-doc-planner` finds the changed docs itself from git — it needs no file list. Relay
nothing to the user mid-run: append its **Needs your call** items to `REVIEW` under a
`## Final tidy` heading like any other topic. Commit as `harvest(<project>): tidy`, record
`tidy.done`.

This is deliberately last rather than first. Forge's migration steps put a tidy before the
harvest; on a backlog this size that would read every design doc before a single decision was
recovered, and risk exhausting the run before anything landed. Tidying after means the pass
also sees everything the harvest added, which is the more useful moment.

## Then print the summary — the only report

End with the review file path, then one table:

```
Harvest complete — <N> of <M> topics done, <F> failed.
Review: <REVIEW>

| # | Topic | Target | Findings | Deleted | Questions | Contradictions | Commit |
|---|-------|--------|----------|---------|-----------|----------------|--------|
```

Then, in at most five lines: what failed and why, whatever is still under `ARCHIVE`, and the
single sentence that matters — **every "Contradicts the code" entry is a possible bug and every
"Needs your call" is an unmade decision, and nothing in the design docs was written from
either.**

## What this command never does

- **Never asks.** Restated because it is the whole point.
- **Never writes a design doc or a PRD.** Only `forge-doc-writer` does.
- **Never answers an open question**, resolves a contradiction, or edits a planner report.
- **Never touches `src/`**, a submodule, `project.json`, `.claude/`, or another project.
- **Never deletes outside `ARCHIVE`**, and never `ARCHIVE` itself.
- **Never rewrites history** — no amend, no rebase, no force, no reset.
- **Never runs `/set-project` or `/set-system`.** If the wrong project is active, stop and say
  so before the first dispatch.
