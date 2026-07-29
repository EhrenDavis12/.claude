#!/bin/bash
# Tier 2 wiring for the forge-doc-planner agent.
#
# Fires on SessionStart. The docs under Docs/ are hand-written by the user between
# sessions, so the condition "docs have changed and have not been tidied" almost always
# becomes true while Claude Code is NOT running. A PostToolUse hook would never see it.
# This checks for it once, at the only moment it can be observed.
#
# Non-blocking: injects context, decides nothing. See
# .claude/skills/agent-creator/references/wiring.md
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# Not a git repo, or git unavailable — nothing to say.
changed=$(git status --porcelain -- Docs 2>/dev/null) || exit 0
[ -z "$changed" ] && exit 0

files=$(printf '%s\n' "$changed" | awk '{print $NF}' | paste -sd', ' -)

jq -cn --arg files "$files" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: ("Docs under Docs/ have uncommitted changes (\($files)) that may not have been tidied. Once the user has finished editing, dispatch: Agent(subagent_type: \"forge-doc-planner\", prompt: \"Docs under Docs/ were edited — plan what needs tidying.\"), then hand its report to Agent(subagent_type: \"forge-doc-writer\", ...) to apply. Do not run this while the user is still mid-brain-dump; ask if unsure.")
  }
}'
