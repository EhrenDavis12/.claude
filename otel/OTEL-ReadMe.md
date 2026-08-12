# Watching your agents with OTEL — explained like you're five

You have a robot team (your agents). Right now you can't *see* how hard each robot is
working. **OTEL** is a way for the robots to shout out numbers while they work — "I used 5,000
tokens!", "I cost 2 cents!", "I took 30 seconds!" — and this folder catches those shouts and
draws them as **pictures on a webpage** so you can look.

There are three little helper programs, and they come in one box (Docker):

| Helper | Its job | Where you look |
|---|---|---|
| **Collector** | Catches the shouts from Claude Code | (you don't look here) |
| **Prometheus** | Remembers all the numbers | http://localhost:9090 |
| **Grafana** | Draws the pretty pictures | **http://localhost:3000** ← the fun one |

You need **Docker Desktop** installed and running. That's the only thing to install.

---

## Do this once each time you want to watch

### Step 1 — Turn on the catchers
Open a terminal in the repo and run:
```bash
cd .claude/otel
docker compose up -d
```
Wait ~20 seconds. Three helpers are now running. (First time, it downloads them — give it a
minute.)

### Step 2 — Tell Claude Code to start shouting
Open **another** terminal (or the same one, move back to the repo root) and run:
```bash
source .claude/otel/telemetry.env
```
That's the ON switch. It only affects **this one terminal**.

### Step 3 — Use Claude Code like normal
In that **same terminal**, start Claude:
```bash
claude
```
Do your normal work — run your pipeline, let the agents go. They're shouting numbers now.

### Step 4 — Look at the pictures
Open your web browser to **http://localhost:3000**. No password — it just opens.
On the left, click **Dashboards → "Claude Code — Agent Performance"**.

Give it 30–60 seconds after the agents run (the numbers travel every 10 seconds), then the
charts fill in.

---

## What am I looking at?

The dashboard has these pictures:

There are **two** dashboards, and the split is not cosmetic — they are fed by different
sources because no single source has everything.

### "Claude Code — Agent Performance" (live dollars, no agent names)

Fed by Claude Code's own telemetry. It knows real money, and it updates while a run is
happening. What it cannot tell you is *which* agent did anything — see the warning below.

- **Total cost / Total tokens** — the big running totals, everything so far.
- **Cost: subagents vs main vs auxiliary** — how much of the spend is delegated work versus
  the main loop. This one is genuinely useful and is the reason to keep this dashboard.
- **Tokens by type** — input vs output vs **cacheRead**. A giant `cacheRead` slice is the
  "re-reading the same docs on every dispatch" tax.
- **Cost over time, per model** — watch this climb while a pipeline runs; the steep lines are
  your `opus` agents.

> **The per-agent and per-team panels on this dashboard do not work, and cannot be made to.**
> Claude Code reports every custom subagent as `agent_name="custom"` — your agent's actual name
> is never put on the wire. So "Cost per agent" collapses to a single bar labelled `custom`, and
> the team panels find no `forge-*` prefix to split on. Use the dashboard below instead.

### "Claude Code — Subagent Efficiency (by name)" (agent names, no dollars)

Fed by `agent-exporter`, which serves the run log that the `SubagentStop` hook keeps at
`.claude/metrics/agent-runs.jsonl`. That log is the **only** place your agent names exist, so
this is the dashboard to stare at.

- **Efficiency by agent** — one row per named agent: runs, avg seconds, avg turns, avg tool
  calls, avg output tokens, peak context, avg cache re-read, and how often it got blocked.
  This is the whole diagnostic table from `.claude/tools/README.md`, live.
- **Average seconds per run** — the slow agents, ranked.
- **Peak context reached** — the agents drowning in context. This is the one that grows as your
  design docs grow; fix it by narrowing what the agent must read, not by making it smarter.
- **Blocked & resumed** — runs that sat waiting for a human answer. A high count on one agent
  means it keeps returning questions it could have answered by reading.

It has no dollar figures: the run log records tokens, not prices. Read cost from the first
dashboard and attribution from this one.

**How to actually use it:** screenshot "Efficiency by agent" now — that is your baseline. After
your docs grow, compare. The agent whose peak context and avg turns grew most is the one the
scale is hurting, by name, with no guessing.

---

## Turning it OFF

**The numbers switch (per terminal):**
- Easiest: just **close that terminal** (or open a new one and don't `source` the env file).
- Or, in the same terminal: `source .claude/otel/telemetry-off.sh`

**The helper programs:**
```bash
cd .claude/otel
docker compose down
```
This stops all three. Your saved numbers go away too (that's fine — this is for live watching;
the `.claude/tools/agent-metrics.py` log is what keeps long-term history).

To pause without losing data: `docker compose stop` (and `docker compose start` to resume).

---

## When the pictures are empty

Almost always one of these, in order:

1. **You didn't `source` the env file in the same terminal you ran `claude` from.** This is
   the #1 cause. The ON switch only affects the terminal you flipped it in.
2. **Not enough time passed.** Numbers travel every 10 seconds; the agents also have to
   actually *do* something first. Run a real task, wait a minute.
3. **The helpers aren't up.** Run `docker compose ps` in `.claude/otel` — all three should say
   "running".
4. **Check Claude Code is really shouting:** start it with `claude --debug` and look for OTEL
   export lines (or errors).
5. **Check the numbers arrived:** open http://localhost:9090, type `claude_code` in the box, and
   press enter. If names pop up, the data is flowing and the problem is only in Grafana. If
   nothing pops up, the problem is upstream (steps 1–4).

---

## The exact numbers Claude Code sends (for the curious)

Metrics (these become the charts). Names are lowercased with underscores:

| Metric | What it is | Useful labels |
|---|---|---|
| `claude_code_cost_usage` | dollars spent | `agent_name`, `query_source`, `model`, `effort` |
| `claude_code_token_usage` | tokens used | `type` (input/output/cacheRead/cacheCreation), `agent_name`, `query_source`, `model` |
| `claude_code_session_count` | sessions started | `start_type` |
| `claude_code_active_time_total` | seconds of active work | |
| `claude_code_commit_count` | git commits made | |

**`agent_name` is a trap.** It sounds like it holds your agent's name and it does not — every
custom subagent reports as the literal string `custom`, because agent names are user-authored
text that Claude Code deliberately does not export. So this query returns exactly one bar:
```promql
sum by (agent_name) (claude_code_cost_usage{query_source="subagent"})   # -> {agent_name="custom"}
```
What `query_source` *does* give you honestly is the three-way split — `main`, `auxiliary`,
`subagent` — which is worth charting:
```promql
sum by (query_source) (claude_code_cost_usage)
```

For anything per-agent, use the `claude_agent_*` metrics from `agent-exporter` instead:
```promql
claude_agent_worked_duration_seconds_total / claude_agent_worked_runs_total   # avg s/run, by name
sort_desc(claude_agent_max_context_tokens)                                    # who is drowning in context
```

**A note on metric names.** The collector must set `translation_strategy:
UnderscoreEscapingWithoutSuffixes` for these names to come out as written. The older
`add_metric_suffixes: false` key is silently ignored from collector 0.15x on — no error, no
warning — and everything arrives as `claude_code_token_usage_tokens_total` instead, leaving
every panel empty. If the dashboards go blank after a collector upgrade, check that first.

There are also **events** (logs) with richer per-tool detail (e.g. `claude_code.tool_result`
carries `duration_ms` per tool call, and `claude_code.subagent_completed` carries tokens and
duration per dispatch — though again without the agent's name). This stack captures them to the
collector's log (`docker compose logs -f otel-collector`) but doesn't chart them yet — ask and
we can add a Loki + Grafana logs view.

---

## OTEL vs the other tool (`agent-metrics.py`)

You have **two** ways to see agent performance, and they're friends:

- **`agent-metrics.py`** (in `.claude/tools/`) — no setup, reads Claude Code's own transcript
  files. Great for a quick table in the terminal and for **permanent history** (the
  SubagentStop hook saves every run forever). Use this daily.
- **OTEL + Grafana** (this folder) — needs Docker running, but gives **live pictures** and
  splits **cost in real dollars** per agent/model. Use this when you want to *watch* a run or
  show someone a chart.

Same story, two windows. Start with `agent-metrics.py`; reach for OTEL when you want the
dashboard.
