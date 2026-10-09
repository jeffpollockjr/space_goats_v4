import unittest
from dataclasses import replace

from space_goats.engine import Game
from space_goats.models import Move, Rules
from tests.helpers import CARDS, game, put, tiny_game


class SetupAndDrawTests(unittest.TestCase):
    def test_original_deck(self):
        self.assertEqual(len(CARDS), 104)
        self.assertEqual(len({card.name for card in CARDS}), 17)
        self.assertEqual(sum(card.goat_count for card in CARDS), 68)
        self.assertEqual(sum(card.name == "Quarantine Zone" for card in CARDS), 3)
        self.assertEqual(sum(card.name == "Space Sickness" for card in CARDS), 3)
        self.assertEqual(sum(card.name == "Double Trouble" for card in CARDS), 2)

    def test_setup_deals_five_cards_and_nannies_are_regular_hand_goats(self):
        g = game(players=5, rules=Rules())
        g.deal()
        self.assertEqual([len(p.hand) for p in g.players], [5] * 5)
        self.assertEqual([len(p.goats) for p in g.players], [0] * 5)
        dealt_nannies = [card for p in g.players for card in p.hand if card.effect_id == "nanny"]
        self.assertTrue(all(not g.acquisitions[card.uid].auto_play for card in dealt_nannies))
        g.assert_invariants()

    def test_nanny_chain_is_automatic_and_replaces_draw(self):
        g = tiny_game(["Astro-Billy", "Hyper-Jumping Nanny", "Hyper-Jumping Nanny"])
        g.phase = "normal"
        g.deck.sort(key=lambda card: card.effect_id == "nanny")
        g.draw(g.players[0])
        self.assertEqual(len(g.players[0].goats), 2)
        self.assertEqual(len(g.players[0].hand), 1)
        self.assertEqual(g.final_start_seat, 0)
        self.assertTrue(all(g.acquisitions[c.uid].auto_play for c in g.players[0].goats))
        g.assert_invariants()

    def test_last_card_nanny_is_placed_without_bonus_draw(self):
        g = tiny_game(["Hyper-Jumping Nanny"])
        g.phase = "normal"
        g.draw(g.players[0])
        self.assertEqual(g.players[0].goat_total, 1)
        self.assertEqual(g.final_start_seat, 0)
        self.assertEqual(g.deck, [])

    def test_setup_nanny_is_dealt_as_a_regular_hand_goat(self):
        g = tiny_game(["Hyper-Jumping Nanny", "Astro-Billy"])
        g.deck.sort(key=lambda c: c.effect_id == "nanny")
        g.draw(g.players[0], "deal")
        self.assertEqual(len(g.players[0].hand), 1)
        self.assertEqual(len(g.players[0].goats), 0)
        self.assertEqual(len(g.deck), 1)
        g.phase = "normal"
        nanny = g.players[0].hand[0]
        self.assertIn(Move(nanny, 0), g.legal_moves(g.players[0]))
        g.play(g.players[0], Move(nanny, 0))
        self.assertEqual(g.players[0].goats, [nanny])
        self.assertEqual(len(g.deck), 1)

    def test_quarantine_blocks_nanny_effect_and_bonus_draw(self):
        g = game()
        put(g, "Quarantine Zone", zone="specials")
        nanny = next(card for card in g.deck if card.effect_id == "nanny")
        ordinary = next(card for card in g.deck if card.name == "Astro-Billy")
        g.deck.remove(nanny)
        g.deck.remove(ordinary)
        g.deck.extend([ordinary, nanny])
        g.phase = "normal"
        g.draw(g.players[0])
        self.assertEqual(g.players[0].hand, [nanny])
        self.assertIn(ordinary, g.deck)
        self.assertFalse(g.acquisitions[nanny.uid].auto_play)
        self.assertEqual(len(g.players[0].goats), 0)
        g.assert_invariants()


