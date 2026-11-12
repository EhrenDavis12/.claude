#!/bin/bash
# annie's runner: checks the queue every few seconds with no Claude and no tokens, and starts
# one fresh Claude per job through worker.py. That Claude works the one job and is closed
# when it marks itself finished, so every job starts with an empty context. Only one worker
# ever runs in the main slot. A second, paid slot runs one item marked paid (q.py paid) beside
# it: remote models only, so it never competes for the local model server. A worker lives as
# long as its notes promise, never longer than worker.py's JOB_MAX — worker.py says how — and
# this loop kills worker.py itself if it outlives that.
# With nothing to work in the main slot and the mastermind switched on (q.py auto on), it starts a
# /annie-mastermind worker. Once a day, before a job, it runs worker.py's self-test, so a
# takedown that has stopped firing shows in the log before a night is lost to it, and archives
# done items older than a day (q.py archive).
#
#   run.sh start    start the runner in the background
#   run.sh stop     stop it, and any worker running (its job stays `working` and the next
#                   worker resumes it from its note)
#   run.sh park     stop it without cutting a job off: now if idle, else once the current
#                   workers end. `start` clears it
#   run.sh restart  let the current workers finish their jobs, then stop and start the runner —
#                   how a change to these scripts takes effect without cutting a job off
#   run.sh paid on|off  the paid slot's switch; on unless switched off. Off, paid items wait
#   run.sh status   is it running, is its loop still ticking, what each slot is on, the log
#   run.sh selftest prove a takedown fires, on fake jobs in both slots, now
#   run.sh loop     the loop itself, in the foreground (what `start` runs)
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
Q="$HERE/q.py"
LOG="$HERE/runner.log"
PID="$HERE/runner.pid"
PARK="$HERE/runner.park"   # present: start no new worker; the loop exits once none runs
PAIDOFF="$HERE/paid.off"   # present: the paid slot starts nothing
BEAT="$HERE/runner.beat"   # touched every few seconds: a stale one means the loop is not running
DAY="$HERE/selftest.day"   # the day the self-test last ran
CHECK_EVERY=5     # seconds between looks at the queue
FAIL_SLEEP=120    # a worker died within a minute: pause its slot, so a broken setup cannot spin
WORKER_MAX=$(( 6 * 3600 + 30 * 60 ))   # worker.py's JOB_MAX and half an hour to close

