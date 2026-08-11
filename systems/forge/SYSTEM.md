# System: forge

> **Active.** This file is in context because `CLAUDE.md` imports it. If you are reading these
> rules, forge is the system in force. See `.claude/systems/README.md` to swap.

The forge pipeline: design docs → PRD → code → tests. Ten agents, one territory each, and a
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
    → harvest → delete the PRD
```

**Tests come before the code.** `forge-test-author` is told to work from the PRD and never
from the implementation; running it first makes that structurally impossible to break rather
than merely instructed. `forge-code-writer`'s definition of done becomes "the pre-written tests
pass," and the PRD's binding content ends up executable — which is what makes deleting it safe
later.

`forge-test-auditor` runs *before* the code for the same reason it matters most there: the code
will be built to satisfy whatever these tests demand, so a weak test does not merely miss a bug,
it becomes the target.

Running tests is a `Bash` checkpoint, not a pipeline stage — after `forge-code-writer` to reach
green, and after `forge-code-cleaner` to confirm it stayed green. **There is no test-runner
agent**, because running a command needs no judgment. Nor is there a play-test agent: use the
`/run` skill and look at the app yourself. Appearance, spacing, animation, and feel are checked
that way, never asserted.

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

A project here wrote 210,000 words of PRD against zero lines of code before this rule existed.
When in doubt, build.

## Closing out a PRD

A PRD is scaffolding, not a source of truth. It holds two things with opposite lifetimes: the
**decisions**, which outlive the feature, and the **build instructions**, which the code
replaces the moment it exists. Keeping the second forever is what makes PRDs a decaying second
description of the code that something then has to police.

### The four states

A PRD's state lives in the `> **Status:**` line the house style already gives it. Nothing else
tracks it — state stored in two places is state that goes stale.

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

### The close-out order

1. Tests pass, `forge-code-reviewer` and `forge-code-prd-alignment` are clean.
2. **Harvest it.** Any decision that exists *only* in the PRD goes back into the design docs —
   dispatch `forge-doc-planner` with the PRD named as a decision source, then `forge-doc-writer`.
3. **Check the invariant:** no decision may exist only in a PRD. If deleting it would lose
   something you could not rebuild from the design docs, the harvest is not finished.
4. **Delete it** — `git rm`. Git keeps the history; an archive folder becomes a second source
   of truth again. Deletion is a git operation, so it is the main loop's, not an agent's.
   `git log --diff-filter=D -- <prds>/` lists every retired PRD if you need one back.

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
| `forge-doc-writer` | Applies a `forge-doc-planner` plan to the source-of-truth docs, changing nothing the plan didn't name. | sonnet / medium | **yes** | Tier 1 |
| `forge-prd-author` | Turns settled design decisions into a PRD for one feature. | opus / high | **yes** | Tier 1 |
| `forge-prd-reviewer` | Reports whether a PRD is buildable without guessing, before anyone builds from it. | opus / high | no | Tier 1 |
| `forge-code-writer` | Writes the source code for one bounded, PRD-specified task. | sonnet / high | **yes** | Tier 1 |
| `forge-code-cleaner` | Removes dead code, stale comments, and duplication from the current diff without changing behavior. | sonnet / medium | **yes** | Tier 1 |
| `forge-code-reviewer` | Reports correctness defects in the current change. | opus / high | no | Tier 1 |
| `forge-code-prd-alignment` | Reports where an implementation diverges from what its PRD specified. | sonnet / high | no | Tier 1 |
| `forge-test-author` | Writes tests from the PRD's requirements rather than from the implementation. | sonnet / high | **yes** | Tier 1 |
| `forge-test-auditor` | Reports which tests assert real behavior and which only assert that the code runs. | sonnet / high | no | Tier 1 |

Files live in `.claude/agents/forge/` and carry the `forge-` prefix. Both are required, and for
different reasons — see `.claude/agents/README.md`, which holds the doctrine that outlives this
system. Add or change an agent only through `/agent-creator`, and update this table when you do:
`system.json` beside this file lists the same ten names, and `/set-system` reads it to know what
to deny when forge is inactive. A roster row without a `system.json` entry is an agent that
stays dispatchable after a swap.

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
