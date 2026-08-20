#!/usr/bin/env bash
# sim.sh — see and touch the booted iOS Simulator.
#
# Every coordinate this script takes or prints is a *screenshot pixel* — the same
# coordinate you read straight off the PNG that `shot` produces. The device-point
# and macOS-screen conversions happen in here so nothing upstream has to know the
# device's scale factor or where the window sits.
#
# Requires: cliclick (brew install cliclick), Xcode command line tools, and
# Accessibility permission for the terminal running this.

set -euo pipefail

CACHE="${TMPDIR:-/tmp}/sim-geometry.cache"

die() { echo "sim.sh: $*" >&2; exit 1; }

osa() {
  osascript -e "tell application \"System Events\" to tell process \"Simulator\" to $1" 2>/dev/null \
    || die "could not talk to Simulator. Is it running, and does this terminal have Accessibility permission? (System Settings -> Privacy & Security -> Accessibility)"
}

require_booted() {
  xcrun simctl list devices booted 2>/dev/null | grep -q Booted \
    || die "no booted simulator. Boot one with: xcrun simctl boot '<device name>' && open -a Simulator"
}

# Position of the Simulator window, re-read every time so moving the window
# mid-session doesn't silently send taps to the wrong place.
window_frame() { osa 'get {position, size} of window 1' | tr -d ' '; }

# --- prep -------------------------------------------------------------------
# Puts the Simulator into the one configuration where the mapping is a pure
# translation: bezels off (window content is exactly the screen) and Point
# Accurate zoom (1 device point == 1 macOS point, so scale is only the device's
# own pixel ratio). Writes the derived scale and title-bar height to a cache.
cmd_prep() {
  require_booted
  osascript -e 'tell application "Simulator" to activate' >/dev/null

  # "Show Device Bezels" is a checkbox; only click it when it is on.
  local marked
  marked=$(osa 'get value of attribute "AXMenuItemMarkChar" of menu item "Show Device Bezels" of menu 1 of menu bar item "Window" of menu bar 1' || echo "")
  if [ "$marked" = "✓" ]; then
    osa 'click menu item "Show Device Bezels" of menu 1 of menu bar item "Window" of menu bar 1' >/dev/null
    sleep 0.4
  fi

  osa 'click menu item "Point Accurate" of menu 1 of menu bar item "Window" of menu bar 1' >/dev/null
  sleep 0.6

  local frame win_w win_h shot px_w px_h scale titlebar
  frame=$(window_frame)
  win_w=$(echo "$frame" | cut -d, -f3)
  win_h=$(echo "$frame" | cut -d, -f4)

  shot="${TMPDIR:-/tmp}/sim-prep-shot.png"
  xcrun simctl io booted screenshot --type=png "$shot" >/dev/null 2>&1 \
    || die "screenshot failed — is a device booted?"
  px_w=$(sips -g pixelWidth  "$shot" | awk '/pixelWidth/{print $2}')
  px_h=$(sips -g pixelHeight "$shot" | awk '/pixelHeight/{print $2}')

  # In Point Accurate with bezels off the window is exactly as wide as the
  # device, so the device's pixel ratio falls out of the width alone.
  scale=$(awk -v p="$px_w" -v w="$win_w" 'BEGIN{printf "%.6f", p/w}')
  titlebar=$(awk -v h="$win_h" -v p="$px_h" -v s="$scale" 'BEGIN{printf "%.3f", h - p/s}')

  printf 'scale=%s\ntitlebar=%s\npx_w=%s\npx_h=%s\n' "$scale" "$titlebar" "$px_w" "$px_h" > "$CACHE"
  echo "ready — screen ${px_w}x${px_h}px at ${scale}x, window $(echo "$frame" | cut -d, -f1,2), title bar ${titlebar}pt"
}

load_cache() {
  [ -f "$CACHE" ] || cmd_prep >/dev/null
  # shellcheck disable=SC1090
  . "$CACHE"
}

# --- geom -------------------------------------------------------------------
cmd_geom() {
  load_cache
  echo "screen:   ${px_w}x${px_h} px  (scale ${scale}x)"
  echo "window:   $(window_frame)"
  echo "titlebar: ${titlebar} pt"
}

# --- shot -------------------------------------------------------------------
cmd_shot() {
  require_booted
  local out="${1:-${TMPDIR:-/tmp}/sim-shot.png}"
  xcrun simctl io booted screenshot --type=png "$out" >/dev/null 2>&1 \
    || die "screenshot failed"
  echo "$out"
}