class ActionTests(unittest.TestCase):
    def test_goat_count_is_value_not_card_count(self):
        g = game()
        card = put(g, "Twin Kids")
        g.play(g.players[0], Move(card, 0))
        self.assertEqual(g.players[0].goat_total, 2)
        self.assertEqual(len(g.players[0].goats), 1)

    def test_eject_victim_chooses_lowest_goat_and_it_goes_to_orbit(self):
        g = game()
        low = put(g, "Astro-Billy", 1, "goats")
        high = put(g, "The G.O.A.T.", 1, "goats")
        action = put(g, "Airlock Malfunction")
        move = g.legal_moves(g.players[0])[0]
        self.assertIsNone(move.target_card_uid)
        g.play(g.players[0], move)
        self.assertEqual(g.orbital, [low])
        self.assertEqual(g.players[1].goats, [high])
        self.assertIn(action, g.discard)

    def test_victim_also_chooses_which_goat_is_stolen(self):
        g = game()
        low = put(g, "Astro-Billy", 1, "goats")
        put(g, "The G.O.A.T.", 1, "goats")
        put(g, "Tractor Beam")
        move = g.legal_moves(g.players[0])[0]
        g.play(g.players[0], move)
        self.assertIn(low, g.players[0].goats)

    def test_destroy_does_not_eject(self):
        g = game()
        goat = put(g, "Twin Kids", 1, "goats")
        action = put(g, "Laser Blast")
        g.play(g.players[0], Move(action, 1))
        self.assertIn(goat, g.discard)
        self.assertEqual(g.orbital, [])
        self.assertEqual(g.players[1].goats, [])

    def test_steal_transfers_goat_without_new_acquisition(self):
        g = game()
        goat = put(g, "The G.O.A.T.", 1, "goats")
        action = put(g, "Tractor Beam")
        old_count = len(g.acquisitions)
        g.play(g.players[0], Move(action, 1))
        self.assertIn(goat, g.players[0].goats)
        self.assertEqual(g.players[1].goats, [])
        self.assertEqual(g.acquisitions[goat.uid].player_seat, 1)
        self.assertEqual(len(g.acquisitions), old_count)

    def test_vacuum_takes_all_orbit_goats(self):
        g = game()
        goats = [put(g, "Twin Kids", 1, "goats"), put(g, "Astro-Billy", 1, "goats")]
        g.players[1].goats.clear()
        g.orbital.extend(goats)
        action = put(g, "Orbital Vacuum")
        g.play(g.players[0], Move(action, 0))
        self.assertEqual(g.players[0].goat_total, 3)
        self.assertEqual(g.orbital, [])

    def test_wrench_removes_modifier_and_restores_hand_limit(self):
        g = game()
        wiring = put(g, "Chewed Wiring", zone="specials")
        wrench = put(g, "Space Wrench")
        self.assertEqual(g.players[0].hand_limit(g.rules), 3)
        g.play(g.players[0], Move(wrench, 0, wiring.uid))
        self.assertEqual(g.players[0].hand_limit(g.rules), 5)
        self.assertIn(wiring, g.discard)

    def test_empty_target_actions_are_illegal(self):
        g = game()
        for name in ("Tractor Beam", "Airlock Malfunction", "Laser Blast", "Orbital Vacuum", "Space Wrench"):
            put(g, name)
        self.assertEqual(g.legal_moves(g.players[0]), [])

    def test_illegal_play_does_not_consume_card(self):
        g = game()
        card = put(g, "Laser Blast")
        with self.assertRaises(ValueError):
            g.play(g.players[0], Move(card, 1, 9999))
        self.assertIn(card, g.players[0].hand)


