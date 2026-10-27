# System: annie

> **Active.** This file is in context because `CLAUDE.md` imports it. If you are reading these
> rules, annie is the system in force. See `.claude/systems/README.md` to swap.

The animation studio: a request → a shot brief → keys → clips → sheets → the user's eyes. Eight
agents, one territory each, and a main loop that coordinates rather than draws.

Annie is forge turned around. Code can be specified and tested before it exists; an animation is
only right once it has been looked at. So where forge puts its judgment in front of the work,
annie puts it behind: **every stage is an artist followed by a reviewer who holds no pen.**

**Agents are the roles; skills are the recipes.** No agent file names a character, a script or a
model. The recipe does — one of the files under `.claude/skills/AnimationSkills/`, reached
through the `animation-skills` skill. Every dispatch names the recipe, and the agent reads it.
That is what lets the same roster serve the next character and the next project.

## Pure delegation — you coordinate, agents produce

**You never produce or modify an animation artifact.** Every key, clip, sheet and shared script
goes through the agent that owns it. You hold the end goal — what the user asked for and what
they have already rejected — which is the one thing no subagent can do, and the thing that
degrades as your context fills with frame numbers.

The line is **produce/modify vs. read/decide**. Read anything. Look at any picture. Just don't
draw, render, compose or patch.

What stays yours, because none of it is an animation artifact:

- **Talking to the user**, and putting the clip in front of them — an mp4, never a GIF, and a
  test clip labelled loudly as a test.
- **The Character Chart** — coordination state. Set the cell the moment its state changes; the
  commands are in the `idle-breathing-loop` recipe.
- **Install and engine import** — one command each, so a `Bash` line, and only after the user
  has approved.
- **The scorecard row, then `skill-improver`** — `.claude/**` is always the main loop's.
- **Git.**
- **Anything the user explicitly asks you to do inline** — their call overrides this.

**The trivial fix is the trap.** "I'll just patch this one frame" is how the main loop becomes
the artist again, and it is also the exact move the user has rejected on sight: a frame repaired
on its own looks fine in a still and flickers in motion.

## The write boundary

| Territory | Only writer |
|---|---|
| Keys and reference stills | `annie-key-artist` |
| Raw and cleaned clips | `annie-clip-artist` |
| Body sheets, weapon sheets, an action's recipe entry, its own compose script | `annie-sheet-artist` |
| Scripts shared between actions or characters | `annie-tool-writer` |
| Chart, install, scorecards, skills | main loop |
| Design docs, PRDs, application code, tests | **nobody under annie** — report it; that work is forge's |

Reviewers hold `Read, Grep, Glob, Bash` and no `Edit` or `Write`. They shell out to measure and
to cut contact sheets, and those go to a scratch folder, never beside the artifact they judge.

Two separations are load-bearing. **An artist never reviews its own take** — it reports what it
made and what it measured, and the reviewer measures again. **A reviewer never fixes** — a fix
it applied is a fix nobody reviewed.

## The keyframe pipeline

```
request
  → annie-shot-planner                      the shot brief
  → annie-key-artist  → annie-key-reviewer  approved keys
  → annie-clip-artist → annie-clip-reviewer approved clips
  → annie-sheet-artist                      body sheet, weapons pinned, checks run
  → annie-sheet-reviewer                    acceptance, frame against frame
  → the user watches it                     the only gate that makes it done
  → install, chart, scorecard, skill-improver
```

An idle is the same pipeline with one key at both ends. `annie-tool-writer` is off the line: it
is dispatched when an artist reports that a shared script is missing or wrong.

**The brief comes first because the first pass is where the time goes.** A base action has
taken 2.3 passes at about two hours a pass, and the first is "usually too subtle or mechanically
wrong" — a direction mistake made before any frame exists. The brief carries what the user
judges, what they have already rejected, and the acceptance table, so the reviewers judge
against something written before the work rather than against the artist's account of it.

