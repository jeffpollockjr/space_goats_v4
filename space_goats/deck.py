"""Read the original deck format: every CSV row is one physical card."""

import csv
from pathlib import Path
from typing import List

from .models import Card, KNOWN_CARDS


def load_deck(path: Path) -> List[Card]:
    cards = []
    definitions = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"Card Type", "Card Name", "Goat Count", "Effect", "Quip"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Deck CSV must contain: " + ", ".join(sorted(required)))
        for line, row in enumerate(reader, start=2):
            name = row["Card Name"].strip()
            card_type = row["Card Type"].strip()
            if name not in KNOWN_CARDS:
                raise ValueError(f"Line {line}: no effect implementation for {name!r}.")
            expected_type, effect_id = KNOWN_CARDS[name]
            if card_type != expected_type:
                raise ValueError(f"Line {line}: {name} must have type {expected_type}.")
            try:
                count = int(row["Goat Count"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Line {line}: Goat Count must be an integer.") from exc
            if (card_type == "Goat" and not 1 <= count <= 3) or (card_type != "Goat" and count != 0):
                raise ValueError(f"Line {line}: invalid Goat Count for {card_type}.")
            definition = (card_type, count, row["Effect"])
            if name in definitions and definitions[name] != definition:
                raise ValueError(f"Line {line}: conflicting definitions for {name}.")
            definitions[name] = definition
            cards.append(Card(len(cards), card_type, name, count, effect_id, row["Effect"], row["Quip"]))
    if not cards:
        raise ValueError("Deck CSV is empty.")
    return cards
