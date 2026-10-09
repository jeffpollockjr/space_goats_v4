import unittest

from space_goats.models import Move
from tests.helpers import game, put


class AITests(unittest.TestCase):
    def test_context_contains_own_hand_and_only_public_opponent_information(self):
        g = game()
        own = put(g, "Twin Kids", 0)
        hidden = put(g, "The G.O.A.T.", 1)
        context = g.context(0)
        self.assertIn(own, context.hand)
        self.assertNotIn(hidden, context.hand)
        self.assertEqual(context.players[1].hand_size, 1)
        self.assertFalse(hasattr(context.players[1], "hand"))

    def test_ai_does_not_spend_final_actions_on_draw_or_hand_limit_modifiers(self):
        g = game()
        alfalfa = put(g, "Hydroponic Alfalfa")
        wiring = put(g, "Chewed Wiring")
        g.phase = "final_orbit"
        g.remaining_final_seats = [0, 1]
        g.actions_left = 2
        self.assertLess(g.ai.score(g.context(0), Move(alfalfa, 0)), 0)
        self.assertLess(g.ai.score(g.context(0), Move(wiring, 1)), 0)
        self.assertIsNone(g.ai.choose_move(g.context(0), g.legal_moves(g.players[0])))

    def test_final_wrench_can_unlock_second_goat_play(self):
        g = game()
        quarantine = put(g, "Quarantine Zone", zone="specials")
        wrench = put(g, "Space Wrench")
        goat = put(g, "The G.O.A.T.")
        g.phase = "final_orbit"
        g.remaining_final_seats = [0, 1]
        g.actions_left = 2
        first = g.ai.choose_move(g.context(0), g.legal_moves(g.players[0]))
        self.assertEqual(first.card, wrench)
        g.play(g.players[0], first)
        g.actions_left = 1
        second = g.ai.choose_move(g.context(0), g.legal_moves(g.players[0]))
        self.assertEqual(second.card, goat)

    def test_final_downgrade_has_no_value_after_targets_final_turn(self):
        g = game()
        quarantine = put(g, "Quarantine Zone")
        g.phase = "final_orbit"
        g.remaining_final_seats = [0]
        self.assertLess(g.ai.score(g.context(0), Move(quarantine, 1)), 0)


if __name__ == "__main__":
    unittest.main()
