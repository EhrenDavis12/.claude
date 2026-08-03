# Measuring & debugging agent performance

Tooling and method for answering: *are my agents still effective, where is the pipeline
slowing down, and is the cause the code, the SOT, or the agents themselves?*

This lives under `.claude/` because it is about the agent **system**, not any project's
design docs. It is system-agnostic — it works for forge, direct, or whatever comes next.

## The tool: `agent-metrics.py`

Claude Code already writes a full JSONL transcript for every subagent run to
`~/.claude/projects/<encoded-cwd>/<session>/subagents/agent-*.jsonl`. Nothing to enable.
The script mines those transcripts and reports, **per agent type**, the numbers that actually
explain a slowdown:

```
python3 .claude/tools/agent-metrics.py            # per-agent averages, this repo
python3 .claude/tools/agent-metrics.py --runs     # every individual run, slowest first
python3 .claude/tools/agent-metrics.py --json     # machine-readable, for trend tracking
python3 .claude/tools/agent-metrics.py --log      # report from the durable history log
python3 .claude/tools/agent-metrics.py --sync     # fold current runs into that log (hooks call this)
```

### Durable history (survives transcript pruning)

Claude Code prunes raw transcripts after ~30 days, which would erase your history. The
`SubagentStop`/`Stop` hook `.claude/hooks/capture-agent-metrics.sh` runs `--sync` automatically
after every agent, folding each run into `.claude/metrics/agent-runs.jsonl` (git-ignored,
per-machine). The sync is idempotent and self-healing — a run captured mid-flight is overwritten
by its final numbers on the next sync. Read that long-term history any time with `--log`. If you
want cross-machine history, commit the log yourself; by default it stays local.

| Column | Reads as |
|---|---|
| `turns` | assistant API requests — the length of the agent's agentic loop |
| `tool_calls` | tool invocations (Read/Grep/Bash…) |
| `out_tok` | output tokens — how much the agent generated |
| `max_ctx` | largest context window it reached (input + cache_read + cache_creation) |
| `cache_read` | cached input re-read — the fixed re-read tax of starting fresh each dispatch |
| `dur_s` | wall-clock seconds, first message to last |

**How to read the bars:**
- high `dur_s` + high `turns` → a **slow or looping** agent. Cap it (see `maxTurns`) and/or
  tighten its prompt so it converges faster.
- high `max_ctx` → an agent **drowning in context**. This is the one that grows with your SOT:
  as docs and instructions get bigger, every fresh dispatch loads more before doing any work,
  and quality degrades as the window fills. Fix by narrowing what the agent must read, not by
  making the agent smarter.
- high `cache_read`, many runs → the **per-dispatch re-read overhead** (CLAUDE.md + SYSTEM.md +
  manifest + docs, reloaded on every dispatch and every batch-and-resume round). Compounds with
  the number of round trips, which is why "more open questions" feels like "everything is slow."

### Live dollar-cost dashboard (OTEL)

