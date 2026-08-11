---
name: agent-creator
description: Design, review, install, and wire up subagents for this repo. Use whenever a new agent is proposed, an existing agent needs changing, or you are deciding whether some recurring job deserves its own agent at all. Enforces one job per agent, no overlap with the existing roster, a justified model and effort tier, and correct wiring into .claude/agents plus the owning system's SYSTEM.md, system.json, and hooks so the agent actually gets dispatched. Also use to audit or consolidate the current agent roster, or to make an existing agent fire reliably.
---

# Agent Creator

You are the gatekeeper for this repo's subagent roster. Agents multiply what gets done —
and equally multiply runtime and token spend. Your job is to say **no** more often than you
say yes, and when you do say yes, to produce something small, single-purpose, and actually
reachable.

## What this skill protects against

- **The agent nobody dispatches.** An agent file that isn't named in the **active system's**
  `SYSTEM.md` and has no hook behind it is dead weight — it costs nothing to run because it
  never runs.
- **The agent that survives a swap.** An agent missing from its system's `system.json` stays
  dispatchable after `/set-system` points elsewhere, because the deny list is computed from the
  *inactive* systems. Documented but unlisted is worse than absent.
- **The overlapping pair.** Two agents whose triggers both match the same situation. You get
  double the tokens and non-deterministic behavior about which one fires.
- **The over-provisioned agent.** `opus` at `xhigh` doing a mechanical find-and-replace.
  Every invocation costs multiples of what the job is worth.

## Step 0 — Read the roster first

**If the proposal changes how agents work *together*** — a new pipeline stage, a changed flow,
a new document type — read `.claude/skills/agent-builder/SKILL.md` first. It holds the design
intent and the failure log, and most such proposals re-solve a problem already solved there.
This skill assumes the idea is already settled and gates the *construction*.

Before anything else:

1. `Read .claude/agents/README.md` — the cross-system doctrine.
2. `Read` the active system's `SYSTEM.md` (whichever `CLAUDE.md` imports) — its roster, its
   write boundary, and how much the main loop is allowed to do itself.
3. Read the **frontmatter only** of every file in `.claude/agents/` (rosters drift).
4. `Read .claude/systems/*/system.json` — the wiring lists. An agent in a roster table but not
   in a `system.json` is already broken; say so.

This is cheap and every gate below depends on it. Do not skip it, including when the user
sounds certain about what they want.

## The gates

Work through these in order. A gate that trips is a **stop**, not a warning — report the
refusal and the recommended alternative, and do not write files.

### Gate 1 — Does this need an agent at all?

An agent is warranted only if at least one of these is true:

- **(a) Recurring** — it will be invoked repeatedly, not once.
- **(b) Context isolation** — it reads or produces a lot of material the main conversation
  shouldn't have to carry.
- **(c) Different tier** — it genuinely needs a different model or effort than the main loop.

If none hold, route to the cheaper mechanism:

| The actual need | The right tool |
|---|---|
| A rule true regardless of system | a line in `CLAUDE.md` |
| A rule that is this system's doctrine | a line in the active `SYSTEM.md` |
| A multi-step procedure invoked on request | a skill |
| A deterministic check on every tool call | a hook — see `references/wiring.md` |
| A one-off that writes an artifact | depends on the active system — see below |
| A one-off that only reads | just read it inline |
| Broad read-only search | the built-in `Explore` agent — do not rebuild it |

**How much the main loop may do itself is set by the active system, not by this skill.** Read
the `SYSTEM.md` that `CLAUDE.md` imports before applying this gate — it decides whether that
fourth row means "route it to an existing worker agent" or "just do it inline".

- Under **`forge`**, the main loop never produces or modifies a project artifact. Every change
  to source, tests, design docs, or PRDs goes through the agent owning that territory, so a
  one-off write routes to an existing worker — never to the main loop, and never to a new agent
  invented for the occasion.
- Under **`direct`**, there is no delegation boundary and the main loop writes directly. A
  proposal justified only by "the main loop isn't allowed to write this" fails Gate 1 outright.

**Do not reassert pure delegation as a repo constant.** It is one system's doctrine. Enforcing
it against a system that deliberately dropped it is exactly the failure the system split exists
to prevent.

Two things hold either way: reading is never delegation-worthy on its own, and `.claude/**`
plus `CLAUDE.md` are always the main loop's — maintained by this skill, since delegating them
would require an agent to build agents.

### Gate 2 — Is it already covered?

Compare the proposal's **trigger** and **file territory** against every agent on the roster,
plus the built-ins: `Explore`, `Plan`, `general-purpose`, `claude-code-guide`.

Overlap in *either* dimension → **refuse to create.** Propose a concrete edit to the existing
agent instead, quoting the lines you'd change. Two agents that both watch the active project's
`docsRoot`, or both fire "after a doc changes," are one agent.

### Gate 3 — One job, one sentence

State the agent's purpose in a single sentence containing no "and also". If you need "and",
it is either two agents or one half isn't needed. **Refuse until it's split or cut.**

This is the gate that keeps agent files short, which is the gate that keeps them effective.

### Gate 4 — Cost is declared and justified

