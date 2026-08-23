from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.product_intelligence.models import PackConfiguration, PackKind

if TYPE_CHECKING:
    from app.cart_optimization.types import CandidateItemAllocation


class QuantityResolutionStatus(StrEnum):
    """Outcome of resolving requested Variant quantity to platform listing units."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    UNSUPPORTED = "unsupported"


class VariantQuantitySemantics(BaseModel):
    """Immutable record of how a requested canonical Variant quantity maps
    to platform listing units.

    This contract does NOT perform unit conversion, pack equivalence, or
    commercial equivalence inference. It only determines whether the
    relationship between requested variant units and listing units can
    be safely established given the canonical variant's governed
    PackConfiguration.

    When ``status`` is ``RESOLVED``, ``resolved_listing_units`` holds the
    deterministic 1:1 count of platform listing units required.
    When ``status`` is ``UNRESOLVED`` or ``UNSUPPORTED``,
    ``resolved_listing_units`` is ``None`` and the caller must not
    assume a listing-unit count.
    """

    model_config = ConfigDict(frozen=True)

    canonical_variant_id: str
    requested_quantity: int
    pack_kind: PackKind
    consumer_unit_count: int | None
    pack_configuration_status: str
    listing_quantity_text: str | None
    resolved_listing_units: int | None
    status: QuantityResolutionStatus
    rationale: tuple[str, ...] = Field(default_factory=tuple)


class VariantQuantityResolutionService:
    """Resolve canonical Variant requested quantity into platform listing units.

    Resolution rules (all fail-closed):

    * ``single_unit`` + ``complete``: each requested variant unit equals one
      platform listing unit (1:1). ``resolved_listing_units = requested_quantity``.
    * ``multipack`` + ``complete``: each requested variant unit equals one
      platform listing unit (the listing IS the multipack).
      ``resolved_listing_units = requested_quantity``.
    * ``combo`` / ``assortment``: ``UNSUPPORTED`` -- component-level
      commercial structure does not support a scalar listing-unit mapping.
    * ``unknown`` pack kind or non-``complete`` configuration: ``UNRESOLVED``.
    * No ``PackConfiguration``: ``UNRESOLVED``.

    The service does NOT parse ``listing_quantity_text``, perform unit
    conversion, or infer commercial equivalence. The listing quantity text
    is recorded only for provenance.
    """

    def resolve(
        self,
        *,
        canonical_variant_id: str,
        requested_quantity: int,
        pack_configuration: PackConfiguration | None,
        listing_quantity_text: str | None = None,
    ) -> VariantQuantitySemantics:
        if not canonical_variant_id.strip():
            raise ValueError("canonical_variant_id is required")
        if requested_quantity <= 0:
            raise ValueError("requested_quantity must be positive")

        if pack_configuration is None:
            return self._unresolved(
                canonical_variant_id,
                requested_quantity,
                PackKind.unknown,
                None,
                "unknown",
                listing_quantity_text,
                "no PackConfiguration is available for the canonical Variant; "
                "listing-unit mapping cannot be established",
            )

        pack_kind = pack_configuration.pack_kind
        status_str = pack_configuration.pack_configuration_status

        if pack_kind in (PackKind.combo, PackKind.assortment):
            return VariantQuantitySemantics(
                canonical_variant_id=canonical_variant_id,
                requested_quantity=requested_quantity,
                pack_kind=pack_kind,
                consumer_unit_count=pack_configuration.consumer_unit_count,
                pack_configuration_status=status_str,
                listing_quantity_text=listing_quantity_text,
                resolved_listing_units=None,
                status=QuantityResolutionStatus.UNSUPPORTED,
                rationale=(
                    f"{pack_kind.value} pack: component-level commercial structure "
                    "does not support a scalar listing-unit mapping",
                ),
            )

        if pack_kind is PackKind.unknown:
            return self._unresolved(
                canonical_variant_id,
                requested_quantity,
                pack_kind,
                pack_configuration.consumer_unit_count,
                status_str,
                listing_quantity_text,
                f"unknown pack kind (configuration_status={status_str}): "
                "cannot determine listing-unit relationship",
            )

        if status_str != "complete":
            return self._unresolved(
                canonical_variant_id,
                requested_quantity,
                pack_kind,
                pack_configuration.consumer_unit_count,
                status_str,
                listing_quantity_text,
                f"{pack_kind.value} pack with pack_configuration_status={status_str}: "
                "complete configuration required for 1:1 listing-unit resolution",
            )

        return VariantQuantitySemantics(
            canonical_variant_id=canonical_variant_id,
            requested_quantity=requested_quantity,
            pack_kind=pack_kind,
            consumer_unit_count=pack_configuration.consumer_unit_count,
            pack_configuration_status=status_str,
            listing_quantity_text=listing_quantity_text,
            resolved_listing_units=requested_quantity,
            status=QuantityResolutionStatus.RESOLVED,
            rationale=(
                f"{pack_kind.value} pack with complete configuration: "
                "each requested variant unit equals one platform listing unit",
            ),
        )

    def resolve_from_allocation(
        self,
        *,
        allocation: "CandidateItemAllocation",
        pack_configuration: PackConfiguration | None,
        listing_quantity_text: str | None = None,
    ) -> VariantQuantitySemantics:
        """Convenience entry point: resolve semantics from a candidate
        allocation paired with the canonical variant's pack configuration.
        """
        return self.resolve(
            canonical_variant_id=allocation.canonical_variant_id,
            requested_quantity=allocation.quantity,
            pack_configuration=pack_configuration,
            listing_quantity_text=listing_quantity_text,
        )

    @staticmethod
    def _unresolved(
        canonical_variant_id: str,
        requested_quantity: int,
        pack_kind: PackKind,
        consumer_unit_count: int | None,
        pack_configuration_status: str,
        listing_quantity_text: str | None,
        reason: str,
    ) -> VariantQuantitySemantics:
        return VariantQuantitySemantics(
            canonical_variant_id=canonical_variant_id,
            requested_quantity=requested_quantity,
            pack_kind=pack_kind,
            consumer_unit_count=consumer_unit_count,
            pack_configuration_status=pack_configuration_status,
            listing_quantity_text=listing_quantity_text,
            resolved_listing_units=None,
            status=QuantityResolutionStatus.UNRESOLVED,
            rationale=(reason,),
        )
