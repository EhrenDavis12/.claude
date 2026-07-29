# Agent doctrine

How agents are designed, named, and wired in this repo — the part that outlives any one system.
**Which agents exist right now is not here.** That belongs to the active system: see
`.claude/systems/<name>/SYSTEM.md` for its roster, and `.claude/systems/README.md` for how
systems work.

Maintained by the `/agent-creator` skill — add, change, or retire agents through it rather than
by hand, so the overlap and cost gates actually get applied.

## Systems own agents

| System | Folder | Prefix | Covers |
|---|---|---|---|
| `forge` | `.claude/agents/forge/` | `forge-` | design docs → PRD → code → tests |
| `direct` | — | — | no agents; the main loop works inline |

Agents live in their system's folder **and** carry its prefix. Both are required:
project-level subfolders are discovered but **do not namespace** — the dispatch name comes
entirely from the `name:` field, so `.claude/agents/forge/x.md` with `name: x` is dispatched
as plain `x`. The folder groups files; the prefix is the only thing identifying the system
at dispatch time. (Verified with a throwaway canary agent, not assumed.)

`name:` always matches the filename stem, which is why paths stutter
(`forge/forge-doc-planner.md`). The path is cosmetic; the name is what gets typed.

A system is not a project. The `forge` pipeline runs against whichever project `/set-project`
has made active, and agents resolve their paths from that project's manifest. Never add a
per-project agent — add a project.

**Every agent must be listed in its system's `system.json`.** That file is what `/set-system`
reads to build the deny list, and the list is computed from *inactive* systems — so an agent
missing from it stays dispatchable after a swap. A roster row is documentation; the
`system.json` entry is the wiring.

There is no numeric cap on agents — a limit that gets raised whenever it binds isn't a
constraint. What actually prevents sprawl is Gate 1 (does this need an agent at all), Gate 2
(does something already cover it), and Gate 3 (one job, one sentence). Those refuse on
substance; a number only refuses on arithmetic.

## Positions

**Planner** runs before the worker. **Reviewer** runs after. Only workers hold write tools.

| Position | Runs | Holds write tools? | Suffix |
|---|---|---|---|
| **Planner** | *before* the worker | **No** | `-planner` |
| **Worker** | does the thing | Yes, for its territory only | plain noun (`-writer`, `-author`) |
| **Reviewer** | *after* the worker | **No** | `-reviewer`, or a precise synonym (`-auditor`, `-alignment`) |

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

`forge`'s roster is the worked example — `forge-doc-planner` runs before `forge-doc-writer` and
is therefore a planner, even though what it does looks like reviewing documents.

## The write boundary

**One chokepoint per territory, enforced by each agent's `tools:` field** — a tools restriction
is a harder guarantee than a gatekeeper agent, and costs nothing. Read-only agents have no
`Edit` or `Write` tool at all.

When adding an agent, **default to read-only.** Write access has to be argued for.

Which territories exist, and who owns them, is the active system's business — see its
`SYSTEM.md`.

## Project scope

This is a mono repo with **one project active at a time**, and project scoping is repo-level:
it does not change when the system does. Every agent opens by reading
`.claude/project/active.json` for the slug, then the manifest whose `.name` matches it
(conventionally `Docs/<slug>/project.json`), which supplies `docsRoot`, `prds`, `roadmap`,
`srcRoots`, and optional `stack` and `parkingLotDocs` — all repo-relative and already joined.

An agent that cannot find either file **stops and reports that `/set-project` must run** rather
than guessing — a silent fallback is how the pipeline previously came to point at a directory
that did not exist.

So: **every new agent needs the shared "Project scope" block**, listing which manifest keys it
uses. Copy it from any existing agent, or from
`.claude/skills/agent-creator/references/agent-template.md`. Without it the agent has no paths
at all.

`srcRoots` are git submodules — any agent that scopes itself by diff must use
`git -C <srcRoot> diff`. See `CLAUDE.md`.

## Deliberately not agents

| Need | Use instead |
|---|---|
| Planning an implementation | built-in `Plan` agent |
| Broad read-only search | built-in `Explore` agent |
| Security review | `/security-review` skill |
| Switching or registering a project | `/set-project` skill |
| Switching the agent system | `/set-system` skill |

Built-in agents count against overlap checks: `Explore`, `Plan`, `general-purpose`,
`claude-code-guide`.

An agent may deliberately overlap a bundled skill — `forge-code-cleaner` and
`forge-code-reviewer` overlap `/simplify` and `/code-review`. The justification is always the
same one: skills run in the main loop and spend its context, and preserving that context for
goal-holding is the reason a roster is shaped the way it is. State it explicitly; don't assume
it.

**Wiring tiers:** 1 = on-demand (`description` + a dispatch line in the active `SYSTEM.md`) ·
2 = `PostToolUse` or `SessionStart` reminder hook · 3 = `Stop` enforcement hook. See
`.claude/skills/agent-creator/references/wiring.md`.

A hook owned by a system must **self-gate** on `CLAUDE.md`'s import line — `settings.json` does
not follow the swap on its own. `.claude/hooks/docs-pending.sh` is the worked example.
