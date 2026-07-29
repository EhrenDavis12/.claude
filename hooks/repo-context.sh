#!/bin/bash
# Injects the active project into the main loop's context at session start.
#
# Project scoping is a property of the repo, not of any one agent system, so this hook is
# never gated on which system is active. Agents resolve their own scope by reading the pointer
# and manifest themselves — that read is authoritative. This hook exists so the *main loop*
# knows which project is active without having to go looking, and so a session that has no
# active project says so out loud instead of silently defaulting to a guessed path.
#
# Non-blocking: injects context, decides nothing. See
# .claude/skills/agent-creator/references/wiring.md
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# No jq — say nothing rather than emit malformed JSON.
command -v jq >/dev/null 2>&1 || exit 0

POINTER=".claude/project/active.json"

emit() {
  jq -cn --arg ctx "$1" '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: $ctx
    }
  }'
}

if [ ! -f "$POINTER" ]; then
  emit "No active project is set. Agents that resolve their scope from the manifest will refuse to run until one is. Run /set-project."
  exit 0
fi

slug=$(jq -r '.project // empty' "$POINTER" 2>/dev/null) || slug=""
if [ -z "$slug" ]; then
  emit "$POINTER exists but names no project. Run /set-project to set one."
  exit 0
fi

# Convention is Docs/<slug>/project.json, but the manifest whose .name matches the slug wins —
# so a project folder can be renamed without breaking the pointer.
#
# Deliberately matches .name only, never .aliases: /set-project resolves aliases at
# activation time and always writes the canonical name here, so a pointer holding an alias is
# a bug worth surfacing rather than quietly accepting.
manifest=""
for candidate in "Docs/$slug/project.json" Docs/*/project.json; do
  [ -f "$candidate" ] || continue
  if [ "$(jq -r '.name // empty' "$candidate" 2>/dev/null)" = "$slug" ]; then
    manifest="$candidate"
    break
  fi
done

if [ -z "$manifest" ]; then
  emit "The active project is \"$slug\" but no Docs/*/project.json declares that name. The manifest is missing or its .name does not match. Run /set-project to fix this before dispatching any agent."
  exit 0
fi

ctx=$(jq -r --arg m "$manifest" '
  "Active project: \(.name) — \(.title // .name).\n"
  + "Manifest: \($m) (authoritative for every path below).\n"
  + "  design docs: \(.docsRoot) — every .md directly under it, excluding PRDs/ and the roadmap\n"
  + "  PRDs:        \(.prds)\n"
  + "  roadmap:     \(.roadmap)\n"
  + "  src roots:   \(.srcRoots | join(", "))\n"
  + (if .stack then "  stack:       \(.stack)\n" else "" end)
  + "Only this project is in scope. Do not read or write docs belonging to another project. "
  + "To switch projects, run /set-project"
  + (if (.aliases | length) > 0 then " (this one also answers to: \(.aliases | join(", ")))." else "." end)
' "$manifest" 2>/dev/null) || exit 0

[ -z "$ctx" ] && exit 0
emit "$ctx"
