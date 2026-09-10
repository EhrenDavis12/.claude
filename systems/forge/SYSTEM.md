# System: forge

> **Active.** This file is in context because `CLAUDE.md` imports it. If you are reading these
> rules, forge is the system in force. See `.claude/systems/README.md` to swap.

The forge pipeline: design docs → PRD → code → tests. Twelve agents, one territory each, and a
main loop that coordinates rather than builds.

Paths below are **manifest keys**, resolved from the active project (see `CLAUDE.md`). No agent
holds a hardcoded path.

## Pure delegation — you coordinate, agents produce

**You never produce or modify a project artifact.** Every change to source, tests, design docs,
or PRDs goes through the agent that owns that territory. You coordinate and hold the end goal —
the one thing no subagent can do, and the thing that degrades as your context fills with
implementation detail.

The line is **produce/modify vs. read/decide**. You decide what happens next, dispatch agents,
read their reports, research answers to their questions, and talk to the user. Read whatever you
need. Just don't write.

Three carve-outs, because they aren't project artifacts:

- **`.claude/**` and `CLAUDE.md`** — the agent system itself, via `/agent-creator`. Delegating
  it would need an agent to build agents.
- **Git operations** — commits and branches are coordination, not authorship.
- **Anything the user explicitly asks you to do inline** — their call overrides this.

Neither ambiguity nor tight iteration is a reason to keep work inline: the first is handled by
batch-and-resume (`CLAUDE.md`), the second by `SendMessage` resuming an agent with its context
rather than restarting it.

**The trivial change is the trap.** Delegating a one-line fix costs one dispatch; doing it
inline costs the boundary. "I'll just do this one" is how you drift back into being a
forge-code-writer, and you won't notice until your context is already full.

## The write boundary

Judgment and write access are held by different agents on purpose. One writer per territory:

