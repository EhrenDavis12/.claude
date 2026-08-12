#!/usr/bin/env python3
"""Prometheus exporter for per-agent run history.

Claude Code's own OTEL export reports every custom subagent as agent_name="custom" —
the name you actually dispatched is never on the wire. The names live only in
.claude/metrics/agent-runs.jsonl, which the SubagentStop hook keeps up to date by
mining subagent transcripts. This serves that file as Prometheus metrics so the
per-agent view can exist at all.

Stateless by design: every scrape recomputes totals from the whole log. The log is
append-only, so the counters come out monotonic without this process remembering
anything — which means it can restart, or lose its disk, without corrupting a series.

  METRICS_FILE  path to agent-runs.jsonl   (default /data/agent-runs.jsonl)
  PORT          listen port                (default 9101)
  SUSPECT_DURATION_SECONDS  idle-inflation cutoff (default 3600)
  AGENTS_DIR    agent definitions, for the model tier  (default /agents)
  PRICES_FILE   rates in USD per million tokens        (default /prices.json)

A note on duration. The log records wall-clock from an agent's first message to its
last, which for a *resumed* agent spans the hours or days its questions sat waiting
for a human answer. Those runs read as ~4 days of "runtime" against a median of ~4
minutes. So duration is exported twice: `duration_seconds_total` keeps every run
honestly, and `worked_duration_seconds_total` drops runs past the cutoff so the
per-agent averages mean something. The dropped ones stay visible and countable in
`idle_suspect_runs_total` rather than disappearing.
"""
import glob
import json
import os
import re
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

METRICS_FILE = os.environ.get("METRICS_FILE", "/data/agent-runs.jsonl")
PORT = int(os.environ.get("PORT", "9101"))
SUSPECT_DURATION = float(os.environ.get("SUSPECT_DURATION_SECONDS", "3600"))
AGENTS_DIR = os.environ.get("AGENTS_DIR", "/agents")
PRICES_FILE = os.environ.get("PRICES_FILE", "/prices.json")

# Counters are summed over all history; gauges describe the latest/extreme run.
COUNTERS = [
    ("claude_agent_runs_total", "Completed subagent runs", None),
    ("claude_agent_worked_runs_total", "Runs excluding resume-inflated ones", None),
    ("claude_agent_idle_suspect_runs_total", "Runs dropped as resume-inflated", None),
    ("claude_agent_duration_seconds_total", "Total wall-clock seconds, every run", "dur_s"),
    ("claude_agent_worked_duration_seconds_total", "Wall-clock seconds, resume-inflated runs excluded", None),
    ("claude_agent_turns_total", "Total assistant turns (agentic loop length)", "turns"),
    ("claude_agent_tool_calls_total", "Total tool invocations", "tool_calls"),
    ("claude_agent_output_tokens_total", "Total output tokens generated", "out_tok"),
    ("claude_agent_cache_read_tokens_total", "Total cached input re-read (dispatch tax)", "cache_read"),
]
GAUGES = [
    ("claude_agent_max_context_tokens", "Largest context window ever reached", "max_ctx"),
    ("claude_agent_last_duration_seconds", "Wall-clock seconds of the most recent run", "dur_s"),
    ("claude_agent_last_run_timestamp_seconds", "Unix time the most recent run ended", "ended_ts"),
]

_LABEL_ESCAPE = re.compile(r'([\\"\n])')


def _esc(value):
    """Escape a Prometheus label value: backslash, quote, newline."""
    return _LABEL_ESCAPE.sub(
        lambda m: {"\\": r"\\", '"': r"\"", "\n": r"\n"}[m.group(1)], str(value)
    )


def _labels(pairs):
    return ",".join(f'{k}="{_esc(v)}"' for k, v in pairs)


_FRONTMATTER_KEY = re.compile(r"^(name|model)\s*:\s*(.+?)\s*$")


