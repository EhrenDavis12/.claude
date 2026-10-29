#!/bin/bash
# annie's runner: checks the queue every few seconds with no Claude and no tokens, and starts
# one fresh Claude per job through worker.py. That Claude works the one job and is closed
# when it marks itself finished, so every job starts with an empty context. Only one worker
# ever runs, and none is ever killed for running long — worker.py says how. With nothing to
# work and the mastermind switched on (q.py auto on), it starts a /annie-mastermind worker.
#
#   run.sh start    start the runner in the background
#   run.sh stop     stop it, and the worker if one is running (its job stays `working`
#                   and the next worker resumes it from its note)
#   run.sh park     stop it without cutting a job off: now if idle, else once the current
#                   worker ends. `start` clears it
#   run.sh restart  let the current worker finish its job, then stop and start the runner —
#                   how a change to these scripts takes effect without cutting a job off
#   run.sh status   is it running, is a worker on a job, the last lines of the log
#   run.sh loop     the loop itself, in the foreground (what `start` runs)
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
Q="$HERE/q.py"
LOG="$HERE/runner.log"
PID="$HERE/runner.pid"
PARK="$HERE/runner.park"   # present: start no new worker; the loop exits
CHECK_EVERY=5     # seconds between looks at the queue
FAIL_SLEEP=120    # a worker died within a minute: pause, so a broken setup cannot spin

running() { [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; }
say() { echo "$(date '+%Y-%m-%d %H:%M:%S') | $*" >> "$LOG"; }

# Work exists when an item is queued, or a `working` one was left by a stopped worker.
has_work() { python3 "$Q" list 2>/dev/null | grep -qE '^#[0-9]+ \[(queued|working)'; }

loop() {
  cd "$REPO" || exit 1
  say "runner started (pid $$)"
  worker=""
  trap 'say "runner stopped"; [ -n "$worker" ] && kill "$worker" 2>/dev/null; rm -f "$PID"; exit 0' INT TERM
  while true; do
    if [ -f "$PARK" ]; then say "parked; runner stopped"; rm -f "$PID"; exit 0; fi
    prompt="/annie-queue --one"
    if has_work; then
      # Named for its job, so it is plain in the session list and in Remote Control what it is.
      job=$(python3 "$Q" peek | cut -c1-60)
      name="autoworker ${job}"
    elif [ "$(python3 "$Q" idle --claim 2>/dev/null)" = "go" ]; then
      # Nothing to work and the mastermind's switch is on: one pass to tidy Blocked and make
      # at most one auto job. q.py's gate holds the caps and the cooldown, so an empty pass
      # cannot spin.
      prompt="/annie-mastermind"
      name="autoworker mastermind"
    else
      sleep "$CHECK_EVERY"
      continue
    fi
    say "worker started: $name"
    began=$(date +%s)
    python3 "$HERE/worker.py" "$name" "$prompt" >> "$LOG" 2>&1 &
    worker=$!
    wait "$worker"
    code=$?
    worker=""
    took=$(( $(date +%s) - began ))
    say "worker ended (exit $code, $(( took / 60 )) min)"
    [ "$code" -ne 0 ] && [ "$took" -lt 60 ] && sleep "$FAIL_SLEEP"
  done
}

case "${1:-status}" in
  start)
    rm -f "$PARK"
    if running; then echo "already running (pid $(cat "$PID"))"; exit 0; fi
    # By full path through bash: `sh run.sh start` leaves $0 as a bare "run.sh", which nohup
    # cannot find, and the loop died before writing a line. Its errors go to the log, not away.
    nohup bash "$HERE/run.sh" loop >> "$LOG" 2>&1 &
    echo $! > "$PID"
    echo "started (pid $!) — log: $LOG"
    ;;
  restart)
    if ! running; then exec bash "$HERE/run.sh" start; fi
    r=$(cat "$PID"); w=$(pgrep -P "$r" | head -1)
    # Waits in the background: the job may have hours left.
    nohup bash -c "while [ -n '$w' ] && kill -0 '$w' 2>/dev/null; do sleep 5; done
      kill '$r'; while kill -0 '$r' 2>/dev/null; do sleep 1; done
      bash '$HERE/run.sh' start" >> "$LOG" 2>&1 &
    echo "will restart when the current job is parked"
    ;;
  park)
    if ! running; then echo "not running"; exit 0; fi
    touch "$PARK"
    if pgrep -P "$(cat "$PID")" >/dev/null; then
      echo "will stop when the current job ends"
    else
      kill "$(cat "$PID")"; rm -f "$PID"; echo "stopped"
    fi
    ;;
  stop)
    if running; then kill "$(cat "$PID")" && echo "stopped"; else echo "not running"; fi
    rm -f "$PID"
    ;;
  status)
    if running; then
      echo "runner running (pid $(cat "$PID"))"
      pgrep -P "$(cat "$PID")" >/dev/null && echo "a worker is on a job" || echo "idle, checking every ${CHECK_EVERY}s"
    else
      echo "runner not running"
    fi
    if [ -f "$LOG" ]; then tail -n 5 "$LOG"; fi
    ;;
  loop) loop ;;
  *) echo "usage: run.sh start|stop|park|restart|status"; exit 1 ;;
esac
