#!/bin/bash
# The trigger for the PRD close-out. Belongs to the `forge` system.
#
# settings.json does not follow CLAUDE.md's import line, so this hook would keep firing after a
# swap and tell a system with no harvest agents to run a close-out. Hence the self-gate below.
#
# Fires on SessionStart. "Green + reviewer clean" is a state nobody announces — it becomes true
# at the end of the longest day of a build, which is when it is least likely to be noticed — so
# built PRDs sat undeleted for weeks. The PRDs directory is a work queue: an empty one means
# done, so anything still in it is either mid-build or an un-drained close-out. This lists what
# is there, once, at the one moment a fresh session can act on it.
#
# Deliberately NOT keyed on "do tests exist for this PRD": the only detector for that was source
# files citing the PRD's path, which the agents are now told never to write. Presence, age, and
# tracked state come from the repo alone. Tracked state matters because `git rm` fails on an
# untracked file — see SYSTEM.md, "The close-out order", step 4.
#
# Non-blocking: injects context, decides nothing. See
# .claude/skills/agent-creator/references/wiring.md
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0

# The gate: forge must be the active system. The import line is the single source of truth for
# that, so derive it here rather than trusting a second copy of the answer.
grep -qxF '@.claude/systems/forge/SYSTEM.md' CLAUDE.md 2>/dev/null || exit 0

# No active project — repo-context.sh already says so. Don't say it twice.
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

prds=$(jq -r '.prds // empty' "$manifest" 2>/dev/null) || exit 0
[ -z "$prds" ] && exit 0
[ -d "$prds" ] || exit 0

now=$(date +%s)
list=""
count=0
for f in "$prds"/*.md; do
  [ -f "$f" ] || continue
  # Age from the file's mtime; stat's flags differ between BSD (macOS) and GNU.
  mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null) || continue
  days=$(( (now - mtime) / 86400 ))
  if [ -n "$(git ls-files -- "$f" 2>/dev/null)" ]; then
    tracked="tracked"
  else
    tracked="untracked"
  fi
  list="${list:+$list, }$(basename "$f") (${days}d since last edit, ${tracked})"
  count=$((count + 1))
done

# The intended steady state: nothing open, nothing to say.
[ "$count" -eq 0 ] && exit 0

jq -cn --arg n "$count" --arg list "$list" --arg prds "$prds" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: ("\($n) PRD(s) are open in \($prds): \($list). A PRD is deleted at close-out, so one open for weeks is either mid-build or an un-drained close-out. For each: if its tests exist and pass, run the close-out in SYSTEM.md — forge-harvest-planner, then forge-doc-writer, confirm Ready to delete covers every doc it owes, commit the PRD if untracked, then git rm it. If it was never built and its premises have gone stale, say so and ask the user before harvesting. Do not start this mid-build; tell the user what is open and ask if unsure.")
  }
}'