For a live, per-agent view in **real dollars** (which the transcript parser can't compute), see
`.claude/otel/` — a one-command Docker stack (OTEL Collector + Prometheus + Grafana) plus a
plain-language `OTEL-ReadMe.md`. Claude Code's `claude_code.cost.usage` and
`claude_code.token.usage` metrics carry `agent.name` and `query_source=subagent` attributes, so
the dashboard splits cost and tokens per agent natively. Use the transcript parser daily; reach
for OTEL when you want to *watch* a run or show a chart.

## The method: is it the code, the SOT, or the agents?

Measure before you theorize. The three suspects leave different fingerprints:

1. **The SOT (docs/spec).** Fingerprint: `max_ctx` and `cache_read` climb over time across
   *every* agent, and the read-heavy agents (`forge-doc-planner`, `forge-prd-author`,
   `forge-prd-reviewer`) climb fastest. Diagnosis: the spec got big enough that loading it is
   the job. Also shows up as **round trips** — an ambiguous or contradictory SOT makes agents
   return questions, and each batch-and-resume round pays the whole re-read tax again.

2. **The agents (prompts/wiring).** Fingerprint: one agent has high `turns`/`dur_s` while its
   peers are flat, or its `out_tok` is huge relative to what it produces. Diagnosis: that
   agent's prompt lets it wander, re-derive, or over-explore. This is a per-agent fix.

3. **The code.** Fingerprint: only the code agents (`forge-code-writer`, `-cleaner`,
   `-reviewer`) are slow, and their `tool_calls`/`max_ctx` scale with the size of the source
   tree they grep. (Today the tic-tac-toe submodule is ~empty, so this is *not* your current
   cause — which is itself a useful finding: a doc-heavy slowdown is a SOT or agent problem,
   not a code problem.)

### Establish a baseline, then watch the trend

A single number means nothing; the trend is the signal. Capture a snapshot now and re-capture
after the SOT grows or a prompt changes:

```
python3 .claude/tools/agent-metrics.py --json > .claude/tools/baseline-$(date +%F).json
```

Diff two snapshots to see which agent regressed and by how much. That converts "it feels
slower" into "`forge-prd-reviewer` went from 14 to 31 turns and 40k to 95k `max_ctx` after the
Theming doc doubled."

## Where this structure breaks down (the scaling story)

The forge pipeline is a **serial chain of fresh-context agents**. Two costs grow with scale:

- **Per-dispatch fixed cost** — every agent reloads CLAUDE.md + SYSTEM.md + manifest + its
  slice of the SOT before it works. This grows with your *instructions and docs*, and it is
  paid N times per pipeline run (once per agent) and again on every resume.
- **Serial latency** — several stages are opus/high and run one after another. Wall-clock is
  the *sum*, and opus/high is the slowest per-turn tier.

The knee is reached when fixed re-read cost per agent starts to rival the actual work, and/or
when the number of round trips (driven by SOT ambiguity) multiplies that fixed cost. Levers,
cheapest first:
1. **Cut round trips** — tighten the SOT so agents stop returning answerable questions. Biggest
   win, because each avoided round is a whole pipeline's worth of re-reads saved.
2. **Right-size the tier** — every opus/high agent is a deliberate latency choice. Re-justify
   each one against measured `dur_s`; drop a reviewer to sonnet if data shows it doesn't need
   opus.
3. **Narrow what each agent reads** — pass the specific doc/PRD paths in the dispatch so the
   agent greps less.
4. **Parallelize independent stages** — dispatch agents with no data dependency in one message.

## Bounding a runaway agent: `maxTurns`

`maxTurns` in an agent's frontmatter caps how many agentic turns it may take before Claude Code
stops it. It is a **safety guardrail against a looping agent, not a speed-up** — it makes a
runaway *fail fast and visibly* instead of silently burning turns. It will not make a
well-behaved agent finish sooner.

```yaml
---
name: forge-doc-planner
model: opus
effort: high
maxTurns: 50      # catches a runaway; a normal plan runs well under this
---
```

Set the cap from measured data: run `agent-metrics.py --runs`, take an agent's normal `turns`,
and set `maxTurns` comfortably above it (e.g. ~2–3x). Too low and you kill real work mid-run.

**Verify it's live on your CLI version:** unknown frontmatter keys are ignored silently, so a
no-op is possible. Confirm by dispatching the agent against a deliberately over-broad task and
checking whether it stops at the cap (its transcript ends at `maxTurns` assistant turns). If it
doesn't, your version predates the field — use a `PreToolUse` hook or a tighter prompt instead.

## Making agent communication reliable

In forge, agents don't talk to each other — the **main loop** is the bus. "Unreliable
communication" is almost always the main loop passing thin context on dispatch, or losing an
agent's partial work on resume. Concrete fixes:

1. **Dispatch with resolved paths, not descriptions.** State the exact manifest-resolved paths
   (docs, PRD, srcRoot) in the prompt. The agent reads the manifest itself, but handing it the
   paths saves a round trip and removes a guess. (SYSTEM.md already says to do this — the
   metrics tool shows the cost when it's skipped: extra `tool_calls` spent re-discovering paths.)
2. **Resume, never re-dispatch, to continue blocked work.** A returning agent's questions get
   answered and it continues via `SendMessage(to: "<agent-name>", …)`, which restores its
   transcript and partial work. A fresh `Agent` call re-reads everything and throws the partial
   result away — you pay the full re-read tax twice. (CLAUDE.md's batch-and-resume rule.)
3. **Answer what you can before asking the user.** Most returned "questions" are research the
   main loop should do from the spec/code. Over-asking is the expensive failure mode.
4. **Make hand-offs structured.** A planner that hands the writer a precise, itemized list (not
   prose) makes the writer's job deterministic and its run shorter — visible as lower `turns`
   on the downstream agent.
