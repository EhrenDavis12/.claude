#!/usr/bin/env python3
"""One annie worker, from start to close. run.sh calls this once per job.

The worker is an interactive Claude session, because only an interactive session shows up in
Remote Control, where the user can watch it or talk to it from claude.ai or their phone. It
runs under a pseudo-terminal nobody looks at, so it needs no window.

A worker closes when it writes its "finished" mark (the file named in $ANNIE_WORKER_DONE) as
its last step, or when it is taken down. A worker taken down is closed, whole process tree, and
its item stays `working`, so the runner starts a fresh worker that resumes it from its note.
After MAX_RESTARTS of the same item it goes to `blocked` with a question instead, so a job that
sticks every time cannot loop (user, 2026-10-28: "identify that the job is stuck take it down
and rebuild it").

Every worker has a ceiling, and no sign of life can lift it. Signs of life are guesses from the
outside, and each one has had a hole that kept a dead worker "alive" all night — a wait loop,
app bookkeeping in the transcript, a runaway script's processor use. So a worker lives by a
promise it keeps instead: each `q.py note` on its item buys the stage the minutes it names
(`--minutes`, q.py caps them) or STAGE_DEFAULT, and a worker past that with no new note is taken
down. JOB_MAX caps one worker whatever its notes say. The signs below only bring a takedown
sooner, for a worker that has plainly stopped; they never hold one off.

Signs of life, any one is enough:
  - its session transcript (or a subagent's) gained a real turn — a user or assistant entry.
    Bookkeeping lines the app appends to an idle session (artifact ledgers, titles) do not count:
    they cleared the flag every half hour on a worker that had sat idle all night.
  - processes under it used at least CPU_LIFE seconds of processor in one look. A wait loop
    (`while pgrep ...; do sleep 15; done`) costs a hundredth of a second a look and is not
    life: two such loops whose pgrep matched their own shell kept a worker "alive" for 15 hours
    while nothing happened (2026-10-27). Processor use alone is life for CPU_ONLY_MAX at most:
    a measuring script whose process pool respawned its children forever burned eight cores
    for 7 hours with no turn, no file written and the reviewer waiting on it (2026-10-30).
  - a file changed in its scratchpad or task output, or — checked once before it is called
    stuck — anywhere under the work folders (WORK_DIRS)
  - the local model server has a job running (its renders are not under the worker)

A lost connection or a sleeping computer is not a stuck job (user's move, 2026-10-31: three
workers died on `API Error: Can't reach the API server`, each counted, and the item was parked).
While offline, and across any sleep, the clocks are held and nothing is taken down. A worker
whose turn ended on a connection error is restarted once the connection is back, and that
restart does not count toward MAX_RESTARTS, up to NET_RESTARTS.

A worker runs in one of the runner's two slots, named by $ANNIE_SLOT: `main` (the default)
or `paid`, which works only items marked paid and beside the main one. Each slot has its own
finished mark and screen file, and watches only its own slot's item.

  worker.py NAME [PROMPT]       PROMPT defaults to /annie-queue --one
  worker.py --selftest          prove a takedown fires, on a fake job in a scratch folder
  worker.py --flag              republish the Queue page from a short session
"""
import datetime
import json
import os
import pty
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
Q = HERE / "q.py"
PAID = os.environ.get("ANNIE_SLOT") == "paid"
DONE = HERE / ("worker.paid.done" if PAID else "worker.done")
# The last of the worker's screen, for when something goes wrong.
TTY = HERE / ("worker.paid.tty" if PAID else "worker.tty")
TRANSCRIPTS = Path.home() / ".claude" / "projects" / str(REPO).replace("/", "-")
MODEL_SERVER = "http://127.0.0.1:8188/queue"
# The web tools are for the mastermind's research jobs.
TOOLS = "Agent Bash Read Edit Write Grep Glob Skill SendMessage Artifact WebSearch WebFetch".split()
SCALE = float(os.environ.get("ANNIE_TIME_SCALE", "1"))   # the self-test runs minutes as seconds
TICK = 30 / SCALE                 # seconds between looks
STAGE_DEFAULT = 90 * 60 / SCALE   # what a note without --minutes buys — the same as q.py's
JOB_MAX = 6 * 3600 / SCALE        # one worker, whatever its notes say; the next resumes the item
STUCK_AFTER = 30 * 60 / SCALE     # no sign of life this long: take it down
CLOSE_AFTER_DONE = 30 / SCALE     # the finished mark is the last step; give its final words time to land
IDLE_AFTER = 5 * 60 / SCALE       # turn ended, no finished mark: it is waiting for input
CPU_LIFE = 0.5 / SCALE            # processor seconds in one look that count as work, not a wait loop
CPU_ONLY_MAX = 90 * 60 / SCALE    # processor use with no other sign of life this long: a runaway script
BLIND_AFTER = 10 * 60 / SCALE     # no transcript on disk by now: the turn-based signs are blind
KILL_GRACE = 15                   # seconds between asking the tree to stop and killing it
CALL_TIMEOUT = 60                 # every q.py and ps call; nothing here may hang the watcher
FLAG_TIMEOUT = 300                # the short session that republishes the page
MAX_RESTARTS = 2                  # taken down this many times on one item: block it with a question
NET_RESTARTS = 12                 # uncounted restarts for a lost connection, on one item; then they count
SLEPT_AFTER = 5 * 60 / SCALE      # a gap this long between looks: the computer was asleep
API_HOST = ("api.anthropic.com", 443)
OFFLINE_MARK = HERE / "offline.test"   # present: online() says no. The self-test's switch
RESTARTS = HERE / "restarts.json"
SCRATCH = Path(f"/private/tmp/claude-{os.getuid()}") / str(REPO).replace("/", "-")
# Where a worker's artists write. Not the skills or the Chart: the desk writes those, and a
# desk edit must not keep a stuck worker looking alive.
WORK_DIRS = [REPO / "src" / "asset-animation-demo" / "local_runs",
             REPO / "src" / "unity-side-scroler" / "sideScrollerBattles" / "Assets"]
