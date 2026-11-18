#!/bin/zsh
# After every merge into a srcRoot's main: push it, push the root (EhrensDocs and the moved
# pointers), and refresh the user's play copy so the Unity editor they look at is always the
# latest approved game. The user asked for this on 2026-11-17: "keep both up-to-date and
# always pushed ... kill off the running unity instance and update the unity instance".
#
#   sync.sh            push, then refresh the play copy
#   sync.sh --no-play  push only
#
# Stops on the first problem — a push refused, a merge from origin that conflicts — and says
# so; it never forces anything.
set -u
ROOT=${0:A:h:h:h:h:h}
GAME=$ROOT/src/guildmasters-descent
PLAY=$HOME/work/gmd-play
UNITY=/Applications/Unity/Hub/Editor/6000.6.2f1/Unity.app

cd "$ROOT" || exit 1

git -C "$GAME" push -q origin main || { echo "sync: game push refused"; exit 1; }

git fetch -q origin
if [ -n "$(git rev-list HEAD..origin/main)" ]; then
  if ! git merge -q --no-edit origin/main -m "Merge online edits into this checkout"; then
    git merge --abort
    echo "sync: root merge from origin conflicts — aborted, nothing pushed"
    exit 1
  fi
fi
git push -q origin main || { echo "sync: root push refused"; exit 1; }
echo "sync: game and root pushed ($(git -C "$GAME" rev-parse --short main))"

[ "${1:-}" = "--no-play" ] && exit 0
[ -d "$PLAY" ] || { echo "sync: no play copy at $PLAY"; exit 0; }

if [ "$(git -C "$PLAY" rev-parse HEAD)" = "$(git -C "$GAME" rev-parse main)" ]; then
  echo "sync: play copy already current"
  exit 0
fi

pid=$(pgrep -f "MacOS/Unity -projectPath $PLAY" | head -1)
if [ -n "$pid" ]; then
  kill -TERM "$pid"
  for i in {1..45}; do pgrep -f "projectPath $PLAY" >/dev/null || break; sleep 2; done
  pgrep -f "projectPath $PLAY" >/dev/null && { echo "sync: Unity on the play copy would not close"; exit 1; }
fi
rm -f "$PLAY/Temp/UnityLockfile"
git -C "$PLAY" checkout -q --detach main || { echo "sync: play copy checkout failed"; exit 1; }
open -n -a "$UNITY" --args -projectPath "$PLAY"
echo "sync: play copy at $(git -C "$PLAY" rev-parse --short HEAD), Unity reopened"
