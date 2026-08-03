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

- **Total cost / Total tokens** — the big running totals, everything so far.
- **Cost per agent (subagents)** — a bar for each agent. *The longest bar is your most
  expensive agent.* This is the one to stare at. If `forge-prd-reviewer` has the longest bar
  every run, that's where your time and money go.
- **Tokens per agent** — same idea, but "how much did each agent read and write." A huge bar
  here usually means that agent is loading a lot of context (your growing docs).
- **Cost: subagents vs main vs auxiliary** — how much of the spend is the agents themselves
  vs the main loop.
- **Tokens by type** — input vs output vs **cacheRead**. A giant `cacheRead` slice is the
  "re-reading the same docs on every dispatch" tax we talked about.
- **Cost over time, per model** — watch this climb while a pipeline runs; the steep lines are
  your `opus` agents.

**How to actually use it:** run your pipeline once, screenshot the "Cost per agent" bars. That
is your baseline. Next week, after your docs have grown, run it again and compare. The bar that
grew the most tells you exactly which agent the scale is hurting — no guessing.

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

The magic label is **`agent_name`** with **`query_source="subagent"`** — that's what lets every
chart split things out per agent. Example query you can paste into Grafana or Prometheus:
```promql
sum by (agent_name) (claude_code_cost_usage{query_source="subagent"})
```
= "total dollars, broken down by which agent spent them."

There are also **events** (logs) with richer per-tool detail (e.g. `claude_code.tool_result`
carries `duration_ms` per tool call). This stack captures them to the collector's log
(`docker compose logs -f otel-collector`) but doesn't chart them yet — ask and we can add a
Loki + Grafana logs view.

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
