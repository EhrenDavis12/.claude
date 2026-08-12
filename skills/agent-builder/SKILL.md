---
name: agent-builder
description: The design record for this repo's agent system — how the flow is meant to work, what each agent is for, and the hard-won rules behind the current shape. Use before proposing any change to how agents work together: a new stage, a changed pipeline, a rethought document type, or "should this be an agent at all?" Read it to check a new idea against the design intent before building; it explains why the system looks like this, which the individual agent files deliberately do not. Not the installer — /agent-creator gates and wires an individual agent once the idea survives this file.
---

# Agent builder — how this system is designed to work

This is the **design memory**. Individual agent files say what each agent does; none of them
say why the set is shaped this way, so that reasoning used to live only in conversation and
had to be rebuilt every time. Read this before changing how agents work *together*.

**Two skills, different jobs — keep them that way:**

| | `agent-builder` (this file) | `/agent-creator` |
|---|---|---|
| Answers | "Does this idea fit how we work?" | "Is this agent built and wired correctly?" |
| Scope | The flow, the layers, the principles | One agent: gates, tools, tier, install |
| When | Before proposing a change | Once the idea survives |

Ideas come here first. Construction goes there. If you find yourself restating gates from
`/agent-creator` here, or design rationale from here in there, they are drifting — stop.

## The three layers

Everything in this repo is one of three things, and most mistakes are content sitting in the
wrong one:

```
SOT (design docs)   "what are we building, and why does it work this way"   permanent
      │
      ▼
PRD                 "what am I building now, and when am I done"            temporary
      │
      ▼
Code + tests        "how, exactly"                                          permanent
```

**The three-way test.** For any line of content:

- True even if this feature were never built → **SOT**
- Only true while this chunk is being built → **PRD**
- The code states it more precisely than prose can → **code**

A PRD is a **translation layer**, not a second source of truth. It slices one chunk out of the
SOT, sequences it, translates it into buildable work, and says what "done" means. It **cites**
decisions and architecture; it never **makes** them.

A PRD written before its SOT was trustworthy will hold decisions anyway. Getting back to the
shape above is two steps, and the second is the one that gets forgotten:

```
harvest   forge-harvest-planner → forge-doc-writer    decisions land in the SOT
drain     git rm                                      the PRD's copy stops existing
```

**Harvest without drain is duplication, not migration.** The drain is total — the PRD is
deleted, never edited into a thinner version of itself. A PRD that has given up its decisions has
given up its reason to exist, and editing one down preserves the structure that made it wrong:
the numbering, the cross-PRD citations, the accumulated shape. The replacement is generated
fresh from the current SOT when its feature is about to be built — if that feature earns a PRD
at all.

**Architecture is global, so it lives in the SOT — never in a PRD.** This is the line that
matters most. Per-feature architecture is how 24 PRDs came to cite each other's numbered
requirements, so renumbering one cascaded into three and a single revision took days. Shared
contracts belong in `Tech Design.md` or in the code.

## What each agent is for

| | Agent | Its one job |
|---|---|---|
| **Docs** | `forge-doc-planner` | Decides what the docs should say |
| | `forge-harvest-planner` | Decides what a PRD's decisions add to the docs, and what they replace |
| | `forge-doc-writer` | Writes it. Decides nothing. |
| **Spec** | `forge-prd-author` | Turns settled decisions into one PRD |
| | `forge-prd-reviewer` | "Is anything still unclear *and expensive*?" |
| **Code** | `forge-code-writer` | Builds one PRD task |
| | `forge-code-cleaner` | Deletes the leftovers |
| | `forge-code-reviewer` | Hunts bugs |
| | `forge-code-prd-alignment` | "Did we build what we said?" |
| **Tests** | `forge-test-author` | Writes tests from the spec, not the code |
| | `forge-test-auditor` | "Do these tests actually test anything?" |

The pattern repeats per territory: **one agent thinks, one agent writes, one agent checks.**
The thinker never holds a pen, so a bad idea cannot reach a file directly. Agent names carry
their phase (`forge-code-prd-alignment`, not `forge-prd-alignment`) because the phase is the
first thing you need when reading a pipeline.

## The order: tests before code

```
prd-author → prd-reviewer → test-author → test-auditor → code-writer
    → cleaner → code-reviewer → code-prd-alignment → harvest → delete PRD
```

