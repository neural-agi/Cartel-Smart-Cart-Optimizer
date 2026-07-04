from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.product_intelligence.assertions import DeterministicAssertionManager
from app.product_intelligence.assertions.types import AssertionUpdateRequest
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    EvidenceReference,
    IdentityStatus,
    Measurement,
    PackConfiguration,
    PackKind,
    Product,
    ProductLifecycleStatus,
    ProductVariant,
    QuantityDimension,
    VariantLifecycleStatus,
)


def _run(coro):
    return asyncio.run(coro)


def _evidence(
    source_type: str,
    source_id: str,
    *,
    capture_timestamp: datetime | None = None,
    note: str | None = None,
) -> EvidenceReference:
    return EvidenceReference(
        source_type=source_type,
        source_id=source_id,
        capture_timestamp=capture_timestamp,
        note=note,
    )


def _measurement(amount: str, unit: str, dimension: QuantityDimension) -> Measurement:
    return Measurement(
        value=Decimal(amount),
        unit=unit,
        dimension=dimension,
        content_basis="net_content",
        assertion_status="asserted",
    )


def _product(
    product_id: str = "product-1",
    *,
    lifecycle_status: ProductLifecycleStatus = ProductLifecycleStatus.active,
    evidence_references: list[EvidenceReference] | None = None,
) -> Product:
    return Product(
        canonical_product_id=product_id,
        product_identity_status=IdentityStatus.established,
        brand_reference=BrandReference(
            canonical_brand_name="Amul",
            display_label="Amul",
            is_unknown=False,
            evidence_references=[
                _evidence("brand", "brand-1", note="brand-reference")
            ],
        ),
        product_type="milk",
        canonical_display_name="Amul Taaza Milk",
        identity_attributes=[
            AttributeAssertion(
                name="milk_type",
                value="toned",
                role="identity_critical",
                evidence_references=[_evidence("attribute", "attribute-1")],
            )
        ],
        descriptive_attributes=[
            AttributeAssertion(
                name="packaging_claim",
                value="fresh",
                role="descriptive",
                evidence_references=[_evidence("attribute", "attribute-2")],
            )
        ],
        canonical_category_reference=CategoryReference(
            category_id="dairy-milk",
            category_path="dairy/milk",
            taxonomy_version="v1",
            review_state="approved",
        ),
        lifecycle_status=lifecycle_status,
        catalog_revision="rev-1",
        evidence_references=evidence_references
        if evidence_references is not None
        else [_evidence("product", "product-1", note="product-reference")],
    )


def _variant(
    variant_id: str = "variant-1",
    *,
    product_id: str = "product-1",
    lifecycle_status: VariantLifecycleStatus = VariantLifecycleStatus.active,
    evidence_references: list[EvidenceReference] | None = None,
    component_evidence: list[EvidenceReference] | None = None,
) -> ProductVariant:
    return ProductVariant(
        canonical_variant_id=variant_id,
        canonical_product_id=product_id,
        variant_identity_status=IdentityStatus.established,
        variant_identity_attributes=[
            AttributeAssertion(
                name="fat_content",
                value="toned",
                role="identity_critical",
                evidence_references=[
                    _evidence("variant_attribute", "variant-attribute-1")
                ],
            )
        ],
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit,
            consumer_unit_count=1,
            content_per_consumer_unit=_measurement("500", "ml", QuantityDimension.volume),
            total_declared_content=_measurement("500", "ml", QuantityDimension.volume),
            packaging_form="pouch",
            component_set=[],
            pack_configuration_status="complete",
        ),
        lifecycle_status=lifecycle_status,
        catalog_revision="rev-1",
        evidence_references=evidence_references
        if evidence_references is not None
        else [_evidence("variant", "variant-1", note="variant-reference")],
    )


def _request(
    *,
    product: Product | None,
    variant: ProductVariant | None,
    evidence_references: list[EvidenceReference] | None = None,
    decision_references: list[str] | None = None,
) -> AssertionUpdateRequest:
    return AssertionUpdateRequest(
        product=product,
        variant=variant,
        evidence_references=evidence_references
        if evidence_references is not None
        else [_evidence("review", "review-1", note="decision-evidence")],
        decision_references=decision_references
        if decision_references is not None
        else ["review-1"],
    )


