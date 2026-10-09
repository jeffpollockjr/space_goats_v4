import unittest
from collections import Counter
from dataclasses import replace

from space_goats.engine import Game
from space_goats.models import Acquisition
from space_goats.reporting import Aggregator, observation_row
from tests.helpers import BY_NAME, CARDS


class TrackingTests(unittest.TestCase):
    def test_zero_is_a_valid_play_and_discard_turn(self):
        played = Acquisition(BY_NAME["Astro-Billy"], 0, 0, "deal", played_turn=0)
        discarded = Acquisition(BY_NAME["Astro-Billy"], 0, 0, "deal", discarded_turn=0)
        self.assertEqual(played.outcome, "played")
        self.assertEqual(discarded.outcome, "discarded_unplayed")
        self.assertEqual(played.wait_turns, 0)
        self.assertEqual(discarded.wait_turns, 0)

    def test_used_and_unused_holding_time_ends_at_correct_event(self):
        card = BY_NAME["Astro-Billy"]
        self.assertEqual(Acquisition(card, 0, 3, "draw", played_turn=5, game_end_turn=20).wait_turns, 2)
        self.assertEqual(Acquisition(card, 0, 3, "draw", discarded_turn=7, game_end_turn=20).wait_turns, 4)
        self.assertEqual(Acquisition(card, 0, 3, "draw", game_end_turn=20).wait_turns, 17)

    def test_quick_slow_never_buckets_and_denominators(self):
        agg = Aggregator(CARDS, 2)
        card = BY_NAME["Astro-Billy"]
        for delay in (0, 1, 2, 3, 9, 10):
            agg.add_observation(Acquisition(card, 0, 0, "draw", played_turn=delay, game_end_turn=20))
        agg.add_observation(Acquisition(card, 0, 0, "draw", discarded_turn=1, game_end_turn=20))
        agg.add_observation(Acquisition(card, 0, 0, "draw", game_end_turn=12))
        # Only this card was observed; use its counters directly.
        row = agg.usage["Astro-Billy"]
        self.assertEqual(row["acquired"], 8)
        self.assertEqual(row["played"], 6)
        self.assertEqual(row["played_within_2_turns"], 3)
        self.assertEqual(row["played_next_turn"], 1)
        self.assertEqual(row["played_turn_after_next"], 1)
        self.assertEqual(row["played_after_3_to_9_turns"], 2)
        self.assertEqual(row["played_after_10_plus_turns"], 1)
        self.assertEqual(row["never_played"], 2)
        self.assertEqual(row["discarded_unplayed"], 1)
        self.assertEqual(row["left_in_hand"], 1)
        self.assertEqual(row["held_10_plus_turns"], 2)
        self.assertEqual(row["long_or_never_played"], 3)

    def test_blocked_attempt_is_used_not_resolved(self):
        agg = Aggregator(CARDS, 2)
        rec = Acquisition(BY_NAME["Laser Blast"], 0, 4, "draw", played_turn=5, blocked=True)
        agg.add_observation(rec)
        row = agg.usage[rec.card.name]
        self.assertEqual(row["played"], 1)
        self.assertEqual(row["played_within_2_turns"], 1)
        self.assertEqual(row["blocked_plays"], 1)
        self.assertEqual(row["resolved_plays"], 0)

    def test_automatic_use_and_reactions_are_counted_separately(self):
        agg = Aggregator(CARDS, 2)
        agg.add_observation(Acquisition(BY_NAME["Hyper-Jumping Nanny"], 0, 2, "draw", played_turn=2, auto_play=True, resolved=True))
        agg.add_observation(Acquisition(BY_NAME["Goat-Yoga Focus"], 1, 2, "draw", played_turn=2, reaction=True, resolved=True))
        self.assertEqual(agg.usage["Hyper-Jumping Nanny"]["auto_played"], 1)
        self.assertEqual(agg.usage["Goat-Yoga Focus"]["reaction_plays"], 1)

    def test_complete_game_statistics_reconcile(self):
        agg = Aggregator(CARDS, 4)
        for seed in range(7):
            agg.add(Game(CARDS, 4, seed, start_seat=seed % 4).run())
        rows = agg.card_rows()
        self.assertEqual(sum(row["acquired"] for row in rows), 104 * 7)
        for row in rows:
            self.assertEqual(row["acquired"], row["played"] + row["never_played"])
            self.assertEqual(row["never_played"], row["discarded_unplayed"] + row["left_in_hand"])
            self.assertEqual(row["played"], row["resolved_plays"] + row["blocked_plays"])
            self.assertEqual(row["played_within_2_turns"], row["played_same_turn"] + row["played_next_turn"] + row["played_turn_after_next"])
            self.assertEqual(row["played"], row["played_within_2_turns"] + row["played_after_3_to_9_turns"] + row["played_after_10_plus_turns"])
        self.assertAlmostEqual(sum(row["win_rate_pct"] for row in agg.player_rows()), 100, places=3)

    def test_per_card_observation_keeps_owner_counters(self):
        record = Acquisition(BY_NAME["Astro-Billy"], 1, 3, "normal_draw", played_turn=5, game_end_turn=12)
        row = observation_row(14, record)
        self.assertEqual(row["game"], 14)
        self.assertEqual(row["player"], "Player 2")
        self.assertEqual(row["observed_hold_turns"], 2)


if __name__ == "__main__":
    unittest.main()
