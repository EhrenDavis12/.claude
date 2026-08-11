# System: direct

> **Active.** This file is in context because `CLAUDE.md` imports it. If you are reading these
> rules, direct is the system in force. See `.claude/systems/README.md` to swap.

No pipeline is running. You do the work yourself, inline.

This is "off" written down. It is a real system rather than a missing import so that the state
is legible: a session that opens with no system named is broken, not relaxed.

## What that means

**Write project artifacts directly.** Design docs, PRDs, source, and tests are all yours. There
is no delegation boundary, no territory ownership, and no writer-per-path table — those belong
to `forge` and are not in context right now.

**Do not dispatch `forge-*` agents.** They are denied in `settings.json` while this system is
active, so a dispatch fails rather than half-works. If you want them, **ask the user to run
`/set-system forge`** — it is a user-only command. Don't try to route around the denial.

**The built-in agents are still available** and worth using for what they are good at: `Explore`
for broad read-only search, `Plan` for implementation strategy. Neither writes, so neither
conflicts with anything here.

## What still applies

Everything in `CLAUDE.md`, in full. Specifically:

- **The documentation house style** — heading order, `## Open Questions` last, revising in
  place rather than keeping a decision log, never answering an open question yourself,
  preserving the user's voice, wrapping at column 90. These are properties of the docs, not of
  the pipeline that used to edit them. Editing a design doc yourself does not license
  rewriting it in your own words — but it does oblige you to delete the wording a settled
  answer supersedes, here as much as under forge.
- **The active project** — one project at a time, paths from its manifest, `/set-project` to
  switch, and stop rather than guess if the pointer or manifest is missing.
- **`srcRoots` are git submodules** — diff with `git -C <srcRoot> diff`.
- **Batch and resume** — still true of the built-in agents you do dispatch.

## Adding agents while this system is active

Don't. `/agent-creator` installs into `.claude/agents/`, and an agent that belongs to no system
is one nothing will deny on the next swap. If a job here genuinely wants an agent, that is
evidence for a new system rather than a loose agent — add `.claude/systems/<name>/` with a
`SYSTEM.md` and a `system.json` listing it.