def test_product_only_assertion_is_applied_deterministically() -> None:
    manager = DeterministicAssertionManager()
    product = _product()
    request = _request(product=product, variant=None)

    response = _run(manager.apply(request))

    assert response.product is not None
    assert response.variant is None
    assert response.assertion_reference == "product:product-1"
    assert response.product.canonical_product_id == "product-1"

    state = manager._product_states["product-1"]
    assert state.current is not None
    assert state.current.product is not None
    assert state.current.product.evidence_references[0].source_type == "product"
    assert state.current.product.evidence_references[1].source_type == "review"
    assert state.current.decision_references == ("review-1",)
    assert state.history == []


def test_variant_only_assertion_is_applied_deterministically() -> None:
    manager = DeterministicAssertionManager()
    variant = _variant()
    request = _request(product=None, variant=variant)

    response = _run(manager.apply(request))

    assert response.product is None
    assert response.variant is not None
    assert response.assertion_reference == "variant:variant-1"
    assert response.variant.canonical_variant_id == "variant-1"

    state = manager._variant_states["variant-1"]
    assert state.current is not None
    assert state.current.variant is not None
    assert state.current.variant.evidence_references[0].source_type == "review"
    assert state.current.variant.evidence_references[1].source_type == "variant"
    assert state.current.decision_references == ("review-1",)
    assert state.history == []


def test_combined_assertion_updates_both_product_and_variant() -> None:
    manager = DeterministicAssertionManager()
    product = _product()
    variant = _variant()
    request = _request(product=product, variant=variant)

    response = _run(manager.apply(request))

    assert response.product is not None
    assert response.variant is not None
    assert response.assertion_reference == "product:product-1|variant:variant-1"
    assert manager._product_states["product-1"].current is not None
    assert manager._variant_states["variant-1"].current is not None


def test_invalid_parent_handling_fails_closed_and_rolls_back() -> None:
    manager = DeterministicAssertionManager()
    baseline_request = _request(product=_product(), variant=None)
    _run(manager.apply(baseline_request))
    product_snapshot = manager._product_states["product-1"].current.product.model_dump(
        mode="json"
    )

    invalid_request = _request(
        product=_product("product-1"),
        variant=_variant("variant-1", product_id="product-2"),
    )

    with pytest.raises(ValueError):
        _run(manager.apply(invalid_request))

    assert manager._product_states["product-1"].current.product.model_dump(mode="json") == product_snapshot
    assert "variant-1" not in manager._variant_states


def test_atomic_rollback_behavior_for_invalid_request() -> None:
    manager = DeterministicAssertionManager()
    valid_request = _request(product=_product(), variant=None)
    _run(manager.apply(valid_request))
    product_history_before = list(manager._product_states["product-1"].history)

    invalid_request = AssertionUpdateRequest(
        product=_product("product-2"),
        variant=None,
        evidence_references=[_evidence("review", "review-2")],
        decision_references=["   "],
    )

    with pytest.raises(ValueError):
        _run(manager.apply(invalid_request))

    assert manager._product_states["product-1"].history == product_history_before
    assert "product-2" not in manager._product_states


def test_deterministic_replay_returns_identical_response() -> None:
    request = _request(product=_product(), variant=_variant())
    manager_a = DeterministicAssertionManager()
    manager_b = DeterministicAssertionManager()

    response_a = _run(manager_a.apply(request))
    response_b = _run(manager_b.apply(request.model_copy(deep=True)))

    assert response_a.model_dump(mode="json") == response_b.model_dump(mode="json")
    assert response_a.assertion_reference == response_b.assertion_reference


def test_no_op_reapply_keeps_state_stable() -> None:
    manager = DeterministicAssertionManager()
    request = _request(product=_product(), variant=_variant())

    first_response = _run(manager.apply(request))
    first_product_history = list(manager._product_states["product-1"].history)
    first_variant_history = list(manager._variant_states["variant-1"].history)
    second_response = _run(manager.apply(request.model_copy(deep=True)))

    assert first_response.model_dump(mode="json") == second_response.model_dump(mode="json")
    assert manager._product_states["product-1"].history == first_product_history
    assert manager._variant_states["variant-1"].history == first_variant_history


