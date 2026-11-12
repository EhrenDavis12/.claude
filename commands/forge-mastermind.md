---
description: One mastermind pass over forge's queue when it has no work — tidy Blocked, then make at most one auto job that serves the user's Focus. Also how an auto job is worked
argument-hint: "(none — the runner starts it when the queue is empty and the switch is on)"
allowed-tools: Agent, Bash, Read, Grep, Glob, Skill, WebSearch, WebFetch
---

# Forge's mastermind

The arguments, if any, are: `$ARGUMENTS`

The runner starts this when forge's queue has nothing to work for the active project and the
user has switched the mastermind on. It keeps the queue moving one small step at a time while
the user is away. It **follows choices the user has already made and never makes a new one.**
This is annie's mastermind, ported; its jobs are proposals, research and look-backs, never a
build.

```
Q=.claude/systems/forge/queue/q.py
F=<docsRoot>/queue/focus.md          # resolve docsRoot from the active project's manifest
OUT=<docsRoot>/queue/reports
```

Resolve the active project and its manifest first. If none, or `$F` is missing or its Goal is
empty, make nothing, say why in one line, and write the finished mark.

`$F` is the user's Focus: the **Goal**, what matters **Right now**, what is **Not included**,
what waits for **Later**, and the topics to **Learn**. It is theirs — read it, never edit it.
Every job you make moves us toward the Goal by way of Right now.

**What to do next is reasoned, not listed.** Work out the gap between where the project is and
the Goal, and pick the step that closes the most of it. What the user has dropped, paused or
ruled out is in `$F`, memory and the queue's notes — read it there and steer clear.

## The rules

1. **Never ask the user anything, and never add to Blocked.** No `AskUserQuestion`, no
   `q.py ask`. A job that would need the user's answer is not made.
2. **Proposals, research and look-backs only.** No code, no test, no PRD, no design-doc edit,
   no branch. Reports land under `$OUT`. Building is the user's yes away: a proposal becomes
   a queue item only when the desk adds it on their word.
3. **No paid call of any kind.** A web search is fine.
4. **One job per pass.** A pass makes at most one item, `add --auto --bg`. q.py's gate holds
   the usage stop, a short cooldown and the pause while auto results wait for the user; there
   is no cap on how many jobs.
5. **Process lessons are proposed, never made.** A change to an agent, a command, the runner
   or the pipeline goes in the report under `PROPOSAL:` — never made.
6. **Never answer a taste question or an open design question** — how something should look
   or feel, or anything a design doc lists under Open Questions. Those stay open, however sure
   you are.

## A pass

1. **Know what exists — by search, not by reading the board.** Never `list` it whole:
   - `python3 $Q list --brief` — one short line per item, every state, done included;
   - `python3 $Q find <word> [<word> ...]` — searches the queue **and** the archive. Search
     for each candidate job's subject before choosing it, and read an item in full only when
     a hit could be the same work;
   - `ls $OUT`, the roadmap, and `$F`, which is short.
2. **Tidy Blocked.** `python3 $Q show <id>` each blocked item from the brief list — only
   those — and for each open question:
   - If a design doc or memory **already states** the answer, and it is neither a taste
     question nor an open one, answer it:
     `python3 $Q answer <id> <n> "Mastermind (<date>): <answer> — from <where it is said>, quoted: '<the words>'."`
     A guess, an inference, or "most likely" is not an answer; leave it open.
   - If a big blocked item has a part that does not depend on the open question, that part
     may be this pass's one job, titled `Split from #<id>: …`, as a proposal in a report — not
     a queued build.
   Then `python3 $Q list --brief`: if anything is now queued, the runner will pick it up —
   stop here.
3. **Make one job.** Pick the kind, in this order of preference:
   - **Propose** — when `$OUT` has no proposal report newer than `$F`'s Goal and Right now
     (`git log -1 --format=%ct` on each, or the report's date), or none from the last 7 days:
     the gap between the code and the Goal, as proposed queue items.
   - **Look back** — when no look-back report from the last 7 days is in `$OUT`: how the
     queue's recent items went — passes in review, blocks, takedowns, what the user rejected —
     and where the process cost more than it should have.
   - **Research** — the first Learn topic in `$F` with no report in `$OUT`.
4. **Check it before adding.** Every line must be yes, or the job is not made:
   - You searched for it (`find`, `ls $OUT`) and read every hit that could be the same work.
   - It moves us toward the Goal by way of Right now, and touches nothing in Not included or
     Later.
   - It can finish without the user's answer to anything.
   - It produces a report, not code.
   - Nothing in the queue (done included), the archive or `$OUT` already covers it. Name the
     closest existing work in the job's note and say in one clause why this is not a repeat.
   - One worker can finish it in about two hours.
5. **Add it:**
   `python3 $Q add --auto --bg "<Propose|Look back|Research> : <title>" --note "Serves: <which part of Right now>. Closest existing: <item or report> — not a repeat because <why>. Job: <what to write, where, done when>."`
   Then `python3 $Q render` and publish to the Queue page, as `SYSTEM.md` says.
6. **Report** in two lines: what was tidied, what was made (or why nothing was).

If nothing passes the check, make nothing. An empty pass is a good outcome, not a failure.

**Last step, always:** `[ -n "$FORGE_WORKER_DONE" ] && touch "$FORGE_WORKER_DONE"`

## Working an auto job

`/forge-queue` sends an item marked `auto` here instead of through the pipeline. Its note says
what to make. The rules above still hold. Note before each stage, as `/forge-queue` says — the
runner holds an auto job to its promises too.

- **Propose** — dispatch once:
  ```
  Agent(subagent_type: "forge-queue-planner", prompt: "Target: the goal in <$F>. Queue: run `python3 <$Q> list --brief` and `find` for what is held. Design docs: <docsRoot>. Source: <srcRoots>. PRDs: <prds>.")
  ```
  Write `$OUT/<date>-propose.md`: its **Proposed** rows, each on its own line as
  `PROPOSAL: <row, verbatim>`; then **Dropped**, **Already covered** and **Needs your call**
  as it gave them. A **Needs your call** that blocks the goal itself is said in the note, never
  asked.
- **Look back** — read the queue's done, dropped and blocked items (`list --brief`, `find`),
  the runner log's takedowns, and the agent metrics if the project keeps them; dispatch
  `forge-retro-planner` when the friction is in the pipeline itself. Write
  `$OUT/<date>-lookback.md`: what worked, what did not, and each fix as a `PROPOSAL:` line.
- **Research** — read the design docs and code first, then search the web for what good games
  and studios do. Write `$OUT/<topic-slug>.md`: what they do; what applies to us, given the
  Focus; the options with what each would mean for the game; then any `PROPOSAL:` lines.
  Short. Never a decision — the user makes it.

Then commit the report at the root (`git add -A <docsRoot>/queue/reports && git commit -m
"queue(<project>): <kind> report"`), `python3 $Q note <id> "<one line: what it found>"`, and
`python3 $Q move <id> review`. A job that cannot finish says why in its note and goes to
`review` too, never to `blocked`.

$ARGUMENTS