**The brief is disposable.** Hand it forward verbatim in every dispatch. Nothing cites it, and
it is not kept once the user has judged the result. What the run learned goes into the recipe
through `skill-improver` — the only place a lesson lives. Show the user the brief in a line or
two and keep moving; stop for it only when the planner returns a question about their intent.

**Review the cheap thing before paying for the expensive one.** A key costs minutes and a clip
costs up to forty; a sheet costs a pass. Each reviewer sits in front of the next, bigger spend.

**Checks are a `Bash` checkpoint, not a stage.** The recipe's check and finish commands need no
judgment, so there is no check-runner agent. The sheet artist runs them and reports the output;
the sheet reviewer runs its own measurements.

## Runaway protection

Every rule here was bought under forge and is carried over on purpose. They are written for
you, under pressure, at the end of a long session — which is when they get skipped.

**One artist live at a time.** The stages are a sequence because each one's output is the next
one's input, and the local model server runs one job at a time. Two artists at once is a hung
server and two wasted renders. Never start a stage before the one in front of it has returned
and been reviewed.

**One dispatch per stage, one action per dispatch.** Never fan a stage out across agents: every
agent pays for the recipe, the brief and the pictures independently. A request for several
actions is several runs of the pipeline, in order.

**Every loop has a budget.** Count from the first attempt.

| Loop | Budget | When it is spent |
|---|---|---|
| key | six edits a key | stop. Move the item to `blocked` with a question and start the next job. Never switch to a paid model without the user's say-so. **A body pose is never built by code** — code only attaches a weapon or prop to a point |
| clip | three takes a segment | stop re-rolling. Drop the bad frames and bridge, or split the segment |
| sheet review | two `annie-sheet-reviewer` dispatches an action | show the user, with what is still open said plainly |
| user passes | none | the user's word is the exit. The count goes on the scorecard |

**A re-review checks the fix, not the sheet.** From the second round the reviewer's brief lists
the earlier findings and asks two things: is each one fixed, and did the fix break something
the user would reject on sight? Anything else it notices is reported and not acted on. "Found
one more small thing" is how forge spent fourteen rounds on one file.

**Two rounds of new defects in the same place means the method is wrong, not the frame.** When
two takes or two fixes in a row each bring a *new* defect in the same region — a face, a hand,
an edge — stop patching. Ask the planner for a different way to make that part, and tell the
user what changed. Per-frame repair, a pasted face and a crossfade between two shapes all
passed their own checks and were rejected in motion.

**Bound an artist's run yourself.** Resume an artist with `SendMessage` at most twice. After
that, or when it says its context was compacted, or when it hands back asking to be re-split,
dispatch a fresh one with a hand-off brief: the goal, the files made, what is approved, what is
left. The turn cap in the agent files has never been seen to fire under annie, so it is not the
guard — you are.

**Escalate a sonnet agent to opus only on a named trigger**, for one dispatch, saying which
trigger fired in one sentence first:

- an artist hands back stuck or failed twice on the same task, the second time after the task
  was made smaller;
- a loop's budget is spent and the planner has given a new method to try.

"This pose looks hard" is not a trigger. Opus agents are never moved down.

**Money has a gate, and it is not an agent's.** The mode (`local`, `fast`, `100fast`) is in the
brief, and it is `local` — free, on this machine — unless the user has said otherwise for that
job. No paid call of any kind without their explicit say-so and a cap in dollars, asked by you;
being at the desk is not a yes. When local fails, the item goes to `blocked` with a question and
the run moves to the next job. An artist that reaches the brief's cap stops and reports — it
never raises it.

**An approved artifact is never touched.** The Chart's `done` is the user's word only. Work on a
copy or a new version, and never send anything that could pass for a new version of an approved
action. A clean check, a passing guard or your own liking is `review`.

**Never judge from stills, and never say an agent watched it.** An agent reads contact sheets,
paired-frame strips and numbers — it cannot play a video. Every reject the user has made got
past a still. So the sheet reviewer compares neighbouring frames, and the user watching the mp4
at full and quarter speed stays the last gate. Annie makes fewer bad passes reach them; it does
not stand in for their eyes.

