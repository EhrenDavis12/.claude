---
description: Open a pull request from the current branch for one or more repos in this mono repo
argument-hint: "[repo or project names — omit for the main repo]"
allowed-tools: Bash, Read, Glob, Grep
---

# Create pull requests

Open one PR per named target, from whatever branch that repo is currently on into `Dev`, and
hand the user the URLs. **The user clicks merge. This command never merges, never force-pushes,
and never rewrites history.**

The targets, if any, are: `$ARGUMENTS`

## What a target names

Each argument is a **repo**, resolved in this order:

1. **The mono repo itself** — `local-RED-dev`, `root`, `repo`, or `.` all mean the repository at
   the repo root.
2. **A project** — match the argument against `Docs/*/project.json` on `.name` first, then on
   `aliases`. A project resolves to **every path in its `srcRoots`** — one PR per src root. So
   `tic-tac-toe` resolves to `src/Tic-Tac-Toe-Extreme`.
3. **A literal path** to a directory that is a git repo — accepted as-is.

`/create-pr tic-tac-toe local-RED-dev` is therefore two PRs: one in the `Tic-Tac-Toe-Extreme`
submodule, one in `local-RED-dev`.

**With no arguments, the target is the mono repo alone.** Don't guess that the user also meant
the active project — an unasked-for PR is worse than a missing one.

If an argument matches nothing, **stop and say so** rather than falling back to the mono repo.
Name what you tried: the project slugs you found and the aliases you checked.

Targets are independent. One failing does not cancel the others — finish the rest and report
the failure alongside the successes.

### Order matters: submodules first

When the target list includes both the mono repo and one of its submodules, **create the
submodule PRs first**. The mono repo's diff contains the submodule pointer bump, and its PR body
should link the submodule PR that the bump points at. Reverse the order and the parent PR
describes a commit no one can review yet.

## `srcRoots` are submodules — scope every git command with `-C`

A `git diff` from the repo root shows a **changed submodule pointer**, never the code inside it.
Every command in this file runs as `git -C <repoPath> …`, including for the mono repo itself.
There is no bare `git` here. This repo has already shipped one bug from getting this wrong.

## Per repo, in order

### 1. Resolve the base branch

Read the remote's actual heads — `git -C <repo> ls-remote --heads origin` — and pick the base:

1. `Dev` if it exists (match case-insensitively, then use the **real** name from the remote —
   `Dev` and `dev` are different refs to git and only one of them exists).
2. Otherwise the repo's default branch: `gh repo view --json defaultBranchRef -q
   .defaultBranchRef.name`.

Say which one you resolved and why in the plan below. If it fell back, say it fell back — the
user asked for `Dev`, and a PR quietly retargeted at `main` is the kind of thing that gets
noticed after the merge.

### 2. Check the head branch is sane

Stop this target, with the reason, if:

- **Detached HEAD** — `git -C <repo> symbolic-ref -q HEAD` fails. Common in submodules. There is
  no branch to open a PR from; the user needs to check one out.
- **Head equals base** — you can't PR a branch into itself.
- **No commits ahead** — `git -C <repo> rev-list --count origin/<base>..HEAD` is `0`. Report
  "nothing to PR" and move on. This is a normal outcome, not an error.
- **An open PR already exists** for this head → base. Return that URL instead of opening a
  second one, and label it as pre-existing.

### 3. Handle uncommitted work — ask, never assume

`git -C <repo> status --porcelain`. If it is not empty, **stop and ask the user** what to do:
commit it, or open the PR without it. Do not commit on your own initiative.

Two things are hard stops regardless of the answer — report and skip the target:

- **Unresolved merge conflicts** (`UU`, `AA`, `DD` in the status). Never resolve a conflict as
  part of opening a PR.
- **Uncommitted changes inside a submodule** when the target is the mono repo. Committing the
  parent would pin a pointer at a commit that doesn't reflect the working tree.

### 4. Read the diff

```
git -C <repo> diff origin/<base>...HEAD --stat
git -C <repo> log origin/<base>..HEAD --format='%s%n%b'
git -C <repo> diff origin/<base>...HEAD
```

Three dots for the diff — it compares against the merge base, so it shows what this branch did,
not what happened on the base since it forked. Two dots for the log.

If the full diff is large, read the `--stat` and the commit messages first and pull only the
files that matter into context. You are writing a summary, not a review.

### 5. Push the branch

`git -C <repo> push -u origin HEAD`. Plain push only. If it is rejected as non-fast-forward,
**stop and report** — the fix is the user's call, and it is never `--force`.

### 6. Write the PR

**Short. That is the whole point of this command.** A reviewer should get the shape of the
change in under thirty seconds and go read the diff for the rest.

Title: `<area>: <what changed>`, under 72 characters, no trailing period.

Body, exactly this shape:

```markdown
## What changed
- One bullet per meaningful change, grouped by area. Max 8 bullets.

