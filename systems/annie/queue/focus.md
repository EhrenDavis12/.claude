# Focus

The user owns this file. The desk rewrites it the same turn the user changes direction, in
place, keeping their words. Every auto job the mastermind makes moves us toward the Goal, by
way of "Right now" unless that line is empty.

## Goal

- Be ready to build every asset a game needs, on demand. The game design is being worked
  separately; once it lands, we generate the art, animations and effects to develop
  everything in it.
- So we need a proven method for each type of asset, so we are prepared.
- A step further: generate assets the game can start using now.

## How every animation is made now (user, 2026-11-11) — overrides older method rules

The user, 2026-11-11: "simply controlling the start of the strike to the end of the strike for
the attack action looks like we can really control this whole animation process by simply
approving the final wind up pose and the final strike pose ... every single action needs a start
and an end. The start is the complete wind up pose. The end is the completed follow-through
everything else in the middle sea dance can do." (Proved on the Fighter attack with two
nano-banana keys and Seedance 1 Pro; it replaced one-picture-in, which never held the face.)

So, for every action of every character and enemy:
- **Two approved keys, start and end.** The start is the complete wind-up (the game snaps
  straight to it from the at-the-ready stance; no wind-up frames). The end is the completed
  follow-through. Seedance 1 Pro gets both as first and last frame plus a short prompt and
  makes the middle.
- **Hurt and guard** need one drawn key each (fully hurt, full guard); the at-the-ready key is
  their other end: ready -> hurt -> ready, ready -> guard -> ready.
- **Same size on every key.** Keys drawn by an image model come out at different scales, and
  the figure grows or shrinks across the clip. Every key is scaled and placed as a whole image
  by code to match the at-the-ready key (head and body height, boots on one ground line, one
  plate) before it is approved or rendered.
- **Keys are the user's to approve** on one numbered still sheet before any clip is paid for.
- **The grade:** a solid action, and the same weapon, clothes and face, no new details.
- **Which picture each animation starts from** (user, 2026-11-09): "Just to be clear, we have the two poses. The two poses aren't to be used for every single animation. I've identified already that the running animation needs the relaxed pose not the action pose, but the other animations tend to need the action pose so for example, hurt attack defend all of those should be referencing the action pose while the run. The start run in the end run should be referencing the relaxed pose you can almost say even the end run animation could be going off of the action pose as well. Well, have to determine what's best for that one but I'm thinking maybe pulling an image from the run animation as a reference that might be a better way to do it, but we can decide that when we get there or just identify different ideas there but not to use both of them otherwise we get what we got with the assassin where he was running with his daggers in front of them and not swinging his arms. It looks terrible so we don't need the action pose for the running animations just the relaxed pose for the running animations and then the rest of the animations will probably end up utilizing this action pose" So: idle, attack, hurt, defend (and other combat actions) start from the ACTION (at-the-ready) pose; run and run start start from the RELAXED pose; run stop is undecided (ideas: the action pose, or a frame taken from the run itself) - try options and show them. Never feed both poses to one animation.

## Away week (2026-11-02 to 2026-11-09)

The user, 2026-11-02: "I am not going to have internet for 1 week I want you to keep going character, design,
  enemy designs, go ahead and animate them all the way just keep going. You have one week of
  free running Room and then I will come back and evaluate what you do then but until then you
  are it is up to you to keep moving just build a list of things that I need to approve. I am
  not going to be here to approve it. I will not be able to do anything for the next week so it
  is on you make that very clear you have to keep going just pay attention to your token usage.
  That's your only limitation for the next week. Think of all the different types of characters
  that we want as far as enemies. I know we have a night that was going to be a tank. We have a
  fighter go ahead and do those guys we already picked the mage get him fully rendered think of
  other assets. The game might need and just start working on them. Don't now do not wait for
  me. Any other sound effects the game might need do not wait for me. Update the mastermind to
  have these same instructions so that way it's going to operate. It has no more limitations
  other than token usage keep going."

The user, 2026-11-02: "Good Remember you can't wait for me for the next week. I really will not be on the Internet. I will be on a cruise out in the middle of the ocean with zero Internet so I cannot help you. You have to know this and keep moving. I want you to make sure there's a job in the queue at all times working something even if it's arbitrary I want it working something."

So, until the user is back (about 2026-11-09):

- **The queue is never empty.** Something is always working. Keep at least five jobs queued
  ahead, long animation jobs among them, so work goes on even while the usage stop holds the
  mastermind (queued jobs still run then).