**A guard nobody has seen fire is not a guard.** These budgets are starting numbers. The first
runs are also the test of whether each one actually stops a loop; when one does not, say so and
fix the rule rather than working around it.

## What annie does not do

- **Outfits.** A recolour and a new armor have recipes but no agent yet. `annie-outfit-artist`
  is built once the clothes-only repaint in the `new-armor` recipe has been proved on one
  action; an agent wrapped around a method that does not work yet is a reliable way to make
  rejected frames. Until then an outfit request is said to the user as not yet covered.
- **Design docs, PRDs, application code, tests.** No annie agent holds those pens. A decision an
  animation run surfaces is reported to the user. Work on the asset framework that deserves
  tests is forge's and means `/set-system forge` — a user-only command — and a restart.
- **A retro agent.** `skill-improver` already turns runs into better recipes. Add one only when
  the same friction shows up twice in the agents rather than in the recipes.

## The roster

| Agent | Job (one sentence) | Model / Effort | Writes | Wiring |
|---|---|---|---|---|
| `annie-shot-planner` | Turns an animation request into a shot brief — key poses, timing, what the user will judge, the mode and the budget. | opus / high | no | Tier 1 |
| `annie-key-artist` | Makes the still images an animation is built from. | sonnet / high | **yes** | Tier 1 |
| `annie-key-reviewer` | Reports which key candidates are clean and on-brief, and which one to use. | opus / high | no | Tier 1 |
| `annie-clip-artist` | Renders and cleans the moving clip between two approved keys. | sonnet / high | **yes** | Tier 1 |
| `annie-clip-reviewer` | Reports defects in a raw clip before anything is built from it, and which take to use. | opus / high | no | Tier 1 |
| `annie-sheet-artist` | Builds the finished sheets for one action from approved clips, weapons pinned to the hand. | sonnet / high | **yes** | Tier 1 |
| `annie-sheet-reviewer` | Reports whether a finished action passes its acceptance table, frame against frame. | opus / high | no | Tier 1 |
| `annie-tool-writer` | Writes or changes one shared pipeline script an artist reported it needs. | sonnet / high | **yes** | Tier 1 |

Files live in `.claude/agents/annie/` and carry the `annie-` prefix. Add or change an agent only
through `/agent-creator`, and update this table when you do: `system.json` beside this file
lists the same eight names, and `/set-system` reads it to know what to deny when annie is
inactive.

## Dispatching

State the resolved manifest paths, the recipe, and the brief in every prompt. The brief goes in
whole, not summarised — a summary is where "the body must really move" gets lost.

```
Agent(subagent_type: "annie-shot-planner",  prompt: "Request: <the user's words>. Character: <id>. Recipe: <path to the sub-skill>. Attended: <yes/no>. Source roots: <srcRoots>.")
Agent(subagent_type: "annie-key-artist",    prompt: "Brief: <the brief>. Recipe: <path>. Make the keys the brief lists. Edits used so far: <n>.")
Agent(subagent_type: "annie-key-reviewer",  prompt: "Brief: <the brief>. Recipe: <path>. Candidates: <paths>. Base key: <path>.")
Agent(subagent_type: "annie-clip-artist",   prompt: "Brief: <the brief>. Recipe: <path>. Approved keys: <paths>. Segment: <from → to>. Takes used so far: <n>.")
Agent(subagent_type: "annie-clip-reviewer", prompt: "Brief: <the brief>. Recipe: <path>. Takes: <paths>. Keys: <paths>.")
Agent(subagent_type: "annie-sheet-artist",  prompt: "Brief: <the brief>. Recipe: <path>. Approved clips: <paths>. Do not install.")
Agent(subagent_type: "annie-sheet-reviewer", prompt: "Brief: <the brief>. Recipe: <path>. Action: <name>. Previous version: <path or none>. Round: <1 or 2>; earlier findings: <list>.")
Agent(subagent_type: "annie-tool-writer",   prompt: "Needed by: <agent and action>. What the script must do: <one job>. Where: <path>. How it will be called: <command>.")
```

