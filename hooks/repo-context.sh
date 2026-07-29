#!/bin/bash
# Injects the repo's context at session start: the active project, the active agent system, and
# a check that the two halves of a system swap actually agree.
#
# Both are properties of the repo, not of any one agent system, so this hook belongs to no
# system and is never gated. Agents resolve their own project scope by reading the pointer and
# manifest themselves — that read is authoritative. This hook exists so the *main loop* knows
# what it is operating under without going looking, and so a session that is misconfigured says
# so out loud instead of silently running in a mixed state.
#
# Non-blocking: injects context, decides nothing. See
# .claude/skills/agent-creator/references/wiring.md
set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# No jq — say nothing rather than emit malformed JSON.
command -v jq >/dev/null 2>&1 || exit 0

POINTER=".claude/project/active.json"
SETTINGS=".claude/settings.json"

emit() {
  jq -cn --arg ctx "$1" '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: $ctx
    }
  }'
}

alerts=""
alert() { alerts="${alerts}!! $1"$'\n'; }

# ---------------------------------------------------------------------------
# The active system
#
# CLAUDE.md's single import line is the source of truth. Everything else — the deny list, the
# skill overrides, each system hook's self-gate — derives from it. This block is the guard rail
# for the one thing the harness will not complain about on its own.
# ---------------------------------------------------------------------------
system=""
import_re='^@\.claude/systems/[a-z0-9-]+/SYSTEM\.md$'
n_imports=$(grep -cE "$import_re" CLAUDE.md 2>/dev/null || true)
n_imports=${n_imports:-0}

if [ "$n_imports" -eq 0 ]; then
  alert "CLAUDE.md names no active system. Expected exactly one line matching @.claude/systems/<name>/SYSTEM.md — no system rules are loaded. Ask the user to run /set-system (user-only command)."
elif [ "$n_imports" -gt 1 ]; then
  alert "CLAUDE.md has $n_imports system import lines; exactly one is allowed. Two systems' rules are in context at once, which is the thing this design exists to prevent. Ask the user to run /set-system to fix (user-only command)."
else
  target=$(grep -E "$import_re" CLAUDE.md | head -1)
  target=${target#@}
  system=$(basename "$(dirname "$target")")
  if [ ! -f "$target" ]; then
    # It is not documented whether a dangling @ import fails loudly or is silently skipped.
    # This check is what makes it visible either way.
    alert "CLAUDE.md imports $target but that file does not exist. The active system's rules are missing from this session. Ask the user to run /set-system to repoint it (user-only command)."
    system=""
  fi
fi

# ---------------------------------------------------------------------------
# Drift: settings.json vs. the active system
#
# A swap has two halves — the import line and settings.json — written by /set-system in that
# order. Disagreement means a half-finished swap, so say so rather than run mixed.
# ---------------------------------------------------------------------------
if [ -n "$system" ] && [ -f "$SETTINGS" ] && compgen -G ".claude/systems/*/system.json" >/dev/null; then
  want_deny=$(jq -rs --arg sys "$system" \
    '[.[] | select(.name != $sys) | .agents[]? | "Agent(\(.))"] | unique | join(",")' \
    .claude/systems/*/system.json 2>/dev/null || echo "")
  want_skills=$(jq -rs --arg sys "$system" \
    '[.[] | select(.name != $sys) | .skills[]?] | unique | join(",")' \
    .claude/systems/*/system.json 2>/dev/null || echo "")

  have_deny=$(jq -r \
    '[.permissions.deny[]? | select(startswith("Agent("))] | unique | join(",")' \
    "$SETTINGS" 2>/dev/null || echo "")
  have_skills=$(jq -r \
    '[(.skillOverrides // {}) | to_entries[] | select(.value == "off") | .key] | unique | join(",")' \
    "$SETTINGS" 2>/dev/null || echo "")

  if [ "$want_deny" != "$have_deny" ]; then
    alert "Half-finished system swap: with \"$system\" active, settings.json should deny [${want_deny:-none}] but denies [${have_deny:-none}]. Agents from an inactive system are still dispatchable. Ask the user to re-run /set-system $system (user-only command)."
  fi
  if [ "$want_skills" != "$have_skills" ]; then
    alert "Half-finished system swap: with \"$system\" active, settings.json should switch off [${want_skills:-none}] but switches off [${have_skills:-none}]. Ask the user to re-run /set-system $system (user-only command)."
  fi
fi

sys_line=""
if [ -n "$system" ]; then
  title=$(jq -r '.title // .name' ".claude/systems/$system/system.json" 2>/dev/null || echo "$system")
  sys_line="Active system: $system — $title. Its rules are imported at the end of CLAUDE.md. To swap, the user runs /set-system — it is a user-only command; you cannot swap systems yourself."$'\n'
fi

# ---------------------------------------------------------------------------
# The active project
# ---------------------------------------------------------------------------
finish() {
  # $1 is the project half; alerts are appended last so they are the freshest thing read.
  out="${sys_line}$1"
  [ -n "$alerts" ] && out="${out}"$'\n'"${alerts}"
  emit "$out"
  exit 0
}

if [ ! -f "$POINTER" ]; then
  finish "No active project is set. Agents that resolve their scope from the manifest will refuse to run until one is. Ask the user to run /set-project — it is a user-only command; you cannot run it yourself."
fi

slug=$(jq -r '.project // empty' "$POINTER" 2>/dev/null) || slug=""
if [ -z "$slug" ]; then
  finish "$POINTER exists but names no project. Ask the user to run /set-project (user-only command)."
fi

# Convention is Docs/<slug>/project.json, but the manifest whose .name matches the slug wins —
# so a project folder can be renamed without breaking the pointer.
#
# Deliberately matches .name only, never .aliases: /set-project resolves aliases at activation
# time and always writes the canonical name here, so a pointer holding an alias is a bug worth
# surfacing rather than quietly accepting.
manifest=""
for candidate in "Docs/$slug/project.json" Docs/*/project.json; do
  [ -f "$candidate" ] || continue
  if [ "$(jq -r '.name // empty' "$candidate" 2>/dev/null)" = "$slug" ]; then
    manifest="$candidate"
    break
  fi
done

if [ -z "$manifest" ]; then
  finish "The active project is \"$slug\" but no Docs/*/project.json declares that name. The manifest is missing or its .name does not match. Ask the user to run /set-project (user-only command) before dispatching any agent."
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
  + "To switch projects the user runs /set-project — a user-only command you cannot run"
  + (if (.aliases | length) > 0 then " (this one also answers to: \(.aliases | join(", ")))." else "." end)
' "$manifest" 2>/dev/null) || ctx=""

[ -z "$ctx" ] && [ -z "$sys_line" ] && [ -z "$alerts" ] && exit 0
finish "$ctx"
