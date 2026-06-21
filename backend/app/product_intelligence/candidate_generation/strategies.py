from __future__ import annotations

from dataclasses import dataclass
from re import findall
from typing import Iterable


def tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    return [token for token in findall(r"[a-z0-9]+", text.lower()) if token]


def unique_tokens(*values: str | None) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        tokens.update(tokenize(value))
    return tokens


def quantity_hints(text: str | None) -> set[str]:
    tokens = tokenize(text)
    hints: set[str] = set()
    for token in tokens:
        if token.isdigit() or token in {"ml", "l", "ltr", "litre", "litres", "g", "kg"}:
            hints.add(token)
    patterns = findall(r"\d+\s*x\s*\d+", (text or "").lower())
    hints.update(pattern.replace(" ", "") for pattern in patterns)
    if "pack" in tokens:
        hints.add("pack")
    return hints


def overlap_size(left: Iterable[str], right: Iterable[str]) -> int:
    return len(set(left) & set(right))


@dataclass(frozen=True, slots=True)
class CandidateSignal:
    """Deterministic evidence extracted from a candidate comparison."""

    brand_overlap: int
    family_overlap: int
    category_overlap: int
    quantity_overlap: int

    @property
    def total(self) -> int:
        return (
            self.brand_overlap
            + self.family_overlap
            + self.category_overlap
            + self.quantity_overlap
        )

