#!/bin/bash
# Tier 2 wiring for the forge work queue. Belongs to the `forge` system.
#
# Fires on SessionStart and prints the state of <docsRoot>/queue/ — counts per section, what
# is claimed in Processing, what is waiting on the user in Blocked, and any Processing item
# whose branch has gone quiet. The user edits the queue between sessions, so SessionStart is
# the only moment the change can be observed; a PostToolUse hook would never see it.
#
# Self-gates on CLAUDE.md's import line, because settings.json does not follow a system swap.
# Non-blocking: injects context, decides nothing.
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0

grep -qxF '@.claude/systems/forge/SYSTEM.md' CLAUDE.md 2>/dev/null || exit 0

slug=$(jq -r '.project // empty' .claude/project/active.json 2>/dev/null) || exit 0
[ -z "$slug" ] && exit 0

manifest=""
for candidate in "Docs/$slug/project.json" Docs/*/project.json; do
  [ -f "$candidate" ] || continue
  if [ "$(jq -r '.name // empty' "$candidate" 2>/dev/null)" = "$slug" ]; then
    manifest="$candidate"
    break
  fi
done
[ -z "$manifest" ] && exit 0

docs_root=$(jq -r '.docsRoot // empty' "$manifest" 2>/dev/null) || exit 0
[ -z "$docs_root" ] && exit 0
queue="$docs_root/queue"
[ -d "$queue" ] || exit 0

# Items are the `- ` lines after the header's `---` rule. Notes and answers are indented, so
# they never match. Goal.md is prose and is not counted.
count() { awk 'f && /^- /{n++} /^---$/{f=1} END{print n+0}' "$queue/$1.md" 2>/dev/null || echo 0; }
items() { awk 'f && /^- /{print} /^---$/{f=1}' "$queue/$1.md" 2>/dev/null || true; }

proposed=$(count Proposed); later=$(count Later); inbox=$(count Inbox); ready=$(count Ready)
processing=$(count Processing); blocked=$(count Blocked); done_n=$(count Done)
unanswered=$(grep -cE '^[[:space:]]+A:[[:space:]]*$' "$queue/Blocked.md" 2>/dev/null || true)
unanswered=${unanswered:-0}
goal_set="no"
if awk 'f && NF && !/^## Not included/ && !/^-[[:space:]]*$/{found=1} /^---$/{f=1} END{exit !found}' "$queue/Goal.md" 2>/dev/null; then
  goal_set="yes"
fi

summary="Work queue at $queue — goal set: $goal_set · proposed $proposed · later $later · inbox $inbox · ready $ready · processing $processing · blocked $blocked ($unanswered unanswered) · done (30d) $done_n."

claimed=$(items Processing)
[ -n "$claimed" ] && summary="$summary
Claimed (hands off):
$claimed"

# A Processing item whose branch has not moved in a day is probably an abandoned session.
stale=""
now=$(date +%s)
while IFS= read -r line; do
  [ -z "$line" ] && continue
  branch=$(printf '%s' "$line" | sed -n 's/.*branch \([^ ·]*\).*/\1/p')
  [ -z "$branch" ] && continue
  latest=0
  while IFS= read -r root; do
    [ -d "$root" ] || continue
    ts=$(git -C "$root" log -1 --format=%ct "$branch" -- 2>/dev/null || true)
    [ -n "$ts" ] && [ "$ts" -gt "$latest" ] && latest=$ts
  done < <(jq -r '.srcRoots[]? // empty' "$manifest" 2>/dev/null)
  if [ "$latest" -eq 0 ] || [ $((now - latest)) -gt 86400 ]; then
    stale="$stale
$line"
  fi
done <<< "$claimed"
[ -n "$stale" ] && summary="$summary
Possibly abandoned (branch quiet for over a day, or missing) — do not re-pick without asking:$stale"

waiting=$(items Blocked)
[ -n "$waiting" ] && summary="$summary
Blocked on the user:
$waiting"

next="Nothing is waiting on the queue."
if [ "$ready" -gt 0 ] || [ "$inbox" -gt 0 ] || { [ "$blocked" -gt 0 ] && [ "$unanswered" -eq 0 ]; }; then
  next="Run /forge-queue to work it — or /loop 30m /forge-queue to keep working it."
elif [ "$goal_set" = "yes" ] && [ "$later" -gt 0 ]; then
  next="Nothing to build. /forge-queue would refine Later items; /forge-queue --propose re-runs the goal engine."
fi
summary="$summary
$next"

jq -cn --arg s "$summary" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $s}}'