SKIP_DIRS = {"chart"}
TURN_TYPES = ("user", "assistant")
# Claude Code marks the shells it starts with its own session's identity, and the runner is
# often started from the desk's session. A worker that inherits CLAUDE_CODE_CHILD_SESSION writes
# no transcript at all: every worker from 2026-10-27 08:09 on ran with the turn-based signs blind,
# and nothing said so. The rest point at the desk's session and are as wrong for a worker.
INHERITED = ("CLAUDECODE", "CLAUDE_PID", "AI_AGENT", "CLAUDE_CODE_CHILD_SESSION",
             "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_SESSION_ATTENDED",
             "CLAUDE_CODE_BRIDGE_SESSION_ID", "CLAUDE_CODE_MESSAGING_SOCKET",
             "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_EXECPATH")


def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}", flush=True)


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in INHERITED}
    env.update(extra)
    return env


def run(cmd):
    """A short command with a time limit: the watcher must never wait on what it watches."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=CALL_TIMEOUT).stdout
    except subprocess.TimeoutExpired:
        log(f"timed out after {CALL_TIMEOUT}s: {' '.join(cmd[:3])}")
        return ""


def _entries(path, size=262144, most=64 << 20):
    """The parsed JSON lines at the end of one transcript file. One line can be bigger than
    the window (a reviewer's image read is), so the window doubles until a line parses."""
    try:
        total = os.path.getsize(path)
        with open(path, "rb") as f:
            while True:
                f.seek(max(0, total - size))
                lines = f.read().decode("utf-8", "replace").splitlines()
                if size < total:
                    lines = lines[1:]           # the first line is cut partway
                out = []
                for line in lines:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
                if out or size >= total or size >= most:
                    return out
                size *= 2
    except OSError:
        return []


def _stamp(entry):
    t = entry.get("timestamp")
    if not t:
        return 0.0
    try:
        return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def transcript_written(sid):
    """The time of the newest real turn (user or assistant) in this session's transcript or
    any of its subagents', or 0. Bookkeeping lines are not signs of life."""
    files = [TRANSCRIPTS / f"{sid}.jsonl"]
    side = TRANSCRIPTS / sid
    if side.is_dir():
        files += list(side.rglob("*.jsonl"))
    newest = 0.0
    for f in files:
        entries = _entries(f)
        for e in entries:
            if e.get("type") in TURN_TYPES:
                newest = max(newest, _stamp(e))
        # A subagent writing its transcript is alive (a live reviewer while the worker's own
        # turn has ended); and a file whose lines will not parse is still a sign by its mtime.
        if f.parent != TRANSCRIPTS or not entries:
            try:
                newest = max(newest, f.stat().st_mtime)
            except OSError:
                pass
    return newest


def turn_ended(sid):
    """True when the session's last real entry closes a turn: it stopped and is waiting."""
    last = None
    for e in _entries(TRANSCRIPTS / f"{sid}.jsonl"):
        if e.get("type") in TURN_TYPES or (e.get("type") == "system"
                                          and e.get("subtype") in ("turn_duration", "stop_hook_summary")):
            last = e
    if last is None:
        return False
    if last.get("type") == "system":
        return True
    msg = last.get("message") or {}
    return last.get("type") == "assistant" and msg.get("stop_reason") == "end_turn"


def cpu_seconds(t):
    """ps TIME, [[dd-]hh:]mm:ss.cc, as seconds."""
    days, _, t = t.rpartition("-")
    secs = 0.0
    for part in t.split(":"):
        secs = secs * 60 + float(part)
    return secs + (int(days) * 86400 if days else 0)


def under_cpu(root):
    """Processor time used by every process below the Claude process, not counting Claude
    itself — its screen keeps redrawing even when nothing is happening."""
    kids, cpu = {}, {}
    for line in run(["ps", "-Ao", "pid=,ppid=,time="]).splitlines():
        pid, ppid, t = line.split()
        kids.setdefault(int(ppid), []).append(int(pid))
        cpu[int(pid)] = cpu_seconds(t)
    total, todo = 0.0, list(kids.get(root, []))
    while todo:
        pid = todo.pop()
        total += cpu.get(pid, 0.0)
        todo += kids.get(pid, [])
    return total


def newest_file(roots, since=0.0):
    """The newest mtime under these folders, stopping early once one beats `since`."""
    newest = 0.0
    for root in roots:
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                try:
                    m = os.stat(os.path.join(dirpath, f)).st_mtime
                except OSError:
                    continue
                if m > newest:
                    newest = m
                    if since and newest > since:
                        return newest
    return newest


def descendants(root):
    kids = {}
    for line in run(["ps", "-Ao", "pid=,ppid="]).splitlines():
        pid, ppid = map(int, line.split())
        kids.setdefault(ppid, []).append(pid)
    found, todo = [], list(kids.get(root, []))
    while todo:
        pid = todo.pop()
        found.append(pid)
        todo += kids.get(pid, [])
    return found


def strays(sid):
    """Processes running from this worker's scratchpad. A script started with nohup or in a
    new session leaves the tree when Claude dies, but its command line still names the folder."""
    mark = str(SCRATCH / sid)
    out = []
    for line in run(["ps", "-Ao", "pid=,command="]).splitlines():
        pid, _, command = line.strip().partition(" ")
        if mark in command and int(pid) != os.getpid():
            out.append(int(pid))
    return out


def signal_all(pids, sig):
    for p in pids:
        try:
            os.kill(p, sig)
        except (ProcessLookupError, PermissionError):
            pass


def online():
    if OFFLINE_MARK.exists():
        return False
    if SCALE != 1:
        return True       # the self-test must not depend on this machine's connection
    try:
        socket.create_connection(API_HOST, timeout=3).close()
        return True
    except OSError:
        return False


def connection_lost(sid):
    """True when the session's last turn is a connection error from the API, not its own words."""
    last = None
    for e in _entries(TRANSCRIPTS / f"{sid}.jsonl"):
        if e.get("type") in TURN_TYPES:
            last = e
    if last is None or not last.get("isApiErrorMessage"):
        return False
    text = json.dumps((last.get("message") or {}).get("content"))
    return (last.get("apiError") == "connection_failed" or "went to sleep" in text
            or "reach the API" in text)


def restarts(item, add=0, clear=False):
    try:
        counts = json.loads(RESTARTS.read_text())
    except (OSError, ValueError):
        counts = {}
    key = str(item)
    if clear:
        counts.pop(key, None)
    else:
        counts[key] = counts.get(key, 0) + add
    RESTARTS.write_text(json.dumps(counts))
    return counts.get(key, 0)


def model_server_busy():
    if PAID:
        return False      # the paid slot never uses it: a render there is the main slot's
    try:
        with urllib.request.urlopen(MODEL_SERVER, timeout=3) as r:
            return bool(json.load(r).get("queue_running"))
    except Exception:
        return False


def items():
    try:
        return json.loads((HERE / "queue.json").read_text())["items"]
    except (OSError, ValueError, KeyError):
        return []


def working_id():
    for it in items():
        if it["state"] == "working" and bool(it.get("paid")) == PAID:
            return it["id"]
    return None


def deadline(item):
    """When the item's last note said its stage would be done, or 0."""
    for it in items():
        if it["id"] == item and it.get("deadline"):
            try:
                return datetime.datetime.fromisoformat(it["deadline"]).timestamp()
            except ValueError:
                return 0.0
    return 0.0


SPAWNED = []      # the headless publishes, reaped each look so none is left a zombie


def flag(on, why="", item=None):
    """Set or clear the flag, then republish the Queue page so the user sees it."""
    item = item if item is not None else working_id()
    if item is not None:
        run(["python3", str(Q), "stuck" if on else "unstuck", str(item), *([why] if on else [])])
    elif not on:
        return
    item = item if item is not None else f"{NAME} (its item is no longer marked working)"
    # The runner cannot publish. A short session can, but only an interactive one: `claude -p`
    # is not offered Artifact. No session can push to the phone from here: PushNotification
    # refuses under a terminal it counts as active, so the alert is the page and a Mac banner.
    # Started, not waited on: the watcher keeps watching meanwhile.
    say = (f"Job #{item} looks stuck: {why}" if on else f"Job #{item} is moving again")
    subprocess.Popen(["osascript", "-e", "on run argv", "-e",
                      'display notification (item 1 of argv) with title "Annie queue"', "-e",
                      "end run", say[:200]],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(HERE / "runner.log", "a") as out:
        SPAWNED.append(subprocess.Popen(
            ["python3", str(Path(__file__).resolve()), "--flag"],
            cwd=REPO, env=clean_env(), stdin=subprocess.DEVNULL, stdout=out, stderr=out,
            start_new_session=True))


def flag_session():
    """One short interactive session, not on Remote Control so it never crowds the user's session
    list: republish the page, write what happened to its finished mark in its own scratchpad
    (it may not write under .claude), and close."""
    sid = str(uuid.uuid4())
    mark = SCRATCH / sid / "flag.done"
    mark.parent.mkdir(parents=True, exist_ok=True)
    prompt = (f"Run `python3 {Q} render` and publish what it prints to the Queue page, whose link "
              f"is in .claude/systems/annie/SYSTEM.md, as SYSTEM.md says. If a publish is refused "
              f"as a conflict, publish the same thing again, up to three tries. Do nothing else. "
              f"Last, write one line saying whether the page published, with Bash, to {mark}")
    cmd = ["claude", prompt, "--session-id", sid, "-n", "autoflag", "--permission-mode", "dontAsk",
           "--allowedTools", "Bash", "Artifact"]
    pid, fd = pty.fork()
    if pid == 0:
        import fcntl, struct, termios
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 160, 0, 0))
        os.chdir(REPO)
        os.execvpe(cmd[0], cmd, clean_env(ANNIE_FLAG_SESSION="1"))
    limit, reading, ended = time.time() + FLAG_TIMEOUT, True, False
    while time.time() < limit and not mark.exists():
        r, _, _ = select.select([fd] if reading else [], [], [], 1)
        if r:
            try:
                reading = bool(os.read(fd, 65536))
            except OSError:
                reading = False
        if os.waitpid(pid, os.WNOHANG)[0]:
            ended = True
            break
    result = mark.read_text().strip() if mark.exists() else ""
    if not ended:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(pid, sig)
            except (ProcessLookupError, PermissionError):
                pass
            time.sleep(5)
    shutil.rmtree(mark.parent, ignore_errors=True)
    log(f"flag session: {result or 'no result, the page may not have gone out'}")


