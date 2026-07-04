from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.product_intelligence.assertions.interfaces import AssertionManager
from app.product_intelligence.assertions.types import (
    AssertionUpdateRequest,
    AssertionUpdateResponse,
)
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    EvidenceReference,
    PackComponent,
    PackConfiguration,
    Product,
    ProductVariant,
)


logger = get_logger(__name__)


class DeterministicAssertionRequestFactory:
    """Build deterministic assertion requests from orchestration inputs."""

    def build(
        self,
        *,
        product: Product | None,
        variant: ProductVariant | None,
        evidence_references: list[EvidenceReference],
        decision_references: list[str],
    ) -> AssertionUpdateRequest:
        return AssertionUpdateRequest(
            product=product.model_copy(deep=True) if product is not None else None,
            variant=variant.model_copy(deep=True) if variant is not None else None,
            evidence_references=[
                reference.model_copy(deep=True) for reference in evidence_references
            ],
            decision_references=list(decision_references),
        )


@dataclass(frozen=True, slots=True)
class _AssertionRevision:
    """Canonical immutable snapshot for a single assertion entity."""

    assertion_reference: str
    product: Product | None
    variant: ProductVariant | None
    evidence_references: tuple[EvidenceReference, ...]
    decision_references: tuple[str, ...]


@dataclass(slots=True)
class _AssertionState:
    """Current canonical assertion state plus append-only history."""

    current: _AssertionRevision | None = None
    history: list[_AssertionRevision] = field(default_factory=list)