# Screenshot pixel -> macOS screen point, emitted as a *signed offset from the
# global origin*. cliclick reads a leading "-" as a relative move, so a negative
# absolute coordinate cannot be expressed directly — and every coordinate is
# negative whenever the Simulator sits on a display left of the main one. Hopping
# to 0,0 first and then moving by a signed delta reaches any point on any display.
to_screen() {
  local px="$1" py="$2" frame wx wy win_w
  frame=$(window_frame)
  wx=$(echo "$frame" | cut -d, -f1)
  wy=$(echo "$frame" | cut -d, -f2)
  win_w=$(echo "$frame" | cut -d, -f3)
  # A stale cache is the one failure that stays silent: the tap still lands
  # somewhere, just not where it was aimed. The window width is the tell, since
  # in Point Accurate it must equal the device width, so check it before aiming.
  awk -v w="$win_w" -v p="$px_w" -v s="$scale" \
    'BEGIN{ exit ((w - p/s) < 1 && (w - p/s) > -1) ? 0 : 1 }' \
    || die "the Simulator window no longer matches the cached geometry (zoom, bezels, or device changed) — run: sim.sh prep"
  awk -v px="$px" -v py="$py" -v wx="$wx" -v wy="$wy" -v s="$scale" -v t="$titlebar" \
    'BEGIN{printf "%+d,%+d", int(wx + px/s + 0.5), int(wy + t + py/s + 0.5)}'
}

# Park the cursor on a point given as a signed offset from the origin.
move_to() { cliclick m:0,0 "m:$1" >/dev/null; }

focus() { osascript -e 'tell application "Simulator" to activate' >/dev/null; sleep 0.25; }