Tests are written from the PRD **before the implementation exists**. That is not a style
preference — it converts the pipeline's load-bearing separation from an instruction into a
physical fact. `forge-test-author` is told never to work from the implementation; if there is
no implementation, it cannot. The PRD's binding content becomes executable, which is what makes
deleting the PRD safe afterward: the spec does not vanish, it changes form into something that
cannot silently drift from the code.

Consequences worth remembering:

- `forge-test-auditor` moves **before** the code. The code gets built to satisfy these tests, so
  a weak test is not a missed bug — it is a target, and the flaw gets implemented on purpose.
- `forge-code-writer`'s definition of done becomes "the pre-written tests pass", and its new
  failure mode is *satisfying the assertion without implementing the behavior*.
- `forge-code-prd-alignment` narrows to the two things a green suite structurally cannot catch:
  requirements with **no test at all**, and code built **beyond what was asked**.
- It gives you a measured one-shot rate — did the code pass first run? — which is the honest
  version of the confidence score that was considered and rejected.

**What is deliberately not an agent here:** running tests (whatever the stack's test command
is, it is a `Bash` checkpoint — no judgment involved) and play-testing (the `/run` skill, and
better done by a human looking at the screen).

## Which tests are worth writing

Match the test to what a wrong answer costs — the same reversibility axis that decides whether
a feature earned a PRD at all. One principle, two applications.

These are properties of tests, not framework names. **Agents stay stack-agnostic**: they
resolve these into the actual tooling via the manifest's `stack`, the project's testing policy
if it declares one, and the conventions of the tests already in the repo.

| Kind | Verdict |
|---|---|
| Static analysis / linting | Always. Effectively free. |
| **Fast isolated tests over pure logic** | The default and most of the value |
| **Property/invariant tests** | Highest value per line for rules and state machines — covers a space you cannot enumerate |
| Rendered-component tests | Only where a wrong guess is expensive. Never for appearance |
| **Pixel-snapshot tests** | Only where the visual design is settled. Otherwise every unrelated change invalidates them |
| End-to-end on a real device | One smoke test, late, on request |
| Play test | Free, irreplaceable, and the user's — not an agent's |

## The question loop

Agents cannot ask questions mid-run. This is the loop that resolves that, and every box is
load-bearing:

```
  Agent hits a question reading cannot settle
              │
              ▼
  Finishes everything else, returns ONE batch of questions
              │
              ▼
  Main loop answers what research can settle — most of them
              │
              ▼
  Asks the user only the intent questions            ◄── user is asked once
              │
              ▼
  forge-doc-planner: turns the answer into a REVISE finding —
    the new text, AND every old passage it supersedes
              │
              ▼
  forge-doc-writer: applies it exactly. Old wording deleted.
              │
              ▼
  SendMessage resumes the SAME agent, memory intact
              │
              ▼
  Agent cites the doc and carries on
```

Two things people get wrong here:

- **The planner is not skippable.** The writer only applies a list and may invent nothing. The
  planner is what sweeps every doc for wording the new answer contradicts — the step that
  keeps docs from arguing with themselves.
- **Resume, never re-dispatch.** `SendMessage` keeps the agent's partial work. A fresh `Agent`
  call re-reads everything and discards what it figured out: full price twice, for less.

## Principles

1. **One job, one sentence.** If it needs "and also", it is two agents or one is unneeded.
2. **Judgment and write access live in different agents.** Enforced by `tools:`, not by
   politeness. Default new agents to read-only; write access is argued for.
3. **Planner before a destructive write. Reviewer after work whose correctness is only visible
   in the output.** Wanting both usually means the worker's territory is too big.
4. **Every loop needs an exit condition** — see the failure log below.
5. **The default is to build.** Specification is the argued exception, and the argument is
   always *what does a wrong guess cost to fix?* Expensive or irreversible → spec it.
   Cheap and visible at runtime → build it and look.
6. **Revise in place; git is the audit trail.** Never keep a decision log in prose.
7. **Nothing may exist in only one place downstream.** A decision living only in a PRD is
   misfiled, because PRDs are deleted and the SOT is not.
8. **Agents are stack-agnostic; projects are not.** An agent names the *property* it wants —
   fast, isolated, asserts behavior — never a framework, command, or file extension. Anything
   true only of the current project's tooling belongs in that project's manifest, which is how
   the same roster serves the next project without an edit. The tell: if swapping the project
   would make a sentence in an agent false, that sentence is in the wrong file.

