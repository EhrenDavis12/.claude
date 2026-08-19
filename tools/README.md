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
| `dur_s` | wall-clock seconds, first message to last — **includes idle time**, so a run that sat waiting reports hours it never worked; never rank cost by it |

**How to read the bars:**
- Rank cost by `turns`, `out_tok`, and `cache_read` — never `dur_s`, which is dominated by
  idle in exactly the tail you inspect when hunting outliers. High `turns` → a slow or looping
  agent; tighten its prompt or shrink the dispatch so it converges faster.
- high `max_ctx` → an agent **drowning in context**. This is the one that grows with your SOT:
  as docs and instructions get bigger, every fresh dispatch loads more before doing any work,
  and quality degrades as the window fills. Fix by narrowing what the agent must read, not by
  making the agent smarter.
- high `cache_read`, many runs → the **per-dispatch re-read overhead** (CLAUDE.md + SYSTEM.md +
  manifest + docs, reloaded on every dispatch and every batch-and-resume round). Compounds with
  the number of round trips, which is why "more open questions" feels like "everything is slow."

### Comparing agent teams (systems)

This repo runs **one agent team (system) at a time** — forge today, a lighter team tomorrow —
swapped with `/set-system`. The metrics classify every run by the team that owns it, so you can
tell whether a swap or a tweak actually helped.

Classification is authoritative and needs no bookkeeping: each run's agent is looked up in every
`.claude/systems/<name>/system.json` `agents` list. `forge-code-writer` → `forge`; a future
`lite-builder` listed in `.claude/systems/lite/system.json` → `lite`, **automatically, with no
change to this tool**. Harness helpers (`Explore`, `Plan`, `claude-code-guide`) that belong to no
team show as `(builtin)`. Because it keys on the agent name, it is historical-proof — a run stays
correctly attributed to its team no matter which team is active when you read the report.

Every report leads with a **per-team comparison** row (runs, avg turns, output, context,
duration); the per-agent detail below it is grouped under its team. The `system` is also written
into each durable-log record, so history stays classified.

```
python3 .claude/tools/agent-metrics.py --by-system         # just the team-vs-team headline
python3 .claude/tools/agent-metrics.py --by-system --log    # over all recorded history
```

**How to actually answer "did the lighter team do better?"** Run your task under forge, then swap
to the lighter team (`/set-system`) and run the same task. `--by-system --log` now shows one row
per team: lower `avg_dur_s` / `avg_turns` / `avg_ctx` at equal or better output is the lighter
team winning. To check whether a *change to one team* improved it, compare that team's row before
and after — the log is time-ordered by `ended_ts`, so a dated baseline (below) isolates the two
periods.

### Live dashboards (OTEL)

For a live view in **real dollars** (which the transcript parser can't compute), see
`.claude/otel/` — a one-command Docker stack (OTEL Collector + agent-exporter + Prometheus +
Grafana) plus a plain-language `OTEL-ReadMe.md`. Use the transcript parser daily; reach for
Grafana when you want to *watch* a run or show a chart.

**Cost and agent identity come from different places, and only one of them knows names.** Claude
Code's own `claude_code.cost.usage` / `claude_code.token.usage` metrics report every custom
subagent as `agent_name="custom"` — the name you dispatched is never exported. They give real
dollars split by `query_source` (`main` / `auxiliary` / `subagent`) and by model, and nothing
finer.

The names live only in this tool's own output. So `.claude/otel/agent_exporter.py` serves
`agent-runs.jsonl` — the log the `SubagentStop` hook maintains — to Prometheus as
`claude_agent_*` metrics labelled by `agent` and `system`, and the "Subagent Efficiency (by
name)" dashboard is built on those. Same numbers as `--log` below, drawn instead of printed.

One caveat carried into those metrics: `dur_s` measures first message to last, so a **resumed**
agent's wall-clock includes the hours its questions sat waiting for a human answer. The exporter
splits these out (`claude_agent_worked_*` excludes them, `claude_agent_idle_suspect_runs_total`
counts them) so per-agent averages stay meaningful. `--runs` shows the same inflation here in the
terminal; read a multi-day `dur_s` as "this one was blocked," not "this one is slow."

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

**This roster does not carry `maxTurns`.** On this setup the field is a no-op — verified from
the log, where 60 runs exceeded their declared caps (one at 3.8x) and none was stopped — so an
agent file carrying it declares a guard that does not exist. Unknown frontmatter keys are
ignored silently, which is how twelve agents shipped with caps nobody had ever seen fire.

If a future CLI version honors the field, reintroduce it only from measured data: run
`agent-metrics.py --runs`, take the agent's median `turns`, set the cap ~2–3x above it, and
**verify it fires** by dispatching one deliberately over-broad task and checking the transcript
ends at the cap. Until that check passes, a runaway is bounded by a `PreToolUse` hook or a
tighter prompt, not by frontmatter.

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
