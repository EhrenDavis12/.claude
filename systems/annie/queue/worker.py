#!/usr/bin/env python3
"""One annie worker, from start to close. run.sh calls this once per job.

The worker is an interactive Claude session, because only an interactive session shows up in
Remote Control, where the user can watch it or talk to it from claude.ai or their phone. It
runs under a pseudo-terminal nobody looks at, so it needs no window.

Nothing here kills a worker for taking long: an animation can render for two hours. A worker
closes when it writes its "finished" mark (the file named in $ANNIE_WORKER_DONE) as its last
step, or when it is stuck: no sign of life for STUCK_AFTER, or its turn ended without the mark
for IDLE_AFTER (it is waiting for input nobody will give). A stuck worker is taken down, whole
process tree, and its item stays `working`, so the runner starts a fresh worker that resumes it
from its note. After MAX_RESTARTS of the same item it goes to `blocked` with a question instead,
so a job that sticks every time cannot loop (user, 2026-10-28: "identify that the job is stuck
take it down and rebuild it").

Signs of life, any one is enough:
  - its session transcript (or a subagent's) gained a real turn — a user or assistant entry.
    Bookkeeping lines the app appends to an idle session (artifact ledgers, titles) do not count:
    they cleared the flag every half hour on a worker that had sat idle all night. Workers'
    transcripts have also gone missing from disk entirely, so this sign is never the only one.
  - processes under it used at least CPU_LIFE seconds of processor in one look. A wait loop
    (`while pgrep ...; do sleep 15; done`) costs a hundredth of a second a look and is not
    life: two such loops whose pgrep matched their own shell kept a worker "alive" for 15 hours
    while nothing happened (2026-10-27).
  - a file changed in its scratchpad or task output, or — checked once before it is called
    stuck — anywhere under the work folders (WORK_DIRS)
  - the local model server has a job running (its renders are not under the worker)

  worker.py NAME [PROMPT]       PROMPT defaults to /annie-queue --one
"""
import datetime
import json
import os
import pty
import select
import signal
import subprocess
import sys
import time
import uuid
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
Q = HERE / "q.py"
DONE = HERE / "worker.done"
TTY = HERE / "worker.tty"         # the last of the worker's screen, for when something goes wrong
TRANSCRIPTS = Path.home() / ".claude" / "projects" / str(REPO).replace("/", "-")
MODEL_SERVER = "http://127.0.0.1:8188/queue"
# The web tools are for the mastermind's research jobs.
TOOLS = "Agent Bash Read Edit Write Grep Glob Skill SendMessage Artifact WebSearch WebFetch".split()
TICK = 30                 # seconds between looks
STUCK_AFTER = 30 * 60     # no sign of life this long: take it down
CLOSE_AFTER_DONE = 30     # the finished mark is the last step; give its final words time to land
IDLE_AFTER = 5 * 60       # turn ended, no finished mark: it is waiting for input
CPU_LIFE = 0.5            # processor seconds in one look that count as work, not a wait loop
MAX_RESTARTS = 2          # stuck this many times on one item: block it with a question
RESTARTS = HERE / "restarts.json"
SCRATCH = Path(f"/private/tmp/claude-{os.getuid()}") / str(REPO).replace("/", "-")
# Where a worker's artists write. Not the skills or the Chart: the desk writes those, and a
# desk edit must not keep a stuck worker looking alive.
WORK_DIRS = [REPO / "src" / "asset-animation-demo" / "local_runs",
             REPO / "src" / "unity-side-scroler" / "Assets"]
SKIP_DIRS = {"chart"}
TURN_TYPES = ("user", "assistant")


def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}", flush=True)


