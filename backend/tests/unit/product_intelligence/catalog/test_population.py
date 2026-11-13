import json
from types import SimpleNamespace

import pytest

from app.product_intelligence.catalog.population import (
    CatalogPopulationManifest,
    GovernedCatalogPopulationService,
)
from app.product_intelligence.catalog.resolution import (
    CanonicalListingAssociation,
    ListingResolutionResult,
    ListingResolutionStatus,
)
from app.product_intelligence.catalog.types import CatalogState, CatalogValidationError


def test_review_queue_is_deterministic_and_non_authoritative() -> None:
    observations = [
        SimpleNamespace(
            observation_id="b",
            platform=SimpleNamespace(value="BLINKIT"),
            source_record_id="2",
            normalized_name=None,
            normalized_category=None,
            normalized_quantity="500 ml",
            observed_selling_price=None,
            availability_signal="available",
            raw_artifact_reference=SimpleNamespace(source_reference="raw-b"),
        ),
        SimpleNamespace(
            observation_id="a",
            platform=SimpleNamespace(value="BLINKIT"),
            source_record_id="1",
            normalized_name="amul milk",
            normalized_category=None,
            normalized_quantity="500 ml",
            observed_selling_price=None,
            availability_signal="available",
            raw_artifact_reference=SimpleNamespace(source_reference="raw-a"),
        ),
    ]
    service = GovernedCatalogPopulationService(
        catalog=SimpleNamespace(),
        association_registry=SimpleNamespace(),
        observation_registry=SimpleNamespace(list_all=lambda: tuple(observations)),
    )
    queue = service.build_review_queue()
    assert [item.observation_id for item in queue.observations] == ["a", "b"]
    assert all(item.resolution_state == "unresolved" for item in queue.observations)


def test_manifest_loader_preserves_explicit_empty_state(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema_version": 1, "products": [], "variants": [], "associations": []}))
    manifest = CatalogPopulationManifest.model_validate(json.loads(path.read_text()))
    assert manifest.products == ()
    assert manifest.variants == ()
    assert manifest.associations == ()


def test_manifest_associations_require_exact_resolver() -> None:
    observation = SimpleNamespace(
        observation_id="obs-1", platform=SimpleNamespace(value="BLINKIT"), source_record_id="19512"
    )
    association = CanonicalListingAssociation(
        observation_id="obs-1", platform="BLINKIT", platform_listing_id="19512",
        canonical_product_id="product-1", canonical_variant_id="variant-1",
    )
    manifest = CatalogPopulationManifest(associations=(association,))
    service = GovernedCatalogPopulationService(
        catalog=SimpleNamespace(), association_registry=SimpleNamespace(),
        observation_registry=SimpleNamespace(get=lambda _: observation),
    )
    with pytest.raises(CatalogValidationError, match="exact canonical identity resolver"):
        service._validate_associations_against_resolver(manifest, CatalogState())


def test_manifest_association_must_equal_resolver_output() -> None:
    observation = SimpleNamespace(
        observation_id="obs-1", platform=SimpleNamespace(value="BLINKIT"), source_record_id="19512"
    )
    association = CanonicalListingAssociation(
        observation_id="obs-1", platform="BLINKIT", platform_listing_id="19512",
        canonical_product_id="product-1", canonical_variant_id="variant-1",
    )
    manifest = CatalogPopulationManifest(associations=(association,))
    resolver = SimpleNamespace(resolve=lambda *_: ListingResolutionResult(
        status=ListingResolutionStatus.unresolved, rationale=("identity incomplete",)
    ))
    service = GovernedCatalogPopulationService(
        catalog=SimpleNamespace(), association_registry=SimpleNamespace(),
        observation_registry=SimpleNamespace(get=lambda _: observation), resolver=resolver,
    )
    with pytest.raises(CatalogValidationError, match="identity incomplete"):
        service._validate_associations_against_resolver(manifest, CatalogState())
