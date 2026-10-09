# Rules and explicit assumptions

Sources: the attached Space Goats V4 coding spec and deck CSV. The original
deck contains 104 physical cards: 40 Goats, 32 Actions, 16 Blocks, 16 Specials.
There are 68 goat points in the deck. This implementation does not use rules
from any other card game.

## Setup

The missing setup rule is filled in with five starting hand cards per player.
Shuffle the full deck once. Deal one card per player clockwise, starting with
the starting player, for five rounds. A setup Nanny auto-deploys and its draw
chain supplies the hand card for that deal slot. This can give a player one or
more goats before their first turn. No other starting goats are supplied.
The starting player rotates between simulations.

## Normal turn

1. Draw one card for each attached Hydroponic Alfalfa.
2. Draw one normal card, resolving any Nanny chain.
3. Play one legal card, or take one extra draw instead.
4. Discard to five hand cards, or three with Chewed Wiring.

If any draw exhausts the deck, the remaining normal phases stop immediately.
The current turn changes to Final Orbit and is counted once. No discard
occurs at this transition. If the final card is a Nanny, that card's automatic
placement (or quarantined hand placement) completes as part of the draw, then
the transition begins; there is no attempt to draw its nonexistent bonus.

## Cards

| Card | Copies | Implemented rule |
| --- | ---: | --- |
| Astro-Billy | 15 | Play to your ship; worth 1 goat |
| Twin Kids | 12 | Play to your ship; worth 2 goats |
| The G.O.A.T. | 8 | Play to your ship; worth 3 goats |
| Hyper-Jumping Nanny | 5 | Draw-triggered automatic placement worth 1; draw another card, recursively |
| Airlock Malfunction | 8 | Opponent ejects one goat card to orbit |
| Laser Blast | 6 | Opponent destroys one goat card to discard |
| Tractor Beam | 8 | Choose and steal one opponent goat card |
| Orbital Vacuum | 4 | Move all orbit goat cards to your ship |
| Space Wrench | 6 | Remove one attached Special from any ship |
| Goat-Yoga Focus | 5 | Reaction that blocks Tractor Beam only |
| Cardboard Forcefield | 6 | Reaction that blocks Airlock Malfunction or Laser Blast only |
| Tin-Foil Space Helmet | 5 | Reaction that blocks an attached Special play or Space Wrench |
| Hydroponic Alfalfa | 4 | Attached upgrade; extra draw at start of normal turn |
| Chewed Wiring | 4 | Attached downgrade; hand limit 3 while attached |
| Space Sickness | 4 | Attached downgrade; cannot use Actions against other players |
| Quarantine Zone | 4 | Attached downgrade; cannot add goats to your ship |

For Airlock/Laser, the CSV says the **target opponent** ejects/destroys a goat.
The default assumption lets that victim choose and retain their most valuable
cards. `removal_choice: "attacker"` changes this to the attacker choosing the
highest-value card. A Tractor Beam actor chooses any legal goat to steal.
An empty orbital area or target without a required card makes an Action
illegal; the AI cannot spend it on a nonexistent target.

## Ambiguities resolved

**Quarantine:** the coding spec mentions hand-play restrictions; the CSV says
the player cannot add any more Goat cards. The default uses the broader CSV
meaning: no hand deployment, stealing, scooping, or automatic Nanny entry.
A drawn quarantined Nanny stays in hand and still grants its replacement
draw. It can be played later as a normal one-goat card after Quarantine is
removed, without another draw trigger. `quarantine_scope: "hand_play_only"`
lets steal/scoop/automatic Nannies bypass Quarantine, matching the narrower
coding-spec check. An opponent may still remove a quarantined ship's goats.

**Chewed Wiring:** "permanently" is interpreted as while the Special remains
attached. Otherwise Space Wrench's removal would not restore the limit. Hand
size is enforced at the next normal End Phase, not immediately on attachment.

**Duplicates:** one copy of a given Special per ship by default; different
Specials can coexist. Enabling duplicates makes each Alfalfa add a draw.
Multiple copies of a downgrade continue to apply the same restriction until
all copies of that type are removed. Wrench removes one physical copy.

**Space Sickness:** prevents Tractor Beam, Airlock, Laser, and Wrench targeting
another ship. Wrench on your own ship, Orbital Vacuum, Goat plays, Specials,
and Block reactions remain legal. Specials are not Action cards.

**Special targets:** Specials may legally be attached to any ship, including
your own. The AI chooses self-upgrades and opponent-downgrades.

**Blocks and stack:** play the Action/Special onto a pending stack. Every
other player, clockwise from the actor, gets a reaction window until the
first valid Block is used. Push the Block, resolve it first, and discard it
and the pending card; the pending effect does not happen. Players may defend
another player or prevent a leader's improvement. The AI mostly protects
itself and may stop an opponent leader's upgrade/removal of a downgrade.
The actor cannot block its own card. Blocks are not Actions/Specials and
cannot be counter-blocked; multiple Blocks are unnecessary once canceled.
Off-turn reactions do not consume a turn or its action allowance.

**Nannies:** draw triggers apply to normal draws, Alfalfa, extra draws, setup
draws, and recursive Nanny draws. They are automatic rather than blockable
Action/Special plays. Disable setup triggers with the provided rule setting.

## Final Orbit and winner

The player who drew the final deck card acts first. Continue clockwise once;
each player gets exactly one final turn. Skip start-phase extra draws, the
normal draw, and the hand-limit check. Play **up to two** legal hand cards.
A blocked attempt consumes one of those two slots; reaction Blocks still do
not consume a slot. Recompute legal moves after each resolved play, so Wrench
can remove Quarantine before playing a Goat with the second slot. Players
can decline to play and preserve their hand for the tie-breaker.

No discard reshuffle or extra round occurs. Sum goat values on ships only;
goats in orbit/discard/hand do not score. Highest score wins, then highest
hand size among the tied scorers. If still tied, split a single win credit
equally. Nothing in the sources supplies a further tie-breaker.

## Scope of the AI

All seats use one public-information policy. Moves are scored by immediate
goat gain, relative harm to a competitive opponent, estimated future modifier
value, and freeing restricted hand cards. It uses small seeded jitter for
close decisions. It does not search hidden hands or future deck order.
It avoids Alfalfa/Chewed Wiring plays in Final Orbit because no further draws
or hand-limit checks happen. This is a consistent baseline for analysis, not
an optimal or human-validated player model.
