"""Tests for the governed quantity/pack semantics boundary.

These tests verify that VariantQuantityResolutionService correctly determines
whether a requested canonical Variant quantity maps deterministically to
platform listing units, WITHOUT performing unit conversion, pack equivalence,
or commercial equivalence inference.

See: docs/variant_quantity_normalization_contract.md
See: docs/pack_equivalence_governance.md §"Boundaries of equivalence"
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from app.cart_optimization.quantity_semantics import (
    QuantityResolutionStatus,
    VariantQuantityResolutionService,
    VariantQuantitySemantics,
)
from app.product_intelligence.models import PackConfiguration, PackKind


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _MockAllocation(BaseModel):
    """Lightweight allocation mock matching CandidateItemAllocation's shape
    for resolve_from_allocation testing."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    canonical_variant_id: str
    quantity: int
    retailer_id: str
    checkout_group_id: str


def _pack(
    pack_kind: PackKind = PackKind.single_unit,
    consumer_unit_count: int | None = 1,
    status: str = "complete",
) -> PackConfiguration:
    return PackConfiguration(
        pack_kind=pack_kind,
        consumer_unit_count=consumer_unit_count,
        pack_configuration_status=status,
    )


_SERVICE = VariantQuantityResolutionService()


# ---------------------------------------------------------------------------
# RESOLVED cases (deterministic 1:1 mapping)
# ---------------------------------------------------------------------------


def test_single_unit_complete_resolves_with_1_to_1_listing_units() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-1",
        requested_quantity=3,
        pack_configuration=_pack(PackKind.single_unit, 1, "complete"),
    )

    assert semantics.status is QuantityResolutionStatus.RESOLVED
    assert semantics.resolved_listing_units == 3
    assert semantics.pack_kind is PackKind.single_unit
    assert "listing unit" in semantics.rationale[0]


def test_multipack_complete_resolves_with_1_to_1_listing_units() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-2",
        requested_quantity=5,
        pack_configuration=_pack(PackKind.multipack, 6, "complete"),
    )

    assert semantics.status is QuantityResolutionStatus.RESOLVED
    assert semantics.resolved_listing_units == 5
    assert "listing unit" in semantics.rationale[0]


def test_resolved_semantics_is_serializable_to_json() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-3",
        requested_quantity=2,
        pack_configuration=_pack(PackKind.single_unit, 1, "complete"),
        listing_quantity_text="500 ml",
    )

    dumped = semantics.model_dump(mode="json")
    assert dumped["status"] == "resolved"
    assert dumped["resolved_listing_units"] == 2
    assert dumped["listing_quantity_text"] == "500 ml"


def test_resolved_semantics_is_immutable() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-4",
        requested_quantity=1,
        pack_configuration=_pack(PackKind.single_unit, 1, "complete"),
    )

    with pytest.raises((TypeError, ValueError)):
        semantics.resolved_listing_units = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# UNRESOLVED cases (cannot determine listing-unit mapping)
# ---------------------------------------------------------------------------


def test_no_pack_configuration_is_unresolved() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-5",
        requested_quantity=2,
        pack_configuration=None,
    )

    assert semantics.status is QuantityResolutionStatus.UNRESOLVED
    assert semantics.resolved_listing_units is None
    assert semantics.pack_kind is PackKind.unknown


def test_partial_pack_configuration_is_unresolved() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-6",
        requested_quantity=2,
        pack_configuration=_pack(PackKind.single_unit, 1, "partial"),
    )

    assert semantics.status is QuantityResolutionStatus.UNRESOLVED
    assert semantics.resolved_listing_units is None
    assert "partial" in semantics.rationale[0]


def test_unknown_pack_kind_is_unresolved() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-7",
        requested_quantity=2,
        pack_configuration=_pack(PackKind.unknown, None, "unknown"),
    )

    assert semantics.status is QuantityResolutionStatus.UNRESOLVED
    assert semantics.resolved_listing_units is None


def test_requires_review_status_is_unresolved() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-8",
        requested_quantity=2,
        pack_configuration=_pack(PackKind.multipack, 6, "requires_review"),
    )

    assert semantics.status is QuantityResolutionStatus.UNRESOLVED
    assert "requires_review" in semantics.rationale[0]