## Why
One to three sentences. The intent, not a restatement of the bullets.

## Notes
Only when a reviewer genuinely needs it — a submodule pointer bump and its PR link, a
follow-up that was deliberately left out, a behavior change that isn't obvious from the
title. Omit the whole section when there is nothing.
```

Hard rules for the body:

- **Under 40 lines.** If it doesn't fit, the bullets are too granular — group harder.
- **Never a file-by-file list.** GitHub already shows the file list; repeating it is noise.
- **Never paste diff hunks or code blocks.**
- **No test plan, no checklist, no screenshots section** unless the change actually has one.
- Describe what changed, not what you did. "Scoreboard persists across restarts", not "I added
  a persistence layer".
- One bullet per *change*, not per commit. Squash "fix typo" and "fix typo again" out of
  existence.

Create it with a heredoc so the body survives shell quoting:

```
gh pr create --repo <owner/repo> --base <base> --head <head> --title "<title>" --body "$(cat <<'EOF'
<body>
EOF
)"
```

Do not add a Claude Code footer or co-author trailer to PR bodies here — this command's output
is meant to be short.

## Confirm before you push

Before the first push, show the user one compact plan and **wait for their go-ahead**:

| Repo | Head → Base | Commits | Title |
|---|---|---|---|
| `local-RED-dev` | `swappable-agent-system` → `main` *(no `Dev` — fell back)* | 5 | `agents: make the system swappable` |

Include every skipped target and its reason in the same table. Push and open PRs only after the
user says go. Pushing a branch is outward-facing and hard to take back.

## Report

Finish with one table — **one row per repo a PR was created for**, plus a row for every target
that was skipped or failed, so the table accounts for every target the user named:

| Project | Repo | Status | PR |
|---|---|---|---|
| `tic-tac-toe` | `Tic-Tac-Toe-Extreme` | ✅ created | https://github.com/EhrenDavis12/Tic-Tac-Toe-Extreme/pull/12 |
| `local-RED-dev` | `local-RED-dev` | ✅ created | https://github.com/EhrenDavis12/local-RED-dev/pull/8 |
| `some-project` | `some-other-repo` | ⏭️ skipped | no commits ahead of `Dev` |
| `another-project` | `another-repo` | ♻️ pre-existing | https://github.com/EhrenDavis12/another-repo/pull/3 |

Filling it in:

- **Project** — the argument the user typed that resolved to this repo. For the mono repo, and
  for a literal path, repeat the repo name.
- **Repo** — the directory name of the repo the PR was opened in. A project with several
  `srcRoots` gets one row per src root, all sharing the same Project cell value.
- **Status** — `✅ created`, `♻️ pre-existing` (step 2 found an open PR and you returned it),
  `⏭️ skipped`, or `❌ failed`.
- **PR** — the URL, bare so it stays clickable. Never a markdown link, never shortened. For a
  skipped or failed row, put the reason here instead.

Then stop. Don't offer to merge, don't poll CI, don't summarize the PR bodies back — the user is
about to read them on GitHub.