## The failure log

Every rule above was bought. Keep this list — it is the part that stops a "clean idea" from
reintroducing a solved problem.

| What happened | The rule it bought |
|---|---|
| PRDs reached **210,000 words against zero lines of code** — 10× the design docs they came from | A PRD should be shorter than the code it specifies |
| `forge-prd-reviewer` asked *"could the writer finish without guessing?"* — a bar with no floor, since unspecified states are combinatorial. Every review found more; every revision grew the PRD | Price the guess. Block only on expensive or irreversible. **Empty blocking list = ready, stop** |
| `Tech Design.md` reached **89% `## Decisions`** — the ledger ate the document, and the prose above contradicted the entries below | No decision log. Rewrite the prose, delete what it supersedes |
| Decisions the user settled lived **only inside PRDs**; two PRDs even carried a section admitting content was owed to the design docs, and it was never routed back | The question loop above, and: harvest a PRD before deleting it |
| PRDs cited each other's numbered requirements, so one revision cascaded through three documents | Architecture goes in the SOT. A PRD never cites another PRD |
| `forge-prd-author` had `Write` but no `Edit`, so every revision rewrote a 12,000-word file whole — and overran `maxTurns: 80` at 81 turns | Writers that revise large files need `Edit`. Check tools against what the body actually instructs |
| The inactive `direct` system still taught the old house style, so a swap would have silently restored it | A convention change must be applied to **every** system, not just the active one |
| An "85% confidence of one-shot completion" grade was proposed as a PRD gate, with looping until it passed | Rejected. An uncalibrated number the reviewer both assigns *and* uses to decide whether to loop again is the ratchet with a lab coat on. **Measure the one-shot rate after building; never predict it before** |
| A `Status: Ready` stamp was specified before noticing `forge-prd-reviewer` is read-only and could not write it | **Derive state from the repo, never store it.** Before adding a status field, name the agent whose tools can actually set it |
| Test-runner and play-test agents were proposed | Refused. Running a command needs no judgment, and `/run` already covers play-testing. **If a proposed agent's job is one deterministic command, it is a `Bash` line** |
| Writing the test-strategy rules put Flutter and Dart names — widget tests, golden files, `flutter test` — straight into agents meant to serve any project | Agents name test *properties*, never frameworks. Stack specifics come from the manifest. Written the same day the rule was violated, which is how easily it happens |
| The first harvest copied decisions into the SOT and **removed nothing from the PRDs** — four files came out byte-identical, so every harvested decision then existed in two places | A migration is copy **plus drain**. When designing any move between artifacts, name what removes from the source; the agent writing the destination cannot, and read-only-toward-the-source is usually why |
| The fix for that was a "slim the PRD" step, built into `forge-prd-author` before anyone asked what it was for. It had no use case: shipped PRDs delete, migrated ones are regenerated, and new ones never accumulate decisions to drain | Before building a repair path, check every column of the table it serves. A step that is off the steady-state flow is migration tooling at best — and permanent doctrine is the wrong place for it. Deleted the day after it was written |
| The close-out order assumed one PRD owes one doc. The first real PRD owed three | Harvesting by target doc is what makes supersession correct, so deletion waits until *every* owed doc is harvested. Partial harvest is the normal in-between state, not a failure |

The pattern under most of these: **append-only accumulation instead of revision.** Nothing was
ever rewritten, only added to — in PRDs, in Decisions sections, in review findings. When a new
idea means "we'll also record X", check whether X ever gets deleted, and by whom.

## Using this file

When an idea for the flow comes up:

1. **Which layer does it touch?** SOT, PRD, or code. Ideas that blur two layers are usually the
   problem.
2. **Does it add a loop?** If so, name its exit condition before anything else.
3. **Does it add a place where content accumulates?** Name who deletes from it.
4. **Does it overlap the chart above?** Trigger *or* territory overlap means it is an edit to an
   existing agent, not a new one.
5. **Does the failure log already cover it?** Re-solving a solved problem is the common case.
6. Only then, `/agent-creator` to build and wire it.

Keep this file current. When a rule is bought with real pain, add the row — the log is worth
more than the principles, because principles get re-derived and scars do not.
