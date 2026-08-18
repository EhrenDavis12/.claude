# Agent systems

A **system** is a whole way of working: a set of rules, the agents that enforce them, the skills
that drive them, and the hooks that fire them. **One system is active at a time.**

The point is not configurability. It is that **rules which are never loaded cannot be
misapplied.** The weak form of a switch is a conditional — "while forge is up do X, while it's
down do Y" — which puts both branches in context and leaves the model to pick. The strong form
is this one: `CLAUDE.md` holds only what is true regardless of system and ends with a single
import naming the active one. The inactive system's rules are not in context to be
reinterpreted.

## The systems

| System | What it is |
|---|---|
| `forge` | Pure delegation. Twelve agents, one territory each; the main loop never writes a project artifact. |
| `direct` | Off, made explicit. No pipeline; the main loop does the work inline. |

## Swapping

```
/set-system            # show which is active and what else exists
/set-system direct     # switch
```

**Only the user can swap.** `/set-system` and `/set-project` are commands, not skills, so Claude
has no way to invoke either — and it is told not to reach around them by editing the pointer or
the import line directly. A swap Claude initiated would leave the user reasoning about one rule
set while another is in force, and because half the swap only lands on restart, "in force"
would itself be a mixed state. The switches are worth being slow about.

**A restart is required.** The import line changes what the model reads immediately, but the
agent registry, the skill listing, and the hooks all load at session start. `/set-system` echoes
the newly active rules into the conversation to keep the current session coherent meanwhile —
the same reason `/set-project` echoes its scope.

## The load-bearing problem: hooks don't follow the import line

`CLAUDE.md` has no say over `settings.json`. Swapping the import changes what the model *reads*
and nothing about what the harness *executes* — without the wiring below, a post-swap session
would still fire `docs-pending.sh` and inject "dispatch `forge-doc-planner`" into a system that
has no such agent. Same for agents and skills, which are registered by directory.

So "one line" is true for prose and false for wiring unless each surface is handled:

| Surface | Registered by | How it follows the switch |
|---|---|---|
| Instructions | `CLAUDE.md` | the `@` import line — **the single source of truth** |
| Agents | `.claude/agents/**` | `permissions.deny: ["Agent(<name>)", …]` for inactive systems |
| Skills | `.claude/skills/**` | `skillOverrides: {"<skill>": "off"}` for inactive systems |
| Hooks | `.claude/settings.json` | each system's hook script self-gates on the import line |

There is no batch agent-disable and no per-hook enable flag, so `permissions.deny` listing every
inactive agent and self-gating scripts are the supported mechanisms.

**No files move on a swap.** The import line stays authoritative: hook scripts *derive* the
active system from it, and `/set-system` writes the `settings.json` half. `repo-context.sh`
checks at every session start that the two halves agree, because a half-finished swap otherwise
runs silently in a mixed state.

## Anatomy of a system

```
.claude/systems/<name>/
  SYSTEM.md      # the rules — imported into CLAUDE.md when active
  system.json    # { name, title, summary, agents[], skills[], hooks[] }
```

`system.json` is what lets `/set-system` know which agents to deny and which skills to switch
off without hardcoding a roster. Keep it in sync with `SYSTEM.md`'s own roster: an agent listed
in the prose but missing from `system.json` stays dispatchable after a swap, which is exactly
the failure this design exists to prevent.

`SYSTEM.md` opens with a blockquote saying it is active. That reads oddly on disk and correctly
in context — the only time the model sees the file is when it has been imported.

## What belongs in `CLAUDE.md` instead

**Anything a successor system would also need is repo-level and must not be swappable.** That
covers what the repo is, the active-project machinery, the documentation house style, the
submodule-diff fact, and batch-and-resume (a harness property, true of built-in agents too).

The test when you are unsure: would `direct` still need this sentence? If yes, it is
`CLAUDE.md`'s.

## Adding a system

1. `mkdir .claude/systems/<name>/` and write `SYSTEM.md` and `system.json`.
2. List every agent and skill the system owns in `system.json`, even ones it shares — the deny
   list is computed from *inactive* systems, so an unlisted agent is never denied.
3. Give any hook it owns a self-gate: derive the active system from `CLAUDE.md`'s import line,
   `exit 0` silently unless it matches.
4. `/set-system <name>` to activate, then restart.

Hooks that are genuinely repo-level — `repo-context.sh` is the only one today — belong to no
system and are never gated.