- **Plan by token usage** (user, 2026-11-02: "Yes usage will remain your limit. The $34 on replicate is also a limit so you have to plan your work accordingly plan long jobs that can run on the computer accordingly if you know, we can kick off a free job and that's gonna take two hours and you're running out of tokens that's a prime job to use to execute on B wise in your usage."). Tokens and the $34 are the two limits.
  A long free local render (a Wan clip, a batch of Qwen keys, a sound batch) costs hours of
  computer time but few tokens; planning, reviewing and research cost many tokens. So when
  usage nears the limit (over 70% of the 5-hour window, or the week ahead of pace), the next
  job is a long local render, moved up with `q.py up <id>`; the token-heavy jobs wait for the
  window to reset. While a render runs, a worker waits on it cheaply (`kill -0` on its PID,
  checks minutes apart, never a tight poll), and notes with `--minutes` cover the whole render.
- **An idle never blocks** (user, 2026-11-07: 'Can you show me the failed clips that you say don't work and it is OK that we just skip an idle? It's not happening right for later and continue on with the rest of the animations you don't have to stop because of that. The idol shouldn't be blocking anything.' So: a failed idle is skipped for later, never a blocker; the character's other animations (attack, hurt, defend and the rest) go on from its ready picture.) When an idle fails its budget, park it in review as skipped and queue the character's next animation.
- **Character animation clips are paid, not local** (user, 2026-11-07: "you mentioned Free to try for the idle animations, but we know the local animations don't work that we have to do paid so have you been trying local animation runs this whole time?"). The local
  video model does not make usable character animation, so no clip take for a character or
  enemy action is rendered locally any more: every take goes to the paid model (Seedance
  first) within the $4 an action and the week's $53. Local stays for keys, stills, sound and
  everything else. A take budget counts paid takes only.
- **Every idle and action keeps the character's weapon in hand** (user, 2026-11-07, on the
  failed idles: "Yeah, we can't use those idols. We're missing the weapons."). No axe moved to the back, no sword stuck in the ground, no empty
  hands; those workarounds are rejected.
- **No Unity until the user is back** (user, 2026-11-07, asked to sign in to Unity Hub: "Not back so I cannot do anything on the unit on the computer? I have no access. I'm still remote. I just got a little bit of in order to message you").
  Unity's licence ran out offline and only the user's sign-in renews it. Queue no Unity build,
  test or recording; the skeleton claw effect stays blocked. Use other long free renders
  (local Wan, Qwen keys, sound batches) for the low-token hours instead.
- **Never wait for the user.** Where a pick or an approval is needed, the reviewer's
  recommended candidate is taken as a *provisional pick* and the work goes on from it. The
  pick sheet still goes to `review` so it is on the user's list; the provisional pick is
  written in its note as `PROVISIONAL PICK: <n>, because <reviewer's reason>`. The Queue
  page's "ready for you" list is the list of things for the user to approve.
- **Animate all the way.** Characters: the Mage (Star Sage) fully, the Knight (the tank) and
  the Fighter, each from first designs through their animations, the same set and method as
  the Archer and Assassin. Enemies: goblin, spider and every other enemy type the game would
  face (hobgoblin, skeleton, dragon boss filling 15 spots, and more invented), each from five
  designs through idle, attack, hurt, defend.
- **Other assets the game might need**, and **other sound effects** it might need: start them.
  Make everything the game will need, not the game itself: icons and items, every menu screen
  and page (title, settings, about and credits, character select, shop), backgrounds, props,
  and Unity particle effects for every character's attacks, spells, hits and blocks. Unity
  effect builds and tests are long free jobs, good for when tokens run low.