def test_supersession_appends_history_and_replaces_current_state() -> None:
    manager = DeterministicAssertionManager()
    active_request = _request(product=_product(), variant=_variant())
    superseded_request = _request(
        product=_product(lifecycle_status=ProductLifecycleStatus.superseded),
        variant=_variant(lifecycle_status=VariantLifecycleStatus.superseded),
    )

    _run(manager.apply(active_request))
    _run(manager.apply(superseded_request))

    product_state = manager._product_states["product-1"]
    variant_state = manager._variant_states["variant-1"]

    assert len(product_state.history) == 1
    assert len(variant_state.history) == 1
    assert product_state.current is not None
    assert variant_state.current is not None
    assert (
        product_state.current.product.lifecycle_status
        == ProductLifecycleStatus.superseded
    )
    assert (
        variant_state.current.variant.lifecycle_status
        == VariantLifecycleStatus.superseded
    )


def test_duplicate_evidence_canonicalization_is_deterministic() -> None:
    manager = DeterministicAssertionManager()
    duplicate_timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    product = _product(
        evidence_references=[
            _evidence("product", "product-1", note="first"),
            _evidence(
                "product",
                "product-1",
                capture_timestamp=duplicate_timestamp,
                note="duplicate",
            ),
            _evidence("product", "product-2", note="other"),
        ],
    )
    request = _request(
        product=product,
        variant=None,
        evidence_references=[
            _evidence("review", "review-1", note="request-first"),
            _evidence("review", "review-1", note="request-duplicate"),
        ],
    )

    _run(manager.apply(request))

    stored = manager._product_states["product-1"].current
    assert stored is not None
    assert [
        (ref.source_type, ref.source_id, ref.note)
        for ref in stored.product.evidence_references
    ] == [
        ("product", "product-1", "first"),
        ("product", "product-2", "other"),
        ("review", "review-1", "request-first"),
    ]


def test_duplicate_decision_reference_canonicalization_is_deterministic() -> None:
    manager = DeterministicAssertionManager()
    request = AssertionUpdateRequest(
        product=_product(),
        variant=None,
        evidence_references=[_evidence("review", "review-1")],
        decision_references=["  review-b  ", "review-a", "review-b", "review-a"],
    )

    _run(manager.apply(request))

    stored = manager._product_states["product-1"].current
    assert stored is not None
    assert stored.decision_references == ("review-a", "review-b")


def test_fail_closed_validation_rejects_missing_evidence_and_preserves_state() -> None:
    manager = DeterministicAssertionManager()
    valid_request = _request(product=_product(), variant=None)
    _run(manager.apply(valid_request))

    with pytest.raises(ValueError):
        _run(
            manager.apply(
                AssertionUpdateRequest(
                    product=_product("product-2"),
                    variant=None,
                    evidence_references=[],
                    decision_references=["review-2"],
                )
            )
        )

    assert "product-2" not in manager._product_states
    assert "product-1" in manager._product_states


def test_evidence_preservation_keeps_request_and_model_evidence_visible() -> None:
    manager = DeterministicAssertionManager()
    product = _product()
    variant = _variant()
    product_snapshot = product.model_dump(mode="json")
    variant_snapshot = variant.model_dump(mode="json")
    request = _request(product=product, variant=variant)
    request_snapshot = request.model_dump(mode="json")

    _run(manager.apply(request))

    assert product.model_dump(mode="json") == product_snapshot
    assert variant.model_dump(mode="json") == variant_snapshot
    assert request.model_dump(mode="json") == request_snapshot

    stored_product = manager._product_states["product-1"].current
    stored_variant = manager._variant_states["variant-1"].current
    assert stored_product is not None
    assert stored_variant is not None
    assert {ref.source_id for ref in stored_product.product.evidence_references} == {
        "review-1",
        "product-1",
    }
    assert {ref.source_id for ref in stored_variant.variant.evidence_references} == {
        "review-1",
        "variant-1",
    }
