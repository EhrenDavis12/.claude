---
name: forge-set-project
description: Sets or shows which project the forge agents are scoped to. Use when switching between projects in this mono repo, when starting a session and the active project is wrong or unset, when a forge-* agent reports it cannot find an active project, or when registering a new project so the forge pipeline can work on it. One project is active at a time; every forge agent reads its paths from that project's manifest.
---

# Set the active forge project

This repo is a mono repo. Docs live under `Docs/<project>/`, source under `src/<repo>/`, and
**one project is active at a time**. Every `forge-*` agent resolves its own paths from the
active project's manifest rather than from anything hardcoded, so this command is what points
the whole pipeline at a project.

Two files carry the state:

| File | Holds |
|---|---|
| `.claude/forge/active-project.json` | `{ "project": "<slug>" }` — the pointer, and nothing else |
| `Docs/<project>/forge.json` | that project's manifest: every path, fully resolved |

The manifest is authoritative. The pointer only says which manifest to read.

## The manifest

```json
{
  "name": "tic-tac-toe",
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
constructs one. `name`, `docsRoot`, `prds`, `roadmap`, and `srcRoots` are required; `title`,
`summary`, `stack`, and `parkingLotDocs` are optional.

- `srcRoots` is an array. Most projects have one; some have several. Several are git
  submodules, which is why agents diff with `git -C <srcRoot>` rather than from the repo root.
- `parkingLotDocs` names design docs that are explicitly a holding pen for ideas that are *not*
  the current build. `forge-prd-author` treats them as out of scope for requirements.
- `docsRoot` is matched against git pathspecs, which are **case-sensitive**. It must match the
  tracked path exactly — `Docs/x` will not match a path tracked as `docs/x`.

Design docs are every `.md` **directly under** `docsRoot`, excluding `PRDs/`, `roadmap.md`, and
`forge.json`. Docs are flat by convention here; there is no design-docs subfolder.

## Running it

### With no argument — show and choose

1. `Glob Docs/*/forge.json` and read each one.
2. Read `.claude/forge/active-project.json` if it exists.
3. List every project: slug, title, src roots, and which is currently active.
4. Also list any directory under `Docs/` with **no** `forge.json` as *unregistered* — it holds
   docs the forge pipeline cannot see.
5. Ask which to activate with `AskUserQuestion`. If there is exactly one project and it is
   already active, just report that and stop — don't ask a question with one answer.

### With an argument — activate it

1. Find the manifest whose `.name` equals the argument, case-insensitively. Convention is
   `Docs/<slug>/forge.json`, but **`.name` is what matches** — a folder can be renamed without
   breaking the pointer.
2. **Validate before writing.** All of:
   - the manifest parses as JSON
   - `name`, `docsRoot`, `prds`, `roadmap`, `srcRoots` are all present
   - `name` matches the slug being activated
   - `docsRoot` exists on disk and is tracked by git under that exact case
     (`git ls-files -- <docsRoot> | head -1` returns something)
   - every entry in `srcRoots` exists on disk
   - `prds` exists, or say plainly that it will be created on first use

   Report every problem you find and **do not activate a broken manifest**. An agent that
   resolves to a path that isn't there fails in the middle of real work, which is a far worse
   place to discover it than here.
3. Write `.claude/forge/active-project.json`.
4. **Echo the resolved scope back into the conversation** — see below.

### Unknown project — offer to scaffold

If nothing matches, say so and list what does exist. Then offer to scaffold, and ask for the
title, the one-line summary, and the src roots before creating anything. Scaffolding means:
`Docs/<slug>/` with a `forge.json` and an empty `PRDs/`.

**Never scaffold silently**, and never invent a src root. A manifest pointing at a directory
that does not exist is worse than no manifest, because the failure surfaces later.

`roadmap.md` is **not** created here — `forge-doc-writer` generates it from the docs as its
final step. An empty hand-written one would just be a lie about what the project contains.

## Always echo the resolved scope

Hooks load at session start, so the SessionStart hook that normally announces the active
project has already run by the time this command executes. Without this step the switch is
invisible until restart — and the main loop would keep dispatching agents against the old
project. So end every successful run by printing:

```
Active forge project: <name> — <title>
  design docs: <docsRoot>  (flat .md files; excludes PRDs/, roadmap.md, forge.json)
  PRDs:        <prds>
  roadmap:     <roadmap>
  src roots:   <srcRoots, comma separated>
  stack:       <stack, if set>
```

and state that only this project is in scope for the rest of the session.

## What this command does not do

- **It does not edit design docs.** `forge-doc-writer` owns everything under `docsRoot` except
  `forge.json`, which is configuration and belongs to this command.
- **It does not tidy anything.** If the newly-active project has uncommitted doc changes, that
  is `forge-doc-planner`'s job — mention it, don't act on it.
- **It does not touch `src/`.** Registering a src root does not clone, init, or update a
  submodule. If a declared root is missing, say so and let the user decide.
