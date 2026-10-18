---
name: animation-skills
description: The front door to every animation skill in this repo — making a character's idle, its one-shot actions, a recolour of an armor, a new armor or outfit animated on its own, and sprite-sheet generation through Replicate. Use for any request to create, re-create, fix or review a character animation, an armor or outfit variant, or a weapon overlay; it names the one sub-skill to read for the job.
---

# Animation skills

Every animation skill lives in a folder beside this file. The harness only lists skills that sit
directly under `.claude/skills/`, so this file is the one entry it sees; **pick the row, then Read that
folder's `SKILL.md` and follow it** — do not work from this table.

| The job | Read |
|---|---|
| A character's breathing idle, or an extra motion layered on it (head turn, regrip, weight shift) | `idle-breathing-loop/SKILL.md` |
| A new action on the base armor — hit, defend, attack, run start / loop / stop, death — from key poses, with the weapons pinned to the hand | `base-action/SKILL.md` |
| Sprite-sheet animations through Replicate and the Asset-Gen-Framework (idle, attack, defend, hurt, projectile, burst) | `animate-characters/SKILL.md` |
| A new colour of an armor the character already wears — same shape (Fire Robes) | `recolour-armor/SKILL.md` |
| A new armor or outfit with its own animations, made the base's way from its own base image (Nightmare Cloak) | `new-armor/SKILL.md` |

Two rules hold for all of them:

- **The Character Chart is kept current during the run** — the commands are in
  `idle-breathing-loop/SKILL.md`, "Keep the Character Chart current".
- **A run ends by scoring itself and improving its skill**: append the row the sub-skill's "Scorecard"
  section names, then run the `skill-improver` skill on it. That is how these recipes get better
  instead of being re-learned.

A process that is not in the table yet — it was worked out in a session and lives in a work log — is a
skill waiting to be written. `skill-improver` writes it into this folder and adds its row here.
