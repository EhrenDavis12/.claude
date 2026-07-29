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
forge-prd-author → forge-prd-reviewer → forge-code-writer → forge-code-cleaner → forge-code-reviewer
                                ↕                        forge-prd-alignment
                          forge-test-author → forge-test-auditor
```

Don't skip `forge-prd-reviewer`. Everything downstream treats the PRD as its specification, so
an ambiguity there gets copied into every agent that reads it — and none of them can ask you
about it.

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
| `forge-prd-alignment` | Reports where an implementation diverges from what its PRD specified. | sonnet / high | no | Tier 1 |
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
