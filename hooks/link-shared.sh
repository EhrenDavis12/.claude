#!/bin/sh
# Keep a host project's .claude/ linked to this repo when it is installed as a submodule.
#
# The host's .claude/ is a real directory that mixes two kinds of entry:
#   - shared   : symlinks into this repo (agents, hooks, the forge system, ...)
#   - host-only: real files the host owns and never sends upstream (its own skills,
#                commands, settings.json, project/active.json, metrics/)
#
# A directory that holds only shared entries is linked whole, so new upstream files
# appear at once. A directory that also holds host-only entries is linked entry by entry,
# and a new upstream sibling is invisible until it gets its own link. This script adds
# those links. It runs as a SessionStart hook (silent unless it changed something) and
# as `install.sh --link`.
#
# Rules — every one is what makes this safe to run unattended:
#   - never replace, edit, or delete a real file or directory
#   - never create a link whose target does not exist
#   - remove a symlink only when it points into this repo and its target is gone
#   - skip anything listed in <host>/.claude/.linkignore (one path per line, relative to
#     .claude/, e.g. `skills/playtest`) — that file is the host's, not this repo's
#   - link only what belongs to a host: not .git, install.sh, README.md, the settings.json
#     template, or project/ and metrics/ (per-host state)
#
# Usage: link-shared.sh [host-root]      defaults to $CLAUDE_PROJECT_DIR, then cwd
set -eu

HOST=${1:-${CLAUDE_PROJECT_DIR:-$(pwd)}}
HOST=$(cd "$HOST" && pwd -P)
DEST="$HOST/.claude"
# Physical location of this repo, resolved through whatever symlink invoked us.
REPO=$(cd -P "$(dirname "$0")/.." && pwd -P)

[ -d "$DEST" ] || exit 0
case "$REPO" in "$HOST"/*) ;; *) exit 0 ;; esac   # not a submodule of this host
[ "$REPO" = "$DEST" ] && exit 0                    # installed as .claude itself — nothing to link
REL=${REPO#"$HOST"/}                                # e.g. src/claude-repo

IGNORE="$DEST/.linkignore"
ignored() { [ -f "$IGNORE" ] && grep -qxF "$1" "$IGNORE"; }

added=""; removed=""

# link <path relative to .claude> — target is the same path in this repo.
link() {
  p=$1
  up=""; rest=$p
  while [ "${rest#*/}" != "$rest" ]; do up="../$up"; rest=${rest#*/}; done
  ln -s "../${up}${REL}/$p" "$DEST/$p"
  added="$added $p"
}

for entry in "$REPO"/*; do
  name=$(basename "$entry")
  case "$name" in .git|.github|install.sh|README.md|settings.json|project|metrics) continue ;; esac
  ignored "$name" && continue

  if [ ! -e "$DEST/$name" ] && [ ! -L "$DEST/$name" ]; then
    link "$name"                                  # nothing here yet: link the whole entry
  elif [ -d "$DEST/$name" ] && [ ! -L "$DEST/$name" ] && [ -d "$entry" ]; then
    for child in "$entry"/*; do                   # real dir here: link entry by entry
      [ -e "$child" ] || continue
      c="$name/$(basename "$child")"
      ignored "$c" && continue
      [ -e "$DEST/$c" ] || [ -L "$DEST/$c" ] || link "$c"
    done
  fi
done

# Drop links into this repo whose target has gone away upstream.
for l in $(find "$DEST" -maxdepth 2 -type l); do
  case "$(readlink "$l")" in *"/$REL/"*) [ -e "$l" ] || { rm "$l"; removed="$removed ${l#"$DEST"/}"; } ;; esac
done

[ -n "$added" ]   && echo "link-shared: linked$added"
[ -n "$removed" ] && echo "link-shared: removed dangling$removed"
exit 0