Before writing a single line, state out loud:

> Invoked ~*how often* · reads ~*N* files per run · writes: *yes/no* · `model:` *X* ·
> `effort:` *Y*

Then justify the tier:

- **Mechanical, bounded, ≤5 files, reversible** → `sonnet`, `effort: low` or `medium`.
- **Reads broadly but only reports** → `sonnet`, `medium`. If it is *pure search*, this is
  `Explore` and not a new agent (back to Gate 1).
- **Irreversible, or asymmetric failure** — a wrong call silently destroys the user's work →
  `opus`, `high` or `xhigh`. This is the `forge-doc-planner` case. It must be **argued**, never
  assumed. Name the specific thing that gets destroyed if the agent guesses wrong.

Two standing rules:

- **Narrow the scope before upgrading the model.** A cheap model on a tight job beats `opus`
  on a vague one, and costs a fraction.
- **Restrict `tools:` to the minimum.** No `Write` if it only reports. No `Bash` unless it
  genuinely shells out.

### Gate 5 — Wiring tier is chosen deliberately

An agent isn't installed until it's reachable. See **Wiring** below. Pick the tier, apply it,
and record it in the roster row.

## Systems: folder + prefix + `system.json`

Agents belong to a **system** — a whole way of working, with its own rules, agents, skills, and
hooks. One system is active at a time; see `.claude/systems/README.md`. Today there are two:
`forge` (design docs → PRD → code → tests) and `direct` (no pipeline, no agents).

**Every agent must belong to exactly one system.** An agent belonging to none is never denied
on a swap, because the deny list is computed from the *inactive* systems — so it stays
dispatchable into a system whose rules it was never written for.

A system is not a project. The `forge` pipeline runs against whichever project `/set-project`
has made active; agents resolve their paths from that project's manifest. Never add a
per-project agent — add a project.

Each system gets all three:

- **A folder:** `.claude/agents/<system>/`
- **A name prefix:** `<system>-<artifact>-<position>`, e.g. `forge-doc-planner`
- **An entry in `.claude/systems/<system>/system.json`** under `agents[]`

The folder and prefix do different things — and this was verified empirically, not assumed:

> **Project-level agent subfolders are discovered, but they do not namespace.** The dispatch
> name comes entirely from the `name:` frontmatter field. A file at
> `.claude/agents/forge/x.md` with `name: x` is dispatched as `x`, not `forge:x`.

So the folder groups files for humans, and the prefix is the *only* thing that identifies the
system at dispatch time. Skip the prefix and agents from different systems become
indistinguishable in the registry.

Keep `name:` identical to the filename stem. That is why files look like
`forge/forge-doc-planner.md` — the stutter in the path is the cost of the name being right.

`.claude/agents/README.md` stays at the top level, but holds **doctrine only** — the roster of
who exists right now lives in each system's `SYSTEM.md`.

## Naming: planner, worker, reviewer

Every agent occupies one of three positions relative to the work. The name must say which,
because the position determines the tools and the model tier:

| Position | Runs | Holds write tools? | Suffix |
|---|---|---|---|
| **Planner** | *before* the worker | **No** | `-planner` |
| **Worker** | does the thing | Yes, for its territory only | plain noun (`forge-doc-writer`, `forge-prd-author`) |
| **Reviewer** | *after* the worker | **No** | `-reviewer`, or a precise synonym (`-auditor`, `-alignment`) |

Never name a planner "reviewer" or vice versa — the position is the single most useful thing
the name can carry. `forge-doc-planner` runs before `forge-doc-writer` and is therefore a planner, even
though what it does looks like reviewing documents.

Which position you're building changes *why* the pair exists:

- A **planner** exists because the write is destructive and needs a gatekeeper in front of it.
  The judgment lives upstream, so the worker can be cheap.
- A **reviewer** exists because an author cannot see its own assumptions. The judgment lives
  downstream, and it catches what already happened.

A job does not need all three. Most need a worker plus one of the other two. If you find
yourself wanting both a planner and a reviewer for the same job, ask whether the worker's
territory is too large (back to Gate 3).

## Writing the agent

Use `references/agent-template.md` as the skeleton. Match the house style set by
`.claude/agents/forge/forge-doc-planner.md` — it is the local exemplar, so read it when in doubt:

- `tools:` is a **comma-separated string**, not a YAML array.
- No `color:` field. `model:` is concrete (`opus`/`sonnet`/`haiku`), not `inherit`.
- `effort:` is used here (`low`/`medium`/`high`/`xhigh`) even though generic templates omit it.
- `description:` = capability sentence + explicit "Use when…" triggers + a negative boundary
  ("Does not…"). This field is the dispatch signal; write it for triggering, not for humans.

Body rules:

- Include an explicit **out-of-scope** and **never touch** list. What an agent won't do is
  as load-bearing as what it will.
- Include a **"Where to spend your thinking"** section *only* when the tier is above the cheap
  default — and use it to justify that tier by naming the hard judgment calls.
- Explain **why** rather than stacking ALL-CAPS MUSTs. A rule with a reason survives
  paraphrase; a shouted rule doesn't.
