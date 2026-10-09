"""Aggregate statistics and write readable, spreadsheet-friendly reports."""

import csv
import json
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import Acquisition, Card, GameResult, Rules


def percentile(values: List[int], fraction: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower), 4)


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class Aggregator:
    def __init__(self, cards: List[Card], players: int):
        self.player_count = players
        self.deck_counts = Counter(card.name for card in cards)
        self.card_definitions = {card.name: card for card in cards}
        self.game_rows: List[Dict[str, Any]] = []
        self.game_player_rows: List[Dict[str, Any]] = []
        self.results_by_player = defaultdict(list)
        self.player_start_counts = Counter()
        self.player_final_start_counts = Counter()
        self.usage = {name: Counter() for name in self.deck_counts}
        self.waits_played = defaultdict(list)
        self.waits_unplayed = defaultdict(list)
        self.game_count = 0
        self.shared_games = 0

    def add(self, result: GameResult) -> None:
        self.game_count += 1
        game_id = self.game_count
        self.shared_games += len(result.winners) > 1
        self.player_start_counts[result.start_seat] += 1
        self.player_final_start_counts[result.final_start_seat] += 1
        self.game_rows.append({
            "game": game_id, "game_seed": result.seed,
            "starting_player": result.start_seat + 1, "final_orbit_starting_player": result.final_start_seat + 1,
            "winners": ";".join(f"Player {seat + 1}" for seat in result.winners),
            "winning_goats": max(player.goats for player in result.players),
            "total_player_turns": sum(player.turns for player in result.players),
            "orbit_goats_at_end": result.ending_orbit_goats,
            "discard_cards_at_end": result.ending_discard_cards,
        })
        for player in result.players:
            self.results_by_player[player.seat].append(player)
            self.game_player_rows.append({
                "game": game_id, "game_seed": result.seed, "player": f"Player {player.seat + 1}",
                "started_game": player.seat == result.start_seat,
                "started_final_orbit": player.seat == result.final_start_seat,
                "turns": player.turns, "normal_turns": player.normal_turns,
                "final_turns": player.final_turns, "goats": player.goats,
                "goat_cards": player.goat_cards, "hand_cards": player.hand_cards,
                "is_winner": player.is_winner, "outright_win": player.outright_win,
                "win_credit": round(player.win_credit, 8),
            })
        for observation in result.acquisitions:
            self.add_observation(observation)

    def add_observation(self, record: Acquisition) -> None:
        stats = self.usage[record.card.name]
        stats["acquired"] += 1
        stats["total_observed_hold_turns"] += record.wait_turns
        stats["held_10_plus_turns"] += record.wait_turns >= 10
        stats["acquired_with_fewer_than_2_future_turns"] += record.game_end_turn - record.acquired_turn < 2
        if record.played_turn is not None:
            stats["played"] += 1
            stats["auto_played"] += record.auto_play
            stats["reaction_plays"] += record.reaction
            stats["blocked_plays"] += record.blocked
            stats["resolved_plays"] += record.resolved
            stats["played_same_turn"] += record.wait_turns == 0
            stats["played_next_turn"] += record.wait_turns == 1
            stats["played_turn_after_next"] += record.wait_turns == 2
            stats["played_within_2_turns"] += record.wait_turns <= 2
            stats["played_after_3_to_9_turns"] += 3 <= record.wait_turns <= 9
            stats["played_after_10_plus_turns"] += record.wait_turns >= 10
            self.waits_played[record.card.name].append(record.wait_turns)
        else:
            stats["never_played"] += 1
            stats[record.outcome] += 1
            self.waits_unplayed[record.card.name].append(record.wait_turns)
        stats["long_or_never_played"] += record.played_turn is None or record.wait_turns >= 10

    def player_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for seat in range(self.player_count):
            values = self.results_by_player[seat]
            turns = [value.turns for value in values]
            goats = [value.goats for value in values]
            winner_goats = [value.goats for value in values if value.is_winner]
            win_credit = sum(value.win_credit for value in values)
            win_rate = win_credit / len(values)
            # Approximate Monte Carlo standard error, including fractional tie credits.
            stderr = statistics.stdev([value.win_credit for value in values]) / len(values) ** 0.5 if len(values) > 1 else 0.0
            rows.append({
                "player": f"Player {seat + 1}", "games": len(values),
                "outright_wins": sum(value.outright_win for value in values),
                "shared_wins": sum(value.is_winner and not value.outright_win for value in values),
                "win_credit": round(win_credit, 6), "win_rate_pct": round(win_rate * 100, 4),
                "win_rate_mc_standard_error_pct": round(stderr * 100, 4),
                "avg_turns": round(statistics.mean(turns), 4),
                "median_turns": statistics.median(turns), "min_turns": min(turns), "max_turns": max(turns),
                "p10_turns": percentile(turns, 0.1), "p90_turns": percentile(turns, 0.9),
                "avg_normal_turns": round(statistics.mean(value.normal_turns for value in values), 4),
                "avg_final_turns": round(statistics.mean(value.final_turns for value in values), 4),
                "avg_goats": round(statistics.mean(goats), 4),
                "median_goats": statistics.median(goats), "min_goats": min(goats), "max_goats": max(goats),
                "total_goats": sum(goats),
                "avg_goats_when_winner": round(statistics.mean(winner_goats), 4) if winner_goats else None,
                "avg_goat_cards": round(statistics.mean(value.goat_cards for value in values), 4),
                "avg_ending_hand_cards": round(statistics.mean(value.hand_cards for value in values), 4),
                "games_started": self.player_start_counts[seat],
                "final_orbits_started": self.player_final_start_counts[seat],
            })
        return rows

    def card_rows(self) -> List[Dict[str, Any]]:
        rows = []
        keys = ("played", "auto_played", "reaction_plays", "resolved_plays", "blocked_plays",
                "played_same_turn", "played_next_turn", "played_turn_after_next", "played_within_2_turns",
                "played_after_3_to_9_turns", "played_after_10_plus_turns", "never_played",
                "discarded_unplayed", "left_in_hand", "held_10_plus_turns", "long_or_never_played",
                "acquired_with_fewer_than_2_future_turns")
        for name in self.deck_counts:
            stats = self.usage[name]
            acquired = stats["acquired"]
            waits = self.waits_played[name]
            row = {"card": name, "type": self.card_definitions[name].card_type,
                   "copies_per_deck": self.deck_counts[name], "acquired": acquired}
            row.update({key: stats[key] for key in keys})
            row.update({
                "manual_plays": stats["played"] - stats["auto_played"],
                "played_pct": round(100 * stats["played"] / acquired, 4),
                "quick_use_pct": round(100 * stats["played_within_2_turns"] / acquired, 4),
                "next_1_or_2_turns_pct": round(100 * (stats["played_next_turn"] + stats["played_turn_after_next"]) / acquired, 4),
                "never_played_pct": round(100 * stats["never_played"] / acquired, 4),
                "long_or_never_pct": round(100 * stats["long_or_never_played"] / acquired, 4),
                "held_10_plus_pct": round(100 * stats["held_10_plus_turns"] / acquired, 4),
                "avg_turns_to_play": round(statistics.mean(waits), 4) if waits else None,
                "median_turns_to_play": statistics.median(waits) if waits else None,
                "p90_turns_to_play": percentile(waits, 0.9) if waits else None,
                "avg_observed_hold_turns_all": round(stats["total_observed_hold_turns"] / acquired, 4),
                "avg_observed_hold_turns_unplayed": round(statistics.mean(self.waits_unplayed[name]), 4)
                    if self.waits_unplayed[name] else None,
            })
            if stats["played"] + stats["never_played"] != acquired:
                raise AssertionError("Card usage counts do not reconcile.")
            rows.append(row)
        return rows

    def summary(self, seed: int, rules: Rules, elapsed: float, deck_path: str,
                logged_games: int, replay_seed: Any = None) -> Dict[str, Any]:
        player_rows = self.player_rows()
        card_rows = self.card_rows()
        quick = sorted(card_rows, key=lambda row: (-row["quick_use_pct"], -row["played_within_2_turns"], row["card"]))
        least = sorted(card_rows, key=lambda row: (-row["long_or_never_pct"], -row["long_or_never_played"], row["card"]))
        total_turns = [row["total_player_turns"] for row in self.game_rows]
        return {
            "simulator_version": "1.0.0", "simulations": self.game_count,
            "players": self.player_count, "master_seed": seed, "replay_game_seed": replay_seed,
            "deck_file": deck_path, "deck_cards": sum(self.deck_counts.values()),
            "distinct_cards": len(card_rows), "rules": rules.to_dict(),
            "elapsed_seconds": round(elapsed, 3), "logged_games": logged_games,
            "games_with_shared_winners": self.shared_games,
            "avg_total_player_turns_per_game": round(statistics.mean(total_turns), 4),
            "player_statistics": player_rows, "card_statistics": card_rows,
            "most_quickly_used": quick, "least_used": least,
            "definitions": {
                "turns": "Completed normal turns plus one Final Orbit turn; interrupted normal turn becomes that final turn.",
                "goats": "Sum of Goat Count, not number of physical cards.",
                "win_rate": "Fractional win credits / games; equal winners share one win credit.",
                "wait_turns": "Owner's turn counter at play/discard/end minus counter at acquisition; never global turns.",
                "quick_use": "Played within 0, 1, or 2 owner turns after acquisition, divided by all acquisitions.",
                "exact_next_1_or_2": "Separate metric excluding same-turn use.",
                "least_used": "Never played OR played 10+ owner turns after acquisition, divided by all acquisitions.",
                "held_10_plus": "Actually held 10+ owner turns, whether played, discarded, or left in hand.",
                "played": "Includes automatic Nanny placement and reactions; blocked attempts still count as used.",
                "resolved": "The play's effect resolved; this is not a measurement of later strategic benefit.",
                "late_acquisitions": "Cards with fewer than two future owner turns at game end; raw rates are not survival-adjusted.",
            },
        }


