# OTEL — command reference

Every command runs from the repo root unless it says otherwise. Docker Desktop must be running.

| Where | URL |
|---|---|
| Grafana (dashboards) | http://localhost:3000 |
| Prometheus (raw queries) | http://localhost:9090 |
| Exporter (raw agent metrics) | http://localhost:9101/metrics |

---

## Start the stack

```bash
cd .claude/otel
docker compose up -d
```

## Stop the stack

```bash
cd .claude/otel
docker compose stop          # pause, keeps stored numbers
docker compose down          # stop and discard stored numbers
```

## Turn telemetry on

```bash
source .claude/otel/telemetry.env
claude
```

Run both in the **same terminal** — the switch only affects that terminal.

## Turn telemetry off

```bash
source .claude/otel/telemetry-off.sh
```

Or close the terminal.

---

## See agents by name — terminal

```bash
python3 .claude/tools/agent-metrics.py --log            # per-agent averages
python3 .claude/tools/agent-metrics.py --log --runs     # every run, slowest first
python3 .claude/tools/agent-metrics.py --by-system --log # team totals only
python3 .claude/tools/agent-metrics.py --json           # machine-readable
```

Read `runs` for executions and `avg_dur_s` for runtime.

## See agents by name — Grafana

1. `cd .claude/otel && docker compose up -d`
2. Open http://localhost:3000/d/subagent-efficiency
3. Set the time range (top right) to **Last 90 days**
4. Read the **Efficiency by agent** table — `runs` is executions, `avg s/run` is runtime
5. Click any column header to re-sort
6. Use the **Agent team** dropdown (top left) to filter to `forge`

## See dollars and live activity — Grafana

Open http://localhost:3000/d/claude-agents

---

## Save a baseline snapshot

```bash
python3 .claude/tools/agent-metrics.py --json > .claude/tools/baseline-$(date +%F).json
```

## Change cost rates

```bash
# edit .claude/otel/model-prices.json, then:
cd .claude/otel
docker compose restart agent-exporter
```

Re-prices all history on the next scrape.

## Apply a config change

```bash
cd .claude/otel
docker compose restart otel-collector   # after editing otel-collector-config.yaml
docker compose restart prometheus       # after editing prometheus.yml
docker compose restart agent-exporter   # after editing agent_exporter.py or model-prices.json
docker compose up -d                    # after editing docker-compose.yml
```

Dashboard JSON in `grafana/dashboards/` reloads on its own within 30 seconds — no restart.

---

## Check it is working

```bash
cd .claude/otel && docker compose ps                    # all four services Up
curl -s http://localhost:9101/metrics | head            # exporter serving
curl -s http://localhost:8889/metrics | grep claude     # collector serving
open http://localhost:9090/targets                      # both targets UP
```

## Read logs

```bash
cd .claude/otel
docker compose logs -f otel-collector
docker compose logs -f agent-exporter
docker compose logs --tail 50 grafana
```

## Query directly

Paste into the box at http://localhost:9090:

```promql
sum by (agent) (claude_agent_runs_total)
claude_agent_worked_duration_seconds_total / claude_agent_worked_runs_total
sort_desc(claude_agent_max_context_tokens)
sort_desc(sum by (agent) (claude_agent_estimated_cost_usd_total))
sum by (query_source) (claude_code_cost_usage)
```

---

## When panels are empty

Run these in order:

```bash
cd .claude/otel && docker compose ps                    # 1. all services Up?
curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"[a-z]*"'   # 2. targets up?
curl -s http://localhost:9101/metrics | head -3         # 3. exporter has data?
curl -s http://localhost:8889/metrics | grep -c claude  # 4. collector has data?
```

If step 4 returns 0, re-`source` the env file and restart `claude` in that terminal.

If the **agent-name** dashboard is empty, the stack is not the problem — check the log:

```bash
wc -l .claude/metrics/agent-runs.jsonl
```

## Force a metrics refresh

```bash
python3 .claude/tools/agent-metrics.py --sync   # fold current runs into the log
```

Runs automatically after every agent; use only to refresh by hand.