class DeterministicAssertionManager(AssertionManager):
    """Deterministic in-memory canonical assertion manager."""

    def __init__(self) -> None:
        self._product_states: dict[str, _AssertionState] = {}
        self._variant_states: dict[str, _AssertionState] = {}

    async def apply(self, request: AssertionUpdateRequest) -> AssertionUpdateResponse:
        normalized_request = self._normalize_request(request)
        self._validate_request(normalized_request)

        product = (
            self._canonical_product(normalized_request.product)
            if normalized_request.product is not None
            else None
        )
        variant = (
            self._canonical_variant(normalized_request.variant)
            if normalized_request.variant is not None
            else None
        )

        if (
            product is not None
            and variant is not None
            and variant.canonical_product_id != product.canonical_product_id
        ):
            raise ValueError(
                "variant canonical_product_id must match product canonical_product_id"
            )

        product_revision = self._plan_product_revision(product, normalized_request)
        variant_revision = self._plan_variant_revision(variant, normalized_request)

        if product_revision is not None:
            self._commit_revision(self._product_states, product.canonical_product_id, product_revision)
        if variant_revision is not None:
            self._commit_revision(self._variant_states, variant.canonical_variant_id, variant_revision)

        logger.info(
            "assertion_apply_complete product=%s variant=%s",
            product.canonical_product_id if product else None,
            variant.canonical_variant_id if variant else None,
        )

        response_product = (
            self._product_states[product.canonical_product_id].current.product
            if product is not None
            else None
        )
        response_variant = (
            self._variant_states[variant.canonical_variant_id].current.variant
            if variant is not None
            else None
        )
        assertion_reference = self._assertion_reference(product, variant)
        return AssertionUpdateResponse(
            product=self._copy_product(response_product),
            variant=self._copy_variant(response_variant),
            assertion_reference=assertion_reference,
        )

    def _validate_request(self, request: AssertionUpdateRequest) -> None:
        if request.product is None and request.variant is None:
            raise ValueError("assertion request must include a product, variant, or both")

        evidence_references = self._canonical_evidence_references(
            request.evidence_references
        )
        if not evidence_references:
            raise ValueError("assertion request requires at least one evidence reference")

        decision_references = self._canonical_decision_references(
            request.decision_references
        )
        if not decision_references:
            raise ValueError("assertion request requires at least one decision reference")

    def _plan_product_revision(
        self,
        product: Product | None,
        request: AssertionUpdateRequest,
    ) -> _AssertionRevision | None:
        if product is None:
            return None
        canonical_product = self._canonical_product(product)
        evidence_references = self._merged_evidence_references(
            request.evidence_references,
            canonical_product.evidence_references,
        )
        canonical_product.evidence_references = list(evidence_references)
        decision_references = self._canonical_decision_references(
            request.decision_references
        )
        existing_state = self._product_states.get(canonical_product.canonical_product_id)
        planned = _AssertionRevision(
            assertion_reference=self._product_reference(
                canonical_product.canonical_product_id
            ),
            product=canonical_product,
            variant=None,
            evidence_references=tuple(evidence_references),
            decision_references=tuple(decision_references),
        )
        if existing_state and existing_state.current and self._revision_equals(
            existing_state.current, planned
        ):
            return existing_state.current
        if canonical_product.lifecycle_status.value == "superseded" and existing_state and existing_state.current:
            logger.info(
                "assertion_supersede entity=product canonical_product_id=%s",
                canonical_product.canonical_product_id,
            )
        elif existing_state and existing_state.current:
            logger.info(
                "assertion_update entity=product canonical_product_id=%s",
                canonical_product.canonical_product_id,
            )
        else:
            logger.info(
                "assertion_create entity=product canonical_product_id=%s",
                canonical_product.canonical_product_id,
            )
        return planned

    def _plan_variant_revision(
        self,
        variant: ProductVariant | None,
        request: AssertionUpdateRequest,
    ) -> _AssertionRevision | None:
        if variant is None:
            return None
        canonical_variant = self._canonical_variant(variant)
        evidence_references = self._merged_evidence_references(
            request.evidence_references,
            canonical_variant.evidence_references,
        )
        canonical_variant.evidence_references = list(evidence_references)
        decision_references = self._canonical_decision_references(
            request.decision_references
        )
        existing_state = self._variant_states.get(canonical_variant.canonical_variant_id)
        planned = _AssertionRevision(
            assertion_reference=self._variant_reference(
                canonical_variant.canonical_variant_id
            ),
            product=None,
            variant=canonical_variant,
            evidence_references=tuple(evidence_references),
            decision_references=tuple(decision_references),
        )
        if existing_state and existing_state.current and self._revision_equals(
            existing_state.current, planned
        ):
            return existing_state.current
        if canonical_variant.lifecycle_status.value == "superseded" and existing_state and existing_state.current:
            logger.info(
                "assertion_supersede entity=variant canonical_variant_id=%s",
                canonical_variant.canonical_variant_id,
            )
        elif existing_state and existing_state.current:
            logger.info(
                "assertion_update entity=variant canonical_variant_id=%s",
                canonical_variant.canonical_variant_id,
            )
        else:
            logger.info(
                "assertion_create entity=variant canonical_variant_id=%s",
                canonical_variant.canonical_variant_id,
            )
        return planned

    def _commit_revision(
        self,
        registry: dict[str, _AssertionState],
        key: str,
        revision: _AssertionRevision,
    ) -> None:
        state = registry.get(key)
        if state is None:
            registry[key] = _AssertionState(current=revision, history=[])
            return
        if state.current is not None and state.current != revision:
            state.history.append(state.current)
        state.current = revision

    def _revision_equals(
        self,
        left: _AssertionRevision,
        right: _AssertionRevision,
    ) -> bool:
        return (
            self._dump_product(left.product) == self._dump_product(right.product)
            and self._dump_variant(left.variant) == self._dump_variant(right.variant)
            and list(left.evidence_references) == list(right.evidence_references)
            and list(left.decision_references) == list(right.decision_references)
        )

    def _normalize_request(self, request: AssertionUpdateRequest) -> AssertionUpdateRequest:
        product = self._canonical_product(request.product) if request.product else None
        variant = self._canonical_variant(request.variant) if request.variant else None
        evidence_references = self._canonical_evidence_references(
            request.evidence_references
        )
        decision_references = self._canonical_decision_references(
            request.decision_references
        )
        return AssertionUpdateRequest(
            product=product,
            variant=variant,
            evidence_references=evidence_references,
            decision_references=decision_references,
        )

    def _canonical_product(self, product: Product) -> Product:
        canonical = product.model_copy(deep=True)
        canonical.brand_reference = self._canonical_brand_reference(
            canonical.brand_reference
        )
        canonical.identity_attributes = self._canonical_attributes(
            canonical.identity_attributes
        )
        canonical.descriptive_attributes = self._canonical_attributes(
            canonical.descriptive_attributes
        )
        canonical.evidence_references = self._canonical_evidence_references(
            canonical.evidence_references
        )
        return canonical

    def _canonical_variant(self, variant: ProductVariant) -> ProductVariant:
        canonical = variant.model_copy(deep=True)
        canonical.variant_identity_attributes = self._canonical_attributes(
            canonical.variant_identity_attributes
        )
        canonical.pack_configuration = self._canonical_pack_configuration(
            canonical.pack_configuration
        )
        canonical.evidence_references = self._canonical_evidence_references(
            canonical.evidence_references
        )
        return canonical

    def _canonical_brand_reference(self, brand_reference: BrandReference) -> BrandReference:
        canonical = brand_reference.model_copy(deep=True)
        canonical.evidence_references = self._canonical_evidence_references(
            canonical.evidence_references
        )
        return canonical

    def _canonical_attributes(
        self,
        attributes: list[AttributeAssertion],
    ) -> list[AttributeAssertion]:
        canonical_attributes = [attribute.model_copy(deep=True) for attribute in attributes]
        for attribute in canonical_attributes:
            attribute.evidence_references = self._canonical_evidence_references(
                attribute.evidence_references
            )
        canonical_attributes.sort(
            key=lambda item: (
                item.role,
                item.name,
                item.value,
                item.qualifier or "",
                item.assertion_status,
            )
        )
        return canonical_attributes

    def _canonical_pack_configuration(
        self,
        pack_configuration: PackConfiguration,
    ) -> PackConfiguration:
        canonical = pack_configuration.model_copy(deep=True)
        canonical.component_set = self._canonical_components(canonical.component_set)
        return canonical

    def _canonical_components(
        self,
        components: list[PackComponent],
    ) -> list[PackComponent]:
        canonical_components = [component.model_copy(deep=True) for component in components]
        canonical_components.sort(
            key=lambda item: (
                item.label,
                item.quantity_text or "",
                self._measurement_key(item.quantity),
            )
        )
        return canonical_components

    def _canonical_evidence_references(
        self,
        evidence_references: list[EvidenceReference],
    ) -> list[EvidenceReference]:
        canonical: dict[tuple[str, str], EvidenceReference] = {}
        for evidence_reference in evidence_references:
            source_type = evidence_reference.source_type.strip()
            source_id = evidence_reference.source_id.strip()
            if not source_type or not source_id:
                raise ValueError("evidence references must include source_type and source_id")
            key = (source_type, source_id)
            if key not in canonical:
                canonical[key] = evidence_reference.model_copy(
                    update={"source_type": source_type, "source_id": source_id},
                    deep=True,
                )
        return [canonical[key] for key in sorted(canonical)]

    def _merged_evidence_references(
        self,
        *groups: list[EvidenceReference],
    ) -> list[EvidenceReference]:
        merged: list[EvidenceReference] = []
        for group in groups:
            merged.extend(group)
        return self._canonical_evidence_references(merged)

    def _canonical_decision_references(self, decision_references: list[str]) -> list[str]:
        canonical: list[str] = []
        seen: set[str] = set()
        for decision_reference in decision_references:
            normalized = decision_reference.strip()
            if not normalized:
                raise ValueError("decision references must not be blank")
            if normalized in seen:
                continue
            seen.add(normalized)
            canonical.append(normalized)
        canonical.sort()
        return canonical

    def _product_reference(self, canonical_product_id: str) -> str:
        return f"product:{canonical_product_id}"

    def _variant_reference(self, canonical_variant_id: str) -> str:
        return f"variant:{canonical_variant_id}"

    def _assertion_reference(
        self,
        product: Product | None,
        variant: ProductVariant | None,
    ) -> str:
        if product is not None and variant is not None:
            return (
                f"product:{product.canonical_product_id}|"
                f"variant:{variant.canonical_variant_id}"
            )
        if product is not None:
            return f"product:{product.canonical_product_id}"
        if variant is not None:
            return f"variant:{variant.canonical_variant_id}"
        raise ValueError("assertion reference requires a product, variant, or both")

    def _dump_product(self, product: Product | None) -> dict[str, object] | None:
        return None if product is None else product.model_dump(mode="json")

    def _dump_variant(self, variant: ProductVariant | None) -> dict[str, object] | None:
        return None if variant is None else variant.model_dump(mode="json")

    def _copy_product(self, product: Product | None) -> Product | None:
        return None if product is None else product.model_copy(deep=True)

    def _copy_variant(self, variant: ProductVariant | None) -> ProductVariant | None:
        return None if variant is None else variant.model_copy(deep=True)

    def _measurement_key(self, measurement) -> tuple[object, ...]:
        if measurement is None:
            return ()
        return (
            measurement.value,
            measurement.unit,
            measurement.dimension.value,
            measurement.content_basis,
            measurement.assertion_status,
        )