def agent_models():
    """Map agent name -> model tier, read from each agent's own frontmatter.

    The tier is never guessed: an agent whose definition we can't read is left
    out, counted as unpriced, and kept out of the cost totals. That keeps a
    missing definition visible as a gap rather than as a plausible wrong number.
    """
    models = {}
    for path in glob.glob(os.path.join(AGENTS_DIR, "**", "*.md"), recursive=True):
        try:
            with open(path, "r", errors="replace") as fh:
                if fh.readline().strip() != "---":
                    continue  # no frontmatter block
                name = model = None
                for line in fh:
                    if line.strip() == "---":
                        break
                    match = _FRONTMATTER_KEY.match(line)
                    if match:
                        key, value = match.group(1), match.group(2).strip().strip("\"'")
                        if key == "name":
                            name = value
                        else:
                            model = value
        except OSError:
            continue
        if name and model:
            models[name] = model.lower()
    return models


def prices():
    """Rates in USD per million tokens, plus the cache-read discount."""
    try:
        with open(PRICES_FILE, "r", errors="replace") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError):
        return {}, 0.1
    table = cfg.get("prices_usd_per_mtok")
    if not isinstance(table, dict):
        return {}, 0.1
    try:
        multiplier = float(cfg.get("cache_read_multiplier", 0.1))
    except (TypeError, ValueError):
        multiplier = 0.1
    return table, multiplier


