"""Game rules, exact deck-exhaustion transition, reactions, and card tracking."""

import random
from typing import Any, Dict, List, Optional

from .ai import DecisionContext, PublicPlayer, SharedAI
from .models import Acquisition, Card, GameResult, Move, Player, PlayerResult, Rules


class Game:
    def __init__(self, cards: List[Card], player_count: int, seed: int, start_seat: int = 0,
                 rules: Optional[Rules] = None, record_events: bool = False,
                 check_invariants: bool = False):
        if not 2 <= player_count <= 5:
            raise ValueError("Space Goats supports 2 to 5 players.")
        if not 0 <= start_seat < player_count:
            raise ValueError("Invalid starting seat.")
        if not cards or len({card.uid for card in cards}) != len(cards):
            raise ValueError("The deck must be nonempty and card IDs must be unique.")
        self.rules = rules or Rules()
        self.rules.validate()
        self.cards = tuple(cards)
        self.seed = seed
        self.start_seat = start_seat
        self.players = [Player(seat) for seat in range(player_count)]
        self.rng = random.Random(seed)
        self.ai = SharedAI(self.rng)
        self.deck = list(cards)
        self.rng.shuffle(self.deck)
        self.discard: List[Card] = []
        self.orbital: List[Card] = []
        self.stack: List[Move] = []
        self.acquisitions: Dict[int, Acquisition] = {}
        self.events: List[Dict[str, Any]] = []
        self.record_events = record_events
        self.check_invariants = check_invariants
        self.phase = "setup"
        self.final_start_seat: Optional[int] = None
        self.current_seat = start_seat
        self.remaining_final_seats: List[int] = []
        self.actions_left = 1

    def event(self, name: str, seat: Optional[int] = None, card: Optional[Card] = None, **details: Any) -> None:
        if not self.record_events:
            return
        entry = {"event_number": len(self.events) + 1, "event": name, "phase": self.phase,
                 "player": seat + 1 if seat is not None else None,
                 "player_turn": self.players[seat].turns if seat is not None else None,
                 "deck_remaining": len(self.deck)}
        if card is not None:
            entry.update(card=card.name, card_id=card.uid)
        entry.update(details)
        self.events.append(entry)

    def context(self, seat: int) -> DecisionContext:
        return DecisionContext(seat, tuple(self.players[seat].hand), tuple(
            PublicPlayer(player.seat, tuple(player.goats), tuple(player.specials), len(player.hand))
            for player in self.players
        ), tuple(self.orbital), len(self.deck), self.rules, self.phase == "final_orbit",
            self.actions_left, tuple(self.remaining_final_seats))

    def can_add_goat(self, player: Player, from_hand: bool = False) -> bool:
        if not player.has("quarantine"):
            return True
        return not from_hand

    def draw(self, player: Player, source: str = "normal_draw") -> None:
        """Resolve an entire nanny chain, stopping at the exact final deck pop.

        Nanny auto-placement resolves for that drawn card before scoring, even
        when it is the final card. No further phase or bonus draw can proceed.
        """
        next_source = source
        while self.deck and self.final_start_seat is None:
            card = self.deck.pop()
            observation = Acquisition(card, player.seat, player.turns, next_source)
            self.acquisitions[card.uid] = observation
            self.event("draw", player.seat, card, source=next_source)
            is_nanny = (card.effect_id == "nanny" and self.phase != "setup"
                        and not player.has("quarantine"))
            if is_nanny:
                player.goats.append(card)
                observation.played_turn = player.turns
                observation.auto_play = True
                observation.resolved = True
                self.event("auto_play", player.seat, card)
            else:
                player.hand.append(card)
                if card.effect_id == "nanny" and self.phase == "setup":
                    self.event("nanny_dealt_as_goat", player.seat, card)
                elif card.effect_id == "nanny" and player.has("quarantine"):
                    self.event("nanny_quarantined", player.seat, card,
                               explanation="Kept in hand; the Nanny effect is blocked.")
            if not self.deck:
                self.final_start_seat = player.seat
                self.event("deck_exhausted", player.seat, card)
                break
            if not is_nanny:
                break
            next_source = "nanny_bonus"

    def deal(self) -> None:
        self.phase = "setup"
        self.event("game_start", self.start_seat, seed=self.seed, players=len(self.players))
        for _ in range(self.rules.starting_hand_size):
            for offset in range(len(self.players)):
                seat = (self.start_seat + offset) % len(self.players)
                self.draw(self.players[seat], "deal")
                if self.final_start_seat is not None:
                    return
        self.maybe_check()

    @staticmethod
    def find_card(cards: List[Card], uid: Optional[int]) -> Card:
        return next(card for card in cards if card.uid == uid)

    def legal_moves(self, player: Player) -> List[Move]:
        moves = []
        opponents = [other for other in self.players if other.seat != player.seat]
        for card in player.hand:
            effect = card.effect_id
            if card.card_type == "Goat":
                if self.can_add_goat(player, from_hand=True):
                    moves.append(Move(card, player.seat))
            elif card.card_type == "Special":
                for target in self.players:
                    if self.rules.allow_duplicate_specials or not target.has(effect):
                        moves.append(Move(card, target.seat))
            elif card.card_type == "Action":
                if effect == "scoop":
                    if self.orbital and self.can_add_goat(player):
                        moves.append(Move(card, player.seat))
                elif effect == "remove_modifier":
                    for target in self.players:
                        if target.seat != player.seat and player.has("sickness"):
                            continue
                        moves.extend(Move(card, target.seat, special.uid) for special in target.specials)
                elif not player.has("sickness"):
                    if effect == "steal" and not self.can_add_goat(player):
                        continue
                    for target in opponents:
                        if not target.goats:
                            continue
                        if effect == "steal":
                            moves.append(Move(card, target.seat))
                        else:
                            moves.append(Move(card, target.seat))
        return moves

    @staticmethod
    def valid_block(block: Card, move: Move) -> bool:
        if block.effect_id == "block_steal":
            return move.card.effect_id == "steal"
        if block.effect_id == "block_remove_goat":
            return move.card.effect_id in ("eject", "destroy")
        if block.effect_id == "block_modifier":
            return move.card.card_type == "Special" or move.card.effect_id == "remove_modifier"
        return False

    def mark_played(self, player: Player, card: Card, reaction: bool = False) -> None:
        observation = self.acquisitions[card.uid]
        if observation.played_turn is not None:
            raise AssertionError("A physical card cannot be played from hand twice.")
        observation.played_turn = player.turns
        observation.reaction = reaction
        self.event("block" if reaction else "play", player.seat, card,
                   waited_own_turns=observation.wait_turns)

    def play(self, player: Player, move: Move) -> None:
        if move not in self.legal_moves(player):
            raise ValueError("Illegal move.")
        player.hand.remove(move.card)
        self.mark_played(player, move.card)
        if move.card.card_type == "Goat":
            player.goats.append(move.card)
            self.acquisitions[move.card.uid].resolved = True
            self.event("goat_added", player.seat, move.card, goats=player.goat_total)
            self.maybe_check()
            return
        # Pending action is below the first reaction. Blocks are not counter-blockable.
        self.stack.append(move)
        for offset in range(1, len(self.players)):
            defender = self.players[(player.seat + offset) % len(self.players)]
            blocks = [card for card in defender.hand if self.valid_block(card, move)]
            block = self.ai.choose_block(self.context(defender.seat), move, blocks)
            if block is not None:
                defender.hand.remove(block)
                self.mark_played(defender, block, reaction=True)
                self.stack.append(Move(block, player.seat))
                self.discard.append(self.stack.pop().card)
                self.discard.append(self.stack.pop().card)
                self.acquisitions[block.uid].resolved = True
                self.acquisitions[move.card.uid].blocked = True
                self.event("blocked", player.seat, move.card, by_player=defender.seat + 1,
                           block_card=block.name, target_player=move.target_seat + 1)
                self.maybe_check()
                return
        pending = self.stack.pop()
        self.resolve(player, pending)
        self.acquisitions[move.card.uid].resolved = True
        self.maybe_check()

    def resolve(self, player: Player, move: Move) -> None:
        card = move.card
        target = self.players[move.target_seat] if move.target_seat is not None else None
        if card.card_type == "Special":
            target.specials.append(card)
            self.event("special_attached", player.seat, card, target_player=target.seat + 1)
            return
        self.discard.append(card)
        effect = card.effect_id
        if effect in ("eject", "destroy", "steal"):
            # The targeted player chooses which of their goats is affected.
            goat = self.ai.choose_goat_to_remove(target.goats)
            target.goats.remove(goat)
            if effect == "eject":
                self.orbital.append(goat)
            elif effect == "destroy":
                self.discard.append(goat)
            else:
                player.goats.append(goat)
            self.event(effect, player.seat, card, target_player=target.seat + 1,
                       affected_card=goat.name, affected_card_id=goat.uid, goat_value=goat.goat_count)
        elif effect == "scoop":
            goat_count = sum(goat.goat_count for goat in self.orbital)
            card_ids = [goat.uid for goat in self.orbital]
            player.goats.extend(self.orbital)
            self.orbital.clear()
            self.event("scoop", player.seat, card, goat_value=goat_count, affected_card_ids=card_ids)
        elif effect == "remove_modifier":
            special = self.find_card(target.specials, move.target_card_uid)
            target.specials.remove(special)
            self.discard.append(special)
            self.event("modifier_removed", player.seat, card, target_player=target.seat + 1,
                       affected_card=special.name, affected_card_id=special.uid)
        else:
            raise AssertionError(f"Unhandled action: {card.name}")

    def enforce_hand_limit(self, player: Player) -> None:
        while len(player.hand) > player.hand_limit(self.rules):
            card = self.ai.choose_discard(self.context(player.seat), self.legal_moves(player))
            player.hand.remove(card)
            self.discard.append(card)
            self.acquisitions[card.uid].discarded_turn = player.turns
            self.event("discard", player.seat, card, waited_own_turns=self.acquisitions[card.uid].wait_turns)

    def normal_turn(self, player: Player) -> None:
        self.phase = "normal"
        self.current_seat = player.seat
        self.actions_left = 1
        player.turns += 1
        self.event("turn_start", player.seat)
        # Snapshot count prevents any mid-phase change from adding extra triggers.
        alfalfa_count = sum(card.effect_id == "alfalfa" for card in player.specials)
        for _ in range(alfalfa_count):
            self.draw(player, "alfalfa")
            if self.final_start_seat is not None:
                return
        self.draw(player)
        if self.final_start_seat is not None:
            return
        action_slots = 2 if player.has("double_trouble") else 1
        self.actions_left = action_slots
        for action_index in range(action_slots):
            self.actions_left = action_slots - action_index
            move = self.ai.choose_move(self.context(player.seat), self.legal_moves(player))
            if move is None:
                if action_index == 0:
                    self.draw(player, "extra_draw")
                    if self.final_start_seat is not None:
                        return
                break
            self.play(player, move)
        self.enforce_hand_limit(player)
        player.normal_turns += 1
        self.event("turn_end", player.seat, goats=player.goat_total, hand_cards=len(player.hand))
        self.maybe_check()

    def final_orbit(self, reuse_started_turn: bool) -> None:
        self.phase = "final_orbit"
        self.remaining_final_seats = [(self.final_start_seat + offset) % len(self.players)
                                      for offset in range(len(self.players))]
        self.event("final_orbit_start", self.final_start_seat)
        for offset, seat in enumerate(tuple(self.remaining_final_seats)):
            player = self.players[seat]
            self.current_seat = seat
            if offset != 0 or not reuse_started_turn:
                player.turns += 1
            self.actions_left = self.rules.final_orbit_cards
            self.event("turn_start", seat)
            while self.actions_left > 0:
                move = self.ai.choose_move(self.context(seat), self.legal_moves(player))
                if move is None:
                    self.event("pass", seat)
                    break
                self.play(player, move)
                self.actions_left -= 1
            player.final_turns += 1
            self.remaining_final_seats.remove(seat)
            self.event("turn_end", seat, goats=player.goat_total, hand_cards=len(player.hand))
            self.maybe_check()

    def run(self) -> GameResult:
        self.deal()
        seat = self.start_seat
        reuse_started_turn = False
        while self.final_start_seat is None:
            self.normal_turn(self.players[seat])
            if self.final_start_seat is not None:
                reuse_started_turn = True
                break
            seat = (seat + 1) % len(self.players)
        self.final_orbit(reuse_started_turn)
        best_goats = max(player.goat_total for player in self.players)
        tied = [player for player in self.players if player.goat_total == best_goats]
        best_hand = max(len(player.hand) for player in tied)
        winners = tuple(player.seat for player in tied if len(player.hand) == best_hand)
        result_players = [PlayerResult(
            player.seat, player.turns, player.normal_turns, player.final_turns, player.goat_total,
            len(player.goats), len(player.hand), 1.0 / len(winners) if player.seat in winners else 0.0,
            player.seat in winners, len(winners) == 1 and player.seat in winners
        ) for player in self.players]
        for observation in self.acquisitions.values():
            observation.game_end_turn = self.players[observation.player_seat].turns
        self.phase = "finished"
        self.event("game_end", winners=[seat + 1 for seat in winners],
                   scores=[player.goat_total for player in self.players],
                   hand_sizes=[len(player.hand) for player in self.players])
        self.assert_invariants()
        if len(self.acquisitions) != len(self.cards):
            raise AssertionError("Every deck card must have an acquisition record.")
        if any(player.turns != player.normal_turns + 1 or player.final_turns != 1 for player in self.players):
            raise AssertionError("Each player must receive exactly one Final Orbit turn.")
        return GameResult(self.seed, self.start_seat, self.final_start_seat, winners, result_players,
                          list(self.acquisitions.values()), self.events,
                          sum(card.goat_count for card in self.orbital), len(self.discard))

    def maybe_check(self) -> None:
        if self.check_invariants:
            self.assert_invariants()

    def assert_invariants(self) -> None:
        physical = list(self.deck) + self.discard + self.orbital + [move.card for move in self.stack]
        for player in self.players:
            physical.extend(player.hand + player.goats + player.specials)
            if any(card.card_type != "Goat" for card in player.goats):
                raise AssertionError("Only Goat cards can be in a spaceship's goat area.")
            if any(card.card_type != "Special" for card in player.specials):
                raise AssertionError("Only Special cards can be attached as modifiers.")
        if sorted(card.uid for card in physical) != sorted(card.uid for card in self.cards):
            raise AssertionError("A card was duplicated, lost, or invented.")
        if any(card.card_type != "Goat" for card in self.orbital):
            raise AssertionError("Only Goat cards can be in orbit.")
