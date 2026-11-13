#!/usr/bin/env python3
"""forge's work queue: one JSON file, five states, a read-only page. A port of annie's.

The main loop is the only writer. The user manages the queue by talking to Claude Code (the
desk, /forge-desk), and watches it at a glance on the Queue page. States, in page order:

  working  the pipeline is on it — one at a time, because two live writers in one srcRoot
           is two builds stepping on each other
  review   a built change waiting for the user's eyes: a screenshot or recording attached,
           the branch named in the note. Only the user's word makes it done
  blocked  an open question or blocker on the item
  queued   waiting its turn, top first
  done     the user approved it

Every item belongs to the project that was active when it was added. The queue is shared by
every project, but `next`, `peek`, `check` and the mastermind's gate see only the active
project's items, so a switch with /set-project switches the queue too.

An item added with --auto was made by the mastermind, not the user, and says so on the page.
The mastermind runs only when the queue has no work, and its switch, caps and last pass live
in mastermind.json.

Queued items sit in one of two lanes. `now` is the default; `background` is long work that
runs only when nothing in `now` is waiting.

  q.py add "title" [--top] [--bg] [--note TEXT]
  q.py list [--brief]             the whole queue as text; --brief is one short line per item
  q.py show ID [ID ...]           those items in full, from the queue or the archive
  q.py find WORD [WORD ...]       items in the queue or the archive matching every word, one
                                  line each — search first, read in full only what matches
  q.py next                       claim the top `now` item, else the top background one
  q.py peek                       the job the next worker will take, without claiming it
  q.py check                      between stages: "yield" if a background item is working
                                  while a `now` item waits, else "carry on"
  q.py lane ID now|background     move an item to the other lane
  q.py move ID STATE [--top]
  q.py up ID                      move a queued item to the top
  q.py note ID TEXT [--minutes N] replace the item's one-line status note. On a working item
                                  it is also the worker's promise: the note buys its stage N
                                  minutes (default 90, at most 180), and worker.py takes down a
                                  worker past that with no new note
  q.py clip ID PATH               attach the screenshot or recording to look at; the item goes
                                  to review
  q.py ask ID TEXT [--blocker]    add a question; the item goes to blocked
  q.py answer ID N TEXT           answer question N; with none left open it goes back on top
  q.py drop ID                    remove an item outright
  q.py archive [--days N]         move done items untouched for N days (default 1) out of the
                                  queue into archive.json; show and find still read them
  q.py stuck ID TEXT              the runner's flag: the worker shows no sign of life
  q.py unstuck ID                 clear it, when the worker comes back to life
  q.py auto on|off|status         the mastermind's switch; off unless the user says otherwise
  q.py limit PERCENT|default       raise (or lower) the usage stop until the weekly reset, then
                                  it falls back to the default on its own
  q.py idle [--claim]             may the mastermind run now? "go", or "no: <why>"; --claim
                                  on "go" stamps the pass, so the runner starts only one
  q.py render                     write page/ for the claude.ai artifact; prints what to publish
  q.py serve [--port 8765]        the same page live, on 127.0.0.1 only
"""
import argparse
import fcntl
import html
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUEUE = HERE / "queue.json"
MASTER = HERE / "mastermind.json"
# Off until the user flips it. No cap on how many jobs: the usage plan and a clean board are
# the limits. The short cooldown only stops back-to-back passes that make nothing.
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
USAGE_CACHE = HERE / "usage.cache.json"
USAGE_EVERY = 300
MASTER_DEFAULT = {"on": False, "review_cap": 3, "cooldown_min": 10,
                  "usage_limit": 85,
                  "last_pass": "", "made": []}
REPO = HERE.parents[3]
STAGE_DEFAULT = 90   # minutes a note buys the stage it starts; worker.py holds the same number
STAGE_MAX = 180      # the most one note may promise: a longer stage notes again part way
STATES = ["working", "review", "blocked", "queued", "done"]
LABELS = {"working": "Working", "review": "Needs your eyes", "blocked": "Blocked",
          "queued": "Queued", "done": "Done"}
def active_project():
    """The active project's slug, or "" — the pointer /set-project writes."""
    try:
        return json.loads((REPO / ".claude" / "project" / "active.json").read_text()).get("project", "")
    except (OSError, ValueError):
        return ""