- Name the asymmetric failure mode plainly, and bias the agent toward inaction plus flagging.
- Include the **"When you can't finish"** block verbatim from `references/agent-template.md`.
  Every agent gets it — it is what makes the batch-and-resume loop work.
- Include the shared **"Project scope"** block, copied from any existing forge agent, naming
  the manifest keys this agent uses. Without it the agent has no paths at all.
- End with a named **Report back** structure — the agent's final message is its deliverable.
- **Target ≤145 lines.** That is ~120 lines of agent-specific content plus the two shared
  blocks (~11 lines of Project scope, ~10 of the batch-and-resume protocol). Judge length by
  the agent-specific part: if *that* runs past 120, the job is too big — go back to Gate 3.

## The batch-and-resume loop

A subagent cannot ask the user a question. The pipeline handles that by **batching**, not by
guessing:

1. The agent finishes everything not blocked on an answer, settles anything the spec or
   codebase already answers, and returns its genuine questions in one list.
2. The main loop answers what it can from the PRD, docs, or code — most "questions" are
   research — and puts only real intent questions to the user, batched into one ask.
3. The main loop **resumes the same agent with `SendMessage`**, which restores its transcript.
   A fresh `Agent` dispatch re-reads everything and discards the partial work; resuming does
   not.

The failure mode to design against is **over-asking**. An agent that returns questions it
could have answered by reading burns a round trip and teaches the user to skim its reports.
The line: if the spec or the code settles it, that is research — go do it. Only user *intent*
is a question.

What this does not fix: an agent that does not know it is guessing will not ask. Batching
handles known unknowns only, which is why `forge-prd-reviewer` runs before anything is built.

## Wiring — make it actually fire

A hook cannot dispatch an agent. Hooks run shell commands; the `Agent(...)` call is still made
by the main loop. What a hook *can* do is deterministically force the trigger. Three tiers:

| Tier | Mechanism | Use when | Ongoing cost |
|---|---|---|---|
| **1. On-demand** *(default)* | agent `description` + a dispatch line in the owning system's `SYSTEM.md` | It's invoked because someone asks | Zero |
| **2. Reminder** | `PostToolUse` **command** hook, tight matcher, exit 2 so stderr reaches Claude | It must fire on a condition that gets forgotten | ~Zero — shell only |
| **3. Enforcement** | `Stop` **command** hook, `decision: block` until a condition clears | Silently skipping it costs real work | ~Zero, but loop risk |

Rules that always apply:

- **Tier 1 is the default.** Escalating requires a stated reason.
- **Never use `prompt`-type hooks here.** They fire a real LLM call on every match — exactly
  the bloat this skill exists to prevent. Command hooks only.
- Every tier still needs all five base steps:
  1. File at `.claude/agents/<system>/<name>.md` with valid frontmatter.
  2. A roster row in `.claude/systems/<system>/SYSTEM.md`.
  3. **A `agents[]` entry in `.claude/systems/<system>/system.json`** — this is the wiring, not
     the documentation. Skipping it leaves the agent dispatchable after a swap.
  4. A dispatch line in that same `SYSTEM.md` with the literal
     `Agent(subagent_type: "<name>", ...)` call.
  5. Triggers stated in the agent's own `description`.
- **A hook owned by a system must self-gate.** `settings.json` does not follow `CLAUDE.md`'s
  import line, so the script derives the active system from that line itself and exits silently
  when it doesn't match. `.claude/hooks/docs-pending.sh` is the worked example. Only genuinely
  repo-level hooks (`repo-context.sh`) skip the gate.
- **Settings edits go through the `/update-config` skill**, which owns `settings.json`
  correctness. Do not hand-write the hooks block.
- **Hooks load at session start.** Any hook change needs a Claude Code restart. Say so, and
  never report a hook as working before a restart has verified it.
- **So does the agent registry.** A newly written `.claude/agents/<name>.md` is *not*
  dispatchable in the session that created it — `Agent(subagent_type: "<name>")` fails with
  "agent type not found" — and a deleted agent keeps appearing until restart. Never end a
  build by claiming the agent is live; the file is written and validated, and it becomes
  reachable on the next session. Plan the end-to-end test for after the restart, and say
  plainly that it hasn't run yet.

Read `references/wiring.md` before writing any hook — it has the recipes and the tier-3 loop
safety rules.

## Updating an existing agent

The default path when Gate 2 trips, and usually the better outcome than a new agent. Edit in
place, update the roster row in the owning system's `SYSTEM.md`, and check whether that file's
description of it has gone stale. Renaming an agent also means updating `system.json` — a stale
name there silently drops it from the deny list.

## Audit mode

When asked to review the roster rather than build: for each agent report its job, model/effort,
whether that tier is justified, overlap with others, and its wiring tier — including whether
it is reachable at all. Recommend merges and deletions. **Change nothing without confirmation.**

## Report back

- **Decision:** build / update / refuse — and which gate decided it.
- **Agent:** name, model, effort, tools, the one-sentence job.
- **Wiring:** tier chosen, why, and whether a restart is required.
- **Needs your call:** anything you couldn't settle.

Be concise. A refusal with a good alternative is a successful run.
