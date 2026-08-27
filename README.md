# `.claude`

A portable Claude Code configuration — agents, skills, commands, hooks, and a telemetry stack —
packaged so it can be dropped into any project as that project's `.claude/` directory.

The organising idea is that **one agent *system* is active at a time**. A system is a whole way
of working: rules, the agents that enforce them, the skills that drive them, and the hooks that
fire them. Rules which are never loaded cannot be misapplied, so the inactive system's rules are
not in context at all — see [`systems/README.md`](systems/README.md).

| System | What it is |
|---|---|
| `forge` | Pure delegation. Twelve agents, one territory each; the main loop never writes a project artifact. |
| `direct` | Off, made explicit. No pipeline; the main loop does the work inline. |

## What's in here

```
agents/        subagent definitions, namespaced by system (agents/forge/…)
commands/      user-only slash commands — /set-project, /set-system, /create-pr
hooks/         SessionStart and SubagentStop shell hooks
metrics/       where captured agent-run metrics land (contents gitignored)
otel/          optional OpenTelemetry + Prometheus + Grafana stack for agent telemetry
project/       active.json — the pointer to the active project
skills/        skills, including the agent-creator and agent-builder meta-skills
systems/       one directory per system: SYSTEM.md (the rules) + system.json (the roster)
tools/         helper scripts — agent-metrics.py, sim.sh
settings.json  hook registration, permission deny-list, skill overrides
```

## Installing into a project

```sh
# snapshot — a plain copy, no ongoing link to this repo
curl -fsSL https://raw.githubusercontent.com/EhrenDavis12/.claude/main/install.sh | sh -s -- .

# or, from a clone of this repo
./install.sh /path/to/your/project
./install.sh /path/to/your/project --submodule   # track this repo as a git submodule
```

Pick **snapshot** when the project will diverge — most of the time, since half of what is here
is tuned to a specific repo. Pick **`--submodule`** when you want fixes to flow both ways; note
that a fresh clone of the host repo then has an empty `.claude/` until
`git submodule update --init`, which means the first session in that clone runs with no agents,
no skills, and no hooks.

## After installing: the three things that are not optional

**1. The host project needs a `CLAUDE.md`, and it must import the active system.** Nothing in
this repo supplies it — the system rules live in `systems/<name>/SYSTEM.md` and reach the model
only through a single import line at the end of the host project's `CLAUDE.md`:

```markdown
@.claude/systems/forge/SYSTEM.md
```

Exactly one such line. `hooks/repo-context.sh` treats that line as the source of truth for which
system is active and complains at session start if there are zero, two, or a dangling one.
Everything that is true *regardless* of system — what the repo is, the active-project machinery,
the documentation house style, how you talk to the user — belongs above that line in
`CLAUDE.md`, not in a system file. The test: would the `direct` system still need this sentence?

**2. The active-project machinery needs a manifest.** `project/active.json` holds a slug:

```json
{ "project": "my-project" }
```

`hooks/repo-context.sh` then looks for the `Docs/*/project.json` whose `.name` matches that slug
and injects the resolved scope at session start. That manifest is the authoritative path source
for every agent:

```json
{
  "name": "my-project",
  "title": "My Project",
  "summary": "One line.",
  "docsRoot": "Docs/my-project",
  "prds": "Docs/my-project/PRDs",
  "roadmap": "Docs/my-project/roadmap.md",
  "srcRoots": ["src/my-project"],
  "aliases": ["mp"],
  "stack": "TypeScript"
}
```

Every path is repo-relative and already joined, so nothing downstream builds a path. Without a
matching manifest the hook says so plainly and agents refuse to run rather than guessing — a
silent fallback is how this pipeline once came to point at a directory that did not exist.

**3. `jq` must be on `PATH`.** All three hooks need it. `repo-context.sh` exits silently without
it, so the symptom is not an error — it is a session that quietly knows nothing about the
project.

## What to prune per project

Not everything here is generic. Delete what does not apply before the first session:

| Path | Assumes |
|---|---|
| `skills/playtest/`, `tools/sim.sh` | an iOS app and the iOS Simulator |
| `skills/generate-asset/` | the Asset-Gen-Framework CLI checked out under `src/` |
| `commands/create-pr.md` | a mono repo whose sources are git submodules |
| `otel/` | Docker, and wanting a Grafana stack for agent telemetry |
| `agents/forge/`, `systems/forge/` | that you want the twelve-agent delegation pipeline at all |

If you drop a whole system, drop its `systems/<name>/` directory too, and re-run `/set-system`
so `settings.json` stops denying agents that no longer exist.

## Changing the configuration

Use the meta-skills rather than editing by hand — they exist because the wiring has more
surfaces than it looks like:

- **`/agent-creator`** — design, review, install, and wire up a subagent. It gates on overlap
  with the existing roster, a justified model and effort tier, and one job per agent, and it
  updates `agents/`, the owning `SYSTEM.md`, `system.json`, and any hook.
- **`/agent-builder`** — the design record. Read it before changing how agents work *together*:
  a new pipeline stage, a changed document type, or "should this be an agent at all?"
- **`agents/README.md`** — the cross-system doctrine: positions, naming, wiring tiers, overlap
  rules.

The wiring trap worth knowing up front: `CLAUDE.md` has no say over `settings.json`. Swapping the
import line changes what the model *reads* and nothing about what the harness *executes*. Agents
are registered by directory, so an inactive system's agents stay dispatchable unless
`settings.json` denies them by name; skills likewise need `skillOverrides`. That is why every
system carries a `system.json` roster and why `/set-system` writes both halves — and why
`repo-context.sh` checks at every session start that the two halves still agree.

## Telemetry

`otel/` runs an OpenTelemetry collector, Prometheus, and Grafana against the metrics that
`hooks/capture-agent-metrics.sh` writes to `metrics/agent-runs.jsonl`. It is entirely optional
and off unless you start it. See [`otel/OTEL-ReadMe.md`](otel/OTEL-ReadMe.md).