# The page splits queued into its two lanes; everything else is one column per state.
COLUMNS = [("working", "Working"), ("review", "Needs your eyes"), ("blocked", "Blocked"),
           ("now", "Up next"), ("background", "Background"), ("done", "Done")]


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load():
    if not QUEUE.exists():
        return {"next_id": 1, "items": []}
    return json.loads(QUEUE.read_text())


def save(q):
    # Write-then-rename, so the page never reads half a file.
    fd, tmp = tempfile.mkstemp(dir=HERE, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(q, f, indent=2)
        f.write("\n")
    os.replace(tmp, QUEUE)


def load_master():
    m = dict(MASTER_DEFAULT)
    if MASTER.exists():
        m.update(json.loads(MASTER.read_text()))
    return m


def save_master(m):
    fd, tmp = tempfile.mkstemp(dir=HERE, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(m, f, indent=2)
        f.write("\n")
    os.replace(tmp, MASTER)


def find(q, item_id):
    for it in q["items"]:
        if it["id"] == item_id:
            return it
    sys.exit(f"no item {item_id}")


def place(q, it, state, top=False):
    """Set the state and put the item at the top or bottom of that state's list."""
    q["items"].remove(it)
    it["state"], it["updated"] = state, now()
    same = [i for i, x in enumerate(q["items"]) if x["state"] == state]
    if top and same:
        q["items"].insert(same[0], it)
    else:
        q["items"].append(it)


def open_questions(it):
    return [x for x in it["questions"] if not x.get("answer")]


def owed_questions(items):
    """Open questions the user still owes: a finished item's leftovers are moot."""
    return [(it, x) for it in items if it["state"] != "done" for x in open_questions(it)]


def lane(it):
    return it.get("lane", "now")


def mine(q):
    """The items the runner may work: the active project's."""
    p = active_project()
    return [it for it in q["items"] if it.get("project", p) == p]


def show(it):
    tag = it["state"] + (" · background" if lane(it) == "background" else "") \
        + (" · auto" if it.get("auto") else "") + project_tag(it)
    line = f"#{it['id']} [{tag}] {it['title']}"
    if it.get("note"):
        line += f" — {it['note']}"
    if it.get("stuck"):
        line += f"\n    LOOKS STUCK: {it['stuck']}"
    if it.get("clip"):
        line += f"\n    clip: {it['clip']}"
    for n, x in enumerate(it["questions"], 1):
        kind = "BLOCKER" if x.get("blocker") else "Q"
        line += f"\n    {kind}{n}: {x['text']}"
        if x.get("answer"):
            line += f"\n      A: {x['answer']}"
    return line


def project_tag(it):
    """Named only when it is not the active project, so the everyday view stays short."""
    p = it.get("project", "")
    return f" · {p}" if p and p != active_project() else ""


def cmd_add(a, q):
    project = active_project()
    if not project:
        sys.exit("no active project: run /set-project first")
    it = {"id": q["next_id"], "title": a.title, "state": "queued", "note": a.note or "",
          "clip": "", "questions": [], "lane": "background" if a.bg else "now",
          "project": project, "created": now(), "updated": now()}
    if a.auto:
        it["auto"] = True
        m = load_master()
        # A week of stamps is kept for the status count; dropped items must still count.
        m["made"] = [t for t in m["made"] if t >= _ago(days=7)] + [now()]
        save_master(m)
    q["next_id"] += 1
    q["items"].append(it)
    place(q, it, "queued", a.top)
    print(show(it))


def brief(it, where=""):
    tag = it["state"] + (" · auto" if it.get("auto") else "") + project_tag(it) + where
    return f"#{it['id']} [{tag}] {it['title'][:90]} — {it.get('note', '')[:110]}"


def cmd_list(a, q):
    for state in STATES:
        for it in q["items"]:
            if it["state"] == state:
                print(brief(it) if a.brief else show(it))


def cmd_show(a, q):
    archive = HERE / "archive.json"
    old = json.loads(archive.read_text())["items"] if archive.exists() else []
    for item_id in a.ids:
        it = next((x for x in q["items"] + old if x["id"] == item_id), None)
        print(show(it) if it else f"no item {item_id}")


def cmd_find(a, q):
    """Every item, in the queue or the archive, whose text holds all the words."""
    archive = HERE / "archive.json"
    pools = [(q["items"], "")]
    if archive.exists():
        pools.append((json.loads(archive.read_text())["items"], " · archive"))
    words = [w.lower() for w in a.words]
    hits = 0
    for items, where in pools:
        for it in items:
            text = " ".join([it["title"], it.get("note", "")]
                            + [x["text"] + " " + x.get("answer", "") for x in it["questions"]]).lower()
            if all(w in text for w in words):
                print(brief(it, where))
                hits += 1
    if not hits:
        print("no match")


def promise(it, minutes=STAGE_DEFAULT):
    """When the stage this note starts must have noted again, for worker.py's ceiling."""
    minutes = max(1, min(minutes, STAGE_MAX))
    it["deadline"] = (datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def cmd_next(a, q):
    if any(it["state"] == "working" for it in mine(q)):
        it = next(it for it in mine(q) if it["state"] == "working")
        print(f"already working: {show(it)}")
        return
    queued = [it for it in mine(q) if it["state"] == "queued"]
    queued.sort(key=lambda it: lane(it) == "background")  # stable: keeps each lane's order
    if not queued:
        print("nothing queued")
        return
    place(q, queued[0], "working")
    promise(queued[0])
    print(show(queued[0]))


def cmd_peek(a, q):
    """The job the next worker will take, without claiming it: `#id title`, or nothing."""
    order = [it for it in mine(q) if it["state"] == "working"]
    queued = [it for it in mine(q) if it["state"] == "queued"]
    order += sorted(queued, key=lambda it: lane(it) == "background")
    if order:
        print(f"#{order[0]['id']} {order[0]['title']}")


def cmd_check(a, q):
    working = [it for it in mine(q) if it["state"] == "working"]
    waiting = [it for it in mine(q) if it["state"] == "queued" and lane(it) == "now"]
    if working and lane(working[0]) == "background" and waiting:
        print(f"yield: #{waiting[0]['id']} {waiting[0]['title']} is waiting")
    else:
        print("carry on")


def cmd_lane(a, q):
    if a.lane not in ("now", "background"):
        sys.exit("lane must be now or background")
    it = find(q, a.id)
    it["lane"], it["updated"] = a.lane, now()
    print(show(it))


def cmd_move(a, q):
    if a.state not in STATES:
        sys.exit(f"state must be one of {', '.join(STATES)}")
    it = find(q, a.id)
    place(q, it, a.state, a.top)
    print(show(it))


def cmd_up(a, q):
    it = find(q, a.id)
    place(q, it, it["state"], top=True)
    print(show(it))


def cmd_note(a, q):
    it = find(q, a.id)
    it["note"], it["updated"] = a.text, now()
    promise(it, a.minutes)
    print(show(it))


def cmd_clip(a, q):
    it = find(q, a.id)
    # Copied in beside the queue: a worker's scratchpad is outside the repo, and the page only
    # ever serves files inside it.
    src = Path(a.path).resolve()
    if not src.is_file():
        sys.exit(f"no file {src}")
    keep = HERE / "clips"
    keep.mkdir(exist_ok=True)
    dest = keep / f"{it['id']}{src.suffix.lower()}"
    if src != dest:
        shutil.copyfile(src, dest)
    it["clip"] = str(dest)
    place(q, it, "review")
    print(show(it))


def cmd_ask(a, q):
    it = find(q, a.id)
    it["questions"].append({"text": a.text, "blocker": a.blocker, "answer": "",
                            "asked": now()})
    place(q, it, "blocked")
    print(show(it))


def cmd_answer(a, q):
    it = find(q, a.id)
    if not 1 <= a.n <= len(it["questions"]):
        sys.exit(f"#{a.id} has no question {a.n}")
    it["questions"][a.n - 1]["answer"] = a.text
    it["updated"] = now()
    # An answered item goes back on top of the queue: it already waited once.
    if it["state"] == "blocked" and not open_questions(it):
        place(q, it, "queued", top=True)
    print(show(it))


def cmd_stuck(a, q):
    find(q, a.id)["stuck"] = f"{a.text} (since {now()})"


def cmd_unstuck(a, q):
    find(q, a.id).pop("stuck", None)


def _ago(**span):
    return (datetime.now() - timedelta(**span)).strftime("%Y-%m-%d %H:%M")


def usage_limit(m):
    """The stop point in force: the user's override until the weekly reset it was set
    against, else the default."""
    o = m.get("override") or {}
    if o and datetime.now().timestamp() < datetime.fromisoformat(o["until"]).timestamp():
        return o["limit"]
    return m["usage_limit"]


def cmd_limit(a, q):
    m = load_master()
    if a.percent == "default":
        m.pop("override", None)
    else:
        until = usage_now()["seven_day"]["resets_at"]
        m["override"] = {"limit": float(a.percent), "until": until}
    save_master(m)
    cmd_auto(argparse.Namespace(switch="status"), q)


def cmd_auto(a, q):
    m = load_master()
    if a.switch in ("on", "off"):
        m["on"] = a.switch == "on"
        save_master(m)
    today = now()[:10]
    made = sum(t.startswith(today) for t in m["made"])
    limit, o = usage_limit(m), m.get("override")
    over = usage_over(limit)
    until = (f" until {datetime.fromisoformat(o['until']).astimezone().strftime('%a %H:%M')}"
             if o and limit == o["limit"] else "")
    print(f"mastermind {'on' if m['on'] else 'off'} · {made} auto jobs "
          f"today · last pass {m['last_pass'] or 'never'} · usage limit {limit:g}%{until}"
          + (f" — paused: {over}" if over else ""))


def usage_now():
    """The account's 5-hour and 7-day usage, straight from Anthropic — the numbers /usage
    shows — through Claude Code's own sign-in in the keychain. The token is never printed or
    stored. Read at most every USAGE_EVERY seconds, because the runner asks every few."""
    try:
        c = json.loads(USAGE_CACHE.read_text())
        if datetime.now().timestamp() - c["at"] < USAGE_EVERY:
            return c["usage"]
    except (OSError, ValueError, KeyError):
        pass
    import subprocess, urllib.request
    raw = subprocess.run(["security", "find-generic-password", "-s", "Claude Code-credentials",
                          "-w"], capture_output=True, text=True, timeout=10).stdout
    token = json.loads(raw)["claudeAiOauth"]["accessToken"]
    req = urllib.request.Request(USAGE_URL, headers={"Authorization": f"Bearer {token}",
                                                     "anthropic-beta": "oauth-2025-04-20"})
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.load(r)
    usage = {k: d.get(k) for k in ("five_hour", "seven_day")}
    USAGE_CACHE.write_text(json.dumps({"at": datetime.now().timestamp(), "usage": usage}))
    return usage


def weekly_pace(limit, seven_day):
    """The share of the week's limit we may have used by now: the limit spread evenly over
    the 7-day window. Two and a half days into a window at 85% allows about 30%."""
    reset = datetime.fromisoformat(seven_day["resets_at"]).timestamp()
    left = max(0.0, reset - datetime.now().timestamp())
    return limit * (1 - left / (7 * 86400))


def usage_over(limit):
    """Why usage stops the mastermind, or "". Fails closed: no reading, no pass.
    Two stops: either window at or over the limit, and the week ahead of its even pace."""
    try:
        u = usage_now()
    except Exception as err:
        return f"usage could not be read ({type(err).__name__})"
    for key, label in (("five_hour", "5-hour"), ("seven_day", "7-day")):
        used = (u.get(key) or {}).get("utilization")
        if used is not None and used >= limit:
            return f"{label} usage is {used:.0f}%, at or over the {limit:g}% limit"
    week = u.get("seven_day") or {}
    if week.get("utilization") is not None and week.get("resets_at"):
        pace = weekly_pace(limit, week)
        if week["utilization"] > pace:
            return (f"the week is ahead of pace: {week['utilization']:.0f}% used, "
                    f"{pace:.0f}% allowed by now")
    return ""


def goal_set():
    """True when the active project's Focus has text under "## Goal" beyond its comment."""
    import re
    slug = active_project()
    for manifest in [REPO / "Docs" / slug / "project.json", *(REPO / "Docs").glob("*/project.json")]:
        try:
            mf = json.loads(manifest.read_text())
        except (OSError, ValueError):
            continue
        if mf.get("name") != slug:
            continue
        try:
            text = (REPO / mf["docsRoot"] / "queue" / "focus.md").read_text()
        except (OSError, KeyError):
            return False
        goal = re.search(r"^## Goal\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
        body = re.sub(r"<!--.*?-->", "", goal.group(1), flags=re.S).strip() if goal else ""
        return bool(body)
    return False


def idle_reason(q, m):
    """Why the mastermind may not run now, or "" when it may."""
    items = mine(q)
    if not m["on"]:
        return "the switch is off"
    if any(it["state"] in ("queued", "working") for it in items):
        return "the queue has work"
    if sum(1 for it in items if it.get("auto") and it["state"] == "review") >= m["review_cap"]:
        return f"{m['review_cap']} auto results already wait for the user"
    if m["last_pass"] > _ago(minutes=m["cooldown_min"]):
        return f"it ran less than {m['cooldown_min']} minutes ago"
    # A pass with no Goal makes nothing, so it is not started: a session every cooldown to say
    # "no goal" is tokens for nothing.
    if not goal_set():
        return "the project's Focus has no Goal yet"
    # Last, so an idle runner asks only once every other gate is open.
    return usage_over(usage_limit(m))


def cmd_idle(a, q):
    m = load_master()
    why = idle_reason(q, m)
    if why:
        print(f"no: {why}")
        return
    if a.claim:
        m["last_pass"] = now()
        save_master(m)
    print("go")


def cmd_drop(a, q):
    it = find(q, a.id)
    q["items"].remove(it)
    print(f"dropped #{it['id']} {it['title']}")


def cmd_archive(a, q):
    """Done items older than N days leave the live queue for archive.json, under the same lock."""
    cutoff = _ago(days=a.days)
    old = [it for it in q["items"] if it["state"] == "done" and it.get("updated", "") < cutoff]
    if not old:
        print("nothing to archive")
        return
    archive = HERE / "archive.json"
    kept = json.loads(archive.read_text()) if archive.exists() else {"items": []}
    have = {it["id"] for it in kept["items"]}
    for it in old:
        it["archived"] = {"date": now()[:10], "why": f"done, untouched {a.days:g}+ days: archive sweep"}
    kept["items"] += [it for it in old if it["id"] not in have]
    fd, tmp = tempfile.mkstemp(dir=HERE, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(kept, f, indent=2)
        f.write("\n")
    os.replace(tmp, archive)
    for it in old:
        q["items"].remove(it)
    left = sum(it["state"] == "done" for it in q["items"])
    print(f"archived {len(old)} done items; {left} done kept")


# ---- the page -------------------------------------------------------------------------------

# One fragment serves both ways: wrapped in a document for `serve`, and published bare as a
# claude.ai artifact by `render`, whose publish adds the document skeleton itself.
PAGE = """<title>Forge Queue</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* layout: the questions owed first, then one column per state in pipeline order */
:root{--bg:#f3f4f1;--card:#fff;--ink:#1c1f1d;--dim:#646a66;--line:#dfe2dd;
--working:#2f62c9;--review:#a87400;--blocked:#c2410c;--now:#5b6bb5;--background:#8a8f8b;--queued:#6f7671;--done:#2e7d4f;
--body:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
--mono:ui-monospace,"SF Mono",Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151716;--card:#1f2220;
--ink:#e8ebe8;--dim:#9aa19c;--line:#323633;--working:#6c9bf0;--review:#e0a93a;
--blocked:#f0804f;--now:#9aa6e8;--background:#7d837f;--queued:#9aa19c;--done:#5fbf86;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#151716;--card:#1f2220;--ink:#e8ebe8;--dim:#9aa19c;
--line:#323633;--working:#6c9bf0;--review:#e0a93a;--blocked:#f0804f;--now:#9aa6e8;
--background:#7d837f;--queued:#9aa19c;
--done:#5fbf86;color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:15px/1.45 var(--body)}
main{max-width:1400px;margin:0 auto;padding-block:16px 32px;
padding-left:max(16px,env(safe-area-inset-left,0px));
padding-right:max(16px,env(safe-area-inset-right,0px))}
h1{font-size:20px;margin:0 0 2px;text-wrap:balance}
.sub{color:var(--dim);font-size:13px;margin-bottom:16px;font-variant-numeric:tabular-nums}
.asks{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:10px 14px;margin-bottom:16px}
.asks h2{font-size:15px;margin:0 0 6px;color:var(--blocked)}
.asks ul{margin:0;padding-left:18px;display:grid;gap:4px}
.cols{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.col{min-width:0}
.col h2{font-size:12px;letter-spacing:.06em;text-transform:uppercase;margin:0 0 8px;
display:flex;gap:6px;align-items:center}
.dot{width:10px;height:10px;border-radius:50%;flex:none}
.n{color:var(--dim);font-weight:400;font-variant-numeric:tabular-nums}
.stack{display:grid;gap:8px}
.card{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--s);
border-radius:6px;padding:8px 10px;overflow-wrap:anywhere}
.t{font-weight:600}.id{font-family:var(--mono);color:var(--dim);font-weight:400}
.meta{color:var(--dim);font-size:12px;font-variant-numeric:tabular-nums}
.note{font-size:13px;margin-top:4px}.q{font-size:13px;margin-top:6px}
.q b{color:var(--blocked)}.a{color:var(--dim)}a{color:var(--working)}
video,.card img{display:block;width:100%;max-width:100%;margin-top:6px;border-radius:4px;
background:var(--line)}
.empty{color:var(--dim);font-size:13px}
.auto{font:600 11px var(--body);color:var(--now);border:1px solid var(--now);border-radius:999px;
padding:0 7px;margin-left:4px;vertical-align:1px}
.asks h2{display:flex;align-items:center;gap:8px}
.look{display:block;width:100%;padding:0;border:0;background:none;cursor:zoom-in}
.viewer{position:fixed;inset:0;z-index:20;background:var(--bg);display:flex;flex-direction:column}
.viewer[hidden]{display:none}
.viewer .bar{display:flex;justify-content:flex-end;gap:8px;
padding:calc(8px + env(safe-area-inset-top,0px)) max(16px,env(safe-area-inset-right,0px)) 8px
max(16px,env(safe-area-inset-left,0px))}
.viewer .bar button{font:600 15px var(--body);color:var(--card);background:var(--working);
border:0;border-radius:8px;padding:10px 18px;min-height:44px;cursor:pointer}
.viewer .bar button.alt{background:var(--card);color:var(--ink);border:1px solid var(--line)}
.viewer .pic{flex:1;overflow:auto;-webkit-overflow-scrolling:touch;
padding:0 max(16px,env(safe-area-inset-right,0px)) calc(16px + env(safe-area-inset-bottom,0px))
max(16px,env(safe-area-inset-left,0px))}
.viewer .pic img{display:block;margin:0 auto;max-width:100%;height:auto}
.viewer.big .pic img{max-width:none;width:250%}
</style>
<main data-say="{summary}"><h1>Forge queue · {project}</h1><div class="sub">{sub}</div>
{asks}<div class="cols">{cols}</div>
</main>
<div class="viewer" id="viewer" hidden role="dialog" aria-modal="true" aria-label="Picture">
<div class="bar"><button id="viewer-zoom" class="alt" type="button">Zoom in</button>
<button id="viewer-close" type="button">Close</button></div>
<div class="pic" id="viewer-pic"><img id="viewer-img" alt=""></div></div>
<script>
// The picture viewer sits on top of the page, so closing it puts you back where you were.
(function () {
  var v = document.getElementById("viewer"), img = document.getElementById("viewer-img"),
      zoom = document.getElementById("viewer-zoom"), y = 0;
  function close() { v.hidden = true; v.classList.remove("big"); document.body.style.overflow = ""; window.scrollTo(0, y); }
  document.querySelectorAll(".look").forEach(function (b) {
    b.onclick = function () {
      y = window.scrollY; img.src = b.querySelector("img").src; zoom.textContent = "Zoom in";
      v.hidden = false; document.body.style.overflow = "hidden";
      document.getElementById("viewer-close").focus();
    };
  });
  document.getElementById("viewer-close").onclick = close;
  zoom.onclick = function () { var big = v.classList.toggle("big"); zoom.textContent = big ? "Fit to screen" : "Zoom in"; };
  document.getElementById("viewer-pic").onclick = function (e) { if (e.target === this) close(); };
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !v.hidden) close(); });
})();
</script>
"""


def e(s):
    return html.escape(str(s))


def render(q, clip_href, sub):
    items = q["items"]
    asks = ""  # no "Waiting on you" list: user, 2026-10-30, it went stale; cards carry their own questions
    cols = ""
    for state, label in COLUMNS:
        if state in ("now", "background"):
            group = [it for it in items if it["state"] == "queued" and lane(it) == state]
        else:
            group = [it for it in items if it["state"] == state]
        if state == "done":
            group = sorted(group, key=lambda it: it["updated"], reverse=True)[:10]
        cards = ""
        for it in group:
            badge = ('<span class="auto">auto</span>' if it.get("auto") else "") \
                + (f'<span class="auto">{e(it["project"])}</span>' if project_tag(it) else "")
            body = f'<div class="t"><span class="id">#{it["id"]}</span> {e(it["title"])}{badge}</div>'
            body += f'<div class="meta">updated {e(it["updated"])}</div>'
            if it.get("stuck"):
                body += f'<div class="q"><b>Looks stuck</b> {e(it["stuck"])}</div>'
            if it.get("note"):
                body += f'<div class="note">{e(it["note"])}</div>'
            href = clip_href(it) if it.get("clip") else ""
            if href:
                if Path(it["clip"]).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                    body += (f'<button class="look" type="button" aria-label="Open the picture">'
                             f'<img src="{href}" alt="the change to review"></button>')
                else:
                    body += f'<video src="{href}" controls playsinline preload="metadata"></video>'
            for n, x in enumerate(it["questions"], 1):
                kind = "Blocker" if x.get("blocker") else "Q"
                body += f'<div class="q"><b>{kind}{n}</b> {e(x["text"])}'
                if x.get("answer"):
                    body += f'<div class="a">A: {e(x["answer"])}</div>'
                body += "</div>"
            said = spoken(it, label)
            cards += (f'<div class="card" style="--s:var(--{state})" data-say="{e(said)}">'
                      f'{body}</div>')
        head = f"{label}: {len(group)}."
        cols += (f'<div class="col" data-head="{e(head)}"><h2><span class="dot" '
                 f'style="background:var(--{state})"></span>{label} '
                 f'<span class="n">{len(group)}</span></h2>'
                 f'<div class="stack">{cards or "<div class=empty>Nothing here</div>"}</div></div>')
    return (PAGE.replace("{summary}", e(summary(q))).replace("{sub}", e(sub))
            .replace("{project}", e(active_project() or "no project"))
            .replace("{asks}", asks)
            .replace("{cols}", cols))


def spoken(it, label):
    """One card as a sentence or two, for the read-aloud button."""
    parts = [f"{it['title']}. {label}." + (" Made by the mastermind." if it.get("auto") else "")]
    if it.get("stuck"):
        parts.append(f"Looks stuck: {it['stuck']}")
    if it.get("note"):
        parts.append(it["note"])
    for x in it["questions"]:
        kind = "Blocker" if x.get("blocker") else "Question"
        parts.append(f"{kind}: {x['text']}")
        if x.get("answer"):
            parts.append(f"Answered: {x['answer']}")
    return " ".join(parts)


def summary(q):
    """What the user needs to hear first: what is owed, then what is moving, then the counts."""
    items = q["items"]
    said = [f"{it['title']} looks stuck: {it['stuck']}." for it in items if it.get("stuck")]
    look = [it for it in items if it["state"] == "review"]
    if look:
        said.append(f"{len(look)} ready for you to look at: "
                    + "; ".join(it["title"] for it in look) + ".")
    work = [it for it in items if it["state"] == "working"]
    for it in work:
        said.append(f"Working on {it['title']}." + (f" {it['note']}" if it.get("note") else ""))
    if not work:
        said.append("Nothing is being worked on right now.")
    for name, lane_id in (("Up next", "now"), ("In the background", "background")):
        group = [it for it in items if it["state"] == "queued" and lane(it) == lane_id]
        if group:
            said.append(f"{name}: {len(group)} job{'s' if len(group) != 1 else ''}, "
                        f"starting with {group[0]['title']}.")
    return " ".join(said)


def clip_file(it):
    """The item's clip, if it is a real file inside the repo; nothing outside is ever served."""
    path = Path(it["clip"]).resolve()
    return path if path.is_file() and REPO in path.parents else None


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        q = load()
        if self.path.startswith("/clip/"):
            return self.clip(q, self.path[len("/clip/"):])
        if self.path not in ("/", "/index.html"):
            return self.send_error(404)
        page = render(q, lambda it: f"/clip/{it['id']}" if clip_file(it) else "",
                      f"refreshes every 10 s · last loaded {now()}")
        body = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" '
                'content="width=device-width,initial-scale=1"><meta http-equiv="refresh" '
                f'content="10"></head><body>{page}</body></html>').encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def clip(self, q, raw):
        it = next((it for it in q["items"] if str(it["id"]) == raw and it.get("clip")), None)
        path = clip_file(it) if it else None
        if not path:
            return self.send_error(404)
        kind = {".mp4": "video/mp4", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp"}.get(path.suffix.lower(), "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def cmd_serve(a, q):
    server = ThreadingHTTPServer(("127.0.0.1", a.port), Page)
    print(f"forge queue at http://127.0.0.1:{a.port} — ctrl-c to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def cmd_render(a, q):
    """Write the page and its clips to page/, ready to publish as the claude.ai artifact."""
    out = HERE / "page"
    clips = out / "clips"
    shutil.rmtree(clips, ignore_errors=True)
    clips.mkdir(parents=True)
    published = {}
    for it in q["items"]:
        # Done clips stay off the page: approved work is in the game itself.
        src = clip_file(it) if it.get("clip") and it["state"] != "done" else None
        if src:
            name = f"clips/{it['id']}{src.suffix}"
            shutil.copyfile(src, out / name)
            published[it["id"]] = name
    page = render(q, lambda it: published.get(it["id"], ""), f"updated {now()}")
    (out / "index.html").write_text(page)
    print(json.dumps({"file_path": str(out / "index.html"), "root": str(out),
                      "files": {n: n for n in published.values()}}))


def main():
    p = argparse.ArgumentParser(description="forge's work queue")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("title"); s.add_argument("--top", action="store_true"); s.add_argument("--bg", action="store_true"); s.add_argument("--auto", action="store_true"); s.add_argument("--note")
    s = sub.add_parser("auto"); s.add_argument("switch", nargs="?", default="status", choices=["on", "off", "status"])
    s = sub.add_parser("limit"); s.add_argument("percent")
    s = sub.add_parser("idle"); s.add_argument("--claim", action="store_true")
    s = sub.add_parser("list"); s.add_argument("--brief", action="store_true")
    s = sub.add_parser("show"); s.add_argument("ids", type=int, nargs="+")
    s = sub.add_parser("find"); s.add_argument("words", nargs="+")
    sub.add_parser("next")
    sub.add_parser("check")
    sub.add_parser("peek")
    s = sub.add_parser("lane"); s.add_argument("id", type=int); s.add_argument("lane")
    s = sub.add_parser("move"); s.add_argument("id", type=int); s.add_argument("state"); s.add_argument("--top", action="store_true")
    s = sub.add_parser("up"); s.add_argument("id", type=int)
    s = sub.add_parser("note"); s.add_argument("id", type=int); s.add_argument("text"); s.add_argument("--minutes", type=int, default=STAGE_DEFAULT)
    s = sub.add_parser("clip"); s.add_argument("id", type=int); s.add_argument("path")
    s = sub.add_parser("ask"); s.add_argument("id", type=int); s.add_argument("text"); s.add_argument("--blocker", action="store_true")
    s = sub.add_parser("answer"); s.add_argument("id", type=int); s.add_argument("n", type=int); s.add_argument("text")
    s = sub.add_parser("drop"); s.add_argument("id", type=int)
    s = sub.add_parser("archive"); s.add_argument("--days", type=float, default=1)
    s = sub.add_parser("stuck"); s.add_argument("id", type=int); s.add_argument("text")
    s = sub.add_parser("unstuck"); s.add_argument("id", type=int)
    sub.add_parser("render")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8766)
    a = p.parse_args()
    readonly = a.cmd in ("list", "serve", "render", "check", "peek", "auto", "idle", "limit", "find", "show")
    # A change holds the lock from read to write: the desk, the worker and worker.py all write,
    # and two at once would each save over the other's change.
    with open(HERE / "queue.lock", "w") as lock:
        if not readonly:
            fcntl.flock(lock, fcntl.LOCK_EX)
        q = load()
        globals()[f"cmd_{a.cmd}"](a, q)
        if not readonly:
            save(q)


if __name__ == "__main__":
    main()
