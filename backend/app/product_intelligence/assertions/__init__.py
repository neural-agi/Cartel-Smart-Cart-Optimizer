"""Canonical assertion contracts for product intelligence."""

from app.product_intelligence.assertions.interfaces import AssertionManager
from app.product_intelligence.assertions.service import DeterministicAssertionManager
from app.product_intelligence.assertions.types import (
    AssertionUpdateRequest,
    AssertionUpdateResponse,
)

__all__ = [
    "AssertionManager",
    "AssertionUpdateRequest",
    "AssertionUpdateResponse",
    "DeterministicAssertionManager",
]
