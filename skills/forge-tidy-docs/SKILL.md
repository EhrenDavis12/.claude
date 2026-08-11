---
name: forge-tidy-docs
description: Tidy the active project's design docs by running forge-doc-planner and then forge-doc-writer. Use whenever a design doc is added or edited — after your own edits, when the user says an open question has been answered, or when they've finished a brain-dump session.
---

# Tidying the docs: `forge-doc-planner` → `forge-doc-writer`

Doc cleanup is two steps, deliberately. `forge-doc-planner` decides what should change but
**cannot edit anything**; `forge-doc-writer` edits but decides nothing. The expensive, destructive
judgment — "is this question really answered?" — therefore never holds a write tool.

```
Agent(subagent_type: "forge-doc-planner", prompt: "Design docs under <docsRoot> were edited — plan what needs tidying.")
```

Then hand its report, verbatim, to the forge-doc-writer:

```
Agent(subagent_type: "forge-doc-writer", prompt: "<the forge-doc-planner plan>")
```

How they behave, so you know what to expect:

- `forge-doc-planner` finds changed docs itself via `git status`/`git diff -- <docsRoot>` — you
  don't need to list files. It reads *every* design doc in the active project for context,
  because a question in one doc is often answered by an edit in another.
- Its report is a numbered list tagged **MOVE** / **REVISE** / **REMOVE** / **FORMAT**, plus
  a **Needs your call** section. Pass the whole thing through unedited — `forge-doc-writer` applies the
  tagged findings literally and is instructed to ignore **Needs your call**.
- Answered questions are written **into the prose**, in present tense, and the wording they
  supersede is deleted — including in other docs. There is no `## Decisions` section and no
  breadcrumb pointing at one. The doc says what is being built; `git log -p <doc>` is the
  audit trail. A REVISE finding carries the new text verbatim plus every passage to delete,
  and `forge-doc-writer` applies both halves or neither.
- Neither ever invents an answer. Anything uncertain comes back under **Needs your call**.

**Relay the Needs your call items to the user** — those are questions only they can settle.

`forge-doc-planner` runs on Opus at high effort on purpose: deciding whether a question is
*really* answered, and spotting contradictions across docs, is judgment work where a wrong
call silently destroys a design decision. Don't skip the pair to tidy docs inline "because
it's just moving a section around." `forge-doc-writer` runs on Sonnet precisely
because the thinking already happened — if you find yourself wanting it to be smarter, the
report wasn't specific enough.
