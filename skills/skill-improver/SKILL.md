---
name: skill-improver
description: Turn what a run just learned into a better skill, and turn a process that only lives in a work log into a new skill filed in the right category folder. Use at the end of any run of a skill that has a scorecard, whenever the session-start note lists skills with unread scorecard rows or work logs that changed, when the same hand fix has been needed twice, and when the user says a process should become a skill. Runs without asking and without reporting — the user wants the improvement, not a notice of it.
---

# Skill improver

A skill is the current best way to do a job, in the present tense. This skill keeps it that way. It
has two jobs: **improve** a skill from its own runs, and **harvest** a process into a new skill.

## The three rules

1. **Rewrite the wording; never append a log.** A lesson changes the step it concerns, in place, and
   deletes what it replaced. No "changes", "history", "lessons learned" or dated notes inside a skill.
   Git holds what it used to say.
2. **Measure before believing.** A change is an improvement when the scorecard says so. A lesson with
   no number behind it goes in only when it removes a hand fix.
3. **Do not ask and do not announce.** Make the edit. The exception is a change of *method* — replacing
   the approach a skill is built on — which needs a scored side-by-side first (see below), and any
   paid call, which still needs the user's yes.

## Where things live

```
.claude/skills/<Category>/SKILL.md            the category's front door: one table, one row per sub-skill
.claude/skills/<Category>/<skill>/SKILL.md    the recipe
.claude/skills/<Category>/<skill>/scorecard.csv   one row per run — data, never prose
.claude/skills/<Category>/<skill>/scripts/    tools the recipe calls
```

Categories are named for what the skills are for (`AnimationSkills`). A skill that serves the whole
repo (this one, `agent-creator`) stays directly under `.claude/skills/`. The harness lists only direct
children, so a category is reachable through its front-door `SKILL.md` — a new sub-skill is invisible
until it has a row there.

## Improve — after a run

1. **Read the run.** The new scorecard row, and the run's own notes (its work log, the session).
2. **List what the skill did not tell the runner**: every hand fix, every tool written mid-run, every
   retry, every check that passed while the result was wrong, every step that was skipped and not
   missed.
3. **Place each item** — the cheapest destination that stops it recurring:

   | The run showed | Edit |
   |---|---|
   | a step was wrong or out of date | rewrite that step |
   | a step was missing | add it where the runner needed it |
   | a defect and its fix | a row in the skill's defect table — cause and fix, no story |
   | a check that let a bad result through | tighten the acceptance row; say what number, measured how |
   | a script written mid-run that the next run will need | move it under the skill's `scripts/` and name it in the step |
   | a step nobody needed for three runs | delete it |
   | a limit or risk the user must hear before work starts | the skill's opening, not its end |

4. **Compare with earlier rows.** If the numbers the skill exists to drive down (hand fixes, new fix
   tools, minutes, dollars, failing frames) went **up** after the last edit, that edit was wrong:
   revert it (`git -C .claude log -p -- <skill>`) and write what was actually learned instead.
5. **Read the whole skill once more as its next reader**: someone with no memory of this run. Cut what
   they would not act on. A skill that only grows stops being read.

## A change of method

When the rows show a method has stopped improving — the same class of fix on every run — the skill
should say so plainly in its "what still fails" section and name the next method to prove. Proving it
is one run on one item, beside the current method, scored on the skill's own acceptance table. The
winner becomes the recipe; the loser leaves a sentence saying why it lost, where a reader about to
re-try it will see it.

## Harvest — a process that is not a skill yet

A process is ready to become a skill when it has **worked at least once and will be needed again**.
Signs: a work log that has grown a "recipe" or "pipeline" section, a README of commands in a run
folder, the same sequence run by hand in two sessions, a note that says "next time".

1. **Find them.** The session-start note lists work logs that changed since the last harvest. Read
   those, and the memory notes that point at run folders.
2. **Check it is not already a skill** — the category front doors and `.claude/skills/`. If an existing
   skill covers it, that is an *improve*, not a new skill.
3. **Write the recipe, not the story.** From a log of what happened, keep: when to use it, what must be
   true before starting, the steps in order with the real commands, what to check after each, the
   defect table, the acceptance table, what still fails, and the scorecard columns. Drop every date,
   version number, agent name and dead end that does not prevent a regression.
4. **File it**: the category folder it belongs to (make the folder and its front door if it is the
   first of its kind), a row in the front door, and a `scorecard.csv` with its header — plus one row
   per past run the log has real numbers for.
5. **Verify the commands exist** before writing them down: every script and flag the recipe names is
   opened or run with `--help`. A recipe that names a missing file is worse than none.
6. **Stamp the harvest**: `touch .claude/skills/skill-improver/last-harvest`, so the next session-start
   note lists only what changed after it.

## The scorecard

Every skill that can be run has one. The header is in the skill's "Scorecard" section; the columns are
the few numbers that say whether the job got cheaper and better — always including hand fixes, minutes
and dollars, and the user's verdict where a human judges the result. The runner appends the row; this
skill never edits past rows.

## Saving the work

`.claude` is a git submodule: commit inside it and push before the repo root's pointer can move. Commit
when the user asks.
