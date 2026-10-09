"""Terminal entry point. No third-party packages, API keys, or network calls."""

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path
from typing import List, Optional

from .deck import load_deck
from .engine import Game
from .models import Rules
from .reporting import Aggregator, observation_row, render_summary, save_log, write_reports


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
    return number


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Simulate Space Goats V4 with identical, fair AI players.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    result.add_argument("--players", "-p", type=int, choices=range(2, 6), default=4, help="number of AI players")
    result.add_argument("--simulations", "-n", type=positive_int, default=1000, help="games to simulate")
    result.add_argument("--seed", type=int, default=42, help="master seed for repeatable batches")
    result.add_argument("--output", "-o", type=Path, default=Path("results"), help="report directory, relative to your terminal")
    result.add_argument("--deck", type=Path, default=PROJECT_ROOT / "data" / "deck.csv", help="CSV deck, one row per physical card")
    result.add_argument("--rules", type=Path, default=PROJECT_ROOT / "rules.json", help="JSON rule assumptions")
    result.add_argument("--log-games", type=nonnegative_int, default=1, help="number of games to log turn by turn")
    result.add_argument("--top", type=positive_int, default=8, help="cards per terminal ranking; CSVs always contain all")
    result.add_argument("--observations", action="store_true", help="write each physical card's holding-time record")
    result.add_argument("--validate", action="store_true", help="check card conservation after every turn and play")
    result.add_argument("--quiet", action="store_true", help="suppress progress updates; still print final report")
    result.add_argument("--game-seed", type=int, help="replay one game's seed from game_results.csv")
    result.add_argument("--start-player", type=int, choices=range(1, 6), help="fixed starting player; use for replay, otherwise starters rotate")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    command = parser()
    args = command.parse_args(argv)
    if args.start_player is not None and args.start_player > args.players:
        command.error("--start-player cannot exceed --players")
    if args.game_seed is not None and args.start_player is None:
        command.error("--game-seed replay requires --start-player from the same game_results.csv row")
    try:
        cards = load_deck(args.deck)
        with args.rules.open(encoding="utf-8") as handle:
            rule_data = json.load(handle)
        if not isinstance(rule_data, dict):
            raise ValueError("Rules JSON must contain an object.")
        rules = Rules.from_dict(rule_data)
        if args.players * rules.starting_hand_size >= len(cards):
            raise ValueError("Deck must contain more cards than the initial hand slots. Reduce starting_hand_size.")
        args.output.mkdir(parents=True, exist_ok=True)
        games = 1 if args.game_seed is not None else args.simulations
        master_rng = random.Random(args.seed)
        start_offset = master_rng.randrange(args.players)
        aggregate = Aggregator(cards, args.players)
        observations_handle = None
        try:
            observation_writer = None
            if args.observations:
                observations_handle = (args.output / "card_observations.csv").open("w", encoding="utf-8-sig", newline="")
            if not args.quiet:
                print(f"Running {games:,} games with {args.players} AI players ({len(cards)} cards)...", flush=True)
            started = time.perf_counter()
            progress_interval = max(1, games // 10)
            for game_id in range(1, games + 1):
                # 48-bit seeds also survive Excel's 15-significant-digit CSV parsing.
                game_seed = args.game_seed if args.game_seed is not None else master_rng.getrandbits(48)
                start_seat = args.start_player - 1 if args.start_player is not None else (start_offset + game_id - 1) % args.players
                logged = game_id <= args.log_games
                result = Game(cards, args.players, game_seed, start_seat, rules,
                              record_events=logged, check_invariants=args.validate).run()
                aggregate.add(result)
                if logged:
                    save_log(args.output, game_id, result)
                if observations_handle is not None:
                    for observation in result.acquisitions:
                        row = observation_row(game_id, observation)
                        if observation_writer is None:
                            observation_writer = csv.DictWriter(observations_handle, fieldnames=list(row))
                            observation_writer.writeheader()
                        observation_writer.writerow(row)
                if not args.quiet and (game_id % progress_interval == 0 or game_id == games):
                    print(f"  {game_id:,}/{games:,} complete", flush=True)
            elapsed = time.perf_counter() - started
        finally:
            if observations_handle is not None:
                observations_handle.close()
        summary = aggregate.summary(args.seed, rules, elapsed, str(args.deck.resolve()),
                                    min(args.log_games, games), args.game_seed)
        summary["starting_player_policy"] = "fixed" if args.start_player is not None else "rotating"
        summary["fixed_starting_player"] = args.start_player
        summary["observations_written"] = args.observations
        report = render_summary(summary, args.top)
        if args.start_player is not None:
            report = report.replace("starting players rotate", "starting player is fixed")
        write_reports(args.output, aggregate, summary, report)
        print("\n" + report)
        print(f"Reports saved to: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nSimulation interrupted. Run again to regenerate complete reports.", file=sys.stderr)
        return 130
