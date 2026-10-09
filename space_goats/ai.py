"""One symmetric heuristic for every seat; opponents' hands are never exposed.

The AI is intentionally a baseline, not a claim of optimal play. All random
choices use the game's seeded RNG. The weights below are the strategy knobs.
"""

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .models import Card, Move, Rules


@dataclass(frozen=True)
class PublicPlayer:
    seat: int
    goats: Tuple[Card, ...]
    specials: Tuple[Card, ...]
    hand_size: int

    @property
    def goat_total(self) -> int:
        return sum(card.goat_count for card in self.goats)

    def has(self, effect_id: str) -> bool:
        return any(card.effect_id == effect_id for card in self.specials)


@dataclass(frozen=True)
class DecisionContext:
    seat: int
    hand: Tuple[Card, ...]
    players: Tuple[PublicPlayer, ...]
    orbital: Tuple[Card, ...]
    deck_remaining: int
    rules: Rules
    final_orbit: bool
    actions_left: int
    remaining_final_seats: Tuple[int, ...]

    @property
    def me(self) -> PublicPlayer:
        return self.players[self.seat]


class SharedAI:
    """Identical policy and small random tie-breaking noise for all players."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    @staticmethod
    def relevance(context: DecisionContext, seat: int) -> float:
        leader = max(player.goat_total for player in context.players)
        return 0.35 + 0.65 * (context.players[seat].goat_total + 3) / (leader + 3)

    @staticmethod
    def future_turns(context: DecisionContext, seat: int) -> float:
        if context.final_orbit:
            if seat == context.seat:
                return 1.0 if context.actions_left > 1 else 0.0
            return 1.0 if seat in context.remaining_final_seats else 0.0
        return min(8.0, context.deck_remaining / (len(context.players) * 1.6) + 0.5)

    def score(self, context: DecisionContext, move: Move) -> float:
        card = move.card
        effect = card.effect_id
        target = context.players[move.target_seat] if move.target_seat is not None else None
        if card.card_type == "Goat":
            return float(card.goat_count)
        if effect == "scoop":
            return float(sum(goat.goat_count for goat in context.orbital))
        if effect in ("steal", "eject", "destroy"):
            goat = next(goat for goat in target.goats if goat.uid == move.target_card_uid)
            attack_value = goat.goat_count * self.relevance(context, target.seat) * 0.8
            return attack_value + (goat.goat_count if effect == "steal" else 0.0)
        if effect == "remove_modifier":
            special = next(special for special in target.specials if special.uid == move.target_card_uid)
            horizon = self.future_turns(context, target.seat)
            if target.seat == context.seat:
                if special.effect_id == "alfalfa":
                    return -1.0
                if context.final_orbit and special.effect_id == "wiring":
                    return -0.1
                if horizon == 0:
                    return -0.1
                if special.effect_id == "quarantine":
                    hand_goats = sum(item.goat_count for item in context.hand if item.card_type == "Goat")
                    return 1.7 + min(4.0, hand_goats * 0.8) + min(2.0, horizon * 0.25)
                if special.effect_id == "sickness":
                    hand_actions = sum(item.effect_id in ("steal", "eject", "destroy") for item in context.hand)
                    return 0.6 + min(2.5, hand_actions * 0.9) + horizon * 0.1
                return 0.3 + min(1.5, horizon * 0.25)
            if special.effect_id == "alfalfa":
                if context.final_orbit:
                    return -0.1
                return min(3.2, horizon * 0.45) * self.relevance(context, target.seat)
            return -1.0
        if card.card_type == "Special":
            horizon = self.future_turns(context, target.seat)
            if horizon == 0:
                return -0.1
            if effect == "alfalfa":
                if target.seat != context.seat or context.final_orbit:
                    return -1.0
                return min(3.8, horizon * 0.5)
            if context.final_orbit and effect == "wiring":
                return -0.1
            if target.seat == context.seat:
                return -1.0
            strength = {"quarantine": 0.75, "sickness": 0.45, "wiring": 0.32}[effect]
            return min(3.3, horizon * strength) * self.relevance(context, target.seat)
        return -1.0

    def choose_move(self, context: DecisionContext, moves: List[Move]) -> Optional[Move]:
        worthwhile = [(self.score(context, move), move) for move in moves]
        worthwhile = [(score, move) for score, move in worthwhile if score > 0]
        if not worthwhile:
            return None  # Extra draw in normal play; keep hand for ties in Final Orbit.
        return max(worthwhile, key=lambda pair: pair[0] + self.rng.uniform(-0.12, 0.12))[1]

    def choose_block(self, context: DecisionContext, pending: Move, blocks: List[Card]) -> Optional[Card]:
        if not blocks:
            return None
        effect = pending.card.effect_id
        target = context.players[pending.target_seat] if pending.target_seat is not None else None
        protect_self = False
        if target is not None and target.seat == context.seat:
            if effect in ("steal", "eject", "destroy"):
                protect_self = True
            elif pending.card.card_type == "Special":
                protect_self = effect != "alfalfa"
            elif effect == "remove_modifier":
                protect_self = any(card.uid == pending.target_card_uid and card.effect_id == "alfalfa"
                                   for card in target.specials)
                protect_self = protect_self and not context.final_orbit
        if protect_self:
            return self.rng.choice(blocks)
        # Public-information defense against a leader's positive modifier.
        leader = max(player.goat_total for player in context.players)
        gains_upgrade = target is not None and target.seat != context.seat and (
            effect == "alfalfa" or (
                effect == "remove_modifier" and any(
                    card.uid == pending.target_card_uid and card.effect_id != "alfalfa"
                    for card in target.specials
                )
            )
        )
        if gains_upgrade and target.goat_total >= leader and leader > context.me.goat_total:
            if self.future_turns(context, target.seat) > 0:
                return self.rng.choice(blocks)
        return None

    def choose_discard(self, context: DecisionContext, moves: List[Move]) -> Card:
        """Keep valuable goats, useful actions, and a modest defensive reserve."""
        scores = {}
        for move in moves:
            scores[move.card.uid] = max(scores.get(move.card.uid, -1.0), self.score(context, move))
        def keep_value(card: Card) -> float:
            if card.card_type == "Block":
                duplicates = sum(other.effect_id == card.effect_id for other in context.hand)
                value = 0.55 if context.me.goats else 0.25
                if card.effect_id == "block_modifier":
                    value = 0.6
                return value / duplicates
            if card.card_type == "Goat":
                return card.goat_count * (0.8 if context.me.has("quarantine") else 1.0)
            return max(0.05, scores.get(card.uid, 0.05))
        return min(context.hand, key=lambda card: keep_value(card) + self.rng.uniform(-0.05, 0.05))
