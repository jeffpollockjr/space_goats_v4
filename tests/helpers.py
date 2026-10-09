from dataclasses import replace
from pathlib import Path

from space_goats.deck import load_deck
from space_goats.engine import Game
from space_goats.models import Acquisition, Rules

ROOT = Path(__file__).resolve().parent.parent
CARDS = load_deck(ROOT / "data" / "deck.csv")
BY_NAME = {card.name: card for card in CARDS}


def game(players=2, rules=None):
    return Game(CARDS, players, 123, rules=rules or Rules(starting_hand_size=0),
                record_events=True, check_invariants=True)


def tiny_game(names, rules=None, players=2):
    cards = [replace(BY_NAME[name], uid=index) for index, name in enumerate(names)]
    return Game(cards, players, 12, rules=rules or Rules(starting_hand_size=0),
                record_events=True, check_invariants=True)


def put(g, name, seat=0, zone="hand"):
    card = next(card for card in g.deck if card.name == name)
    g.deck.remove(card)
    player = g.players[seat]
    getattr(player, zone).append(card)
    record = Acquisition(card, seat, player.turns, "test_setup")
    if zone != "hand":
        record.played_turn = player.turns
        record.resolved = True
    g.acquisitions[card.uid] = record
    return card