NAME = sys.argv[1] if len(sys.argv) > 1 else "worker"
PROMPT = sys.argv[2] if len(sys.argv) > 2 else "/annie-queue --one"


def main():
    name = NAME
    sid = str(uuid.uuid4())
    DONE.unlink(missing_ok=True)
    env = clean_env(ANNIE_WORKER_DONE=str(DONE))
    # The prompt goes first: --allowedTools takes every word after it as a tool name.
    cmd = ["claude", PROMPT, "--session-id", sid, "-n", name,
           "--remote-control", name, "--permission-mode", "dontAsk", "--allowedTools", *TOOLS]

    pid, fd = pty.fork()
    if pid == 0:
        import fcntl, struct, termios
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 160, 0, 0))
        os.chdir(REPO)
        os.execvpe(cmd[0], cmd, env)

    # The child leads its own process group, so one signal reaches it and all it started — and
    # the tree and the scratchpad's strays are signalled too, for whatever left the group.
    # The tree is taken now: once Claude dies its children belong to launchd, not to it.
    doomed = set()

    def close(*_):
        if doomed:
            return
        doomed.update(descendants(pid) + strays(sid) + [pid])
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        signal_all(doomed, signal.SIGTERM)

        def kill(*_):
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            signal_all(doomed | set(strays(sid)), signal.SIGKILL)
        signal.signal(signal.SIGALRM, kill)
        signal.alarm(KILL_GRACE)
    signal.signal(signal.SIGTERM, close)
    signal.signal(signal.SIGINT, close)
    log(f"worker session {sid}")

    def take_down(why, lost=False):
        """Close it and everything it started. The item stays `working` and the runner's next
        worker resumes it — unless it has been taken down too often, then it is blocked. A
        restart for a lost connection (`lost`) is not the job's fault and does not count."""
        nonlocal taken_down
        if lost and (item is None or working_id() != item
                     or restarts(f"{item}:net", add=1) <= NET_RESTARTS):
            log(f"{why}; restarting it, not counted as stuck")
            taken_down = True
            close()
            return
        # Only an item still `working` is resumed, so only it is counted or blocked: one the
        # worker had already parked for review stays where it is.
        mine = item if item is not None and working_id() == item else None
        n = restarts(mine, add=1) if mine is not None else 1
        if mine is not None and n > MAX_RESTARTS:
            restarts(item, clear=True)
            log(f"stuck again ({why}); #{item} stuck {n} times, moved to blocked")
            run(["python3", str(Q), "ask", str(item), "--blocker",
                 f"This job got stuck {n} times in a row ({why}); each time it was "
                 f"closed and restarted automatically from where it stopped. It is "
                 f"parked so it cannot loop. Restart it (say 'retry'), or drop it?"])
            flag(False, item=item)
        else:
            log(f"stuck ({why}); taking it down, restart {n} of {MAX_RESTARTS}")
            flag(True, f"{why}. Closed and restarted automatically ({n} of {MAX_RESTARTS}); "
                       f"the new worker resumes from the note.")
        taken_down = True
        close()

    screen, reading, status = b"", True, None
    started = time.time()
    alive_at, flagged, done_at, taken_down = started, False, None, False
    other_life_at = alive_at        # the last sign of life that was not processor use alone
    item, cleared, blind_said = None, False, False
    held, offline_since, last_look = 0.0, None, started
    cpu_seen = under_cpu(pid)
    seen = (transcript_written(sid), newest_file([SCRATCH / sid]))
    next_look = time.time() + TICK
    while True:
        # Read the screen while it is open; the end is when Claude exits, not when the screen
        # closes — a stray holding the terminal open must not keep the watcher waiting.
        r, _, _ = select.select([fd] if reading else [], [], [], TICK)
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                data = b""
            if data:
                screen = (screen + data)[-65536:]
            else:
                reading = False
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            break
        if time.time() < next_look:
            continue
        next_look = time.time() + TICK
        SPAWNED[:] = [p for p in SPAWNED if p.poll() is None]

        if done_at is None and DONE.exists():
            log("finished mark written; closing the worker")
            done_at = time.time()
        if done_at and time.time() - done_at > CLOSE_AFTER_DONE:
            close()

        if done_at or taken_down:
            continue
        item = working_id() if working_id() is not None else item

        # Time asleep or offline is nobody's fault: hold every clock across it.
        now, gap = time.time(), time.time() - last_look
        last_look = now
        lapse = 0.0
        if gap > SLEPT_AFTER and offline_since is None:
            log(f"the computer was asleep for {int(gap / 60)} minutes; clocks held")
            lapse = gap
        if not online():
            if offline_since is None:
                log("no connection; clocks held, nothing is taken down")
                offline_since = now
            held += lapse
            alive_at += lapse
            other_life_at += lapse
            continue
        if offline_since is not None:
            lapse += now - offline_since
            log(f"connection back after {int((now - offline_since) / 60)} minutes")
            offline_since = None
        held += lapse
        alive_at += lapse
        other_life_at += lapse
        if turn_ended(sid) and connection_lost(sid):
            take_down("its turn ended on a lost connection", lost=True)
            continue

        if (not blind_said and time.time() - started > BLIND_AFTER
                and not (TRANSCRIPTS / f"{sid}.jsonl").exists()):
            log("no transcript on disk for this session: the turn-based signs are blind, "
                "and only the note's stage time and the other signs can take it down")
            blind_said = True

        # The ceiling first, before any sign of life is read: nothing below can lift it.
        over_job = time.time() - started - held > JOB_MAX
        stage_until = held + max(started + STAGE_DEFAULT, deadline(item) if item is not None else 0)
        if over_job or time.time() > stage_until:
            took = int((time.time() - started - held) / 60)
            take_down(f"it ran {took} minutes, the most one worker may" if over_job else
                      f"its stage ran past the time its last note gave it, with no new note "
                      f"({took} minutes in)")
            continue

        cpu_now = under_cpu(pid)
        busy_cpu = cpu_now - cpu_seen >= CPU_LIFE
        cpu_seen = cpu_now
        now_seen = (transcript_written(sid), newest_file([SCRATCH / sid]))
        if now_seen != seen or model_server_busy():
            other_life_at = time.time()
        elif busy_cpu and time.time() - other_life_at > CPU_ONLY_MAX:
            # Only the processor has moved for a long time: one full look at the work folders
            # before calling it a runaway script.
            if newest_file(WORK_DIRS, since=other_life_at) > other_life_at:
                other_life_at = time.time()
            else:
                mins = int((time.time() - other_life_at) / 60)
                take_down(f"only a script was busy for {mins} minutes, with no new turn and "
                          f"no file written; it was likely spinning")
                continue
        if now_seen != seen or busy_cpu or model_server_busy():
            seen, alive_at = now_seen, time.time()
            if flagged or not cleared:
                # A restarted item carries its old worker's flag until this one shows life.
                if flagged or (item is not None and any(
                        it["id"] == item and it.get("stuck") for it in items())):
                    log("moving again; flag cleared")
                    flag(False)
                cleared, flagged = item is not None, False
            continue
        waiting = turn_ended(sid) and time.time() - max(seen[0], 0) > IDLE_AFTER
        quiet = time.time() - alive_at > STUCK_AFTER
        if not (waiting or quiet):
            continue
        # One full look at the work folders before calling it stuck: a write there is life.
        if newest_file(WORK_DIRS, since=alive_at) > alive_at:
            alive_at = time.time()
            continue
        mins = int((time.time() - alive_at) / 60)
        take_down("its turn ended without the finished mark; it was waiting for input" if waiting
                  else f"no sign of life for {mins} minutes")

    signal.alarm(0)
    TTY.write_bytes(screen)
    if flagged and not taken_down:
        flag(False)
    code = os.waitstatus_to_exitcode(status)
    if done_at and item is not None:
        restarts(item, clear=True)
        restarts(f"{item}:net", clear=True)
    # A worker that wrote its mark finished its job, however its session was closed.
    sys.exit(0 if done_at else (code or 1))