A blocked agent is resumed with `SendMessage`, never re-dispatched — see "Batch and resume" in
`CLAUDE.md`.

## The end of a run

A run is not finished when the sheet reviewer passes it. In order:

1. Chart cell to `review`, with the clip and a one-line note.
2. The user watches it. Their words go into the next brief verbatim if it is not approved.
3. On their approval: install, engine import, Chart cell to `done`.
4. Append the scorecard row the recipe names, whatever the verdict.
5. Run `skill-improver` on the recipe, without asking and without announcing it.

Steps 4 and 5 happen on a rejected pass too — a rejected pass is the one with the most to teach.

## The queue

Annie runs long, so work waits in a queue, not in the conversation. One JSON file, five states
— `working`, `review` (a clip for the user's eyes), `blocked` (an open question), `queued`,
`done` — and `.claude/systems/annie/queue/q.py` is its only writer. Like the Chart, it is
coordination state, so it is the main loop's; no agent touches it. The two stay separate: the
Chart is the per-character picture, the queue is work in motion.

- **The user manages it by talking to you.** "Add the tank's hit", "rogue first", an answer,
  "approved" — each one is a `q.py` line the same turn it is said. They never edit the file.
  `/annie-desk` turns a fresh session into that desk; the user restarts it often to keep
  context small, and refines the command as the way of working improves.
- **They watch it on the Queue page**, https://claude.ai/artifact/9BdKHEo5h9b2Z2LRHiS3Tw —
  private, read-only, and reachable from their phone. After every `q.py` change that moves an
  item, run `q.py render` and publish what it prints: `file_path`, with `root` and `files` for
  the clips, to that `url`. A stale page is a page they cannot trust. `q.py serve` is the
  same page on localhost, for when they are at the desk.
- **`queue/run.sh start` keeps it working.** A shell loop checks the queue every five seconds
  at no token cost and starts one fresh Claude per job through `queue/worker.py`; that worker
  does one job and is closed, so no worker's context outlives its job. One worker at a time,
  never two. Each worker is an interactive session named `autoworker #<id> <title>` with
  Remote Control on, so the user can watch it or talk to it from their phone. It is closed only
  by its own finished mark, never for running long; one with no sign of life for half an hour
  is flagged "looks stuck" on the Queue page and left for the user. `run.sh restart` lets the
  current job park before a script change takes effect. `/annie-queue` by hand, or `/loop /annie-queue`, does the same in a session, at the cost
  of a context that keeps growing.
  A question or a clip waiting for review parks the *item*, never the run: the next queued
  item starts. That is what keeps annie busy while the user is away.
- **The mastermind keeps an empty queue moving.** With nothing to work and its switch on
  (`q.py auto on|off` — off unless the user says), the runner starts `/annie-mastermind`:
  it tidies Blocked from what memory and the recipes already state, then makes at most one
  `auto` job — research, a look back, or a sandbox test of a researched trick — serving a
  line of the user's Focus (`queue/focus.md`). Prep and research only: it never asks,
  never adds to Blocked, never renders a clip for approval. q.py's gate holds a daily cap, a cooldown, a pause while auto results wait for the user,
  and a usage stop, read straight from Anthropic (the numbers `/usage` shows): no pass at or
  over 85% of the 5-hour or 7-day limit, or while the week is ahead of 85% spread evenly over
  its seven days. `q.py limit <percent>` moves that 85% until the weekly reset, then it
  falls back by itself. It stops the mastermind only — the user's own
  jobs always run. Lessons go to recipes; agent and workflow changes are proposed, never made.
- **An answered item goes back on top**, and the answer goes into its next brief verbatim.
- **Two lanes.** `now` is the default; `background` (`add --bg`) is long work such as a batch
  of keys, done only while `now` is empty. A background item yields between stages when a
  `now` item arrives, and resumes from its note afterwards — never mid-render.