running() { [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; }
say() { echo "$(date '+%Y-%m-%d %H:%M:%S') | $*" >> "$LOG"; }

# Work exists for a slot when q.py peek names a job: a queued item, or a `working` one left by
# a stopped worker. Its output is read whole into a variable, never piped: with pipefail, grep -q
# quitting early SIGPIPEd q.py on a long queue and the check read as "no work" (runner sat idle
# overnight, 2026-10-28). A q.py that fails is said in the log, once, instead of reading as an
# empty queue. $1 is "" for the main slot, --paid for the paid one; the job is left in $job.
qfail=""
has_work() {
  local out
  if ! out=$(python3 "$Q" peek $1 2>&1); then
    [ -z "$qfail" ] && say "q.py peek failed, so no job can start: ${out:0:300}"
    qfail=1; return 1
  fi
  [ -n "$qfail" ] && say "q.py peek works again"
  qfail=""
  job=$(echo "$out" | cut -c1-60)
  [ -n "$out" ]
}

# Each slot keeps its own worker pid, start time and failure pause, in pid_<slot>,
# began_<slot> and hold_<slot> (bash 3.2 has no maps, so they are set with printf -v).
start_worker() {   # $1: main or paid
  local slot=$1 hold="hold_$1" prompt="/annie-queue --one" name
  [ "$(date +%s)" -lt "${!hold}" ] && return
  if [ "$slot" = paid ]; then
    [ -f "$PAIDOFF" ] && return
    has_work --paid || return
    prompt="/annie-queue --one --paid"
    name="autoworker paid ${job}"
  elif has_work ""; then
    # Named for its job, so it is plain in the session list and in Remote Control what it is.
    name="autoworker ${job}"
  elif [ "$(python3 "$Q" idle --claim 2>/dev/null)" = "go" ]; then
    # Nothing to work and the mastermind's switch is on: one pass to tidy Blocked and make
    # at most one auto job. q.py's gate holds the board pause, the usage stop and a cooldown, so an empty pass
    # cannot spin. Paid items never count as work here.
    prompt="/annie-mastermind"
    name="autoworker mastermind"
  else
    return
  fi
  if [ "$(cat "$DAY" 2>/dev/null)" != "$(date +%F)" ]; then
    date +%F > "$DAY"
    python3 "$HERE/worker.py" --selftest >> "$LOG" 2>&1
    python3 "$Q" archive >> "$LOG" 2>&1   # done items older than a day leave the live queue
  fi
  say "worker started: $name"
  ANNIE_SLOT=$slot python3 "$HERE/worker.py" "$name" "$prompt" >> "$LOG" 2>&1 &
  printf -v "pid_$slot" '%s' $!
  printf -v "began_$slot" '%s' "$(date +%s)"
}

# Looks in on a slot's worker: kills a worker.py that outlives its own ceiling — the last guard,
# for a watcher that hung — and, once it has ended, logs it and frees the slot.
reap_worker() {   # $1: main or paid
  local slot=$1 p="pid_$1" b="began_$1" worker began code took claude_pid
  worker=${!p}; began=${!b}
  [ -z "$worker" ] && return
  if kill -0 "$worker" 2>/dev/null; then
    [ $(( $(date +%s) - began )) -le "$WORKER_MAX" ] && return
    say "$slot worker.py ran past $(( WORKER_MAX / 60 )) min without closing; killing it"
    kill "$worker" 2>/dev/null; sleep 30
    claude_pid=$(pgrep -P "$worker" | head -1)
    [ -n "$claude_pid" ] && kill -9 -- "-$claude_pid" 2>/dev/null
    kill -9 "$worker" 2>/dev/null
  fi
  wait "$worker"
  code=$?
  printf -v "pid_$slot" '%s' ""
  took=$(( $(date +%s) - began ))
  say "$slot worker ended (exit $code, $(( took / 60 )) min)"
  [ "$code" -ne 0 ] && [ "$took" -lt 60 ] && printf -v "hold_$slot" '%s' $(( $(date +%s) + FAIL_SLEEP ))
}

loop() {
  cd "$REPO" || exit 1
  say "runner started (pid $$)"
  pid_main=""; pid_paid=""; began_main=0; began_paid=0; hold_main=0; hold_paid=0
  trap 'say "runner stopped"; for w in $pid_main $pid_paid; do kill "$w" 2>/dev/null; done; rm -f "$PID"; exit 0' INT TERM
  while true; do
    touch "$BEAT"
    reap_worker main
    reap_worker paid
    if [ -f "$PARK" ]; then
      if [ -z "$pid_main$pid_paid" ]; then say "parked; runner stopped"; rm -f "$PID"; exit 0; fi
    else
      [ -z "$pid_main" ] && start_worker main
      [ -z "$pid_paid" ] && start_worker paid
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
    # Parked, the loop starts nothing new and exits once its workers have ended; then a fresh
    # one starts. Waits in the background: a job may have hours left.
    r=$(cat "$PID"); touch "$PARK"
    nohup bash -c "while kill -0 '$r' 2>/dev/null; do sleep 5; done
      bash '$HERE/run.sh' start" >> "$LOG" 2>&1 &
    echo "will restart when the current jobs are parked"
    ;;
  park)
    if ! running; then echo "not running"; exit 0; fi
    touch "$PARK"
    if pgrep -P "$(cat "$PID")" -f worker.py >/dev/null; then
      echo "will stop when the current jobs end"
    else
      kill "$(cat "$PID")"; rm -f "$PID"; echo "stopped"
    fi
    ;;
  stop)
    if running; then kill "$(cat "$PID")" && echo "stopped"; else echo "not running"; fi
    rm -f "$PID"
    ;;
  paid)
    case "${2:-}" in
      on) rm -f "$PAIDOFF" ;;
      off) touch "$PAIDOFF" ;;
    esac
    [ -f "$PAIDOFF" ] && echo "paid slot off" || echo "paid slot on"
    ;;
  status)
    if running; then
      echo "runner running (pid $(cat "$PID"))"
      age=$(( $(date +%s) - $(stat -f %m "$BEAT" 2>/dev/null || echo 0) ))
      [ "$age" -gt 60 ] && echo "BUT its loop has not ticked for $(( age / 60 )) min — restart it"
      # Read whole, never piped into grep -q (see has_work).
      ws=$(pgrep -P "$(cat "$PID")" -fl worker.py)
      main=$(echo "$ws" | grep worker.py | grep -v "autoworker paid")
      paid=$(echo "$ws" | grep "autoworker paid")
      [ -n "$main" ] && echo "main slot: on a job" || echo "main slot: idle, checking every ${CHECK_EVERY}s"
      if [ -f "$PAIDOFF" ]; then echo "paid slot: off"
      elif [ -n "$paid" ]; then echo "paid slot: on a job"
      else echo "paid slot: idle"; fi
    else
      echo "runner not running"
      [ -f "$PAIDOFF" ] && echo "paid slot: off"
    fi
    if [ -f "$LOG" ]; then tail -n 5 "$LOG"; fi
    ;;
  selftest) python3 "$HERE/worker.py" --selftest ;;
  loop) loop ;;
  *) echo "usage: run.sh start|stop|park|restart|paid on|off|status|selftest"; exit 1 ;;
esac