- **Replicate budget, this week only: $53, a hard limit.** The user, 2026-11-02: "You
  currently have 34 credits in replicate use those very wisely over the next week you are in
  charge of the budget. ... It's your call what to use it on", then: "Also, I went ahead and updated the replicate limit to $53 so you have $53 so I'm getting serious about these animations and I want you to make them good but also keep in mind you have a limit. This is now a hard limit $53 is a hard limit."
  The user, 2026-11-02: "we know music and we know animations need replicate to actually look
  good and be useful but other things can possibly run locally. We don't really need that
  high-powered things for icons ... tests that utilize unity is a good long running free job."
  The desk's plan: the hard stop is **$51 spent this week**, $2 under the $53 for rounding. The
  spend ledger `src/asset-animation-demo/local_runs/replicate_spend.csv` stood at **$4.52**
  before this week, so **stop when its total reaches $55.52**. Read the total before every paid
  call; a call that would pass $55.52 is not made, and the job goes on locally. Only ledgered
  tools (`render_remote.py`, `gen.py`); a call on a path that writes no ledger line is
  hand-logged into the ledger at once, the same minute. `edit_remote.py` may be used for a pose or key the free tool cannot draw (user, 2026-11-07: "Yes it's ok to just use the paid as you see fit. You were given your budget to plan for"), at about $0.04 a try, $0.25 a pose unless the brief says more; it writes no ledger line, so each call is hand-logged into the ledger the same minute. Paid is the desk's and the mastermind's call within the plan, without asking.
  Paid goes to animation clips, music and poses the free tool cannot draw; icons, items, UI screens and pages, props,
  backgrounds, sound effects and Unity work run locally.
  Spend it on: (1) about $38 on animation clips: the user is "getting serious about these
  animations" and wants them good, so use the better model where it shows (Seedance or Wan at
  720p over 480p), with a cap of **$4 per action** in the item's note, through the paid slot
  (`q.py paid <id> on`), so animations render beside the local worker. (2) about $7 on music
  (Celtic battle, title and town tracks). (3) about $6 held back to rescue a job local has
  failed at its budget, $2 cap each. Never on research, sound effects, icons, still sheets or
  anything local does well. When the ledger reaches $49.52, only rescues remain.
- Still binding: local and free except the Replicate budget above; no body pose built by code; an approved
  artifact is never touched; one worker at a time. The only other limit is token usage: the
  usage gate stays on.

### The roster (user, 2026-11-02)

"OK for the main characters I'll go through what we have or what we need. We need the archer which we have the assassin which we have we have the tank we have that one I love to take I never I always hated his weapon so redraw the tank so we can get a new weapon. We also want a brute. The tank and a fighter will also need a Porter something that somebody who's carrying a bunch of stuff will need a scout will need a blacksmith and will need an alchemist. The Porter blacksmith and alchemist and scout are kind of like back line people who need to be in the party, but don't do really much fighting. They're more utility but they're still part of the party. I need all the animations as the others do for the main characters, but as for the main characters we go, the archer the assassin, the tank, the brute, the fighter, and the mage. I'll even throw one extra one in there if you have the time the cleric just to throw one in, but that one's an extra. The other ones are the important ones so you can also work on that as well as all the enemies, the monsters, the dragon skeleton, the spider the goblin, and I'm making them look using the Chibi style, but also like monsters not like humanized monsters but monsters OK I think that's all I can give you please please please keep Work going have those checks to keep the work processing. It's important. I will not be able to see anything I will not be able to respond. I will not be able to approve. You're on your own. Do not wait for approvals. I'll ask later for them when I get back so just feel free to stack up all those approvals necessary, but don't let that stop you working come up with a base image. Don't wait for approval. Start the animations if you think it looks good that means it looks good."

