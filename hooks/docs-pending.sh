#!/bin/bash
# Tier 2 wiring for the forge-doc-planner agent.
#
# Fires on SessionStart. The design docs are hand-written by the user between sessions, so
# the condition "docs have changed and have not been tidied" almost always becomes true while
# Claude Code is NOT running. A PostToolUse hook would never see it. This checks for it once,
# at the only moment it can be observed.
#
# Scoped to the ACTIVE project's docsRoot, not to Docs/ as a whole — with several projects in
# the repo, uncommitted docs in an inactive project are not this session's business.
#
# Non-blocking: injects context, decides nothing. See
# .claude/skills/agent-creator/references/wiring.md
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0

# No active project — forge-active-project.sh already says so. Don't say it twice.
slug=$(jq -r '.project // empty' .claude/forge/active-project.json 2>/dev/null) || exit 0
[ -z "$slug" ] && exit 0

manifest=""
for candidate in "Docs/$slug/forge.json" Docs/*/forge.json; do
  [ -f "$candidate" ] || continue
  if [ "$(jq -r '.name // empty' "$candidate" 2>/dev/null)" = "$slug" ]; then
    manifest="$candidate"
    break
  fi
done
[ -z "$manifest" ] && exit 0

docs_root=$(jq -r '.docsRoot // empty' "$manifest" 2>/dev/null) || exit 0
[ -z "$docs_root" ] && exit 0

# Not a git repo, or git unavailable — nothing to say. The pathspec is case-sensitive and
# must match the tracked path exactly, which is why docsRoot is stored as a real path.
changed=$(git status --porcelain -- "$docs_root" 2>/dev/null) || exit 0
[ -z "$changed" ] && exit 0

# Only the hand-written design docs are forge-doc-planner's territory. PRDs belong to
# forge-prd-author, roadmap.md is generated, and forge.json is configuration.
# Porcelain v1 is "XY " then the path, so the status is exactly the first 3 characters.
# Renames arrive as `old -> new`; keep the new name. Paths containing spaces are quoted.
# Note `paste -d` takes a *cyclic list* of delimiters, so ', ' would alternate comma and
# space. Join on a single comma.
files=$(printf '%s\n' "$changed" \
  | cut -c4- \
  | sed 's/^.* -> //; s/^"//; s/"$//' \
  | grep -v "^${docs_root}/PRDs/" \
  | grep -v "^${docs_root}/roadmap\.md$" \
  | grep -v "^${docs_root}/forge\.json$" \
  | paste -sd, - || true)

[ -z "$files" ] && exit 0

jq -cn --arg files "$files" --arg root "$docs_root" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: ("Design docs under \($root) have uncommitted changes (\($files)) that may not have been tidied. Once the user has finished editing, dispatch: Agent(subagent_type: \"forge-doc-planner\", prompt: \"Docs under \($root) were edited — plan what needs tidying.\"), then hand its report to Agent(subagent_type: \"forge-doc-writer\", ...) to apply. Do not run this while the user is still mid-brain-dump; ask if unsure.")
  }
}'