# --- tap --------------------------------------------------------------------
cmd_tap() {
  [ $# -ge 2 ] || die "usage: sim.sh tap <x> <y>   (screenshot pixel coordinates)"
  load_cache; focus
  local pt; pt=$(to_screen "$1" "$2")
  move_to "$pt"
  cliclick -w 60 c:.
  echo "tapped ${1},${2}px -> screen ${pt}"
}

# --- swipe ------------------------------------------------------------------
cmd_swipe() {
  [ $# -ge 4 ] || die "usage: sim.sh swipe <x1> <y1> <x2> <y2> [steps]"
  load_cache; focus
  local from to steps i fx fy tx ty cx cy nx ny
  from=$(to_screen "$1" "$2"); to=$(to_screen "$3" "$4"); steps="${5:-12}"
  fx=${from%,*}; fy=${from#*,}; tx=${to%,*}; ty=${to#*,}

  move_to "$from"
  cliclick -w 40 dd:.
  # Once the drag is underway the cursor must never leave the path — so each
  # intermediate point is a delta from the last one, not another hop via the
  # origin. Hopping mid-drag traces a zig-zag through 0,0 that no gesture
  # recogniser reads as a swipe, which is exactly how the first version failed.
  cx=$fx; cy=$fy
  for ((i = 1; i <= steps; i++)); do
    nx=$(awk -v a="$fx" -v b="$tx" -v i="$i" -v s="$steps" 'BEGIN{printf "%d", a+(b-a)*i/s}')
    ny=$(awk -v c="$fy" -v d="$ty" -v i="$i" -v s="$steps" 'BEGIN{printf "%d", c+(d-c)*i/s}')
    cliclick -w 12 "m:$(awk -v a="$nx" -v b="$cx" 'BEGIN{printf "%+d", a-b}'),$(awk -v a="$ny" -v b="$cy" 'BEGIN{printf "%+d", a-b}')" >/dev/null
    cliclick -w 12 dm:. >/dev/null
    cx=$nx; cy=$ny
  done
  cliclick -w 40 du:.
  echo "swiped ${1},${2} -> ${3},${4}"
}

# --- text / keys ------------------------------------------------------------
cmd_type() { [ $# -ge 1 ] || die "usage: sim.sh type <text>"; focus; cliclick -w 20 "t:$*"; echo "typed"; }
cmd_key()  { [ $# -ge 1 ] || die "usage: sim.sh key <return|esc|space|...>"; focus; cliclick "kp:$1"; echo "pressed $1"; }

# --- device buttons ---------------------------------------------------------
cmd_home() { focus; osa 'click menu item "Home" of menu 1 of menu bar item "Device" of menu bar 1' >/dev/null; echo "home"; }

# --- record / frames --------------------------------------------------------
# A still cannot show whether an animation eases right, so record the motion and
# lay it out as a contact sheet — a strip of stills is something that can
# actually be looked at, where a video file is not. Recording is start/stop
# rather than a fixed duration because the taps worth filming happen in between.
RECPID="${TMPDIR:-/tmp}/sim-recording.pid"
RECOUT="${TMPDIR:-/tmp}/sim-recording.mp4"

cmd_rec_start() {
  require_booted
  [ -f "$RECPID" ] && die "already recording — run 'sim.sh rec-stop' first"
  RECOUT="${1:-$RECOUT}"
  rm -f "$RECOUT"
  xcrun simctl io booted recordVideo --codec=h264 --force "$RECOUT" >/dev/null 2>&1 &
  echo "$!" > "$RECPID"
  echo "$RECOUT" > "${RECPID}.out"
  sleep 1   # the recorder drops the opening moments if it is not given time to attach
  echo "recording -> $RECOUT"
}

cmd_rec_stop() {
  [ -f "$RECPID" ] || die "not recording"
  local pid out
  pid=$(cat "$RECPID"); out=$(cat "${RECPID}.out")
  # simctl only finalises the container on SIGINT; killing it harder loses the file.
  kill -INT "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  rm -f "$RECPID" "${RECPID}.out"
  [ -s "$out" ] || die "recording produced nothing"
  echo "$out"
}

cmd_frames() {
  [ $# -ge 1 ] || die "usage: sim.sh frames <video> [count] [out.png]"
  local vid="$1" count="${2:-9}" out="${3:-${TMPDIR:-/tmp}/sim-frames.png}"
  [ -f "$vid" ] || die "no such video: $vid"
  command -v ffmpeg >/dev/null || die "ffmpeg not installed (brew install ffmpeg)"
  local dur fps cols rows
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$vid")
  # Spread the requested number of frames evenly across the whole clip.
  fps=$(awk -v c="$count" -v d="$dur" 'BEGIN{printf "%.4f", c/d}')
  cols=$(awk -v c="$count" 'BEGIN{printf "%d", int(sqrt(c)+0.999)}')
  rows=$(awk -v c="$count" -v k="$cols" 'BEGIN{printf "%d", int((c+k-1)/k)}')
  ffmpeg -v error -y -i "$vid" \
    -vf "fps=${fps},scale=240:-1,tile=${cols}x${rows}:margin=6:padding=4:color=0x202020" \
    -frames:v 1 "$out" >/dev/null 2>&1 || die "ffmpeg could not build the contact sheet"
  echo "$out"
}

# --- view -------------------------------------------------------------------
# Screenshots are far larger than they need to be to look at, but shrinking one
# by hand means every coordinate read off it has to be scaled back up — which is
# an easy sum to get wrong and a tap that silently lands on the wrong square. So
# the downscale and the multiplier are produced together.
cmd_view() {
  [ $# -ge 1 ] || die "usage: sim.sh view <shot.png> [maxdim]"
  local src="$1" max="${2:-800}" out h mult
  [ -f "$src" ] || die "no such screenshot: $src"
  out="${src%.png}_view.png"
  sips -Z "$max" "$src" --out "$out" >/dev/null 2>&1 || die "could not resize"
  h=$(sips -g pixelHeight "$src" | awk '/pixelHeight/{print $2}')
  local vh; vh=$(sips -g pixelHeight "$out" | awk '/pixelHeight/{print $2}')
  mult=$(awk -v a="$h" -v b="$vh" 'BEGIN{printf "%.4f", a/b}')
  echo "$out"
  echo "multiply coordinates read off this image by $mult to get tap coordinates"
}

usage() {
  cat <<'USAGE'
sim.sh — see and touch the booted iOS Simulator. All coordinates are screenshot pixels.

  prep                      configure the Simulator so taps land accurately (run once per session)
  geom                      print the current screen size, scale, and window position
  shot [path]               screenshot to path (prints the path)
  view <shot> [maxdim]      shrink a screenshot for viewing, print the coordinate multiplier
  tap <x> <y>               tap at a screenshot pixel
  swipe <x1> <y1> <x2> <y2> [steps]   drag across the screen
  type <text>               type text into the focused field
  key <name>                press a key (return, esc, space, ...)
  home                      press the Home button
  rec-start [out]           start recording video of the screen
  rec-stop                  stop recording (prints the video path)
  frames <video> [n] [out]  lay a recording out as a contact sheet of n stills
USAGE
}

case "${1:-}" in
  prep)  shift; cmd_prep "$@" ;;
  geom)  shift; cmd_geom "$@" ;;
  shot)  shift; cmd_shot "$@" ;;
  view)  shift; cmd_view "$@" ;;
  tap)   shift; cmd_tap "$@" ;;
  swipe) shift; cmd_swipe "$@" ;;
  type)  shift; cmd_type "$@" ;;
  key)   shift; cmd_key "$@" ;;
  home)      shift; cmd_home "$@" ;;
  rec-start) shift; cmd_rec_start "$@" ;;
  rec-stop)  shift; cmd_rec_stop "$@" ;;
  frames)    shift; cmd_frames "$@" ;;
  *)     usage; exit 1 ;;
esac