def table(headers: List[str], rows: Iterable[List[Any]]) -> str:
    data = [[str(value) for value in row] for row in rows]
    widths = [max(len(header), max((len(row[i]) for row in data), default=0)) for i, header in enumerate(headers)]
    lines = ["  ".join(header.ljust(width) for header, width in zip(headers, widths)),
             "  ".join("-" * width for width in widths)]
    lines.extend("  ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in data)
    return "\n".join(lines)


def render_summary(summary: Dict[str, Any], top: int = 8) -> str:
    players = summary["player_statistics"]
    lines = ["SPACE GOATS V4 - SIMULATION REPORT", "=" * 60,
             f"Games: {summary['simulations']:,} | Players: {summary['players']} | Deck: {summary['deck_cards']} cards",
             f"Master seed: {summary['master_seed']} | Runtime: {summary['elapsed_seconds']:.3f}s",
             f"Shared-winner games: {summary['games_with_shared_winners']}", "",
             "PLAYER RESULTS (goats = summed Goat Count; turns include Final Orbit)",
             table(["Player", "Win %", "Solo wins", "Shared", "Avg turns", "Turn range", "Avg goats", "Goats if won"], [
                 [row["player"], f"{row['win_rate_pct']:.2f}", row["outright_wins"], row["shared_wins"],
                  f"{row['avg_turns']:.2f}", f"{row['min_turns']}-{row['max_turns']}", f"{row['avg_goats']:.2f}",
                  f"{row['avg_goats_when_winner']:.2f}" if row['avg_goats_when_winner'] is not None else "n/a"]
                 for row in players]), "",
             "MOST QUICKLY USED (played within 0-2 owner turns / acquired)",
             table(["Card", "Quick %", "Quick plays", "All plays", "Avg wait"], [
                 [row["card"], f"{row['quick_use_pct']:.2f}", row["played_within_2_turns"], row["played"],
                  f"{row['avg_turns_to_play']:.2f}" if row['avg_turns_to_play'] is not None else "n/a"]
                 for row in summary["most_quickly_used"][:top]]), "",
             "LEAST USED (never played OR played 10+ owner turns later / acquired)",
             table(["Card", "Slow/never %", "Never played", "Played 10+", "Held 10+ %"], [
                 [row["card"], f"{row['long_or_never_pct']:.2f}", row["never_played"], row["played_after_10_plus_turns"],
                  f"{row['held_10_plus_pct']:.2f}"] for row in summary["least_used"][:top]]), "",
             "Reading these results:",
             "- All seats use the same AI; starting players rotate. Win rates use shared win credits.",
             "- Nanny auto-placements count as plays; reaction Blocks and blocked attempts also count.",
             "- 'Never played' includes forced discards and cards left in hand; these have separate CSV columns.",
             "- Quick rates include same-turn plays; exact next-turn/turn-after rates are also in card_usage.csv.",
             "- Late draws have fewer opportunities. These rates describe this AI, not optimal human play.",
             "- CSVs contain all card names, per-game scores, turn counts, and additional metrics."]
    return "\n".join(lines) + "\n"


def observation_row(game_id: int, record: Acquisition) -> Dict[str, Any]:
    return {"game": game_id, "card_id": record.card.uid, "card": record.card.name,
            "type": record.card.card_type, "player": f"Player {record.player_seat + 1}",
            "acquisition_source": record.source, "acquired_owner_turn": record.acquired_turn,
            "played_owner_turn": record.played_turn, "discarded_owner_turn": record.discarded_turn,
            "game_end_owner_turn": record.game_end_turn, "observed_hold_turns": record.wait_turns,
            "outcome": record.outcome, "auto_play": record.auto_play, "reaction": record.reaction,
            "blocked_attempt": record.blocked, "resolved_play": record.resolved}


def save_log(output: Path, game_id: int, result: GameResult) -> None:
    folder = output / "logs"
    folder.mkdir(exist_ok=True)
    basename = f"game_{game_id:04d}"
    with (folder / f"{basename}.jsonl").open("w", encoding="utf-8") as handle:
        for event in result.events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    lines = [f"Game {game_id} | seed={result.seed} | starting_player={result.start_seat + 1}"]
    for event in result.events:
        player = f"P{event['player']} T{event['player_turn']}" if event["player"] is not None else ""
        extra = {key: value for key, value in event.items() if key not in (
            "event_number", "event", "phase", "player", "player_turn", "card", "card_id", "deck_remaining"
        )}
        lines.append(f"{event['event_number']:04d} [{event['phase']}] {player} {event['event']} "
                     f"{event.get('card', '')} | deck={event['deck_remaining']} | "
                     + json.dumps(extra, ensure_ascii=False))
    (folder / f"{basename}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(output: Path, aggregate: Aggregator, summary: Dict[str, Any], text: str) -> None:
    write_csv(output / "player_summary.csv", summary["player_statistics"])
    write_csv(output / "card_usage.csv", summary["card_statistics"])
    write_csv(output / "most_used_cards.csv", summary["most_quickly_used"])
    write_csv(output / "least_used_cards.csv", summary["least_used"])
    write_csv(output / "game_results.csv", aggregate.game_rows)
    write_csv(output / "game_player_results.csv", aggregate.game_player_rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (output / "summary.txt").write_text(text, encoding="utf-8")
