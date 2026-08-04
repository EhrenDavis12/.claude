#!/usr/bin/env bash
# SubagentStop / Stop hook: fold finished subagent runs into the durable metrics
# log at .claude/metrics/agent-runs.jsonl, so per-agent performance history
# survives the ~30-day pruning of Claude Code's raw transcripts.
#
# System-agnostic on purpose (like repo-context.sh): measuring agents is useful
# under any system, so this does NOT gate on the active one.
#
# Contract: read-only w.r.t. transcripts, idempotent, and must never fail a turn.
# It ignores hook stdin and just triggers an idempotent sync of whatever runs are
# currently on disk — a design that stays correct no matter which fields the
# SubagentStop payload happens to carry.
set -uo pipefail

DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

command -v python3 >/dev/null 2>&1 || exit 0
python3 "$DIR/.claude/tools/agent-metrics.py" --sync --cwd "$DIR" >/dev/null 2>&1 || true
exit 0