class ModifierTests(unittest.TestCase):
    def test_alfalfa_adds_start_draw_before_normal_draw(self):
        g = game()
        put(g, "Hydroponic Alfalfa", zone="specials")
        g.phase = "normal"
        g.ai.choose_move = lambda context, moves: next((m for m in moves if m.card.card_type == "Goat"), None)
        g.normal_turn(g.players[0])
        sources = [event["source"] for event in g.events if event["event"] == "draw"]
        self.assertEqual(sources[0], "alfalfa")
        self.assertIn("normal_draw", sources)

    def test_wiring_forces_discard_to_three(self):
        g = game()
        put(g, "Chewed Wiring", zone="specials")
        for _ in range(5):
            put(g, "Astro-Billy")
        g.enforce_hand_limit(g.players[0])
        self.assertEqual(len(g.players[0].hand), 3)
        self.assertEqual(len(g.discard), 2)
        self.assertEqual(sum(r.discarded_turn is not None for r in g.acquisitions.values()), 2)
        g.assert_invariants()

    def test_sickness_blocks_opponent_actions_but_not_self_help_or_specials(self):
        g = game()
        put(g, "Space Sickness", zone="specials")
        own_bad = put(g, "Quarantine Zone", zone="specials")
        other_bad = put(g, "Chewed Wiring", 1, "specials")
        put(g, "Twin Kids", 1, "goats")
        for name in ("Tractor Beam", "Laser Blast", "Airlock Malfunction", "Space Wrench", "Quarantine Zone"):
            put(g, name)
        moves = g.legal_moves(g.players[0])
        self.assertFalse(any(m.card.effect_id in ("steal", "destroy", "eject") for m in moves))
        self.assertTrue(any(m.card.effect_id == "remove_modifier" and m.target_card_uid == own_bad.uid for m in moves))
        self.assertFalse(any(m.card.effect_id == "remove_modifier" and m.target_card_uid == other_bad.uid for m in moves))
        self.assertTrue(any(m.card.card_type == "Special" and m.target_seat == 1 for m in moves))

    def test_quarantine_blocks_hand_play_but_allows_steal_and_scoop(self):
        g = game()
        put(g, "Quarantine Zone", zone="specials")
        put(g, "Twin Kids", 1, "goats")
        orbit = put(g, "Astro-Billy", 1, "goats")
        g.players[1].goats.remove(orbit)
        g.orbital.append(orbit)
        for name in ("Astro-Billy", "Tractor Beam", "Orbital Vacuum", "Laser Blast"):
            put(g, name)
        moves = g.legal_moves(g.players[0])
        self.assertFalse(any(m.card.card_type == "Goat" for m in moves))
        self.assertTrue(any(m.card.effect_id == "steal" for m in moves))
        self.assertTrue(any(m.card.effect_id == "scoop" for m in moves))
        self.assertTrue(any(m.card.effect_id == "destroy" for m in moves))

    def test_quarantined_nanny_goat_cannot_be_played_from_hand(self):
        g = game()
        put(g, "Quarantine Zone", zone="specials")
        put(g, "Hyper-Jumping Nanny")
        moves = g.legal_moves(g.players[0])
        self.assertFalse(any(m.card.card_type == "Goat" for m in moves))

    def test_identical_specials_do_not_stack_by_default(self):
        g = game()
        put(g, "Hydroponic Alfalfa", zone="specials")
        put(g, "Hydroponic Alfalfa")
        moves = g.legal_moves(g.players[0])
        self.assertFalse(any(m.target_seat == 0 for m in moves))
        self.assertTrue(any(m.target_seat == 1 for m in moves))

    def test_duplicate_variant_stacks_alfalfa(self):
        g = game(rules=Rules(starting_hand_size=0, allow_duplicate_specials=True))
        put(g, "Hydroponic Alfalfa", zone="specials")
        card = put(g, "Hydroponic Alfalfa")
        g.play(g.players[0], Move(card, 0))
        g.normal_turn(g.players[0])
        self.assertEqual(sum(e["event"] == "draw" and e.get("source") == "alfalfa" for e in g.events), 2)

    def test_double_trouble_grants_two_normal_action_plays(self):
        g = game()
        put(g, "Double Trouble", zone="specials")
        first = put(g, "Astro-Billy")
        second = put(g, "Twin Kids")
        g.phase = "normal"
        g.draw = lambda player, source="normal_draw": None
        g.ai.choose_move = lambda context, moves: next(
            (move for move in moves if move.card.card_type == "Goat"), None)
        g.normal_turn(g.players[0])
        self.assertIn(first, g.players[0].goats)
        self.assertIn(second, g.players[0].goats)
        self.assertEqual(sum(event["event"] == "play" for event in g.events), 2)

    def test_double_trouble_can_attach_to_any_spaceship(self):
        g = game()
        card = put(g, "Double Trouble")
        moves = g.legal_moves(g.players[0])
        self.assertEqual([move.target_seat for move in moves if move.card == card], [0, 1])


