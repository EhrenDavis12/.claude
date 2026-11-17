---
description: Open a pull request from the current branch for one or more repos in this mono repo — a project (all its srcRoots), a submodule by name, or the mono repo itself. kolbe-notebook-schemas, kolbe-utils-nodejs, postman-collections, claude-repo and the mono repo merge into main; every other repo merges into dev
argument-hint: "[project, submodule, or path names] [to <branch>] — omit for the mono repo"
allowed-tools: Bash, Read, Glob, Grep
---

# Create pull requests

Open one PR per resolved repo, from whatever branch that repo is currently on into its base
branch, and hand the user the URLs. **The user clicks merge. This command never merges, never
force-pushes, never commits, and never rewrites history.**

**Push and open the PRs in the same turn. Never stop to confirm.** Invoking this command *is*
the go-ahead — a plan offered back for approval costs a round trip and buys nothing the user
did not already decide by typing the command. The judgment calls below are yours to make: make
them, say what you chose in one line as you go, and keep moving. The only stops are the
per-target skips in steps 1–3, and each skips **that target** while every other one still runs.

The arguments, if any, are: `$ARGUMENTS`

This command learns what a project is from `Docs/*/project.json` and what a submodule is from
`.gitmodules`. The one thing it names by hand is the short list of repos that merge into `main`
(step 1) — that is the user's ruling, not something the repo can tell you.

**A repo the user names is a repo a PR is built from — that repo, and only that repo.** Never
add the mono repo, a sibling submodule, or the active project's other `srcRoots` to the list.

## What an argument names

Strip an optional trailing `to <branch>` first — that is an explicit base branch and applies to
every target. Each remaining argument is a **repo**, resolved in this order:

1. **The mono repo itself** — `root`, `repo`, `.`, or the repo's own directory name.
2. **A project** — match against every `Docs/*/project.json` on `.name` first, then on
   `.aliases` (case-insensitive). A project resolves to **every path in its `srcRoots`** — one
   PR per src root. Say which project an alias resolved to.
3. **A submodule** — a `path` in `.gitmodules` whose last path segment equals the argument
   (so `micro-search` means `src/micro-search`). Read `.gitmodules`; never a hardcoded list.
4. **A literal path** to a directory that is a git repo — accepted as-is.

**With no repo arguments, the target is the mono repo alone.** Don't guess that the user also
meant the active project — an unasked-for PR is worse than a missing one.

If an argument matches nothing exactly, try once for a typo: a case-insensitive near-miss
against the same candidates, one edit away (`micro-benchmrk` → `src/micro-benchmark`). **If
exactly one candidate matches, use it** and say which — don't ask. Stop for that argument only
when two or more match or none does, rather than falling back to the mono repo. Name what you
tried: the project names and aliases you found, and the submodule paths you checked.

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
There is no bare `git` here. For `gh`, which infers the repo from cwd, run
`cd <repoPath> && gh …` in a single command so the working directory stays at the repo root.

## Per repo, in order

### 1. Resolve the base branch

Every repo has one designated base branch. It is fixed by the user, never inferred from which
branches happen to exist:

| Repo (directory name) | Base branch |
|---|---|
| `kolbe-notebook-schemas` | `main` |
| `kolbe-utils-nodejs` | `main` |
| `postman-collections` | `main` |
| `claude-repo` | `main` |
| the mono repo (`local_dev_kolbe`) | `main` |
| **every other repo** | `dev` |

- **The `main` repos never target `dev`.** A `dev` branch on one of them is a mistake — ignore it
  even when it exists. Picking `dev` "because it exists" is exactly the bug this table fixes.
- **Every other repo targets `dev`, and only `dev`.** Read the remote's heads
  (`git -C <repo> ls-remote --heads origin`) and match `dev` case-insensitively, then use the
  **real** name from the remote (`Dev` and `dev` are different refs to git). If no `dev` exists,
  **stop that target** with "no `dev` branch on origin" — never fall back to `main` or the
  default branch.
- **An explicit `to <branch>`** from the arguments overrides the table for that one run. If that
  branch does not exist on the remote, **stop that target** and say so. If it goes against the
  table (e.g. `to dev` for a `main` repo), still honor it, and say so in that repo's row.

For a `main` repo, confirm `main` exists on the remote too; if it doesn't, stop that target —
never retarget. Say the resolved base in one line as you go.

### 2. Check the head branch is sane

Stop this target, with the reason, if:

- **Detached HEAD** — `git -C <repo> symbolic-ref -q HEAD` fails. Common in submodules. There is
  no branch to open a PR from; the user needs to check one out.
- **Head equals base** — you can't PR a branch into itself.
- **No commits ahead** — `git -C <repo> rev-list --count origin/<base>..HEAD` is `0`. Report
  "nothing to PR" and move on. This is a normal outcome, not an error.
- **An open PR already exists** for this head (`cd <repo> && gh pr view --json
  url,baseRefName,state`). Push any new commits, return that URL instead of opening a second
  one, and label it as pre-existing. If its base is not the one step 1 resolved, say so in the
  row (`⚠️ targets dev, should be main`) — never retarget or close it yourself.

