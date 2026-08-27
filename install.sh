#!/bin/sh
# Install this Claude Code configuration as <target>/.claude
#
# Two modes, because they have opposite trade-offs:
#
#   snapshot (default)  a plain copy with no .git — the project owns it outright and is
#                       expected to prune and diverge. Nothing flows back here.
#   --submodule         a git submodule pinned to this repo — fixes flow both ways, but a
#                       fresh clone of the host repo has an empty .claude/ until
#                       `git submodule update --init`, and that first session runs with no
#                       agents, no skills, and no hooks.
#
# Usage:
#   ./install.sh <target-dir> [--submodule] [--force]
#   curl -fsSL https://raw.githubusercontent.com/EhrenDavis12/.claude/main/install.sh | sh -s -- .
set -eu

REPO="https://github.com/EhrenDavis12/.claude.git"
TARGET=""
MODE="snapshot"
FORCE=0

for arg in "$@"; do
  case "$arg" in
    --submodule) MODE="submodule" ;;
    --force)     FORCE=1 ;;
    -h|--help)   sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)          echo "install.sh: unknown option $arg" >&2; exit 2 ;;
    *)           TARGET="$arg" ;;
  esac
done

[ -n "$TARGET" ] || { echo "usage: install.sh <target-dir> [--submodule] [--force]" >&2; exit 2; }
[ -d "$TARGET" ] || { echo "install.sh: no such directory: $TARGET" >&2; exit 1; }

TARGET=$(cd "$TARGET" && pwd)
DEST="$TARGET/.claude"

if [ -e "$DEST" ] && [ "$FORCE" -ne 1 ]; then
  echo "install.sh: $DEST already exists. Move it aside, or pass --force to replace it." >&2
  exit 1
fi

command -v git >/dev/null 2>&1 || { echo "install.sh: git is required." >&2; exit 1; }

if [ "$MODE" = "submodule" ]; then
  git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1 || {
    echo "install.sh: --submodule needs $TARGET to be a git repository." >&2; exit 1; }
  [ "$FORCE" -eq 1 ] && rm -rf "$DEST"
  git -C "$TARGET" submodule add "$REPO" .claude
  echo "Installed $DEST as a submodule of $REPO"
else
  # Source the payload from this checkout if we are running inside one, otherwise fetch it.
  SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
  TMP=""
  if [ ! -f "$SRC/systems/README.md" ]; then
    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT INT TERM
    git clone --quiet --depth 1 "$REPO" "$TMP/payload"
    SRC="$TMP/payload"
  fi

  rm -rf "$DEST"
  mkdir -p "$DEST"
  # -a would drag in .git and the installer itself; enumerate instead.
  for entry in "$SRC"/* "$SRC"/.[!.]*; do
    [ -e "$entry" ] || continue
    name=$(basename "$entry")
    case "$name" in .git|.github|install.sh) continue ;; esac
    cp -R "$entry" "$DEST/$name"
  done
  echo "Installed $DEST (snapshot)"
fi

cat <<'NEXT'

Three things are not optional — see README.md for the detail:

  1. The project needs a CLAUDE.md ending in exactly one import line naming the active system,
     e.g.  @.claude/systems/forge/SYSTEM.md
  2. .claude/project/active.json must name a project that a Docs/*/project.json declares.
  3. jq must be on PATH — every hook needs it, and they fail silently without it.

Then prune what does not apply to this project (playtest, generate-asset, create-pr, otel)
and start a session.
NEXT
