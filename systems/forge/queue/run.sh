#!/bin/bash
# forge's runner, ported from annie's: checks the queue every few seconds with no Claude and no
# tokens, and starts one fresh Claude per job through worker.py. That Claude works the one job
# and is closed when it marks itself finished, so every job starts with an empty context. Only
# one worker ever runs: two live writers in one srcRoot is two builds stepping on each other.
# A worker lives as long as its notes promise, never longer than worker.py's JOB_MAX —
# worker.py says how — and this loop kills worker.py itself if it outlives that.
# With nothing to work and the mastermind switched on (q.py auto on), it starts a
# /forge-mastermind worker. Once a day, before a job, it runs worker.py's self-test, so a
# takedown that has stopped firing shows in the log before a night is lost to it, and archives
# done items older than a day (q.py archive).
#
#   run.sh start    start the runner in the background
#   run.sh stop     stop it, and any worker running (its job stays `working` and the next
#                   worker resumes it from its note)
#   run.sh park     stop it without cutting a job off: now if idle, else once the current
#                   worker ends. `start` clears it
#   run.sh restart  let the current worker finish its job, then stop and start the runner —
#                   how a change to these scripts takes effect without cutting a job off
#   run.sh status   is it running, is its loop still ticking, what it is on, the log
#   run.sh selftest prove a takedown fires, on fake jobs, now
#   run.sh loop     the loop itself, in the foreground (what `start` runs)
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
Q="$HERE/q.py"
LOG="$HERE/runner.log"
PID="$HERE/runner.pid"
PARK="$HERE/runner.park"   # present: start no new worker; the loop exits once none runs
BEAT="$HERE/runner.beat"   # touched every few seconds: a stale one means the loop is not running
DAY="$HERE/selftest.day"   # the day the self-test last ran
CHECK_EVERY=5     # seconds between looks at the queue
FAIL_SLEEP=120    # a worker died within a minute: pause, so a broken setup cannot spin
WORKER_MAX=$(( 6 * 3600 + 30 * 60 ))   # worker.py's JOB_MAX and half an hour to close