# ---------------------------------------------------------------------------
# UNSUPPORTED cases (no scalar listing-unit mapping possible)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pack_kind", [PackKind.combo, PackKind.assortment])
def test_combo_and_assortment_are_unsupported(pack_kind: PackKind) -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-9",
        requested_quantity=2,
        pack_configuration=_pack(pack_kind, 3, "complete"),
    )

    assert semantics.status is QuantityResolutionStatus.UNSUPPORTED
    assert semantics.resolved_listing_units is None
    assert pack_kind.value in semantics.rationale[0]


# ---------------------------------------------------------------------------
# Fail-closed: invalid inputs
# ---------------------------------------------------------------------------


def test_empty_variant_id_raises_value_error() -> None:
    with pytest.raises(ValueError, match="canonical_variant_id is required"):
        _SERVICE.resolve(
            canonical_variant_id="",
            requested_quantity=1,
            pack_configuration=_pack(PackKind.single_unit, 1, "complete"),
        )


def test_whitespace_variant_id_raises_value_error() -> None:
    with pytest.raises(ValueError, match="canonical_variant_id is required"):
        _SERVICE.resolve(
            canonical_variant_id="   ",
            requested_quantity=1,
            pack_configuration=_pack(PackKind.single_unit, 1, "complete"),
        )


@pytest.mark.parametrize("qty", [0, -1, -5])
def test_non_positive_quantity_raises_value_error(qty: int) -> None:
    with pytest.raises(ValueError, match="requested_quantity must be positive"):
        _SERVICE.resolve(
            canonical_variant_id="variant-10",
            requested_quantity=qty,
            pack_configuration=_pack(PackKind.single_unit, 1, "complete"),
        )


# ---------------------------------------------------------------------------
# resolve_from_allocation: integration with allocation shape
# ---------------------------------------------------------------------------


def test_resolve_from_allocation_maps_allocation_quantity() -> None:
    allocation = _MockAllocation(
        item_id="item-1",
        canonical_variant_id="variant-alloc-1",
        quantity=4,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
    )

    semantics = _SERVICE.resolve_from_allocation(
        allocation=allocation,
        pack_configuration=_pack(PackKind.multipack, 12, "complete"),
        listing_quantity_text="12 x 200 ml",
    )

    assert semantics.status is QuantityResolutionStatus.RESOLVED
    assert semantics.resolved_listing_units == 4
    assert semantics.canonical_variant_id == "variant-alloc-1"
    assert semantics.requested_quantity == 4
    assert semantics.listing_quantity_text == "12 x 200 ml"


def test_resolve_from_allocation_unresolved_when_no_pack_config() -> None:
    allocation = _MockAllocation(
        item_id="item-2",
        canonical_variant_id="variant-alloc-2",
        quantity=1,
        retailer_id="BLINKIT",
        checkout_group_id="checkout-1",
    )

    semantics = _SERVICE.resolve_from_allocation(
        allocation=allocation,
        pack_configuration=None,
    )

    assert semantics.status is QuantityResolutionStatus.UNRESOLVED
    assert semantics.resolved_listing_units is None


# ---------------------------------------------------------------------------
# Deterministic serialization
# ---------------------------------------------------------------------------


def test_repeated_resolution_is_deterministic() -> None:
    pack_cfg = _pack(PackKind.single_unit, 1, "complete")

    first = _SERVICE.resolve(
        canonical_variant_id="variant-det-1",
        requested_quantity=2,
        pack_configuration=pack_cfg,
    )
    second = _SERVICE.resolve(
        canonical_variant_id="variant-det-1",
        requested_quantity=2,
        pack_configuration=pack_cfg,
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Rationale captures decision chain
# ---------------------------------------------------------------------------


def test_resolved_rationale_explains_1_to_1_mapping() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-r-1",
        requested_quantity=1,
        pack_configuration=_pack(PackKind.single_unit, 1, "complete"),
    )

    assert len(semantics.rationale) >= 1
    assert any("listing unit" in r for r in semantics.rationale)
    assert any("complete" in r for r in semantics.rationale)


def test_unsupported_rationale_explains_no_scalar_mapping() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-r-2",
        requested_quantity=1,
        pack_configuration=_pack(PackKind.assortment, 1, "complete"),
    )

    assert len(semantics.rationale) >= 1
    assert any("assortment" in r for r in semantics.rationale)


def test_unresolved_rationale_explains_configuration_gap() -> None:
    semantics = _SERVICE.resolve(
        canonical_variant_id="variant-r-3",
        requested_quantity=1,
        pack_configuration=_pack(PackKind.single_unit, None, "partial"),
    )

    assert len(semantics.rationale) >= 1
    assert any("partial" in r for r in semantics.rationale)
