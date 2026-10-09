# Statistics guide

All percentages are 0–100. All turn ages use the **original acquiring player's
own turns**. Each physical deck card is observed once, and the deck is never
recycled. Thus a standard 1,000-game batch has 104,000 acquisitions. The same
named card's rows are aggregated together across all players and games.

## Player summary columns

| Column | Meaning |
| --- | --- |
| `player`, `games` | Persistent seat name and games participated in |
| `outright_wins` | Games won alone |
| `shared_wins` | Games tied after both goat and hand tie-breakers |
| `win_credit` | Solo wins plus fractional shared credits |
| `win_rate_pct` | `100 * win_credit / games` |
| `win_rate_mc_standard_error_pct` | Approximate standard error of sampled win credits; describes sampling noise, not model accuracy |
| `avg_turns`, `median_turns`, `min_turns`, `max_turns` | Completed normal turns plus one Final Orbit turn per game |
| `p10_turns`, `p90_turns` | Interpolated 10th and 90th percentiles |
| `avg_normal_turns`, `avg_final_turns` | Components of total turns; final average is exactly 1 |
| `avg_goats`, `median_goats`, `min_goats`, `max_goats` | Endgame score statistics, summing Goat Count |
| `total_goats` | Sum of that seat's final scores across all games |
| `avg_goats_when_winner` | Average score in solo/shared winning games; blank if no wins |
| `avg_goat_cards` | Physical Goat card count on ship, unlike score |
| `avg_ending_hand_cards` | Remaining hand cards after Final Orbit |
| `games_started`, `final_orbits_started` | Number of first normal/final positions for that seat |

## Card usage columns

| Column | Meaning |
| --- | --- |
| `card`, `type`, `copies_per_deck` | Identity and original deck multiplicity |
| `acquired` | All copies drawn/dealt across the batch, including Nannies |
| `played` | Uses: manual plays, automatic deployments, and reaction Blocks |
| `manual_plays` | `played - auto_played`; includes reaction Blocks |
| `auto_played` | Nanny automatic placements only |
| `reaction_plays` | Off-turn Block uses |
| `resolved_plays` | Effect resolved, including automatic placements and valid Blocks |
| `blocked_plays` | Attempted plays canceled by a Block |
| `played_same_turn` | Owner counter difference 0; can include an off-turn reaction before the next own turn |
| `played_next_turn` | Owner counter difference 1 |
| `played_turn_after_next` | Owner counter difference 2 |
| `played_within_2_turns` | Sum of the three previous buckets |
| `played_after_3_to_9_turns` | First use with age 3 through 9 |
| `played_after_10_plus_turns` | First use with age at least 10 |
| `never_played` | Never used before leaving hand or game end |
| `discarded_unplayed` | Hand-limit discard without prior use |
| `left_in_hand` | Unused at game end |
| `held_10_plus_turns` | Observed hold age at least 10, regardless of eventual use |
| `long_or_never_played` | Never-played count plus played-after-10 count; each card counted once |
| `acquired_with_fewer_than_2_future_turns` | Endgame owner counter minus acquisition counter below 2; indicator of limited opportunity |
| `played_pct` | `100 * played / acquired` |
| `quick_use_pct` | `100 * played_within_2_turns / acquired`; primary most-used ranking |
| `next_1_or_2_turns_pct` | Exact age-1-or-2 rate, excluding immediate plays |
| `never_played_pct` | Never-played share of acquisitions |
| `long_or_never_pct` | Primary least-used ranking |
| `held_10_plus_pct` | Actual observed long-holding share |
| `avg_turns_to_play`, `median_turns_to_play`, `p90_turns_to_play` | Only cards actually used; blank when no plays |
| `avg_observed_hold_turns_all` | Average age until use, forced discard, or game end for all acquired copies |
| `avg_observed_hold_turns_unplayed` | Observed age until discard/end for unused copies |

These identities must reconcile:

```text
acquired = played + never_played
never_played = discarded_unplayed + left_in_hand
played = resolved_plays + blocked_plays
played = played_within_2_turns + played_after_3_to_9_turns + played_after_10_plus_turns
```

For unused cards left in hand, the hold length is the observed duration until
the game ends. There is no prediction of when they would be played if the
game continued. Late acquisitions and needed defensive opportunities affect
raw rates. `acquired_with_fewer_than_2_future_turns` flags late exposures;
there is no survival-adjusted ranking.

A goat card transferred by Tractor Beam or Orbital Vacuum retains its original
draw/use record. Its current owner can change its final scoring location but
not how quickly the original player deployed it. An Action blocked after one
turn counts as an age-1 use and a blocked effect.

## Per-game and raw observations

`game_player_results.csv` gives each player's exact final goat score and turns
for each simulation. Normal turns exclude the partial normal turn that
converts to Final Orbit. The `final_turns` column is always one.

With `--observations`, `card_observations.csv` stores each physical card's ID,
acquiring seat, draw source, acquisition/play/discard/end own-turn counters,
observed hold age, outcome, auto/reaction flags, and blocked/resolved flags.
`card_id` is only unique within a game, so use `(game, card_id)` as its key.

Complete JSONL game logs include pending plays and separate resolved effect
events. A `play` event followed by `blocked` is an attempted use; no corresponding
effect takes place. A normal `turn_start` can be followed by a Final Orbit
`turn_start` with the same player-turn number after deck exhaustion. This is
a phase transition inside one counted turn.
