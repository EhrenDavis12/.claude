#!/bin/bash
# Wiring for the skill-improver skill. Repo-level: not gated on the active system, because a
# skill that learns from its runs is useful under any of them.
#
# Fires on SessionStart. Two conditions it can see that no agent would otherwise notice:
#   1. a skill's scorecard has rows newer than its SKILL.md — a run was scored and the lesson
#      was never folded back into the recipe;
#   2. a work log under the active project's srcRoots changed since the last harvest — a
#      process is being worked out by hand and may be ready to become a skill.
# It also restates the standing rule, so a session that runs a skill ends by improving it
# without the user having to ask.
#
# Non-blocking: injects context, decides nothing. See
# .claude/skills/agent-creator/references/wiring.md
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0
[ -f .claude/skills/skill-improver/SKILL.md ] || exit 0

# 1. Scorecards that are ahead of their skill.
unread=""
while IFS= read -r card; do
  skill_dir=$(dirname "$card")
  [ -f "$skill_dir/SKILL.md" ] || continue
  if [ "$card" -nt "$skill_dir/SKILL.md" ]; then
    unread="${unread:+$unread, }${skill_dir#.claude/skills/}"
  fi
done < <(find .claude/skills -name scorecard.csv -not -path '*/node_modules/*' 2>/dev/null)

# 2. Work logs changed since the last harvest, in the active project only.
logs=""
slug=$(jq -r '.project // empty' .claude/project/active.json 2>/dev/null || true)
manifest=""
if [ -n "$slug" ]; then
  for candidate in "Docs/$slug/project.json" Docs/*/project.json; do
    [ -f "$candidate" ] || continue
    if [ "$(jq -r '.name // empty' "$candidate" 2>/dev/null)" = "$slug" ]; then
      manifest="$candidate"
      break
    fi
  done
fi
if [ -n "$manifest" ]; then
  stamp=.claude/skills/skill-improver/last-harvest
  newer=()
  [ -f "$stamp" ] && newer=(-newer "$stamp")
  while IFS= read -r root; do
    [ -d "$root" ] || continue
    found=$(find "$root" -maxdepth 8 \
      \( -name .git -o -name node_modules -o -name .venv -o -name Library -o -name build \) -prune \
      -o -type f -name 'PROGRESS.md' ${newer[@]+"${newer[@]}"} -print 2>/dev/null | head -5 | paste -sd, - || true)
    [ -n "$found" ] && logs="${logs:+$logs,}$found"
  done < <(jq -r '.srcRoots[]? // empty' "$manifest" 2>/dev/null)
fi

msg="Skills improve themselves here: a run of any skill that has a Scorecard section ends by appending its scorecard row and then running the skill-improver skill on it — without asking and without announcing it. Animation skills live under .claude/skills/AnimationSkills/ and are reached through the animation-skills skill."
[ -n "$unread" ] && msg="$msg Scorecards with rows their skill has not absorbed yet: $unread — run skill-improver (improve) on each before starting new work with that skill."
[ -n "$logs" ] && msg="$msg Work logs changed since the last harvest: $logs — when this session touches that work, run skill-improver (harvest) to see whether a process in them is ready to become a skill."

jq -cn --arg msg "$msg" '{
  hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: $msg }
}'