FAKE_CLAUDE = r'''#!/usr/bin/env python3
# Stands in for claude in the self-test. A flag session is the page publish: done at once.
import json, os, subprocess, sys, time
if os.environ.get("ANNIE_FLAG_SESSION"):
    sys.exit(0)
sid = sys.argv[sys.argv.index("--session-id") + 1]
if os.environ["ANNIE_SELFTEST"] == "lost":
    # What a real worker leaves when the connection drops: a turn ended on an API error.
    t = os.path.join(os.path.expanduser("~/.claude/projects"), os.getcwd().replace("/", "-"))
    os.makedirs(t, exist_ok=True)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(t, sid + ".jsonl"), "w") as f:
        f.write(json.dumps({"type": "assistant", "isApiErrorMessage": True, "timestamp": now,
                            "apiError": "connection_failed", "message": {"content": [
                                {"type": "text", "text": "API Error: Can't reach the API server"}]}}) + "\n")
        f.write(json.dumps({"type": "system", "subtype": "turn_duration", "timestamp": now}) + "\n")
    time.sleep(3600)
scratch = os.path.join("/private/tmp/claude-%d" % os.getuid(), os.getcwd().replace("/", "-"), sid)
os.makedirs(scratch, exist_ok=True)
if os.environ["ANNIE_SELFTEST"] == "done":
    time.sleep(1)
    open(os.environ["ANNIE_WORKER_DONE"], "w").close()
    time.sleep(3600)
# Looks alive to every sign: a script spinning a core in a session of its own (it leaves the
# group, as a pool's children did), and a file written in the scratchpad every moment.
subprocess.Popen([sys.executable, "-c", "while True: pass", scratch], start_new_session=True)
while True:
    open(os.path.join(scratch, "beat"), "w").write(str(time.time()))
    time.sleep(0.2)
'''


