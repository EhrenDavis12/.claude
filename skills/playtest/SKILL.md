---
name: playtest
description: Play the active project's app on the iOS Simulator — look at the real screen, tap around, and watch animations frame by frame. Use after building anything whose correctness is a matter of appearance, timing, or feel rather than assertion: layout, spacing, animation, theming, or any change where the honest check is "does it actually work when you use it?"
---

# Play-testing on the simulator

Tests assert what can be written down. Everything else — whether a tap lands where the finger
expects, whether an animation eases or snaps, whether the board is still readable after a theme
change — is checked by using the app. This skill is how you do that yourself rather than
asking the user to do it for you and report back.

`.claude/tools/sim.sh` is the whole mechanism. It is stack-agnostic and knows nothing about any
project; it sees the screen and touches it.

## Setup, once per session

```
.claude/tools/sim.sh prep
```

This puts the Simulator into the one configuration where a tap can be aimed accurately — device
bezels off, so the window content is exactly the screen, and Point Accurate zoom, so one device
point is one macOS point. It then derives the device's pixel ratio and title-bar height rather
than assuming them, and caches both.

**Run it again if the Simulator window is resized or its zoom changed**, and after booting a
different device. Everything else re-reads the window position on every call, so simply *moving*
the window mid-session is already handled.

Boot a device and start the app first — the script does not launch anything:

```
xcrun simctl list devices booted          # or boot one, then: open -a Simulator
cd <srcRoot> && flutter run -d <udid>     # run this in the background; it stays alive
```

## The loop

Every coordinate — in and out — is a **screenshot pixel**, the same coordinate read straight off
the PNG. Nothing upstream converts anything.

```
.claude/tools/sim.sh shot board.png     # capture
.claude/tools/sim.sh view board.png     # shrink for looking at + print the coordinate multiplier
.claude/tools/sim.sh tap 604 1154       # touch it
```

Use `view` rather than resizing by hand. Reading a coordinate off a shrunken image and forgetting
to scale it back up produces a tap that lands on the wrong control and looks exactly like a bug in
the app — `view` prints the multiplier alongside the image so the sum is never done from memory.

Also available: `swipe x1 y1 x2 y2`, `type <text>`, `key <name>`, `home`, and `geom`.

**Re-screenshot between taps whenever the layout can move.** A banner that grows from one line to
two pushes everything below it down, so the second tap of a two-tap gesture aimed at the first
tap's coordinates lands on a different control. This is not hypothetical — it is how the first
play-test of Tic-Tac-Toe-Extreme failed, and noticing it *was* the finding: a confirm step whose
target moves between the two taps is a mis-tap waiting to happen for a real player too.

Tapping brings the Simulator to the front, which takes keyboard focus from whatever the user was
doing. Worth knowing before firing off a long sequence while they are typing.

## Watching an animation

A still cannot show easing, duration, or a dropped frame. Record the motion and lay it out as a
contact sheet, which is something that can actually be looked at:

```
.claude/tools/sim.sh rec-start
.claude/tools/sim.sh tap 480 1030
.claude/tools/sim.sh tap 480 1099
VIDEO=$(.claude/tools/sim.sh rec-stop)
.claude/tools/sim.sh frames "$VIDEO" 9 sheet.png
```

Nine frames across the clip is usually enough to see whether a transition eases or jumps. Ask for
more when timing the tail of a spring, fewer when confirming that something merely happened.

## Driving a long sequence

A scripted run of many taps fails differently from a single tap: one swallowed tap desyncs
everything after it, and the screenshots at the end look like an app bug rather than a driving
bug. Two rules make a sequence trustworthy.

**Calibrate coordinates from the rendered UI, never from a guess or a glow.** Measure the
element's real rectangle out of a screenshot — the fill, not the halo. A themed board with an
outer glow reads ~30px taller than it is, and a model built from that lands taps near cell
boundaries, where they fall through gaps to whatever catches stray taps underneath. That failure
is invisible per-tap and only shows up as a sequence that quietly goes wrong. Measure the pitch
between repeated elements too, rather than dividing the whole by the count — padding between
groups makes those different numbers.

**Verify against the state that must change, not against "something changed."** Check the
signal the action is defined by: a turn passing, a counter moving, a screen replacing another.
A move that previews and then cancels changes the board, so a board-level check waves it
through; the turn indicator does not move, so a turn-level check catches it. Retry a few times
before failing, and fail loudly with the coordinate — a sequence that reports success while
drifting is worse than one that stops.

## What to actually look for

Play-testing earns its cost on the things a test would never catch, so look for those rather than
re-checking what the suite already covers:

- Does the thing you just changed look right *next to everything else*, not just in isolation?
- Does a control move between the moment it is aimed at and the moment it is hit?
- Does an animation land, or does it snap, stutter, or fight another animation?
- Is text still legible, and are targets still big enough to hit, under the current theme?
- Does the app still make sense after several moves, not just on the first screen?

Report what you saw plainly, including when it looked wrong. A screenshot that shows a defect is
worth more than a paragraph asserting things are fine.

## Requirements

`cliclick` (`brew install cliclick`), Xcode command line tools, `ffmpeg` for contact sheets, and
Accessibility permission for the terminal running Claude Code (System Settings → Privacy &
Security → Accessibility). The script fails with a plain message naming the missing piece rather
than tapping into empty space.
