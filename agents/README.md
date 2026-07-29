# Agent roster

Every agent under `.claude/agents/` must appear here. Maintained by the `/agent-creator` skill
— add, change, or retire agents through it rather than by hand, so the overlap and cost gates
actually get applied.

## Workflows

| Workflow | Folder | Prefix | Covers |
|---|---|---|---|
| `forge` | `.claude/agents/forge/` | `forge-` | design docs → PRD → code → tests |

Agents live in their workflow's folder **and** carry its prefix. Both are required:
project-level subfolders are discovered but **do not namespace** — the dispatch name comes
entirely from the `name:` field, so `.claude/agents/forge/x.md` with `name: x` is dispatched
as plain `x`. The folder groups files; the prefix is the only thing identifying the workflow
at dispatch time. (Verified with a throwaway canary agent, not assumed.)

`name:` always matches the filename stem, which is why paths stutter
(`forge/forge-doc-planner.md`). The path is cosmetic; the name is what gets typed.

**10 agents.** There is no numeric cap — a limit that gets raised whenever it binds isn't a
constraint. What actually prevents sprawl is Gate 1 (does this need an agent at all), Gate 2
(does something already cover it), and Gate 3 (one job, one sentence). Those refuse on
substance; a number only refuses on arithmetic.

## Positions

**Planner** runs before the worker. **Reviewer** runs after. Only workers hold write tools.

| Job | Planner | Worker | Reviewer |
|---|---|---|---|
| Documents | `forge-doc-planner` | `forge-doc-writer` | — |
| PRD | — | `forge-prd-author` | `forge-prd-reviewer` |
| Code | built-in `Plan` | `forge-code-writer` → `forge-code-cleaner` | `forge-code-reviewer`, `forge-prd-alignment` |
| Tests | — | `forge-test-author` | `forge-test-auditor` |

Which position to build is decided by the work, not by preference:

- **Planner** when the action is destructive or irreversible — you cannot review your way out
  of an overwritten design decision.
- **Reviewer** when correctness is only observable in the output — no amount of planning tells
  you whether code runs.
- **Both** is overkill unless a job is *both*. If you want both, the worker's territory is
  probably too large.

Planner + worker is also the cheaper pair: only the planner needs a strong model, so the
worker can run on Sonnet. Worker + reviewer needs both to be capable, because a reviewer must
be at least as strong as the worker to catch its mistakes.

## The roster

| Agent | Job (one sentence) | Model / Effort | Writes | Wiring |
|---|---|---|---|---|
| `forge-doc-planner` | Plans the tidying work on the active project's design docs and hands forge-doc-writer a precise list. | opus / high | no | Tier 2 — `CLAUDE.md` + `SessionStart` hook (`docs-pending.sh`) |
| `forge-doc-writer` | Applies a `forge-doc-planner` plan to the source-of-truth docs, changing nothing the plan didn't name. | sonnet / medium | **yes** | Tier 1 |
| `forge-prd-author` | Turns settled design decisions into a PRD for one feature. | opus / high | **yes** | Tier 1 |
| `forge-prd-reviewer` | Reports whether a PRD is buildable without guessing, before anyone builds from it. | opus / high | no | Tier 1 |
| `forge-code-writer` | Writes the source code for one bounded, PRD-specified task. | sonnet / high | **yes** | Tier 1 |
| `forge-code-cleaner` | Removes dead code, stale comments, and duplication from the current diff without changing behavior. | sonnet / medium | **yes** | Tier 1 |
| `forge-code-reviewer` | Reports correctness defects in the current change. | opus / high | no | Tier 1 |
| `forge-prd-alignment` | Reports where an implementation diverges from what its PRD specified. | sonnet / high | no | Tier 1 |
| `forge-test-author` | Writes tests from the PRD's requirements rather than from the implementation. | sonnet / high | **yes** | Tier 1 |
| `forge-test-auditor` | Reports which tests assert real behavior and which only assert that the code runs. | sonnet / high | no | Tier 1 |

## Write boundary

One chokepoint per territory, enforced by each agent's `tools:` field — a tools restriction is
a harder guarantee than a gatekeeper agent, and costs nothing.

