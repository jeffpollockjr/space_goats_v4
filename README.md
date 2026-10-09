# Space Goats V4 — Python simulator

Run 1,000 complete games from your VS Code terminal, with **2–5 AI players**
using the same strategy. See each player's turns, win rate, and goats, plus
cards played quickly and cards played late or never played.

**Requires Python 3.10 or newer. No packages to install.** This is a local
simulation: it needs no AI subscription, API key, internet connection, or GUI.

## Start here

1. Extract the ZIP.
2. In VS Code, choose **File → Open Folder** and open the extracted
   `space_goats` folder containing `run_simulations.py`.
3. Choose **Terminal → New Terminal**.
4. Run the command below. Change `4` to `2`, `3`, or `5` to change player count.

On macOS or Linux:

```bash
python3 run_simulations.py --players 4
```

On Windows:

```powershell
py run_simulations.py --players 4
```

If your terminal uses `python` instead, this is equivalent:

```bash
python run_simulations.py --players 4
```

Each command runs **1,000 games** by default, prints the aggregated results,
and creates a `results` folder. The pre-generated `sample_results` folder
contains a separate, tested batch of 1,000 four-player games.

## Common commands

These examples use `python3`; on Windows replace it with `py`.

```bash
# Five players, 1,000 games
python3 run_simulations.py --players 5

# Two players, 1,000 games, different random seed and output folder
python3 run_simulations.py --players 2 --seed 123 --output results_2_players

# Larger sample and all 16 cards in the terminal rankings
python3 run_simulations.py --players 4 --simulations 10000 --top 16

# Save every physical card's holding history; log the first three games
python3 run_simulations.py --players 3 --observations --log-games 3

# Check that cards are never lost or duplicated during play
python3 run_simulations.py --players 4 --validate

# Run the included test suite
python3 -m unittest discover -s tests -v

# See every available option
python3 run_simulations.py --help
```

Running with no options uses four players, 1,000 games, and master seed 42.
Use a different `--seed` for another random batch. Repeating the same command
with the same deck, rules, and code reproduces the same game outcomes and
rankings; runtime changes.

## Reports

| File | Contents |
| --- | --- |
| `summary.txt` | Readable report, also printed in the terminal |
| `summary.json` | Complete aggregate statistics, rule settings, and run metadata |
| `player_summary.csv` | Each player's win rate, wins, average/range of turns, goats, and starter counts |
| `game_player_results.csv` | One row per player per game: exact turns, goats, remaining hand, and win credit |
| `game_results.csv` | One row per game: replay seed, starting players, winner(s), winning goats, and total turns |
| `card_usage.csv` | All 17 card names: play rates, holding-time buckets, Blocks, auto-plays, and unused outcomes |
| `most_used_cards.csv` | All cards sorted by percentage played within 0–2 of their owner's turns |
| `least_used_cards.csv` | All cards sorted by percentage never played or played 10+ owner turns later |
| `logs/game_0001.txt` | First game's readable event history, including draws, plays, Blocks, effects, and scores |
| `logs/game_0001.jsonl` | The same event history in machine-readable form |
| `card_observations.csv` | Optional `--observations` export: one record per physical card per game |

CSVs can be opened in Excel. Report paths are relative to your terminal's
current folder. Deck and rule defaults are resolved from the project, so the
runner also works when launched using its absolute path from another folder.

Reusing an output folder overwrites that run's named report files. Older log
files or optional observation files from an earlier, larger run can remain;
use a new `--output` folder for separate experiments. The summary records the
number of logs and whether observations were written for the current run.

## What the statistics mean

**Turns per player:** completed normal turns plus exactly one Final Orbit
turn. If a draw empties the deck, the interrupted normal turn becomes that
player's Final Orbit turn; it is counted once. Each per-game row gives the
exact count. Player summaries give average, median, minimum, maximum, and
10th/90th percentiles.

**Goats:** sum the `Goat Count` values on the player's spaceship. A Twin Kids
card is two goats and The G.O.A.T. is three. The reports also include the
number of physical goat cards, final goat scores for every game, and average
goats in games the player won.

**Win rate:** the highest goat score wins; largest remaining hand breaks a
goat tie. If the hand tie also remains, players share the win equally. Two
shared winners receive 0.5 win credit each. Win rates use these credits, so
they sum to 100% before rounding. Solo wins and shared wins are separate.

**Card age:** count the owner's turns, not all players' turns. A card drawn
on your turn and played immediately has age 0; playing on your next turn has
age 1, and the following turn has age 2. Cards dealt before the game have
acquisition turn 0, so playing on your first turn has age 1. Reaction Blocks
use the blocker's current own-turn counter even when another player acts.

**Most quickly used:** plays with age 0, 1, or 2 divided by all acquisitions
of that card. A separate `next_1_or_2_turns_pct` column implements the exact
"next turn or turn after" definition, excluding age 0. Rates normalize for
different numbers of copies; raw play counts are also present.

**Least used:** cards never played, plus cards first played at age 10 or
older, divided by acquisitions. Never played includes both forced discards
and cards remaining in hand when the game finishes. `held_10_plus_pct`
separately measures cards actually held for 10+ turns, so you can distinguish
long holding from an early forced discard.

Automatic Hyper-Jumping Nanny placements outside setup and reaction Blocks
count as use; setup-dealt Nannies are regular Goat cards in hand.
A blocked Action/Special also counts as used because the player spent the
card. `resolved_plays` and `blocked_plays` separate successful resolution from
blocked attempts. Stealing or scooping an already deployed goat does not
create another hand acquisition or another play of that goat card.

