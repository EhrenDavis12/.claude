# Wiring reference

Read this before writing any hook. Load it only when a hook is actually on the table —
tier 1 needs nothing from this file.

## The central constraint

**A hook cannot dispatch an agent.** Hook actions are `command` (run a shell command) and
`prompt` (run an LLM evaluation). There is no "launch subagent" action. The `Agent(...)` call
is always made by the main loop.

So a hook's job here is to make the trigger *impossible to miss* — by feeding a message back
into the conversation, or by refusing to let the turn end.

## Choose the event by when the condition becomes true

This is the decision that gets made wrong. `PostToolUse` is the familiar event, so it gets
reached for by default — but it only fires when **Claude** uses a tool. If the condition the
agent cares about is created by the *user*, outside the session, `PostToolUse` never sees it.

Ask: **who makes this condition true, and when?**

| The condition becomes true… | Event |
|---|---|
| When Claude edits a file | `PostToolUse` |
| While the user works outside the session (hand-edits, pulls, external tooling) | `SessionStart` |
| At the end of a unit of work | `Stop` |
| Based on what the user just asked for | `UserPromptSubmit` |

`forge-doc-planner` is the worked example. Its docs are hand-written by the user between sessions,
so "docs changed and weren't tidied" is almost always true *before Claude Code starts*. A
`PostToolUse` hook on `Write|Edit` would be near-silent in real use. `SessionStart` catches it
at the only moment it can be observed. If Claude also edits a doc mid-session, it already
knows — that case needs no hook at all.

**Git pathspecs are case-sensitive.** `git status -- Docs` matches nothing when the tracked
path is `docs/`, and the hook then fails *silently* — the exact failure that made this hook a
permanent no-op until it was caught. Take the path from the project manifest, which stores it
as it is really tracked, and never hardcode a spelling.

Corollary: if the in-session case is already visible to Claude, don't add a second hook for
it. One hook at the right moment beats two at the wrong ones.

## Tier 1 — On-demand (default)

No hook. The agent fires because its `description` matches the situation and `CLAUDE.md`
tells Claude to dispatch it.

```
Agent(subagent_type: "NAME", prompt: "...")
```

Probabilistic but free. Correct for anything a person explicitly asks for. **Start here.**

## Tier 2 — Reminder hook

A **command** hook that checks a cheap condition and hands Claude a reminder. Non-blocking:
it informs, it doesn't compel. Two shapes depending on the event you picked above.

### Shape A — `SessionStart` (condition created outside the session)

Fires once per session, cannot loop, cannot block. Emit
`hookSpecificOutput.additionalContext` on stdout to inject context. This is the shape
`forge-doc-planner` uses — see `.claude/hooks/docs-pending.sh`.

```bash
#!/bin/bash
set -euo pipefail
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
command -v jq >/dev/null 2>&1 || exit 0            # no jq → say nothing, don't emit bad JSON

root=$(...)   # resolve from the project manifest; never hardcode a path

changed=$(git status --porcelain -- "$root" 2>/dev/null) || exit 0  # not a repo → silent
[ -z "$changed" ] && exit 0                                          # nothing pending → silent

# Porcelain v1 is "XY " then the path, so cut -c4- strips the status. Renames arrive as
# `old -> new`; keep the new name. `paste -d` takes a *cyclic list* of delimiters, so ', '
# would alternate comma and space — join on a single comma.
files=$(printf '%s\n' "$changed" | cut -c4- | sed 's/^.* -> //; s/^"//; s/"$//' | paste -sd, -)
jq -cn --arg files "$files" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: ("... mentioning \($files) and the exact Agent(...) call to make")
  }
}'
```

Silence on every uninteresting path is the point: no repo, no changes, no jq → exit 0 and say
nothing.

### Shape B — `PostToolUse` (condition created by Claude's own edits)

Fires on a tight matcher and exits 2 so its stderr is fed back to Claude as feedback.

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/remind-NAME.sh",
      "timeout": 5
    }
  ]
}
```

```bash
#!/bin/bash
# .claude/hooks/remind-NAME.sh — exit 2 puts stderr in front of Claude.
set -euo pipefail

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')