def _entries(path, size=262144):
    """The parsed JSON lines at the end of one transcript file."""
    try:
        with open(path, "rb") as f:
            f.seek(max(0, os.path.getsize(path) - size))
            lines = f.read().decode("utf-8", "replace").splitlines()[1:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


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
        for e in _entries(f):
            if e.get("type") in TURN_TYPES:
                newest = max(newest, _stamp(e))
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
    out = subprocess.run(["ps", "-Ao", "pid=,ppid=,time="], capture_output=True, text=True).stdout
    kids, cpu = {}, {}
    for line in out.splitlines():
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
    out = subprocess.run(["ps", "-Ao", "pid=,ppid="], capture_output=True, text=True).stdout
    kids = {}
    for line in out.splitlines():
        pid, ppid = map(int, line.split())
        kids.setdefault(ppid, []).append(pid)
    found, todo = [], list(kids.get(root, []))
    while todo:
        pid = todo.pop()
        found.append(pid)
        todo += kids.get(pid, [])
    return found


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
    try:
        with urllib.request.urlopen(MODEL_SERVER, timeout=3) as r:
            return bool(json.load(r).get("queue_running"))
    except Exception:
        return False


def working_id():
    for it in json.loads((HERE / "queue.json").read_text())["items"]:
        if it["state"] == "working":
            return it["id"]
    return None


def flag(on, why="", item=None):
    """Set or clear the flag, then republish the Queue page so the user sees it."""
    item = item if item is not None else working_id()
    if item is not None:
        subprocess.run(["python3", str(Q), "stuck" if on else "unstuck", str(item), *([why] if on else [])])
    elif not on:
        return
    item = item if item is not None else f"{NAME} (its item is no longer marked working)"
    # The runner cannot publish; a short headless Claude can. A few cents, once per change.
    say = (f"Job #{item} looks stuck: {why}" if on else f"Job #{item} is moving again")
    subprocess.run(
        ["claude", "-p",
         f"Run `python3 {Q} render` and publish what it prints to the Queue page, whose link is "
         f"in .claude/systems/annie/SYSTEM.md, exactly as SYSTEM.md says. If a publish is "
         f"refused as a conflict, render again and publish again. Then send the user a push "
         f"notification: \"{say}\". Do nothing else.",
         "--permission-mode", "dontAsk", "--allowedTools", "Bash", "Artifact", "PushNotification"],
        cwd=REPO, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


NAME = sys.argv[1] if len(sys.argv) > 1 else "worker"
PROMPT = sys.argv[2] if len(sys.argv) > 2 else "/annie-queue --one"


def main():
    name = NAME
    sid = str(uuid.uuid4())
    DONE.unlink(missing_ok=True)
    env = dict(os.environ, ANNIE_WORKER_DONE=str(DONE))
    # The prompt goes first: --allowedTools takes every word after it as a tool name.
    cmd = ["claude", PROMPT, "--session-id", sid, "-n", name,
           "--remote-control", name, "--permission-mode", "dontAsk", "--allowedTools", *TOOLS]

    pid, fd = pty.fork()
    if pid == 0:
        import fcntl, struct, termios
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 160, 0, 0))
        os.chdir(REPO)
        os.execvpe(cmd[0], cmd, env)

    # The child leads its own process group, so one signal reaches it and all it started.
    def close(*_):
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        signal.signal(signal.SIGALRM, lambda *_: os.killpg(pid, signal.SIGKILL))
        signal.alarm(15)
    signal.signal(signal.SIGTERM, close)
    signal.signal(signal.SIGINT, close)
    log(f"worker session {sid}")

    def take_down(why):
        """Stuck: close it and everything it started. The item stays `working` and the runner's
        next worker resumes it — unless it has stuck too often, then it is blocked."""
        nonlocal flagged, taken_down
        n = restarts(item, add=1) if item is not None else 1
        if item is not None and n > MAX_RESTARTS:
            restarts(item, clear=True)
            log(f"stuck again ({why}); #{item} stuck {n} times, moved to blocked")
            subprocess.run(["python3", str(Q), "ask", str(item), "--blocker",
                            f"This job got stuck {n} times in a row ({why}); each time it was "
                            f"closed and restarted automatically from where it stopped. It is "
                            f"parked so it cannot loop. Restart it (say 'retry'), or drop it?"])
            flag(False, item=item)
        else:
            log(f"stuck ({why}); taking it down, restart {n} of {MAX_RESTARTS}")
            flag(True, f"{why}. Closed and restarted automatically ({n} of {MAX_RESTARTS}); "
                       f"the new worker resumes from the note.")
        taken_down = True
        for p in descendants(pid):
            try:
                os.kill(p, signal.SIGTERM)
            except ProcessLookupError:
                pass
        close()

    screen = b""
    alive_at, flagged, done_at, taken_down = time.time(), False, None, False
    item, cleared = None, False
    cpu_seen = under_cpu(pid)
    seen = (transcript_written(sid), newest_file([SCRATCH / sid]))
    next_look = time.time() + TICK
    while True:
        r, _, _ = select.select([fd], [], [], TICK)
        if r:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break                       # the session has exited
            if not data:
                break
            screen = (screen + data)[-65536:]
        if time.time() < next_look:
            continue
        next_look = time.time() + TICK

        if done_at is None and DONE.exists():
            log("finished mark written; closing the worker")
            done_at = time.time()
        if done_at and time.time() - done_at > CLOSE_AFTER_DONE:
            close()

        if done_at or taken_down:
            continue
        item = working_id() if working_id() is not None else item
        cpu_now = under_cpu(pid)
        busy_cpu = cpu_now - cpu_seen >= CPU_LIFE
        cpu_seen = cpu_now
        now_seen = (transcript_written(sid), newest_file([SCRATCH / sid]))
        if now_seen != seen or busy_cpu or model_server_busy():
            seen, alive_at = now_seen, time.time()
            if flagged or not cleared:
                # A restarted item carries its old worker's flag until this one shows life.
                if flagged or (item is not None and any(
                        it["id"] == item and it.get("stuck")
                        for it in json.loads((HERE / "queue.json").read_text())["items"])):
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

    _, status = os.waitpid(pid, 0)
    TTY.write_bytes(screen)
    if flagged and not taken_down:
        flag(False)
    code = os.waitstatus_to_exitcode(status)
    if done_at and item is not None:
        restarts(item, clear=True)
    # A worker that wrote its mark finished its job, however its session was closed.
    sys.exit(0 if done_at else (code or 1))


if __name__ == "__main__":
    main()
