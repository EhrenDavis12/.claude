---
description: Show or switch which agent system is active (forge / direct)
argument-hint: "[system name]"
---

# Set the active agent system

A **system** is a whole way of working: rules, agents, skills, and hooks. One is active at a
time. Read `.claude/systems/README.md` for the design; this file is how to switch.

**This is a command, not a skill — deliberately.** Only the user can run it. Claude has no way
to invoke it on its own.

This is the stricter of the two switches. Changing systems changes the rules Claude is
operating under, and the change is only half-live until a restart — the rules move immediately,
the agent registry and hooks do not. A swap Claude initiated would put the user in the worst
possible position: reasoning about one set of rules while a mixed state is actually in force.

So if a swap is needed — including to repair the half-finished state `repo-context.sh` reports
— **Claude says so and stops.** It does not swap.

The argument, if any, is: `$ARGUMENTS`

The active system is whichever `SYSTEM.md` **`CLAUDE.md`'s single import line** names:

```
@.claude/systems/<name>/SYSTEM.md
```

That line is the source of truth. Everything else — the deny list, the skill overrides, the
hook self-gates — derives from it. Nothing else may disagree with it, which is why
`repo-context.sh` checks agreement at every session start.

## Anatomy

```
.claude/systems/<name>/
  SYSTEM.md      # the rules, imported into CLAUDE.md when active
  system.json    # { name, title, summary, agents[], skills[], hooks[] }
```

`system.json` is what lets this command know what to deny without hardcoding a roster.

## With no argument (`$ARGUMENTS` empty) — show

1. `Glob .claude/systems/*/system.json` and read each one.
2. Read `CLAUDE.md`'s import line to find the active system.
3. Report the active one first with its `title` and `summary`, then list the others.
4. Say what a swap would cost — that a restart is required.

Don't ask which to activate. Unlike `/set-project`, switching systems changes the rules you are
operating under; make the user say it explicitly.

## With an argument — activate it

1. **Resolve.** Find `.claude/systems/$ARGUMENTS/`. Match on the directory name and on
   `system.json`'s `.name` — they should be identical; if they are not, stop and report it.
   If nothing matches, list what does exist and stop. Do not scaffold a system on a typo.

2. **Validate before writing.** All of:
   - `.claude/systems/<name>/SYSTEM.md` exists and is non-empty
   - `system.json` parses, and has `name`, `title`, `agents`, `skills`, `hooks`
   - every agent named in `agents[]` has a file under `.claude/agents/`
   - every skill named in `skills[]` has a directory under `.claude/skills/`
   - every hook path in `hooks[]` exists and is executable

   Report every problem and **do not activate a broken system.** Half a system is worse than
   the wrong one, because the failure surfaces later and looks like a model mistake.

   A missing `SYSTEM.md` is the one to be strictest about: it is not documented whether a
   dangling `@` import fails loudly or is silently skipped, so an unvalidated swap could leave a
   session with *no* system rules and no complaint.

3. **Rewrite the import line** in `CLAUDE.md` — the last line of the file. Exactly one such
   line may exist when you are done. Change nothing else in `CLAUDE.md`.

4. **Rewrite `settings.json`'s two swap-following keys** from every *inactive* system's
   `system.json`. Compute both from scratch each time; do not append.

   - `permissions.deny` — one `"Agent(<name>)"` entry per agent belonging to an inactive
     system. **Preserve any existing deny entry that is not an `Agent(...)` rule** — the user
     may have denied other things for unrelated reasons.
   - `skillOverrides` — `{"<skill>": "off"}` for every skill belonging to an inactive system.

   An agent or skill listed by *no* system is repo-level — `/agent-creator` is the only one —
   and is never denied. `/set-project` and `/set-system` are commands, not skills, so
   `skillOverrides` never applies to them at all.

   Settings edits go through the `/update-config` skill, which owns `settings.json`
   correctness. Do not hand-write the JSON.

5. **Echo the newly active rules into the conversation** — see below.

## Always echo, and always say "restart"

Memory, the agent registry, the skill listing, and the hooks all load at **session start**. So
the swap is only half done until Claude Code restarts:

| What | When it takes effect |
|---|---|
| The rules you read | immediately, via the echo below |
| `permissions.deny` — agents refusing | next session |
| `skillOverrides` — skills disappearing | next session |
| Hook self-gates | next session |

The echo is what keeps the current session coherent meanwhile — the same reason `/set-project`
echoes its scope. Without it the main loop keeps operating under the rules it loaded at startup.

End every successful run by printing:

```
Active system: <name> — <title>
  <summary>
  agents:  <agents, comma separated — or "none">
  skills:  <skills, comma separated — or "none">
  hooks:   <hooks, comma separated — or "none">

Now denied (inactive systems): <the Agent(...) deny list, or "none">
Now switched off:              <the skillOverrides keys, or "none">
```

Then **read the newly active `SYSTEM.md` aloud into the conversation** — a summary of its rules,
not the file verbatim — and state plainly:

> These rules apply from now. The agent registry, skill listing, and hooks change on restart.

Never report a swap as complete before that restart. The import line is live immediately;
nothing else is.

## Adding a system

Only when asked. Create `.claude/systems/<name>/` with both files, list every agent and skill
the system owns in `system.json`, give each of its hooks a self-gate on the import line, then
activate. `.claude/systems/README.md` has the full checklist.

`/set-system direct` is how you turn the pipeline off. It is a real system with its own rules
rather than an absent import, because a session that opens naming no system is broken rather
than relaxed.

## What this command does not do

- **It does not move files.** Every system's agents, skills, and hooks stay on disk; the switch
  is which of them are reachable.
- **It does not edit any `SYSTEM.md`.** It reads them and rewrites one line of `CLAUDE.md` plus
  two keys in `settings.json`.
- **It does not change the active project.** That is `/set-project`, and it is repo-level —
  scoping survives a system swap untouched.
