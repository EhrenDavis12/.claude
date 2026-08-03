#!/usr/bin/env python3
"""
agent-metrics.py — per-agent performance report, mined from Claude Code's own
session transcripts. No telemetry setup, no code changes to your agents: it reads
the JSONL that Claude Code already writes to ~/.claude/projects/<cwd>/.

What it measures, per subagent RUN and aggregated per AGENT TYPE:
  runs        how many times that agent was dispatched
  turns       assistant API requests the agent made (its agentic loop length)
  tool_calls  total tool invocations (+ a breakdown of which tools)
  out_tok     output tokens generated (a proxy for how much the agent "wrote/thought")
  max_ctx     largest context window the agent reached on any single request
              (input + cache_read + cache_creation) — how full its window got
  cache_read  total cached input re-read across the run — the fixed re-read tax
              of starting fresh and re-loading CLAUDE.md/SYSTEM.md/docs each dispatch
  dur_s       wall-clock seconds from the agent's first to last message

Why these: turns + dur_s find the SLOW agents; max_ctx finds the agents drowning
in context (the thing that degrades quality as your SOT grows); cache_read exposes
the per-dispatch re-read overhead that compounds as instructions grow.

Usage:
  python3 .claude/tools/agent-metrics.py                # this repo, all sessions
  python3 .claude/tools/agent-metrics.py --session <id> # one session only
  python3 .claude/tools/agent-metrics.py --json         # machine-readable
  python3 .claude/tools/agent-metrics.py --runs         # every run, not just aggregates
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

AGENTID_RE = re.compile(r"agentId:\s*([0-9a-f]+)", re.I)


def encoded_cwd(path):
    # Claude Code encodes the cwd by replacing non-alphanumerics with '-'
    return re.sub(r"[^a-zA-Z0-9]", "-", os.path.abspath(path))


def project_dir(cwd):
    base = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
    return os.path.join(base, "projects", encoded_cwd(cwd))


def parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def iter_lines(path):
    with open(path, "r", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def build_agentid_map(proj):
    """agentId -> agent_type, mined from the parent session transcripts.

    Pairs each Agent/Task tool_use (which carries subagent_type) with the
    tool_result whose text embeds 'agentId: <id>', joined by tool_use_id.
    """
    type_by_tooluse = {}   # tool_use_id -> subagent_type
    id_by_tooluse = {}     # tool_use_id -> agentId
    for main in glob.glob(os.path.join(proj, "*.jsonl")):
        for rec in iter_lines(main):
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") in ("Task", "Agent"):
                    st = (block.get("input") or {}).get("subagent_type")
                    if block.get("id"):
                        type_by_tooluse[block["id"]] = st or block.get("name")
                elif block.get("type") == "tool_result":
                    tid = block.get("tool_use_id")
                    text = block.get("content")
                    if isinstance(text, list):
                        text = " ".join(
                            b.get("text", "") for b in text if isinstance(b, dict)
                        )
                    m = AGENTID_RE.search(text or "")
                    if tid and m:
                        id_by_tooluse[tid] = m.group(1)
    # A single agentId can be referenced by several tool_use_ids (the launch,
    # then later echoes/notifications). Only the launch carries the type, so a
    # known type must never be clobbered by a later unknown reference.
    agentid_to_type = {}
    for tid, aid in id_by_tooluse.items():
        t = type_by_tooluse.get(tid)
        if t and agentid_to_type.get(aid, "unknown") == "unknown":
            agentid_to_type[aid] = t
        else:
            agentid_to_type.setdefault(aid, "unknown")
    return agentid_to_type


def analyze_run(path):
    turns = 0
    tool_calls = 0
    tools = defaultdict(int)
    out_tok = 0
    cache_read = 0
    max_ctx = 0
    first_ts = last_ts = None
    for rec in iter_lines(path):
        ts = parse_ts(rec.get("timestamp", ""))
        if ts is not None:
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)
        msg = rec.get("message") or {}
        if msg.get("role") == "assistant":
            usage = msg.get("usage") or {}
            if usage:
                turns += 1
                out_tok += usage.get("output_tokens", 0) or 0
                cr = usage.get("cache_read_input_tokens", 0) or 0
                cache_read += cr
                ctx = (
                    (usage.get("input_tokens", 0) or 0)
                    + cr
                    + (usage.get("cache_creation_input_tokens", 0) or 0)
                )
                max_ctx = max(max_ctx, ctx)
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_calls += 1
                        tools[block.get("name", "?")] += 1
    dur = (last_ts - first_ts) if (first_ts and last_ts) else 0.0
    return {
        "turns": turns,
        "tool_calls": tool_calls,
        "tools": dict(tools),
        "out_tok": out_tok,
        "cache_read": cache_read,
        "max_ctx": max_ctx,
        "dur_s": round(dur, 1),
        "ended_ts": last_ts or 0.0,
    }


def collect_runs(proj, session=None):
    """Every subagent run currently present in the transcripts, labeled by type."""
    agentid_to_type = build_agentid_map(proj)
    sub_glob = os.path.join(proj, "**", "subagents", "agent-*.jsonl")
    runs = []
    for path in glob.glob(sub_glob, recursive=True):
        if session and session not in path:
            continue
        aid_match = re.search(r"agent-([0-9a-f]+)\.jsonl$", os.path.basename(path))
        aid = aid_match.group(1) if aid_match else "?"
        stats = analyze_run(path)
        stats["agent"] = agentid_to_type.get(aid, "unknown")
        stats["agentId"] = aid
        runs.append(stats)
    return runs


def log_file(cwd):
    return os.path.join(os.path.abspath(cwd), ".claude", "metrics", "agent-runs.jsonl")


def sync_log(proj, cwd):
    """Merge current transcripts into the durable log, self-healing partial runs.

    The transcript is authoritative for any run it still holds (so a run captured
    mid-flight is overwritten by its final numbers on a later sync). Runs whose
    transcripts have been pruned are kept from the existing log. Idempotent.
    """
    path = log_file(cwd)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    by_id = {}
    if os.path.exists(path):
        for rec in iter_lines(path):
            if rec.get("agentId"):
                by_id[rec["agentId"]] = rec  # historical (maybe pruned)
    fresh = 0
    for r in collect_runs(proj):
        if r["turns"] == 0:
            continue  # nothing happened yet; skip empty/just-started transcripts
        if r["agentId"] not in by_id:
            fresh += 1
        by_id[r["agentId"]] = r  # transcript wins over history
    records = sorted(by_id.values(), key=lambda x: x.get("ended_ts", 0))
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    os.replace(tmp, path)
    return len(records), fresh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--session", help="limit to one session id")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--runs", action="store_true", help="show every run, not just aggregates")
    ap.add_argument("--sync", action="store_true",
                    help="append/refresh runs into .claude/metrics/agent-runs.jsonl (for hooks)")
    ap.add_argument("--log", action="store_true",
                    help="report from the durable log instead of live transcripts")
    args = ap.parse_args()

    proj = project_dir(args.cwd)

    if args.sync:
        # Hook-friendly: never fail a turn. No transcripts yet == nothing to do.
        if not os.path.isdir(proj):
            return
        total, fresh = sync_log(proj, args.cwd)
        print(f"agent-metrics: log has {total} run(s) (+{fresh} new)")
        return

    if args.log:
        lf = log_file(args.cwd)
        if not os.path.exists(lf):
            print(f"No metrics log yet at {lf}. It fills as agents run (via the "
                  "SubagentStop hook) or after `--sync`.")
            return
        runs = list(iter_lines(lf))
        if args.session:
            runs = [r for r in runs if args.session in r.get("agentId", "")]
    else:
        if not os.path.isdir(proj):
            print(f"No transcripts found at {proj}", file=sys.stderr)
            sys.exit(1)
        runs = collect_runs(proj, session=args.session)

    if args.json:
        print(json.dumps(runs, indent=2))
        return

    if not runs:
        print("No subagent runs found yet. Dispatch some agents, then re-run.")
        return

    if args.runs:
        print(f"{'agent':<26}{'turns':>6}{'tools':>7}{'out_tok':>9}{'max_ctx':>9}{'dur_s':>8}")
        print("-" * 65)
        for r in sorted(runs, key=lambda x: -x["dur_s"]):
            print(f"{r['agent']:<26}{r['turns']:>6}{r['tool_calls']:>7}"
                  f"{r['out_tok']:>9}{r['max_ctx']:>9}{r['dur_s']:>8}")
        print()

    agg = defaultdict(lambda: defaultdict(float))
    for r in runs:
        a = agg[r["agent"]]
        a["runs"] += 1
        for k in ("turns", "tool_calls", "out_tok", "cache_read", "max_ctx", "dur_s"):
            a[k] += r[k]

    print(f"Per-agent averages over {len(runs)} run(s):\n")
    print(f"{'agent':<26}{'runs':>5}{'avg_turns':>10}{'avg_tools':>10}"
          f"{'avg_out':>9}{'avg_ctx':>9}{'avg_dur_s':>10}")
    print("-" * 79)
    for agent, a in sorted(agg.items(), key=lambda kv: -(kv[1]["dur_s"] / kv[1]["runs"])):
        n = a["runs"]
        print(f"{agent:<26}{int(n):>5}{a['turns']/n:>10.1f}{a['tool_calls']/n:>10.1f}"
              f"{a['out_tok']/n:>9.0f}{a['max_ctx']/n:>9.0f}{a['dur_s']/n:>10.1f}")
    print("\nRead the tall bars: high avg_dur_s + high avg_turns = a slow/looping agent;")
    print("high avg_ctx = an agent drowning in context (quality risk as your SOT grows).")


if __name__ == "__main__":
    main()
