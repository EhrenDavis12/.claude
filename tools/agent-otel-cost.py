#!/usr/bin/env python3
"""
agent-otel-cost.py — real per-agent cost from Claude Code's OTEL log events.

Claude Code labels every custom subagent agent_name="custom" in its metrics, so the
dashboards cannot split spend by forge agent. Since 2.1.311 (28 Oct 2026) each
`api_request` log event carries `agent_id`, the same id the run log records. This joins
the two: cost_usd (what Claude Code itself billed) summed per agent name.

Reads   .claude/metrics/otel-events/*.jsonl   (file exporter output, rotated by size)
        .claude/metrics/agent-runs.jsonl      (agentId -> agent name)
Usage   python3 .claude/tools/agent-otel-cost.py [--days 7] [--json]
Runs whose events predate 2.1.311 have no agent_id and are counted as unmatched.
"""
import argparse, collections, glob, json, os, statistics, time

ap = argparse.ArgumentParser()
ap.add_argument("--days", type=float, default=7)
ap.add_argument("--metrics", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "metrics"))
ap.add_argument("--json", action="store_true")
a = ap.parse_args()
m = os.path.abspath(a.metrics if os.path.isdir(a.metrics) else ".claude/metrics")
since = time.time() - a.days * 86400

names = {}
for line in open(os.path.join(m, "agent-runs.jsonl")):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if r.get("agentId"):
        names[r["agentId"]] = r.get("agent", "?")

def val(v):
    for k in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if k in v:
            return v[k]

seen, per_run = set(), collections.defaultdict(collections.Counter)
for f in sorted(glob.glob(os.path.join(m, "otel-events", "*.jsonl"))):
    if os.path.getmtime(f) < since:
        continue
    for line in open(f, errors="replace"):
        try:
            x = json.loads(line)
        except ValueError:
            continue
        for rl in x.get("resourceLogs", []):
            for sl in rl.get("scopeLogs", []):
                for lr in sl.get("logRecords", []):
                    if int(lr.get("timeUnixNano", 0)) / 1e9 < since:
                        continue
                    at = {kv["key"]: val(kv["value"]) for kv in lr.get("attributes", [])}
                    if at.get("event.name") != "api_request" or not at.get("agent_id"):
                        continue
                    key = (at.get("session.id"), at.get("event.sequence"))
                    if key in seen:
                        continue
                    seen.add(key)
                    c = per_run[at["agent_id"]]
                    c["cost"] += float(at.get("cost_usd") or 0)
                    c["out"] += int(at.get("output_tokens") or 0)
                    c["requests"] += 1

agg = collections.defaultdict(list)
for aid, c in per_run.items():
    agg[names.get(aid, "(unmatched)")].append(c)
rows = []
for agent, runs in agg.items():
    costs = [r["cost"] for r in runs]
    rows.append({"agent": agent, "runs": len(runs), "cost_usd": round(sum(costs), 2),
                 "median_usd": round(statistics.median(costs), 3),
                 "requests": sum(r["requests"] for r in runs),
                 "output_tokens": sum(r["out"] for r in runs)})
rows.sort(key=lambda r: -r["cost_usd"])
if a.json:
    print(json.dumps(rows, indent=1))
else:
    print(f"{'agent':28} {'runs':>5} {'cost $':>9} {'median $':>9} {'requests':>9}")
    for r in rows:
        print(f"{r['agent']:28} {r['runs']:>5} {r['cost_usd']:>9.2f} {r['median_usd']:>9.3f} {r['requests']:>9}")
    print(f"{'total':28} {sum(r['runs'] for r in rows):>5} {sum(r['cost_usd'] for r in rows):>9.2f}")