def selftest():
    """Run this worker on two fake jobs in a scratch copy of the queue, minutes as seconds:
    one that finishes, and one that looks alive to every sign and never finishes. Passes when
    the first closes clean and the second is taken down by its stage time, tree and all. Then
    the runner itself on two alive-looking jobs, a main one and a paid one: passes when it runs
    both at once and each is taken down by its stage time."""
    scale = 120
    base = Path(tempfile.mkdtemp(prefix="annie-selftest-")).resolve()
    scratch = Path(f"/private/tmp/claude-{os.getuid()}") / str(base).replace("/", "-")
    try:
        here = base / ".claude" / "systems" / "annie" / "queue"
        here.mkdir(parents=True)
        shutil.copy(__file__, here / "worker.py")
        shutil.copy(Q, here / "q.py")
        shutil.copy(HERE / "run.sh", here / "run.sh")
        (here / "queue.json").write_text(json.dumps({"next_id": 2, "items": [
            {"id": 1, "title": "self-test", "state": "working", "note": "", "questions": []}]}))
        bin_dir = base / "bin"
        bin_dir.mkdir()
        (bin_dir / "claude").write_text(FAKE_CLAUDE)
        (bin_dir / "claude").chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
                   ANNIE_TIME_SCALE=str(scale))
        results = []
        for mode, want, limit in (("done", 0, 30), ("alive", None, STAGE_DEFAULT * SCALE / scale + 60)):
            began = time.time()
            try:
                p = subprocess.run(["python3", str(here / "worker.py"), "selftest", "x"],
                                   env=dict(env, ANNIE_SELFTEST=mode), capture_output=True,
                                   text=True, timeout=limit)
            except subprocess.TimeoutExpired:
                return f"FAILED: the {mode} job was not closed within {limit:.0f}s"
            took = time.time() - began
            spinning = [l for l in run(["ps", "-Ao", "command="]).splitlines()
                        if "while True: pass" in l and str(scratch) in l]
            if want == 0 and p.returncode != 0:
                return f"FAILED: the finished job exited {p.returncode}\n{p.stdout}"
            if want is None and ("stage ran past" not in p.stdout or p.returncode == 0):
                return f"FAILED: the alive-looking job was not taken down by its stage time\n{p.stdout}"
            if spinning:
                return f"FAILED: the {mode} job left its spinning script running"
            results.append(f"{mode} closed in {took:.0f}s")
        result = lost_test(here, env, scale)
        if result.startswith("FAILED"):
            return result
        results.append(result)
        result = slots_test(here, env, scale, scratch)
        return result if result.startswith("FAILED") else "passed: " + ", ".join(results + [result])
    finally:
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(Path.home() / ".claude" / "projects" / str(base).replace("/", "-"),
                      ignore_errors=True)
        shutil.rmtree(scratch, ignore_errors=True)