def collect():
    """Read the log and fold it into per-(agent, system) aggregates."""
    totals = defaultdict(lambda: defaultdict(float))
    latest = {}
    per_tool = defaultdict(float)
    records = 0
    malformed = 0

    try:
        with open(METRICS_FILE, "r", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    malformed += 1
                    continue
                if not isinstance(rec, dict):
                    malformed += 1
                    continue

                records += 1
                key = (rec.get("agent") or "unknown", rec.get("system") or "(unknown)")

                totals[key]["claude_agent_runs_total"] += 1
                for name, _, field in ((c[0], None, c[2]) for c in COUNTERS if c[2]):
                    try:
                        totals[key][name] += float(rec.get(field) or 0)
                    except (TypeError, ValueError):
                        pass

                # A resumed agent's transcript spans the wait for a human answer, so
                # its wall-clock is not runtime. Keep those runs counted, but out of
                # the series the averages are built from.
                try:
                    dur = float(rec.get("dur_s") or 0)
                except (TypeError, ValueError):
                    dur = 0.0
                if dur >= SUSPECT_DURATION:
                    totals[key]["claude_agent_idle_suspect_runs_total"] += 1
                else:
                    totals[key]["claude_agent_worked_runs_total"] += 1
                    totals[key]["claude_agent_worked_duration_seconds_total"] += dur

                # max_ctx is a high-water mark, not a sum.
                try:
                    ctx = float(rec.get("max_ctx") or 0)
                    totals[key]["_max_ctx"] = max(totals[key].get("_max_ctx", 0), ctx)
                except (TypeError, ValueError):
                    pass

                tools = rec.get("tools")
                if isinstance(tools, dict):
                    for tool, count in tools.items():
                        try:
                            per_tool[(key[0], key[1], str(tool))] += float(count or 0)
                        except (TypeError, ValueError):
                            pass

                try:
                    ended = float(rec.get("ended_ts") or 0)
                except (TypeError, ValueError):
                    ended = 0.0
                if key not in latest or ended >= latest[key][0]:
                    latest[key] = (ended, rec)

    except FileNotFoundError:
        pass

    return totals, latest, per_tool, records, malformed


def render():
    totals, latest, per_tool, records, malformed = collect()
    out = []

    for name, help_text, _ in COUNTERS:
        out.append(f"# HELP {name} {help_text}")
        out.append(f"# TYPE {name} counter")
        for (agent, system), vals in sorted(totals.items()):
            labels = _labels([("agent", agent), ("system", system)])
            out.append(f"{name}{{{labels}}} {vals.get(name, 0):g}")

    out.append("# HELP claude_agent_tool_calls_by_tool_total Tool invocations by tool name")
    out.append("# TYPE claude_agent_tool_calls_by_tool_total counter")
    for (agent, system, tool), count in sorted(per_tool.items()):
        labels = _labels([("agent", agent), ("system", system), ("tool", tool)])
        out.append(f"claude_agent_tool_calls_by_tool_total{{{labels}}} {count:g}")

    # Estimated cost. The run log carries output tokens and cached-input re-read
    # but not fresh input or cache-creation, so this is a floor on real spend —
    # good for ranking agents against each other, not for reconciling a bill.
    table, cache_multiplier = prices()
    models = agent_models()
    costs = {}
    unpriced = {}
    for (agent, system), vals in totals.items():
        rates = table.get(models.get(agent, ""))
        if not rates:
            unpriced[(agent, system)] = vals.get("claude_agent_runs_total", 0)
            continue
        try:
            out_rate = float(rates["output"])
            in_rate = float(rates["input"])
        except (KeyError, TypeError, ValueError):
            unpriced[(agent, system)] = vals.get("claude_agent_runs_total", 0)
            continue
        output_cost = vals.get("claude_agent_output_tokens_total", 0) / 1e6 * out_rate
        cache_cost = (
            vals.get("claude_agent_cache_read_tokens_total", 0)
            / 1e6
            * in_rate
            * cache_multiplier
        )
        costs[(agent, system, models[agent])] = (output_cost, cache_cost)

    for name, help_text, index in (
        ("claude_agent_estimated_cost_usd_total", "Estimated spend (output + cached re-read)", None),
        ("claude_agent_estimated_output_cost_usd_total", "Estimated spend on output tokens", 0),
        ("claude_agent_estimated_cache_read_cost_usd_total", "Estimated spend on cached input re-read", 1),
    ):
        out.append(f"# HELP {name} {help_text}, USD")
        out.append(f"# TYPE {name} counter")
        for (agent, system, model), parts in sorted(costs.items()):
            labels = _labels([("agent", agent), ("system", system), ("model", model)])
            value = sum(parts) if index is None else parts[index]
            out.append(f"{name}{{{labels}}} {value:.6f}")

    out.append("# HELP claude_agent_unpriced_runs_total Runs excluded from cost (model tier unknown)")
    out.append("# TYPE claude_agent_unpriced_runs_total counter")
    for (agent, system), count in sorted(unpriced.items()):
        labels = _labels([("agent", agent), ("system", system)])
        out.append(f"claude_agent_unpriced_runs_total{{{labels}}} {count:g}")

    for name, help_text, field in GAUGES:
        out.append(f"# HELP {name} {help_text}")
        out.append(f"# TYPE {name} gauge")
        for (agent, system), (_, rec) in sorted(latest.items()):
            labels = _labels([("agent", agent), ("system", system)])
            if name == "claude_agent_max_context_tokens":
                value = totals[(agent, system)].get("_max_ctx", 0)
            else:
                try:
                    value = float(rec.get(field) or 0)
                except (TypeError, ValueError):
                    value = 0.0
            out.append(f"{name}{{{labels}}} {value:g}")

    out.append("# HELP claude_agent_log_records Records parsed from the run log")
    out.append("# TYPE claude_agent_log_records gauge")
    out.append(f"claude_agent_log_records {records}")
    out.append("# HELP claude_agent_log_malformed_lines Lines the exporter could not parse")
    out.append("# TYPE claude_agent_log_malformed_lines gauge")
    out.append(f"claude_agent_log_malformed_lines {malformed}")

    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] not in ("/metrics", "/"):
            self.send_response(404)
            self.end_headers()
            return
        try:
            body = render().encode()
        except Exception as exc:  # never let a bad line take the exporter down
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"exporter error: {exc}\n".encode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # scrape-per-10s would otherwise flood the container log


if __name__ == "__main__":
    print(f"agent-exporter serving {METRICS_FILE} on :{PORT}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