Territories are **manifest keys**, resolved per active project — no agent holds a hardcoded
path. See "Project scope" below.

| Territory | Only writer |
|---|---|
| Design docs — `.md` directly under `docsRoot` | `forge-doc-writer` |
| `prds` | `forge-prd-author` |
| `roadmap` (the doc map) | `forge-doc-writer` |
| Source code under `srcRoots` | `forge-code-writer`, then `forge-code-cleaner` |
| Tests under `srcRoots` | `forge-test-author` |
| `project.json` | `/set-project` — configuration, not a doc |

The five read-only agents have no `Edit` or `Write` tool at all. When adding an agent, default
to read-only — write access has to be argued for.

Two separations that are load-bearing:

- **`forge-code-writer` does not write tests.** Tests written by the author of the code assert what
  was built rather than what was specified, which makes the mistake invisible.
- **`forge-test-author` does not edit source.** Fixing the code to make your own test pass destroys
  the signal the test existed to give.

## Project scope

This is a mono repo with **one project active at a time**. Every forge agent opens by reading
`.claude/project/active.json` for the slug, then the manifest whose `.name` matches it
(conventionally `Docs/<slug>/project.json`). The manifest supplies `docsRoot`, `prds`, `roadmap`,
`srcRoots`, and optional `stack` and `parkingLotDocs`, all repo-relative and already joined.

An agent that cannot find either file **stops and reports that `/set-project` must run**
rather than guessing — a silent fallback is how the pipeline previously came to point at a
directory that did not exist.

Two consequences worth knowing when adding an agent:

- **Every new agent needs the shared "Project scope" block**, listing which manifest keys it
  uses. Copy it from any existing forge agent.
- **`srcRoots` are often git submodules.** A `git diff` from the repo root shows only a changed
  submodule pointer, so any agent that scopes itself by diff must use `git -C <srcRoot> diff`.
  Getting this wrong produces an empty diff and a confident "nothing to do".

## The main loop's job — pure delegation

The main loop **never produces or modifies a project artifact.** Every change to source, tests,
design docs, or PRDs goes through the agent owning that territory. The main loop coordinates
and holds the end goal — the one thing no subagent can do, and the thing that degrades as its
context fills with implementation detail.

The line is **produce/modify vs. read/decide.** Deciding, dispatching, reading reports,
researching answers to agents' questions, and talking to the user are all main-loop work.
Reading is never delegation-worthy on its own. Writing always is.

Carve-outs, because they aren't project artifacts: `.claude/**` and `CLAUDE.md` (this system,
via `/agent-creator` — otherwise circular), git operations, and anything the user explicitly
asks for inline.

### Batch and resume

A subagent cannot ask a question, so agents finish what they can, settle whatever research
settles, and return genuine questions in one batch. The main loop answers what it can itself,
asks the user only about intent, then **resumes the same agent with `SendMessage`** — which
restores its transcript. A fresh `Agent` dispatch re-reads everything and discards the partial
work.

This is why neither ambiguity nor tight iteration justifies keeping work inline anymore.
Over-asking is the failure mode: if the spec or the code settles it, that's research, not a
question.

## Deliberately not agents

| Need | Use instead |
|---|---|
| Planning an implementation | built-in `Plan` agent |
| Broad read-only search | built-in `Explore` agent |
| Security review | `/security-review` skill |
| Switching or registering a project | `/set-project` skill |

`forge-code-cleaner` and `forge-code-reviewer` overlap the bundled `/simplify` and `/code-review` skills.
They exist as agents anyway, deliberately: skills run in the main loop and spend its context,
and keeping that context for goal-holding is the reason this roster is shaped the way it is.

**Wiring tiers:** 1 = on-demand (`description` + `CLAUDE.md`) · 2 = `PostToolUse` or
`SessionStart` reminder hook · 3 = `Stop` enforcement hook. See
`.claude/skills/agent-creator/references/wiring.md`.

Built-in agents also count against overlap checks: `Explore`, `Plan`, `general-purpose`,
`claude-code-guide`.
