#!/bin/bash
# Wiring for forge's work queue. Belongs to the `forge` system. A port of annie-queue-pending.sh.
#
# Fires on SessionStart and prints the queue: what is working, what waits for the user's eyes,
# and every open question — and whether the runner is running — so a fresh session starts
# knowing what the user owes and what the queue can do without them.
#
# Self-gates on CLAUDE.md's import line, because settings.json does not follow a system swap.
# Non-blocking: injects context, decides nothing.
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0
grep -qxF '@.claude/systems/forge/SYSTEM.md' CLAUDE.md 2>/dev/null || exit 0

dir=.claude/systems/forge/queue
q=$dir/q.py
[ -f "$dir/queue.json" ] || exit 0

list=$(python3 "$q" list 2>/dev/null) || exit 0
[ -z "$list" ] && exit 0
runner=$(bash "$dir/run.sh" status 2>/dev/null | head -2 | tr '\n' ' ') || runner="unknown"

summary="forge's queue (python3 $q — the only writer; after a change, q.py render and republish the Queue page named in SYSTEM.md). Runner: $runner
$list
Questions above with no A: line are waiting on the user. /forge-desk makes this session the desk; the runner ($dir/run.sh start) works the jobs."

jq -cn --arg s "$summary" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $s}}'