class BlockTests(unittest.TestCase):
    def test_each_block_has_only_its_documented_valid_targets(self):
        expected = {
            "Goat-Yoga Focus": {"Tractor Beam"},
            "Cardboard Forcefield": {"Airlock Malfunction", "Laser Blast"},
            "Tin-Foil Space Helmet": {"Space Wrench", "Hydroponic Alfalfa", "Double Trouble", "Chewed Wiring", "Space Sickness", "Quarantine Zone"},
        }
        by_name = {c.name: c for c in CARDS}
        for block_name, valid in expected.items():
            for name, card in by_name.items():
                self.assertEqual(Game.valid_block(by_name[block_name], Move(card, 0)), name in valid,
                                 (block_name, name))

    def test_valid_block_discards_both_and_cancels_effect(self):
        for action_name, block_name in (("Tractor Beam", "Goat-Yoga Focus"),
                                        ("Airlock Malfunction", "Cardboard Forcefield"),
                                        ("Laser Blast", "Cardboard Forcefield")):
            with self.subTest(action=action_name):
                g = game()
                goat = put(g, "Twin Kids", 1, "goats")
                action = put(g, action_name)
                block = put(g, block_name, 1)
                g.play(g.players[0], Move(action, 1))
                self.assertIn(goat, g.players[1].goats)
                self.assertIn(action, g.discard)
                self.assertIn(block, g.discard)
                self.assertTrue(g.acquisitions[action.uid].blocked)
                self.assertTrue(g.acquisitions[block.uid].reaction)
                self.assertEqual(g.stack, [])

    def test_helmet_blocks_negative_special(self):
        g = game()
        action = put(g, "Quarantine Zone")
        put(g, "Tin-Foil Space Helmet", 1)
        g.play(g.players[0], Move(action, 1))
        self.assertEqual(g.players[1].specials, [])
        self.assertTrue(g.acquisitions[action.uid].blocked)

    def test_helmet_blocks_wrench_removing_own_upgrade(self):
        g = game()
        upgrade = put(g, "Hydroponic Alfalfa", 1, "specials")
        wrench = put(g, "Space Wrench")
        put(g, "Tin-Foil Space Helmet", 1)
        g.play(g.players[0], Move(wrench, 1, upgrade.uid))
        self.assertIn(upgrade, g.players[1].specials)

    def test_unrelated_block_cannot_stop_attack(self):
        g = game()
        goat = put(g, "Twin Kids", 1, "goats")
        action = put(g, "Laser Blast")
        block = put(g, "Goat-Yoga Focus", 1)
        g.play(g.players[0], Move(action, 1))
        self.assertIn(goat, g.discard)
        self.assertIn(block, g.players[1].hand)

    def test_blocks_do_not_consume_the_blockers_turn(self):
        g = game()
        goat = put(g, "Twin Kids", 1, "goats")
        action = put(g, "Tractor Beam")
        put(g, "Goat-Yoga Focus", 1)
        g.play(g.players[0], Move(action, 1))
        self.assertEqual(g.players[1].turns, 0)
        self.assertEqual(g.players[1].normal_turns, 0)

    def test_third_party_can_block_leaders_upgrade(self):
        g = game(players=3)
        put(g, "The G.O.A.T.", 0, "goats")
        action = put(g, "Hydroponic Alfalfa", 0)
        block = put(g, "Tin-Foil Space Helmet", 2)
        g.play(g.players[0], Move(action, 0))
        self.assertIn(block, g.discard)
        self.assertEqual(g.players[0].specials, [])