So:
- **Main characters, in order:** Archer (have), Assassin (have), Tank (approved look, but
  redraw him with a new weapon: the user always hated his mace), Brute (look approved on job
  #12), Fighter, Mage (Star Sage). Each gets the full set of animations the Archer has.
- **Back line, also important:** Porter (carries a load of gear), Scout, Blacksmith,
  Alchemist. Utility party members who barely fight, but still need every animation the
  others have.
- **Extra, only with time left:** the Cleric.
- **Enemies:** goblin, spider, skeleton, dragon (boss, fills all 15 spots), and more. Chibi
  style, but **monsters, not humanized monsters**.
- **Never wait for approval.** Make a base image; if it looks good to the reviewer, it is
  good: start its animations. Every such call stacks on the user's approval list.

- Monsters named (user, 2026-11-09): "I would not call number 2 a hob goblin it looks like something else but its good and we can keep it. just need to name it Gorehorn. Keep each of these monsters and the name of each one they sound good." So: Gorehorn (animating), Ironjaw, Ironback, Warboss and Tusker are each their own monster, kept by name, from characters/hobgoblin/review/pick_sheet.png.
- Skeletons named (user, 2026-11-09): "Keep all of them but #4. do the same as the last keep the names as well." So: Gravehorn, Hound Skull (animating), Barrow Brute and Hollow Stalker kept by name; Crypt Captain dropped. From characters/skeleton/review/pick_sheet.png.
- Spiders named, and the order (user, 2026-11-09): "Number seven needs to be redrawn a number 10 attack at the ready pose needs to be redrawn And do what we did with the other two just continue with the name that you have for each one of them they're good now for now for each one of these both the hot goblin both the skeleton and the spiders just continue with the one you've already selected just finish those out you don't need to go into the other one unless you really looking for more work just those three are good to go. Don't need to go down the road of all these other ones unless you have the time and we've designated the first one as good so let's get the first one drawn done well all completion all the way to completion and then we'll move onto those other ones but keep those other ones in your back pocket." So: all 10 spiders kept by name (Cave Stalker, Brood Bloat, Bone Widow, Jumper, Crystal Back, Tarantula Brute, Venom Fang, Plated Trapdoor, Skull Back, Many-Eyed); Venom Fang needs a full redraw, Many-Eyed its ready pose redrawn.
- **Finish the picked monsters first: Gorehorn, Hound Skull, Cave Stalker, and the goblin Cutthroat (approved 2026-11-09, 'Keep him')** — every animation, all the way to completion, before any other named monster gets work. The other named monsters (and the Venom Fang / Many-Eyed redraws) are back-pocket jobs, only when nothing else is left.

## Right now

- **Animation work is on hold** (user, 2026-11-11): "ok im going to take of the animation for a bit running some stuff through replicate myself. Put animation work on hold and move on." No character, enemy or prop animation jobs, no clip renders, no key work for animations, and no animation research or tests from the mastermind until the user lifts the hold. Other work goes on: design stills, palette and UI, effects, sounds, backgrounds, research outside animation. The Fighter-first line below holds again once the hold is lifted. **Exception, the user's own ask (2026-11-11):** the Fighter's start + end key method job (attack from the user's two nano-banana poses, then hurt and guard keys) runs now — "every single action needs a start and an end. The start is the complete wind up pose. The end is the completed follow-through everything else in the middle sea dance can do."

- **One character first: the Fighter** (user, 2026-11-09): "before starting out all these animations and sending them through the paid models, let's target one specific character and make sure that this method works ... let's go back to our basics. Let's review one character pick one character and get them right". Only the Fighter gets animation jobs (attack, idle, hurt, defend by the one-picture method) until the user approves the method on him. Every other animation is parked; never make or start one. Still pictures, designs and sounds may run.
  Waiting for the Fighter method, to queue once it is approved (taken off the queue 2026-11-10, user: "I see some tickets in needs your eyes that should not be there given our desisions to this point. clean that out"):
  Alchemist hurt from approved design 3 (user, 2026-11-09: 'Let's go with number 3');
  Blacksmith attack, defend and hurt from approved design 2 keys in characters/blacksmith/basekey_v1/keys (user, 2026-11-09: 'Yes, black Smith looking good move on');
  Knight idle with the warhammer, from the at-the-ready key once the hammer grip fix is approved, matching the liked idle v3's whole-body breath (user, 2026-11-09: 'the tank idle looks pretty good. Can we approve that?' then 'We will need consistency go with the Warhammer').
  All by the one-picture method. The away-week animation tests were dropped from the queue (made by the old key method or from picks since changed); their files stay on disk and their lessons are in the recipes.
- **Every idle is battle-ready** (user, 2026-11-09, on the skeleton idle): "The idol should be at the [ready] position ... the idols need to be longer a little bit more diverse, but the breathing looks wonderful ... it needs to be in at the ready at the battle ready position holding their weapon appropriately. This image is at a relaxed position with the weapon somehow glued to his hand in an awkward position looks like Code versus the animation itself." So: every idle, hero or monster, starts from the at-the-ready pose; the weapon is held as the model draws it, never glued on by code at an odd angle; idles are longer and a bit varied; keep the breathing.
- **Songs and sounds play at random from their bucket** (user, 2026-11-09): "keep all the songs in their buckets approved them in the buckets that we have them for and then randomly play them when we call for a song in that bucket" and "keep all the sounds that we have put them into the buckets that should be appropriate for those sounds before we go and run off and make more sounds." Every song and sound set made so far is approved. The only new sound work is filling buckets that have no set yet, as one low-priority job (user, 2026-11-09: "only the ones were missing ... Make that a job that could be executed whenever low priority"); never remake a bucket that has a set.
- **No more music** (user, 2026-11-09): "we can stop generating music because we should have enough at this point ... we don't need music for every single page. We should generally just need menu music and then battle music". Never make a music job; one song plays across all menu pages, not a new one per page. Buckets: menu = sandbox/70 (3) + sandbox/114 (6); battle = sandbox/61 (3) + sandbox/80 (3) + sandbox/132 boss (3); victory 2 and defeat 3 = sandbox/79.
- **No new icons** (user, 2026-11-09): "let's stop creating new icons until we have more game designs available". Don't make icon jobs until the user says there are more game designs.
- Queue order (user, 2026-10-30): "Put long animation jobs at the end of the queue and the
  quick jobs to knock out at the top." Quick jobs (mockups, stills, Unity tests, research)
  go on top; long animation jobs (character video runs) go at the end.
- Mastermind jobs: "Research and effective methods. should be the focus" — research that
  finds the most effective way to make each asset type, before trying it.
- Prove we can make every type of asset a game needs, and keep what each proof makes so it
  can go into the game when we start.
- Icons and items (user, 2026-10-30): painted icons (code shape + local Qwen paint) beat
  code-only ("The code icons are bad and the painted icons do look better"). No more icon
  tests (Blender template, rarity tiers) until the user picks a style from the 10-style sheet.
- No phone-size or mobile examples for now (user, 2026-10-30: "I don't need the mobile
  examples right now so don't worry about those").
- Proven: character animation (the Archer).
- In progress: scene backgrounds (the cave).
- Still to prove: effects, UI, icons, props and items, tiles, sound effects, music.

## When the work runs out

The user, 2026-10-30: "Perp the mister mind today for some good amount of work. tonight if we
run out of work Do attempt the finish the assasin animations. If thats done thing of other
assests we might need. if thats all done then take a look at starting the mage character if
we really run out of any work."

1. Day: research and tests, as above.
2. Night, nothing left to make: finish the Assassin's animations.
3. Then: other assets the game might need.
4. Then: enemies (below) and new characters. The user, 2026-11-01: "Enemy and new characters
   can always be added to the queue if we don't have any work going on". The Mage is the first
   new character. The user picked the Star Sage (purple, design 2) on 2026-11-02: "Star sage
   is the one we want creat 5 active poses for him then keep your self busy with these
   animations". So: five active poses to pick from, his idle meanwhile, and once an active
   pose is picked, queue his attack and hurt the same way the Archer and Assassin were made.
   The user, 2026-11-01: "putting in long jobs like animation for enemies and characters don't
   take many tokens so let those jobs run when we begin to hit our token limit." Queue them
   ahead, since queued jobs keep running at the usage stop.

### Enemies

The user, 2026-10-31: "We might need to start thinking about more characters such as
enemies. Such as goblin's hobgoblins and other sorts, maybe one epic dragon as a boss to test
out different types of placements ... They don't need the full animation sets like running
stopping or anything like that as they just come onto screen with the floorin. but they will
need an idol animation. They will need an attack, a hurt a defend and a death. ... we'll take
each step will take 2 image of each relaxed image and an engaged image of the same character
get those approved first, and then we will knock out some of the animations for them ... you
can always come up with more enemies that we would be facing doesn't have to be limited to
these three. note the dragon one is meant to take up all 15 spots, so it will be a larger
character than the typical one spot person so keep that in mind when generating the large
dragon."

- Start with goblins, hobgoblins and one boss dragon; more enemies may be invented.
- Per enemy: first images of the same character, picked by the user. The user,
  2026-11-01: "For new enemies start off with a relaxed pose and an at the ready pose. This
  should help our animations. Any other poses that can help our animations as reference will
  be welcomed." The user, 2026-11-01: "We don't do an attack wind up . We jump right to the
  strike. We don't need run, start run or stop run, or death animations." The user, 2026-11-01: "I'm
  only asking for the first images of goblin and can you give me 5 to choose from. Then will
  start animating them using the same method used for the archer and assassin. That means we
  don't need In betweens". So five designs, each relaxed and at the ready, no other poses.
  Goblin first, then the spider, then others; a new enemy only after the user has picked the
  one before. The user, 2026-11-02, asked for 10 spider designs now beside a second goblin
  round of uglier goblins built from goblin 1. Only then its animations: idle, attack, hurt, defend. No run or stop, and no
  death animation (user, 2026-10-31: "they can stay in the hurt pose then use particals as
  its they are disintegrating"): one shared disintegrate effect, the hurt pose fading out in
  particles, works for every enemy.
- The dragon fills all 15 spots of a side: one character the size of the whole formation.

## Learn

- What real studios do for game animation
- What makes a good attack
- What makes good animation styling
- Layering and parallax
- Texture mapping
- Gridding
- Billboards with textures
- Pathfinding
