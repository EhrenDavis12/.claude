#!/bin/zsh
# v5: pure breathing loop. Start and end are both the approved K0, so the loop closes by construction.
cd "$(dirname "$0")"
P="2D cartoon game animation of this chibi forest archer standing perfectly still, only breathing: one slow, deep breath in and out, his chest and shoulders rising and falling gently, the cloak swaying a little with it. The head and face do not move at all: eyes open and still, no blinking, mouth closed, silent. Both feet stay planted; the bow stays in his hand; the quiver stays on his back. Exactly the same flat cel shading, shadows and colours throughout. Static camera, flat grey background."
python3 /Users/ehrendavis/work/local-RED-dev/.claude/skills/AnimationSkills/idle-breathing-loop/scripts/gen.py keyframes "$P" --start ../glance_v3/work/K0_plate.png --end ../glance_v3/work/K0_plate.png --frames 49 --width 640 --height 640 --fps 16 --seed 7 -o breathe.mp4
echo BREATHE_DONE