class FinalOrbitTests(unittest.TestCase):
    def test_exhaustion_in_normal_draw_converts_current_turn(self):
        g = tiny_game(["The G.O.A.T."])
        g.normal_turn(g.players[0])
        self.assertEqual(g.final_start_seat, 0)
        self.assertEqual(g.players[0].turns, 1)
        self.assertEqual(g.players[0].normal_turns, 0)
        self.assertEqual(g.players[0].goat_total, 0)
        g.final_orbit(reuse_started_turn=True)
        self.assertEqual(g.players[0].turns, 1)
        self.assertEqual(g.players[0].goat_total, 3)
        self.assertEqual([p.final_turns for p in g.players], [1, 1])

    def test_exhaustion_in_start_phase_skips_normal_draw_and_action(self):
        g = tiny_game(["Hydroponic Alfalfa", "Twin Kids"])
        put(g, "Hydroponic Alfalfa", zone="specials")
        g.normal_turn(g.players[0])
        self.assertEqual([e.get("source") for e in g.events if e["event"] == "draw"], ["alfalfa"])
        self.assertFalse(any(e["event"] == "play" for e in g.events))
        self.assertEqual(g.final_start_seat, 0)

    def test_exhaustion_in_extra_draw_skips_hand_limit(self):
        g = tiny_game(["Cardboard Forcefield", "Goat-Yoga Focus", "Tin-Foil Space Helmet"],
                      rules=Rules(starting_hand_size=0, normal_hand_limit=0))
        put(g, "Cardboard Forcefield")
        g.normal_turn(g.players[0])
        self.assertEqual(g.final_start_seat, 0)
        self.assertEqual(len(g.players[0].hand), 3)
        self.assertEqual(g.discard, [])

    def test_final_order_and_two_actions_without_draw_or_discard(self):
        g = game(players=3)
        put(g, "Twin Kids", 1)
        put(g, "Astro-Billy", 1)
        put(g, "The G.O.A.T.", 1)
        g.final_start_seat = 1
        g.final_orbit(reuse_started_turn=False)
        starts = [e["player"] for e in g.events if e["event"] == "turn_start"]
        self.assertEqual(starts, [2, 3, 1])
        self.assertEqual(len(g.players[1].goats), 2)
        self.assertEqual(g.players[1].goat_total, 5)
        self.assertFalse(any(e["event"] in ("draw", "discard") for e in g.events))

    def test_hand_breaks_goat_tie(self):
        # Override just setup to make a complete, reproducible endgame fixture.
        g = tiny_game(["Twin Kids", "Twin Kids", "Cardboard Forcefield"])
        put(g, "Twin Kids", 0, "goats")
        put(g, "Twin Kids", 1, "goats")
        put(g, "Cardboard Forcefield", 1)
        g.final_start_seat = 0
        g.deal = lambda: None
        result = g.run()
        self.assertEqual(result.winners, (1,))

    def test_exact_tie_splits_credit(self):
        g = tiny_game(["Twin Kids", "Twin Kids"])
        put(g, "Twin Kids", 0, "goats")
        put(g, "Twin Kids", 1, "goats")
        g.final_start_seat = 0
        g.deal = lambda: None
        result = g.run()
        self.assertEqual(result.winners, (0, 1))
        self.assertEqual([p.win_credit for p in result.players], [0.5, 0.5])

    def test_setup_exhaustion_still_gives_each_player_one_final_turn(self):
        g = tiny_game(["Hyper-Jumping Nanny"], rules=Rules(starting_hand_size=5))
        result = g.run()
        self.assertEqual([p.turns for p in result.players], [1, 1])
        self.assertEqual(result.winners, (0,))

    def test_final_card_nanny_then_playable_hand_goat(self):
        g = tiny_game(["Hyper-Jumping Nanny", "Twin Kids"])
        put(g, "Twin Kids")
        result = g.run()
        self.assertEqual(result.players[0].goats, 3)


class WholeGameTests(unittest.TestCase):
    def test_seed_reproducibility_for_every_player_count(self):
        for players in range(2, 6):
            a = Game(CARDS, players, 901, start_seat=players-1, record_events=True, check_invariants=True).run()
            b = Game(CARDS, players, 901, start_seat=players-1, record_events=True, check_invariants=True).run()
            self.assertEqual(a.players, b.players)
            self.assertEqual(a.events, b.events)

    def test_games_conserve_all_cards_and_assign_final_turns(self):
        for players in range(2, 6):
            for seed in range(12):
                result = Game(CARDS, players, seed, start_seat=seed % players, check_invariants=True).run()
                self.assertEqual(len(result.acquisitions), 104)
                self.assertAlmostEqual(sum(p.win_credit for p in result.players), 1)
                self.assertTrue(all(p.final_turns == 1 for p in result.players))
                self.assertTrue(all(p.turns == p.normal_turns + 1 for p in result.players))

    def test_rules_validation(self):
        for data in ({"unknown": 1}, {"normal_hand_limit": -1}, {"allow_duplicate_specials": "yes"},
                     {"final_orbit_cards": 0}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                Rules.from_dict(data)


if __name__ == "__main__":
    unittest.main()