| Territory | Only writer |
|---|---|
| Design docs — `.md` directly under `docsRoot` | `forge-doc-writer` |
| `prds` | `forge-prd-author` |
| `roadmap` (the doc map) | `forge-doc-writer` |
| Source code under `srcRoots` | `forge-code-writer`, then `forge-code-cleaner` |
| Tests under `srcRoots` | `forge-test-author` |
| `project.json` | `/set-project` (configuration, not a doc — and repo-level, not forge's) |

Five agents are read-only and report instead. When adding an agent, default to read-only — write
access has to be argued for.

Two separations are load-bearing and must not be collapsed for convenience: `forge-code-writer`
never writes tests (an author's own tests assert what was built, not what was specified), and
`forge-test-author` never edits source (fixing the code to pass your own test destroys the
signal).

## The feature pipeline

```
forge-prd-author → forge-prd-reviewer → forge-test-author → forge-test-auditor
    → forge-code-writer → forge-code-cleaner → forge-code-reviewer → forge-code-prd-alignment
    → forge-harvest-planner → forge-doc-writer → delete the PRD
```

The last two are the close-out, not a build step: they move the PRD's decisions into the design
docs so the PRD can be deleted. Detail in "Closing out a PRD" below.

**Tests come before the code.** `forge-test-author` is told to work from the PRD and never
from the implementation; running it first makes that structurally impossible to break rather
than merely instructed. `forge-code-writer`'s definition of done becomes "the pre-written tests
pass," and the PRD's binding content ends up executable — which is what makes deleting it safe
later.

`forge-test-auditor` runs *before* the code for the same reason it matters most there: the code
will be built to satisfy whatever these tests demand, so a weak test does not merely miss a bug,
it becomes the target.

**One dispatch per stage, and let it finish.** Splitting a stage across parallel agents looks
like throughput and is not: every agent pays the same fixed cost — the PRD, the design docs,
the existing suite — and pays it independently, because none of them can see what the others
read. Three `forge-test-author`s fanned out over one PRD spent 462M tokens of context re-read,
58% of that day's total, on work one agent would have done once. Split a stage only where the
fixed cost genuinely differs, which in practice means by `srcRoot` — and that split has a
bright line: **one writer per srcRoot, the srcRoot named in its prompt, never a second live
`forge-test-author` or `forge-code-writer` whose scope overlaps it.** Two agents each handed
the whole feature is neither one-per-stage nor one-per-srcRoot: two days after the fan-out
above bought this rule, two test-authors dispatched that way each read a five-srcRoot feature
whole, reached ~930k context, and burned 532M tokens — more than the incident the rule came
from. Both agents now self-bound at ~250k context and hand back asking to be re-split; honor
that request rather than resuming them past it.

Starting the next stage before the current one returns costs the same way twice over. Code
written while `forge-test-author` is still running is code built against tests that do not
exist yet, so `forge-code-writer` gets re-dispatched once per test that lands late — twelve
times, in the run that produced the number above. The pipeline is a sequence because each
stage's output is the next stage's specification.

Running tests is a `Bash` checkpoint, not a pipeline stage — after `forge-code-writer` to reach
green, and after `forge-code-cleaner` to confirm it stayed green. **There is no test-runner
agent**, because running a command needs no judgment. The same checkpoint gates a re-review:
before re-dispatching `forge-code-reviewer` on a fix round, confirm the diff actually moved
(`git -C <srcRoot> diff`) — opus spent on a byte-identical diff only re-confirms the previous
report. Nor is there a play-test agent: run the app
yourself, however this project's stack runs it, and look. Appearance,
spacing, animation, and feel are checked that way, never asserted — and checked by you, not by
asking the user what they saw.

Don't skip `forge-prd-reviewer`. Everything downstream treats the PRD as its specification, so
an ambiguity there gets copied into every agent that reads it — and none of them can ask you
about it.

## Not every feature earns a PRD

**The default is to build.** A PRD is the argued exception, and the argument is always the
same one: *what does a wrong guess cost to fix?*

Write a PRD when a wrong guess is expensive or irreversible — schemas and persistence,
rule and engine semantics, money and entitlements, or a contract several features depend on.
Those are worth settling on paper because the fix later is a migration, a rewrite, or a
refund.

Skip it when the feedback loop is faster than the review loop — layout, animation, menus,
settings, theming, copy. Use the built-in `Plan` agent, build it, run it, look at it, adjust.
A review round costs more than the fix does.

The difference is lifetime, not length. A **PRD is binding**: `forge-test-author` writes tests
from it and `forge-code-prd-alignment` checks against it. A **plan is disposable**: nothing asserts
against it, it is consumed by the build, and — critically — **it is never reviewed.** The
ratchet lives in the review loop, so the lighter path is the one with no review loop at all.

Skipping the PRD skips the spec stages, not the code checks. With no PRD there is no
`forge-prd-author`, no `forge-prd-reviewer`, and nothing for `forge-code-prd-alignment` to
align against — those three are the whole difference between the paths. When behavior is worth
pinning, tests are still written before the code, and a pre-written test still becomes the
code's target — so `forge-test-auditor` still runs before `forge-code-writer`, PRD or not. And
`forge-code-cleaner` and `forge-code-reviewer` still run after: the cheapest agent on the
roster and the last check apply to code from either path. Left unwritten, this sequence gets
improvised, and what gets dropped is exactly these checks.

A project here wrote 210,000 words of PRD against zero lines of code before this rule existed.
When in doubt, build.

**Say the triage out loud.** Before dispatching `forge-prd-author`, state in the conversation
what a wrong guess would cost and why that earns a PRD — one sentence, e.g. "PRD: this changes
a schema, a wrong guess is a migration." If the sentence can't be written, the feature didn't
earn a PRD and the light path applies. Stating it is what keeps "default to build" from being
skipped silently — the cost of the full spec loop on a trivial change is three opus stages
that pin nothing.

## Closing out a PRD

A PRD is scaffolding, not a source of truth. It holds two things with opposite lifetimes: the
**decisions**, which outlive the feature, and the **build instructions**, which the code
replaces the moment it exists. Keeping the second forever is what makes PRDs a decaying second
description of the code that something then has to police.

### The three states

A PRD's state is read from the repo, not stored in the file. Nothing tracks it separately —
state kept in two places is state that goes stale.

| State | How you can tell | Means |
|---|---|---|
| In design | PRD exists, no tests for it | Being written or revised |
| In process | tests for it exist under `srcRoots` | Spec is executable; code underway |
| Done | **the file is gone** | Harvested and deleted |

**State is derived, not stored.** Only `forge-prd-author` can write a PRD, and
`forge-prd-reviewer` is read-only by design — so a `Status: Ready` stamp would need an extra
opus dispatch to flip one line, and would go stale the moment anything moved. The three states
above are readable straight from the repo and cannot disagree with reality. `forge-prd-author`
still writes the house-style `> **Status:**` line, but treat it as a note to a human, never as
the source of truth.

So the PRDs directory is a **work queue, not a work history**: it tells you what is left, never
what is finished. The code is the record of what was built and git is the record of when.
"Where did I leave off?" is `ls <prds>/`, plus whether tests exist for each. An empty directory
means done.

## Harvesting — moving decisions into the SOT

`forge-harvest-planner` owns this, and it is the same mechanism in both places it is used:
routinely at close-out, when one shipped PRD gives up its decisions, and once per project when a
backlog written before this system arrived is migrated wholesale. One PRD is simply the smallest
case, where nothing older exists to supersede. Both contexts are spelled out below.

`forge-doc-planner` cannot do this. It is instructed to report contradictions and never resolve
them, which is correct for living brain-dump docs and exactly wrong here, where resolving them
by date *is* the work.

**One coherent topic per run** — the whole doc when the doc is small, one section when it is
not. The principle is that supersession can only be settled with every claim on a topic visible
at once; that is satisfied by a topic, and a whole document is merely the common case.

Size forces this as much as correctness. A hub doc cited by most of the backlog cannot be
harvested in one pass — one project here had a technical design doc cited by 22 of 24 PRDs, far
past what a single run can hold. The fallback, chunking with a running summary, is worse than
the problem: summaries drift, and a drifted summary corrupts the supersession chain silently.
Splitting by section avoids it entirely, because each section has one or two owning PRDs.

```
Agent(subagent_type: "forge-harvest-planner", prompt: "Harvest <PRD paths or glob> into <target doc>. It does not exist yet — plan its full contents.")
```

Then hand the plan, verbatim, to `forge-doc-writer` — it applies **CREATE** and **REVISE** and
ignores the rest. Relay **Needs your call** and **Contradicts the code** to the user; the second
may be real bugs.

### Harvesting only copies upward — the PRD must still be drained

`forge-harvest-planner` is read-only toward PRDs by design. So the moment a harvest lands, the
decision exists in **both** the SOT and the PRD, and there are two sources of truth — the exact
condition this system exists to remove. **A harvest is not finished until the PRD's copy is
gone.** Left standing, the two copies drift the moment either is edited.

The drain is **total, never partial**: the PRD is deleted, not edited down. Nothing rewrites a
PRD to cite what was harvested out of it — a PRD that has given up its decisions has given up
its reason to exist, and the next one is generated fresh from the now-current SOT when its
feature is about to be built. Editing one into a thinner version of itself keeps the structure
that made it wrong: the numbering, the cross-PRD citations, the accumulated shape.

So there is exactly one ending, and only its timing varies:

| Situation | When the drain happens |
|---|---|
| Feature has shipped | At close-out, below — the tests now carry the spec |
| Feature not built, PRD predates this system | During migration — harvest everything, then delete, then regenerate just-in-time |

Both are `git rm`. Never an archive folder: a directory of retired PRDs becomes a second source
of truth that nothing maintains, which is what was being escaped.

### A PRD usually owes more than one doc

One run harvests one topic, but a single PRD routinely carries material for several — a
theme PRD may owe the theming doc, the architecture doc, and the animation doc at once.

**A PRD may only be deleted once every doc it owes has been harvested**, not merely the first
one. Partial harvest is the normal state in between and is not a failure. `forge-harvest-planner`
names the remaining debts in its report; believe that list over the fact that one run finished.

This is the price of harvesting by target doc rather than by PRD, and it is the right trade:
supersession can only be resolved correctly with every claim on a topic visible at once, so
correctness comes first and deletion waits.

### The close-out order

1. Tests pass, `forge-code-reviewer` and `forge-code-prd-alignment` are clean.
2. **Harvest it.** Any decision that exists *only* in the PRD goes back into the design docs —
   dispatch `forge-harvest-planner` with this one PRD and its target doc, then `forge-doc-writer`.
   Same agent as the bulk migration above: one PRD is simply the smallest case, where there is
   nothing older to supersede. Not `forge-doc-planner` — that one tidies docs against each
   other and is instructed never to resolve a contradiction.
3. **Check the invariant:** no decision may exist only in a PRD. The planner's
   **Ready to delete** line states this directly, and it accounts for *every* doc the PRD
   owes, not just the one this run targeted. If it does not read clean, the harvest is not
   finished and nothing gets deleted.
4. **Delete it** — `git rm`. Git keeps the history; an archive folder becomes a second source
   of truth again. Deletion is a git operation, so it is the main loop's, not an agent's.
   `git log --diff-filter=D -- <prds>/` lists every retired PRD if you need one back.

### Migrating a backlog written before this system

One-time, and not part of the flow above. The previous system's PRDs — per-service and
cross-service sprint folders, over a million words — already sit in
`<docsRoot>/Archived_for_deletion/`, outside the manifest's `prds` path on purpose so nothing
globbing that directory picks one up. They are harvested from there and deleted from there:

1. **Tidy each design doc** so the SOT is structurally sound before anything lands in it.
2. **Harvest one topic at a time** — a design doc, or a section of one. Dispatch
   `forge-harvest-planner` with the target; it greps the archive for the PRDs that touch the
   topic rather than reading it whole. **It is a 20% harvest**: only decisions the running code
   confirms and a maintainer would need to know reach the SOT. Build instructions, test plans,
   and never-shipped intentions are dropped, and the report lists each dropped claim in a line.
3. **Apply** the plan with `forge-doc-writer`; relay **Contradicts the code** and **Needs your
   call** to the user.
4. **Delete what the report names.** `git rm` exactly the paths under **Ready to delete** —
   a PRD, or a whole `sprint_N/` folder once every PRD in it is covered. A PRD marked **Still
   owed** stays until the doc it owes has had its run. The deletion is the main loop's, never
   an agent's: `forge-harvest-planner` holds no write tools by design. **Empty the folder** —
   a staging area that never drains becomes a second source of truth.
5. **Regenerate just-in-time** — one PRD, for the feature about to be built, and only when that
   feature earns a PRD at all. Regenerating the whole backlog rebuilds the problem: this project
   reached over a million words of PRD under the previous system.

**Running it unattended: `/forge-harvest-backlog`.** Steps 2 through 4 are the same loop
dozens of times over, and on a backlog this size that is a walk-away job rather than a session.
That command drives the loop from an authored topic list at
`<docsRoot>/maintenance/harvest/topics.json`: it dispatches the planner and the writer per
topic, `git rm`s exactly what each report marks **Ready to delete**, commits once per topic as
its checkpoint, and resumes from `progress.json` if the session dies. It never asks anything —
every **Contradicts the code** and **Needs your call** lands in
`<docsRoot>/maintenance/harvest/REVIEW-ME.md` for the user to read afterwards. It belongs to
forge (it dispatches forge agents and is listed in `system.json`'s `commands[]`), and it
deviates from step 1 deliberately: the tidy runs once at the *end*, where it also sees what the
harvest added, instead of reading every design doc before a single decision has been recovered.

Most of a migrated backlog should never come back. Under the triage rule above, the majority of
features are built and looked at rather than specified.

**Never delete a partially-built PRD.** If half the requirements shipped, it stays at
`Status: Building` with the rest. Deletion is safe only because the tests now carry the spec in
executable form — which is exactly why tests-before-code and delete-on-done are one decision,
not two.

Short-lived PRDs also can't form the cross-reference web the current set has, where one PRD
cites another's numbered requirements and renumbering cascades. Shared contracts belong in the
design docs or in the code, not in a citation between two documents that are both temporary.

## The roster

| Agent | Job (one sentence) | Model / Effort | Writes | Wiring |
|---|---|---|---|---|
| `forge-doc-planner` | Plans the tidying work on the active project's design docs and hands forge-doc-writer a precise list. | opus / high | no | Tier 2 — this file + `SessionStart` hook (`docs-pending.sh`) |
| `forge-harvest-planner` | Plans how the archived PRD backlog folds into one source-of-truth doc — only the decisions the code confirms and the SOT needs — and names what is then safe to delete. | opus / high | no | Tier 1 |
| `forge-doc-writer` | Applies a `forge-doc-planner` plan to the source-of-truth docs, changing nothing the plan didn't name. | sonnet / medium | **yes** | Tier 1 |
| `forge-prd-author` | Turns settled design decisions into a PRD for one feature. | opus / high | **yes** | Tier 1 |
| `forge-prd-reviewer` | Reports whether a PRD is buildable without guessing, before anyone builds from it. | opus / high | no | Tier 1 |
| `forge-code-writer` | Writes the source code for one bounded, PRD-specified task. | sonnet / high | **yes** | Tier 1 |
| `forge-code-cleaner` | Removes dead code, stale comments, and duplication from the current diff without changing behavior. | sonnet / medium | **yes** | Tier 1 |
| `forge-code-reviewer` | Reports correctness defects in the current change. | opus / high | no | Tier 1 |
| `forge-code-prd-alignment` | Reports where an implementation diverges from what its PRD specified. | sonnet / high | no | Tier 1 |
| `forge-test-author` | Writes tests from the PRD's requirements rather than from the implementation. | sonnet / high | **yes** | Tier 1 |
| `forge-test-auditor` | Reports which tests assert real behavior and which only assert that the code runs. | sonnet / high | no | Tier 1 |
| `forge-retro-planner` | Runs a retrospective on the forge process itself and routes each lesson to where it belongs. | opus / high | no | Tier 1 |

Files live in `.claude/agents/forge/` and carry the `forge-` prefix. Both are required, and for
different reasons — see `.claude/agents/README.md`, which holds the doctrine that outlives this
system. Add or change an agent only through `/agent-creator`, and update this table when you do:
`system.json` beside this file lists the same twelve names, and `/set-system` reads it to know what
to deny when forge is inactive. A roster row without a `system.json` entry is an agent that
stays dispatchable after a swap.

## Learning from the process

`forge-retro-planner` is the pipeline pointed at itself: dispatched on demand — when the user
says something hurt, after a close-out worth examining, or when the same friction shows up
twice — never automatically, because a retro on every session manufactures lessons to justify
itself. It reads the metrics log, git history, and the rules as written, and routes each
lesson to the cheapest destination that fixes it: a failure-log row, an edit to one agent, a
skill, or nothing. It holds no write tools; installing a lesson is the main loop's, through
`/agent-creator`, and only after the user has seen the report.

```
Agent(subagent_type: "forge-retro-planner", prompt: "Retro on <window — this PRD cycle / since <ref>>. <What hurt, if known.>")
```

## Dispatching

State the resolved manifest paths in the prompt when you dispatch a forge agent. The agent reads
the manifest itself and that read is authoritative — passing them just saves it a round trip.

## Tidying the docs

**Run the `forge-tidy-docs` skill whenever a design doc is added or edited** — after your own
edits, when the user says a question has been answered, or when they've finished a brain-dump
session. It runs `forge-doc-planner` (decides, cannot edit) and then `forge-doc-writer` (edits,
decides nothing), and explains what to expect from each.

`roadmap.md` is generated by `forge-doc-writer` and does not follow the house style in
`CLAUDE.md` — it is an index of where things live, not a doc to hand-edit.

## This system's hook

`.claude/hooks/docs-pending.sh` (`SessionStart`) flags uncommitted design-doc changes in the
active project's `docsRoot`, skipping `PRDs/`, `roadmap.md`, and `project.json`, which are not
`forge-doc-planner`'s territory.

It is registered in `settings.json`, which this file has no say over, so it **self-gates**: it
reads `CLAUDE.md`'s import line and exits silently unless forge is the active system. That gate
is what stops it firing into a system with no `forge-doc-planner` to dispatch.
