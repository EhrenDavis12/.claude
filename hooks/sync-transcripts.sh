#!/usr/bin/env bash
# Copy this project's Claude Code session transcripts from ~/.claude/projects/<cwd>/
# into .claude/metrics/transcripts/, so the weekly agent review can read them
# (Cowork can't open ~/.claude). One-way, incremental, never deletes; gitignored.
# Called from capture-agent-metrics.sh. Must never fail a turn.
set -uo pipefail
DIR="${1:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
SRC="${HOME}/.claude/projects/$(printf '%s' "$DIR" | sed 's/[^a-zA-Z0-9]/-/g')"
DEST="$DIR/.claude/metrics/transcripts"
[ -d "$SRC" ] || exit 0
command -v rsync >/dev/null 2>&1 || exit 0
mkdir -p "$DEST"
rsync -a --include='*/' --include='*.jsonl' --exclude='*' "$SRC/" "$DEST/" || true
exit 0