Cards acquired near the end have fewer chances to be played, and some are
held for defense or the hand-size tie-breaker. The raw rankings reflect this
AI and these rules. They do not establish the optimal strategy or prove a
card is weak. See [docs/statistics.md](docs/statistics.md) for the column guide.

## AI players and fairness

Every seat uses the same rules and scoring weights. There are no individual
personalities or stronger players. The policy favors goat gains, steals,
useful modifiers, removing its own restrictions, and attacks on competitive
opponents. It reacts with valid Blocks and discards lower-value cards. Small
seeded random differences break close choices.

The AI sees its own hand, public spaceship cards, orbit, other hand sizes,
and deck length. It cannot see opponents' hand contents or the deck order.
Starting players rotate evenly across the batch, with a seed-selected initial
offset. For 1,000 games and four players, every player starts 250 times. With
three players the counts differ by at most one. Differences in win rate are
still expected from random draws and the game's turn order.

Strategy weights live in `space_goats/ai.py`. They are a practical heuristic,
not a learned model or exhaustive search.

## Assumptions you can adjust

The supplied spec does not define initial hands, duplicate modifiers, or
unresolved ties. Some CSV descriptions are broader than the spec. Defaults
are documented in detail in [docs/rules_and_assumptions.md](docs/rules_and_assumptions.md):

- Deal five cards to each player; a dealt Nanny is a regular hand goat.
- Resolve Nannies outside setup unless Quarantine blocks the entire effect.
- Quarantine prevents Goat card plays from hand, but not steals or scoops; it
  blocks the Nanny effect.
- The target player chooses the goat affected by eject, destroy, or steal; AI
  players choose the lowest goat-count card.
- Double Trouble grants a second play slot during normal action phases.
- Identical Special cards cannot stack on one ship by default.
- Chewed Wiring's reduced limit lasts while attached; Space Wrench restores it.
- Blocks follow the exact restrictions in the coding spec and cannot counter Blocks.
- The deck is never reshuffled; Final Orbit starts immediately on its exhaustion.
- Fully tied winners share win credit.

Edit `rules.json` to compare rule variants. For example:

| Setting | Default | Alternative |
| --- | --- | --- |
| `starting_hand_size` | `5` | Another nonnegative integer |
| `allow_duplicate_specials` | `false` | `true` allows duplicates; Alfalfa copies each add a draw |
| `normal_hand_limit` | `5` | Another nonnegative integer |
| `chewed_hand_limit` | `3` | Another nonnegative integer |
| `final_orbit_cards` | `2` | Another positive integer |

You can also supply a separate rules file using `--rules my_rules.json`.
Changing rules changes the results; compare separate output folders using
the same master seed. Different choices can change how many random numbers
the AI consumes, so later plays are not matched card-for-card across variants.

## Change the deck

`data/deck.csv` contains 104 physical cards. **Each row is
one physical card**, so duplicate or remove rows to change copy counts. Keep
the column headers and CSV quoting intact.

Existing card names determine implemented behavior; the `Effect` column is
descriptive text. Editing that text alone does not change the engine. New card
names require a new effect implementation. The loader rejects unsupported
names, inconsistent duplicate definitions, and invalid card values instead
of silently inventing behavior.

## Replay one game

Open `game_results.csv` in VS Code, find a game's `game_seed` and
`starting_player`, and pass them with the same player count, rules, and deck:

```bash
python3 run_simulations.py --players 4 --game-seed 12345 --start-player 2 --output replay
```

The numbers above are an example; substitute values from your actual row.
`--game-seed` always runs one game and requires `--start-player`. The first
game's complete events are written by default. You can compare the replay's
JSONL with the original log. Use `--log-games 1000` if you want logs for every
game in an original 1,000-game batch.

## Project files

| Path | Purpose |
| --- | --- |
| `run_simulations.py` | Main terminal launcher |
| `space_goats/models.py` | Cards, players, rules, moves, and result records |
| `space_goats/deck.py` | Validated CSV loading |
| `space_goats/engine.py` | Complete rules and turn flow |
| `space_goats/ai.py` | Shared AI and public-information view |
| `space_goats/reporting.py` | Aggregation, CSV/JSON reports, and logs |
| `space_goats/cli.py` | Arguments, simulation loop, seeds, and progress |
| `rules.json` | Editable rule assumptions |
| `data/deck.csv` | Original 104-card deck |
| `docs/original_spec.md` | Original supplied coding spec, unchanged |
| `tests/` | Rules, AI, reporting, replay, and terminal tests |
| `sample_results/` | Verified example run of 1,000 four-player games |
| `requirements.txt` | States that no third-party packages are needed |

## Troubleshooting

- **Python is not found:** use `python3` on macOS/Linux or `py` on Windows.
  Check with `python3 --version` or `py --version`. Install Python 3.10+ if absent.
- **Can't open `run_simulations.py`:** open the folder containing that file,
  or `cd` into it before running the command.
- **Invalid player count:** choose 2, 3, 4, or 5.
- **No fresh random outcomes:** change `--seed`; the default is deliberately repeatable.
- **CSV changed and the loader fails:** restore `data/deck.csv` or fix the row
  identified in the error. Do not edit it as an unquoted comma-separated paragraph.
- **Run interrupted:** run again to regenerate complete reports. Completed
  game logs and an optional partially written observation file may remain.

See [docs/validation.md](docs/validation.md) for the completed verification.
