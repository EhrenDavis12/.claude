#!/bin/bash
# Wiring for annie's work queue. Belongs to the `annie` system.
#
# Fires on SessionStart and prints the queue: what is working, what waits for the user's eyes,
# and every open question — so a fresh session starts knowing what the user owes and what the
# queue can do without them.
#
# Self-gates on CLAUDE.md's import line, because settings.json does not follow a system swap.
# Non-blocking: injects context, decides nothing.
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0
grep -qxF '@.claude/systems/annie/SYSTEM.md' CLAUDE.md 2>/dev/null || exit 0

q=.claude/systems/annie/queue/q.py
[ -f .claude/systems/annie/queue/queue.json ] || exit 0

list=$(python3 "$q" list 2>/dev/null) || exit 0
[ -z "$list" ] && exit 0

summary="annie's queue (python3 $q — the only writer; after a change, q.py render and republish the Queue page named in SYSTEM.md):
$list
Questions above with no A: line are waiting on the user. Run /annie-queue to work it, or /loop /annie-queue to keep working it."

jq -cn --arg s "$summary" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $s}}'
