---
description: Show or switch which project this repo's agents are scoped to
argument-hint: "[project name or alias]"
---

# Set the active project

**This is a command, not a skill — deliberately.** Only the user can run it. Claude has no way
to invoke it on its own, so the active project cannot change without the user typing it. That
matters because the switch is invisible until it is announced: a mid-session change made on
Claude's initiative would leave the user reasoning about one project while Claude works on
another.

If Claude needs the project switched, it **asks and stops**. It does not switch.

The argument, if any, is: `$ARGUMENTS`

This repo is a mono repo. Docs live under `Docs/<project>/`, source under `src/<repo>/`, and
**one project is active at a time**. Project scoping is a property of the repo, not of any one
agent system — every agent resolves its own paths from the active project's manifest rather
than from anything hardcoded, so this command is what points all of them at a project.

Two files carry the state:

| File | Holds |
|---|---|
| `.claude/project/active.json` | `{ "project": "<slug>" }` — the pointer, and nothing else |
| `Docs/<project>/project.json` | that project's manifest: every path, fully resolved |

The manifest is authoritative. The pointer only says which manifest to read.

**The pointer always stores the canonical `name`, never an alias.** Aliases are resolved here,
at activation time, and never written down. Every agent and both `SessionStart` hooks look up
the manifest whose `.name` equals the pointer's slug — writing an alias into the pointer would
break all of them at once.

## The manifest

```json
{
  "name": "tic-tac-toe",
  "aliases": ["ttt"],
  "title": "Tic-Tac-Toe-Extreme",
  "summary": "One line on what this project is.",
  "docsRoot": "Docs/tic-tac-toe",
  "prds": "Docs/tic-tac-toe/PRDs",
  "roadmap": "Docs/tic-tac-toe/roadmap.md",
  "srcRoots": ["src/Tic-Tac-Toe-Extreme"],
  "stack": "Flutter / Dart",
  "parkingLotDocs": ["Alternative Game Styles.md"]
}
```

Every path is **repo-relative and already joined** — an agent uses it as-is and never
constructs one. `name`, `docsRoot`, `prds`, `roadmap`, and `srcRoots` are required; `aliases`,
`title`, `summary`, `stack`, and `parkingLotDocs` are optional.

- `aliases` is an array of short forms that also activate this project — `["ttt"]` makes
  `/set-project ttt` equivalent to `/set-project tic-tac-toe`. They are a typing convenience for
  **this command only**. `name` stays the identity: it is what gets written to the pointer, what
  every agent matches on, and what gets echoed back. Nothing downstream ever sees an alias.
- `srcRoots` is an array. Most projects have one; some have several. Several are git
  submodules, which is why agents diff with `git -C <srcRoot>` rather than from the repo root.
- `parkingLotDocs` names design docs that are explicitly a holding pen for ideas that are *not*
  the current build. Whatever writes requirements treats them as out of scope — under `forge`
  that is `forge-prd-author`.
- `docsRoot` is matched against git pathspecs, which are **case-sensitive**. It must match the
  tracked path exactly — `Docs/x` will not match a path tracked as `docs/x`.

Design docs are every `.md` **directly under** `docsRoot`, excluding `PRDs/`, `roadmap.md`, and
`project.json`. Docs are flat by convention here; there is no design-docs subfolder.

## Running it

### With no argument (`$ARGUMENTS` empty) — show and choose

1. `Glob Docs/*/project.json` and read each one.
2. Read `.claude/project/active.json` if it exists.
3. List every project: slug, aliases (if any), title, src roots, and which is currently active.
   Showing the aliases here is how anyone discovers the short forms exist.
4. Also list any directory under `Docs/` with **no** `project.json` as *unregistered* — it
   holds docs no agent can be scoped to.
5. Ask which to activate with `AskUserQuestion`. If there is exactly one project and it is
   already active, just report that and stop — don't ask a question with one answer.

### With an argument — activate it

1. Find the manifest matching `$ARGUMENTS`, case-insensitively, in this order:
   1. `.name` equals the argument — an exact name always wins.
   2. otherwise, any entry of `.aliases` equals the argument.

   Convention is `Docs/<slug>/project.json`, but **`.name` and `.aliases` are what match** — a
   folder can be renamed without breaking the pointer. Read every `Docs/*/project.json` before
   deciding, not just `Docs/<argument>/project.json`; an alias by definition does not sit at a
   path named after itself.

   If the argument matches an alias, say which project it resolved to, so a typo that happens
   to hit another project's alias is visible rather than silent.

   If two manifests claim the same alias, **stop and report the conflict** — do not pick one.
   Ambiguous aliases are a configuration bug, and guessing hides it.
2. **Validate before writing.** All of:
   - the manifest parses as JSON
   - `name`, `docsRoot`, `prds`, `roadmap`, `srcRoots` are all present
   - `name` matches the folder's project identity, and the resolved argument matched either
     `name` or one of `aliases`
   - no alias collides with another manifest's `name` or `aliases`
   - `docsRoot` exists on disk and is tracked by git under that exact case
     (`git ls-files -- <docsRoot> | head -1` returns something)
   - every entry in `srcRoots` exists on disk
   - `prds` exists, or say plainly that it will be created on first use

   Report every problem you find and **do not activate a broken manifest**. An agent that
   resolves to a path that isn't there fails in the middle of real work, which is a far worse
   place to discover it than here.
3. Write `.claude/project/active.json` — **always `.name`, never the alias the user typed.**
4. **Echo the resolved scope back into the conversation** — see below.

### Unknown project — offer to scaffold

If nothing matches — neither a `name` nor an alias — say so and list what does exist, **with
each project's aliases**, since the argument may simply be a short form that was never
registered. Then offer to scaffold, and ask for the title, the one-line summary, and the src
roots before creating anything. Scaffolding means: `Docs/<slug>/` with a `project.json` and an
empty `PRDs/`.

If the unmatched argument looks like a short form of a name that does exist, offer to add it as
an alias to that manifest instead of scaffolding a new project — that is almost always what was
meant.

**Never scaffold silently**, and never invent a src root. A manifest pointing at a directory
that does not exist is worse than no manifest, because the failure surfaces later.

`roadmap.md` is **not** created here — it is generated from the docs by whatever owns them
(under `forge`, `forge-doc-writer`, as its final step). An empty hand-written one would just be
a lie about what the project contains.

## Always echo the resolved scope

Hooks load at session start, so the SessionStart hook that normally announces the active
project has already run by the time this command executes. Without this step the switch is
invisible until restart — and the main loop would keep dispatching agents against the old
project. So end every successful run by printing:

```
Active project: <name> — <title>
  aliases:     <aliases, comma separated — omit the line if none>
  design docs: <docsRoot>  (flat .md files; excludes PRDs/, roadmap.md, project.json)
  PRDs:        <prds>
  roadmap:     <roadmap>
  src roots:   <srcRoots, comma separated>
  stack:       <stack, if set>
```

Always echo the canonical `<name>`, even when the user activated it by alias — the echoed name
is what the pointer now holds and what every agent will resolve.

and state that only this project is in scope for the rest of the session.

## What this command does not do

- **It does not edit design docs.** `project.json` is configuration and belongs to this
  command; everything else under `docsRoot` belongs to whoever the active system says owns it.
- **It does not tidy anything.** If the newly-active project has uncommitted doc changes,
  mention it and let the active system's doc pipeline handle it — don't act on it.
- **It does not touch `src/`.** Registering a src root does not clone, init, or update a
  submodule. If a declared root is missing, say so and let the user decide.
