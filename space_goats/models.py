"""Data shared by the game, AI, and reporting code."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


KNOWN_CARDS = {
    "Astro-Billy": ("Goat", "goat"),
    "Twin Kids": ("Goat", "goat"),
    "The G.O.A.T.": ("Goat", "goat"),
    "Hyper-Jumping Nanny": ("Goat", "nanny"),
    "Airlock Malfunction": ("Action", "eject"),
    "Laser Blast": ("Action", "destroy"),
    "Tractor Beam": ("Action", "steal"),
    "Orbital Vacuum": ("Action", "scoop"),
    "Space Wrench": ("Action", "remove_modifier"),
    "Goat-Yoga Focus": ("Block", "block_steal"),
    "Cardboard Forcefield": ("Block", "block_remove_goat"),
    "Tin-Foil Space Helmet": ("Block", "block_modifier"),
    "Hydroponic Alfalfa": ("Special", "alfalfa"),
    "Double Trouble": ("Special", "double_trouble"),
    "Chewed Wiring": ("Special", "wiring"),
    "Space Sickness": ("Special", "sickness"),
    "Quarantine Zone": ("Special", "quarantine"),
}


@dataclass(frozen=True)
class Card:
    uid: int
    card_type: str
    name: str
    goat_count: int
    effect_id: str
    effect_text: str = ""
    quip: str = ""


@dataclass(frozen=True)
class Rules:
    starting_hand_size: int = 5
    normal_hand_limit: int = 5
    chewed_hand_limit: int = 3
    allow_duplicate_specials: bool = False
    final_orbit_cards: int = 2

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rules":
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError("Unknown rule(s): " + ", ".join(sorted(unknown)))
        result = cls(**data)
        result.validate()
        return result

    def validate(self) -> None:
        for name in ("starting_hand_size", "normal_hand_limit", "chewed_hand_limit", "final_orbit_cards"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"Rule {name} must be a nonnegative integer.")
        if self.final_orbit_cards < 1:
            raise ValueError("final_orbit_cards must be at least 1.")
        for name in ("allow_duplicate_specials",):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"Rule {name} must be true or false.")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Player:
    seat: int
    hand: List[Card] = field(default_factory=list)
    goats: List[Card] = field(default_factory=list)
    specials: List[Card] = field(default_factory=list)
    turns: int = 0
    normal_turns: int = 0
    final_turns: int = 0

    @property
    def name(self) -> str:
        return f"Player {self.seat + 1}"

    @property
    def goat_total(self) -> int:
        return sum(card.goat_count for card in self.goats)

    def has(self, effect_id: str) -> bool:
        return any(card.effect_id == effect_id for card in self.specials)

    def hand_limit(self, rules: Rules) -> int:
        return rules.chewed_hand_limit if self.has("wiring") else rules.normal_hand_limit


@dataclass(frozen=True)
class Move:
    card: Card
    target_seat: Optional[int] = None
    target_card_uid: Optional[int] = None


@dataclass
class Acquisition:
    """A physical card is acquired from the deck once; discard is never recycled."""

    card: Card
    player_seat: int
    acquired_turn: int
    source: str
    played_turn: Optional[int] = None
    discarded_turn: Optional[int] = None
    auto_play: bool = False
    reaction: bool = False
    blocked: bool = False
    resolved: bool = False
    game_end_turn: int = 0

    @property
    def wait_turns(self) -> int:
        end = self.played_turn
        if end is None:
            end = self.discarded_turn
        if end is None:
            end = self.game_end_turn
        return max(0, end - self.acquired_turn)

    @property
    def outcome(self) -> str:
        if self.played_turn is not None:
            return "played"
        if self.discarded_turn is not None:
            return "discarded_unplayed"
        return "left_in_hand"


@dataclass(frozen=True)
class PlayerResult:
    seat: int
    turns: int
    normal_turns: int
    final_turns: int
    goats: int
    goat_cards: int
    hand_cards: int
    win_credit: float
    is_winner: bool
    outright_win: bool


@dataclass
class GameResult:
    seed: int
    start_seat: int
    final_start_seat: int
    winners: Tuple[int, ...]
    players: List[PlayerResult]
    acquisitions: List[Acquisition]
    events: List[Dict[str, Any]]
    ending_orbit_goats: int
    ending_discard_cards: int
