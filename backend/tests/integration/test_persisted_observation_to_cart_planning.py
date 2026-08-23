from app.cart_optimization.planning import (
    CandidateKey,
    CartPlanningRequest,
    CartPlanningService,
    SuppliedCandidateContext,
    SuppliedPlan,
)
from app.cart_optimization.persistence import (
    FilesystemPlanningRequestRepository,
    FilesystemPlanningResultRepository,
)
from app.cart_optimization.types import CheckoutGroup, EffectiveCostEvaluationReference
from app.cart_optimization.enums import PlanFeasibility
from app.cost_intelligence.evaluation.types import EffectiveCostEvaluationResult
from app.cost_intelligence.shared.money import Money
from app.data_ingestion.observation_registry.filesystem import FilesystemObservationRegistry
from datetime import datetime, timezone

from app.data_ingestion.enums import CaptureType, CompletenessState, Platform
from app.data_ingestion.types import (
    NormalizedObservation,
    ObservationCompleteness,
    RawArtifactReference,
)
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
    FilesystemCanonicalListingAssociationStore,
)
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.services.cart_candidate_discovery import (
    CartCandidateDiscoveryRequest,
    CartCandidateDiscoveryService,
)
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
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
from decimal import Decimal


def _product() -> Product:
    return Product(
        canonical_product_id="product-amul-taaza",
        product_identity_status=IdentityStatus.established,
        brand_reference=BrandReference(
            canonical_brand_name="Amul", display_label="Amul", is_unknown=False
        ),
        product_type="milk",
        canonical_display_name="Amul",
        identity_attributes=[
            AttributeAssertion(name="milk_type", value="toned", role="identity_critical")
        ],
        canonical_category_reference=CategoryReference(
            category_id="dairy-milk",
            category_path="dairy/milk",
            taxonomy_version="v1",
            review_state="approved",
        ),
        lifecycle_status=ProductLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[],
    )


def _variant() -> ProductVariant:
    measurement = Measurement(
        value=Decimal("500"),
        unit="ml",
        dimension=QuantityDimension.volume,
        content_basis="net_content",
        assertion_status="asserted",
    )
    return ProductVariant(
        canonical_variant_id="variant-amul-taaza-500ml",
        canonical_product_id="product-amul-taaza",
        variant_identity_status=IdentityStatus.established,
        variant_identity_attributes=[],
        pack_configuration=PackConfiguration(
            pack_kind=PackKind.single_unit,
            consumer_unit_count=1,
            content_per_consumer_unit=measurement,
            total_declared_content=measurement,
            packaging_form="pouch",
            component_set=[],
            pack_configuration_status="complete",
        ),
        lifecycle_status=VariantLifecycleStatus.active,
        catalog_revision="rev-1",
        evidence_references=[],
    )


def test_persisted_observation_reaches_optimization_with_provenance(tmp_path) -> None:
    catalog = FilesystemAuthoritativeCatalog(
        store=CatalogFilesystemStore(root_dir=tmp_path / "catalog")
    )
    catalog.register_product(_product())
    catalog.register_variant(_variant())

    observation = NormalizedObservation.model_construct(
        source_record_id="listing-1",
        platform=Platform.BLINKIT,
        raw_artifact_reference=RawArtifactReference.model_construct(
            artifact_id="artifact-1",
            job_id="job-1",
            attempt_id="attempt-1",
            platform=Platform.BLINKIT,
            capture_type=CaptureType.SEARCH_RESULTS,
            content_digest="digest-1",
            storage_reference="observations/artifact-1",
            content_type="application/json",
            capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            source_reference="fixture://listing-1",
        ),
        normalized_name="Amul",
        observed_selling_price=Money(currency="INR", minor_units=100),
        evidence_references=tuple(),
        field_references=tuple(),
        completeness=ObservationCompleteness(
            state=CompletenessState.COMPLETE,
            scope_reference="scope-1",
            basis="fixture",
        ),
        parser_version="parser-v1",
        normalization_version="normalizer-v1",
    )
    observation_registry = FilesystemObservationRegistry(tmp_path / "observations")
    observation_registry.register(observation)

    association_registry = FilesystemCanonicalListingAssociationRegistry(
        store=FilesystemCanonicalListingAssociationStore(root_dir=tmp_path / "associations")
    )
    association_registry.register(
        CanonicalListingAssociation(
            observation_id=observation.observation_id,
            platform="BLINKIT",
            platform_listing_id="listing-1",
            canonical_product_id="product-amul-taaza",
            canonical_variant_id="variant-amul-taaza-500ml",
        )
    )

    discovery = CartCandidateDiscoveryService(
        catalog=catalog,
        association_registry=association_registry,
        observation_registry=observation_registry,
    )
    request = CartPlanningRequest(
        discovery=CartCandidateDiscoveryRequest(
            items=({
                "item_id": "item-1",
                "quantity": 1,
                "canonical_product_id": "product-amul-taaza",
                "canonical_variant_id": "variant-amul-taaza-500ml",
            },)
        ),
        candidate_contexts=(SuppliedCandidateContext(
            key=CandidateKey(
                item_id="item-1",
                platform="BLINKIT",
                platform_listing_id="listing-1",
                observation_id=observation.observation_id,
            ),
            retailer_id="retailer-explicit",
            checkout_group_id="group-explicit",
        ),),
        plans=(SuppliedPlan(
            plan_id="plan-persisted-1",
            combination_index=0,
            inconvenience_penalty_units=0,
            retailer_preference_priority=0,
            checkout_groups=(CheckoutGroup(
                checkout_group_id="group-explicit",
                retailer_id="retailer-explicit",
                effective_cost_evaluation_id="ece-persisted-1",
            ),),
            effective_cost_evaluation_reference=EffectiveCostEvaluationReference(
                effective_cost_evaluation_id="ece-persisted-1"
            ),
            effective_cost_evaluation=EffectiveCostEvaluationResult(
                evaluation_id="ece-persisted-1",
                context_id="context-persisted-1",
                effective_cost=Money(currency="INR", minor_units=100),
            ),
            feasibility=PlanFeasibility.FEASIBLE,
            feasibility_evidence=("fixture-feasibility",),
        ),),
        request_id="request-persisted-1",
        optimization_policy_version="policy-v1",
    )

    result = CartPlanningService(discovery=discovery).plan(request)

    assert result.chosen_plan_id == "plan-persisted-1"
    assert result.chosen_plan is not None
    allocation = result.chosen_plan.candidate_item_allocations[0]
    assert allocation.item_id == "item-1"
    assert allocation.canonical_variant_id == "variant-amul-taaza-500ml"
    assert allocation.quantity == 1
    assert allocation.retailer_id == "retailer-explicit"
    assert allocation.checkout_group_id == "group-explicit"
    assert allocation.listing_provenance.observation_id == observation.observation_id
    assert result.chosen_plan.feasibility is PlanFeasibility.FEASIBLE
    assert result.chosen_plan.effective_cost_evaluation_reference.effective_cost_evaluation_id == "ece-persisted-1"

    replayed_request = CartPlanningRequest.model_validate_json(request.model_dump_json())
    replayed_result = CartPlanningService(discovery=discovery).plan(replayed_request)
    assert replayed_request == request
    assert replayed_result == result

    request_repository = FilesystemPlanningRequestRepository(tmp_path / "planning-requests")
    result_repository = FilesystemPlanningResultRepository(tmp_path / "planning-results")
    request_repository.save(request)
    result_repository.save(result)
    assert request_repository.get(request.request_id) == request
    assert result_repository.get(result.optimization_id) == result