def lost_test(here, env, scale):
    """A worker whose turn ended on a connection error while offline: past every time limit it
    is left alone, and once the connection is back it is restarted without being counted."""
    (here / "restarts.json").unlink(missing_ok=True)
    (here / "offline.test").touch()
    wait = (STAGE_DEFAULT * SCALE / scale) + 5      # past the stage time and the quiet limit
    began = time.time()
    p = subprocess.Popen(["python3", str(here / "worker.py"), "selftest", "x"],
                         env=dict(env, ANNIE_SELFTEST="lost"), stdout=subprocess.PIPE, text=True)
    time.sleep(wait)
    if p.poll() is not None:
        return f"FAILED: an offline worker was taken down\n{p.stdout.read()}"
    (here / "offline.test").unlink()
    try:
        out, _ = p.communicate(timeout=40)
    except subprocess.TimeoutExpired:
        p.terminate()
        p.wait()
        return "FAILED: a worker lost to the connection was not restarted when it came back"
    counts = json.loads((here / "restarts.json").read_text())
    if "not counted as stuck" not in out or counts.get("1"):
        return f"FAILED: a lost connection counted as stuck ({counts})\n{out}"
    return f"offline held then restarted uncounted in {time.time() - began:.0f}s"


def slots_test(here, env, scale, scratch):
    """The runner on a main job and a paid job, both alive-looking: both start, side by side,
    and each slot's worker is taken down by its stage time, with nothing left spinning."""
    (here / "restarts.json").unlink(missing_ok=True)
    (here / "queue.json").write_text(json.dumps({"next_id": 3, "items": [
        {"id": 1, "title": "self-test main", "state": "working", "note": "", "questions": []},
        {"id": 2, "title": "self-test paid", "state": "working", "note": "", "questions": [],
         "paid": True}]}))
    (here / "selftest.day").write_text(time.strftime("%Y-%m-%d") + "\n")   # no self-test inside it
    log_file = here / "runner.log"
    runner = subprocess.Popen(["bash", str(here / "run.sh"), "loop"],
                              env=dict(env, ANNIE_SELFTEST="alive"),
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, start_new_session=True)
    limit = STAGE_DEFAULT * SCALE / scale + 90
    began, text = time.time(), ""
    try:
        while time.time() - began < limit:
            text = log_file.read_text() if log_file.exists() else ""
            if "main worker ended" in text and "paid worker ended" in text:
                break
            time.sleep(1)
    finally:
        runner.terminate()
        runner.wait()
        # The runner's workers close their trees on its way out: wait for them.
        while any(str(here) in l for l in run(["ps", "-Ao", "command="]).splitlines()) \
                and time.time() - began < limit + 30:
            time.sleep(1)
    took = time.time() - began
    if "main worker ended" not in text or "paid worker ended" not in text:
        return f"FAILED: the runner's two slots were not both closed within {limit:.0f}s\n{text}"
    first_end = min(text.index("main worker ended"), text.index("paid worker ended"))
    if "worker started: autoworker paid #2" not in text[:first_end] or \
            "worker started: autoworker #1" not in text[:first_end]:
        return f"FAILED: the main and paid slots did not run side by side\n{text}"
    if text.count("stage ran past") < 2:
        return f"FAILED: a slot's worker was not taken down by its stage time\n{text}"
    if any("while True: pass" in l and str(scratch) in l
           for l in run(["ps", "-Ao", "command="]).splitlines()):
        return "FAILED: a slot's job left its spinning script running"
    return f"main and paid slots side by side, both taken down in {took:.0f}s"


if __name__ == "__main__":
    if sys.argv[1:2] == ["--flag"]:
        flag_session()
        sys.exit(0)
    if sys.argv[1:2] == ["--selftest"]:
        result = selftest()
        log(f"self-test {result}")
        sys.exit(0 if result.startswith("passed") else 1)
    main()