running() { [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; }
say() { echo "$(date '+%Y-%m-%d %H:%M:%S') | $*" >> "$LOG"; }

# Work exists when q.py peek names a job: a queued item, or a `working` one left by a stopped
# worker. Its output is read whole into a variable, never piped: with pipefail, grep -q quitting
# early SIGPIPEd q.py on a long queue and the check read as "no work" (annie's runner sat idle
# overnight, 2026-10-28). A q.py that fails is said in the log, once, instead of reading as an
# empty queue. The job is left in $job.
qfail=""
has_work() {
  local out
  if ! out=$(python3 "$Q" peek 2>&1); then
    [ -z "$qfail" ] && say "q.py peek failed, so no job can start: ${out:0:300}"
    qfail=1; return 1
  fi
  [ -n "$qfail" ] && say "q.py peek works again"
  qfail=""
  job=$(echo "$out" | cut -c1-60)
  [ -n "$out" ]
}

start_worker() {
  local prompt="/forge-queue --one" name
  [ "$(date +%s)" -lt "$hold" ] && return
  if has_work; then
    # Named for its job, so it is plain in the session list and in Remote Control what it is.
    name="forgeworker ${job}"
  elif [ "$(python3 "$Q" idle --claim 2>/dev/null)" = "go" ]; then
    # Nothing to work and the mastermind's switch is on: one pass to tidy Blocked and make at
    # most one auto job. q.py's gate holds the board pause, the usage stop and a cooldown, so
    # an empty pass cannot spin.
    prompt="/forge-mastermind"
    name="forgeworker mastermind"
  else
    return
  fi
  if [ "$(cat "$DAY" 2>/dev/null)" != "$(date +%F)" ]; then
    date +%F > "$DAY"
    python3 "$HERE/worker.py" --selftest >> "$LOG" 2>&1
    python3 "$Q" archive >> "$LOG" 2>&1   # done items older than a day leave the live queue
  fi
  say "worker started: $name"
  python3 "$HERE/worker.py" "$name" "$prompt" >> "$LOG" 2>&1 &
  worker=$!
  began=$(date +%s)
}

# Looks in on the worker: kills a worker.py that outlives its own ceiling — the last guard,
# for a watcher that hung — and, once it has ended, logs it and frees the slot.
reap_worker() {
  local code took claude_pid
  [ -z "$worker" ] && return
  if kill -0 "$worker" 2>/dev/null; then
    [ $(( $(date +%s) - began )) -le "$WORKER_MAX" ] && return
    say "worker.py ran past $(( WORKER_MAX / 60 )) min without closing; killing it"
    kill "$worker" 2>/dev/null; sleep 30
    claude_pid=$(pgrep -P "$worker" | head -1)
    [ -n "$claude_pid" ] && kill -9 -- "-$claude_pid" 2>/dev/null
    kill -9 "$worker" 2>/dev/null
  fi
  wait "$worker"
  code=$?
  worker=""
  took=$(( $(date +%s) - began ))
  say "worker ended (exit $code, $(( took / 60 )) min)"
  [ "$code" -ne 0 ] && [ "$took" -lt 60 ] && hold=$(( $(date +%s) + FAIL_SLEEP ))
}

loop() {
  cd "$REPO" || exit 1
  say "runner started (pid $$)"
  worker=""; began=0; hold=0
  trap 'say "runner stopped"; [ -n "$worker" ] && kill "$worker" 2>/dev/null; rm -f "$PID"; exit 0' INT TERM
  while true; do
    touch "$BEAT"
    reap_worker
    if [ -f "$PARK" ]; then
      if [ -z "$worker" ]; then say "parked; runner stopped"; rm -f "$PID"; exit 0; fi
    else
      [ -z "$worker" ] && start_worker
    fi
    sleep "$CHECK_EVERY"
  done
}

case "${1:-status}" in
  start)
    rm -f "$PARK"
    if running; then echo "already running (pid $(cat "$PID"))"; exit 0; fi
    # By full path through bash: `sh run.sh start` leaves $0 as a bare "run.sh", which nohup
    # cannot find, and the loop died before writing a line. Its errors go to the log, not away.
    # In a session of its own: started from a Claude session's shell, it would otherwise share
    # that shell's process group, and go down with it when that session cleans up.
    nohup perl -MPOSIX -e 'POSIX::setsid(); exec @ARGV' bash "$HERE/run.sh" loop >> "$LOG" 2>&1 &
    echo $! > "$PID"
    echo "started (pid $!) — log: $LOG"
    ;;
  restart)
    if ! running; then exec bash "$HERE/run.sh" start; fi
    # Parked, the loop starts nothing new and exits once its worker has ended; then a fresh
    # one starts. Waits in the background: a job may have hours left.
    r=$(cat "$PID"); touch "$PARK"
    nohup bash -c "while kill -0 '$r' 2>/dev/null; do sleep 5; done
      bash '$HERE/run.sh' start" >> "$LOG" 2>&1 &
    echo "will restart when the current job is parked"
    ;;
  park)
    if ! running; then echo "not running"; exit 0; fi
    touch "$PARK"
    if pgrep -P "$(cat "$PID")" -f worker.py >/dev/null; then
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
      age=$(( $(date +%s) - $(stat -f %m "$BEAT" 2>/dev/null || echo 0) ))
      [ "$age" -gt 60 ] && echo "BUT its loop has not ticked for $(( age / 60 )) min — restart it"
      # Read whole, never piped into grep -q (see has_work).
      ws=$(pgrep -P "$(cat "$PID")" -fl worker.py)
      [ -n "$ws" ] && echo "on a job" || echo "idle, checking every ${CHECK_EVERY}s"
    else
      echo "runner not running"
    fi
    if [ -f "$LOG" ]; then tail -n 5 "$LOG"; fi
    ;;
  selftest) python3 "$HERE/worker.py" --selftest ;;
  loop) loop ;;
  *) echo "usage: run.sh start|stop|park|restart|status|selftest"; exit 1 ;;
esac