### 3. Handle uncommitted work — report it, never commit it

`git -C <repo> status --porcelain`. If it is not empty, **open the PR from HEAD anyway** and
name the uncommitted paths in that repo's report row. Do not commit, do not stash, do not ask.
Nothing is lost: the working tree is untouched, and a follow-up commit pushed to the same
branch lands in the open PR — which is cheaper than a blocked command.

Two things are hard stops — report and skip that target:

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

Read the actual diff — the PR body must describe what the code does, not paraphrase commit
subjects. If the full diff is large, read the `--stat` and the commit messages first and pull
only the substantive files into context. You are writing a summary, not a review.

### 5. Push the branch

`git -C <repo> push -u origin HEAD`. Plain push only. If it is rejected as non-fast-forward,
**stop and report** — the fix is the user's call, and it is never `--force`.

### 6. Write the PR

**The title and body become the merge commit message.** When the user merges, GitHub uses them
as the commit on the base branch, so write them to be read in `git log` a year from now by
someone who never saw this PR. Short, but complete: a reviewer gets the shape of the change in
under thirty seconds, and the log tells the story without opening the diff.

Title: `<area>: <what changed>`, under 72 characters, no trailing period. Name the outcome
("usage: limit-window resolver and banded model pricing"), never a vague verb ("updates",
"misc fixes", "longCon work"). Never the branch name.

Body, exactly this shape:

```markdown
## What changed
- One bullet per meaningful change, grouped by area. Lead with a verb (Add, Update, Fix,
  Remove, Refactor). Max 8 bullets.

## Why
One to three sentences. The intent — what problem this solves or what feature it enables —
not a restatement of the bullets. "Keeps X in step" alone is not a reason; say what needed it.

## Notes
Only when a reviewer genuinely needs it: migrations, new env vars / SSM params, seed reruns,
a submodule pointer bump and its PR link, a follow-up deliberately left out, a behavior change
that isn't obvious from the title. Omit the whole section when there is nothing.
```

Hard rules for the body:

- **Under 40 lines.** If it doesn't fit, the bullets are too granular — group harder.
- **Never a file-by-file list.** GitHub already shows the file list; repeating it is noise.
- **Never paste diff hunks or code blocks.**
- **No test plan, no checklist, no screenshots section** unless the change actually has one.
- Describe what changed, not what you did. "Rate limits apply per API key", not "I added a
  rate limiter".
- One bullet per *change*, not per commit. Squash "fix typo" and "fix typo again" out of
  existence.
- **Always call out anything a reviewer must do by hand** — that is what Notes is for.
- **Always call out a breaking change** — a removed export, a new required argument, a changed
  wire contract — in Notes, because the merge commit is where a consumer will look for it.
- **Release bumps are not changes.** `chore(release): x.y.z` commits fold into one Notes line
  ("Version bump to x.y.z; npm publish is a separate step"), never a bullet.

Create it with a heredoc so the body survives shell quoting:

```
cd <repo> && gh pr create --base <base> --head <head> --title "<title>" --body "$(cat <<'PRBODY'
<body>
PRBODY
)"
```

Do not add a Claude Code footer or co-author trailer to PR bodies here.

## Report

**The report is one table and nothing else.** No prose before it, no summary after it, no
recap of the PR bodies, no next steps. Everything the user needs is the four columns below —
anything more buries the URL, which is the one thing this command exists to hand back.

**Every repo the user named gets exactly one row, every time.** A repo with a PR — new or
pre-existing — always has its full URL in the row; a run that opened or found a PR and did not
hand back its URL has failed at the one thing it is for. A skipped or failed repo gets its
reason instead:

| Repo | PR URL | Status | Target branch |
|---|---|---|---|
| `micro-search` | https://github.com/<owner>/<repo>/pull/12 | ✅ created | `dev` |
| `web-notebook` | https://github.com/<owner>/<repo>/pull/3 | ♻️ pre-existing | `dev` |
| `micro-notebook` | — no commits ahead of `dev` | ⏭️ skipped | `dev` |
| `kolbe-utils-nodejs` | https://github.com/<owner>/<repo>/pull/35 | ✅ created | `main` |
| `<mono repo>` | — <the gh error, verbatim> | ❌ failed | `main` |

Filling it in:

- **Repo** — the directory name of the repo. A project with several `srcRoots` gets one row
  per src root.
- **PR URL** — bare, never a markdown link, never shortened, so it stays clickable. For a
  skipped or failed row, put the reason here instead, prefixed `—`.
- **Status** — `✅ created`, `♻️ pre-existing`, `⏭️ skipped`, or `❌ failed`.
- **Target branch** — the base branch the PR targets (or would have targeted), the real
  remote name as resolved in step 1.

## Error handling

- `gh` not authenticated → tell the user to run `gh auth login` themselves (`! gh auth login`,
  since it's interactive).
- Always surface the full `gh` error message.

Then stop. Don't offer to merge, don't poll CI, don't summarize the PR bodies back — the user is
about to read them on GitHub.