# Narrow to the agent's actual territory. Everything else is a silent no-op.
case "$file_path" in
  */Docs/*.md) ;;
  *) exit 0 ;;
esac

echo 'A design doc changed. Dispatch: Agent(subagent_type: "forge-doc-planner", prompt: "Design docs were just edited — plan what needs tidying.")' >&2
exit 2
```

Costs a few milliseconds of shell per matching tool call and zero model tokens until it
actually fires. This is the right tier for "must happen after X, and X is easy to forget."

## Tier 3 — Enforcement hook

A `Stop` **command** hook that blocks the turn from ending until a condition clears.

```json
{
  "matcher": "*",
  "hooks": [
    { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/require-NAME.sh", "timeout": 10 }
  ]
}
```

The script emits `{"decision": "block", "reason": "..."}` on stdout to block, or exits 0
silently to allow the stop.

### Loop safety — read this before choosing tier 3

A `Stop` hook that never clears wedges the session. Four rules, all mandatory:

1. **The condition must be one the agent's own run clears.** If the agent can run to
   completion and the condition still holds, you have built an infinite loop. Test the
   condition's clearing path *before* installing the hook.
2. **Block at most once per condition.** Use a sentinel file keyed to the triggering state,
   and check it first:
   ```bash
   STATE=$(git -C "$CLAUDE_PROJECT_DIR" status --porcelain -- "$root" | shasum | cut -d' ' -f1)
   SENTINEL="$CLAUDE_PROJECT_DIR/.claude/.hook-state/NAME-$STATE"
   [ -f "$SENTINEL" ] && exit 0        # already blocked once for this exact state
   mkdir -p "$(dirname "$SENTINEL")" && touch "$SENTINEL"
   ```
   Add `.claude/.hook-state/` to `.gitignore`.
3. **The `reason` must name the exact call to make.** A vague reason ("cleanup is needed")
   produces a retry loop; a precise one gets acted on immediately:
   ```json
   {"decision": "block", "reason": "Uncommitted design-doc changes have not been tidied. Run: Agent(subagent_type: \"forge-doc-planner\", prompt: \"Design docs were just edited — plan what needs tidying.\")"}
   ```
4. **Document the escape hatch.** Tell the user, at install time: the hook is one entry in
   `settings.json`; deleting it and restarting Claude Code always recovers a wedged session.

## Hook facts that bite

- **Hooks load at session start.** Editing `settings.json` or a hook script has *no effect* on
  the running session. A restart is required. Never report a hook as working until a restart
  has verified it.
- **Matchers are case-sensitive.** `write` does not match `Write`.
- **Hooks on the same event run in parallel** and cannot see each other's output. Design each
  to stand alone.
- **Exit codes:** `0` → stdout shown in transcript; `2` → stderr fed back to Claude; anything
  else → non-blocking error.
- **Never use `prompt`-type hooks for agent wiring.** They fire a real LLM call on every
  match. A `PostToolUse` prompt hook on `Write|Edit` bills a model call on every single file
  edit — the exact bloat this skill exists to prevent.
- **Quote every variable** (`"$file_path"`, `"$CLAUDE_PROJECT_DIR"`) and `set -euo pipefail`.
- **Keep timeouts short** (5–10s). A slow hook stalls every matching tool call.

## Installing

1. Hook scripts go in `.claude/hooks/`, `chmod +x`, referenced via `"$CLAUDE_PROJECT_DIR"`.
2. **The `settings.json` edit goes through the `/update-config` skill** — it owns settings
   correctness, including the exact nesting of the hooks block. Do not hand-write it.
3. Test the script standalone before wiring it up — cover the fire case, the silent case, and
   a hostile case (not a git repo, missing field):
   ```bash
   # SessionStart: most take no meaningful stdin
   echo '{}' | .claude/hooks/NAME.sh; echo "exit=$?"
   # PostToolUse: synthesize the tool payload
   echo '{"tool_name":"Edit","tool_input":{"file_path":"/x/Docs/Rules.md"}}' | .claude/hooks/NAME.sh; echo "exit=$?"
   ```
   If the script manufactures a condition to test (e.g. dirtying a file), **restore it** and
   confirm with `git status` before moving on.
4. After the settings edit, run the command string *as settings.json stores it* — this catches
   quoting bugs that a direct script invocation misses:
   ```bash
   CMD=$(jq -r '.hooks.<event>[0].hooks[0].command' .claude/settings.json)
   echo '{}' | eval "$CMD"; echo "exit=$?"
   ```
   And assert no non-command hooks slipped in:
   ```bash
   jq -e '[.hooks[][].hooks[] | select(.type != "command")] | length == 0' .claude/settings.json
   ```
5. Restart Claude Code, then confirm with `/hooks` (lists what actually loaded) or
   `claude --debug`. **Until then the hook is written but unproven — say so.**
6. Record the tier in the agent's roster row in `.claude/agents/README.md`.
