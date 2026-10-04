from types import SimpleNamespace
from datetime import datetime, timezone

import pytest

from app.services.product_search import ProductSearchRequest, ProductSearchService
from app.product_intelligence.models import IdentityStatus, ProductLifecycleStatus, VariantLifecycleStatus


def _service() -> ProductSearchService:
    product = SimpleNamespace(
        canonical_product_id="product-1",
        product_identity_status=IdentityStatus.established,
        lifecycle_status=ProductLifecycleStatus.active,
        canonical_display_name="Amul Taaza",
        product_type="milk",
        identity_attributes=(SimpleNamespace(name="milk_type", value="toned", role="identity_critical", assertion_status="asserted"),),
        brand_reference=SimpleNamespace(display_label="Amul"),
    )
    variant = SimpleNamespace(
        canonical_variant_id="variant-1",
        canonical_product_id="product-1",
        variant_identity_status=IdentityStatus.established,
        lifecycle_status=VariantLifecycleStatus.active,
        variant_identity_attributes=(),
        pack_configuration=SimpleNamespace(
            total_declared_content=SimpleNamespace(value="500", unit="ml"),
            consumer_unit_count=1,
            pack_configuration_status="complete",
        ),
    )
    association = SimpleNamespace(
        canonical_product_id="product-1",
        canonical_variant_id="variant-1",
        platform="BLINKIT",
        platform_listing_id="listing-1",
        observation_id="observation-1",
    )
    observation = SimpleNamespace(
        platform=SimpleNamespace(value="BLINKIT"),
        observation_id="observation-1",
        raw_artifact_reference=SimpleNamespace(
            capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            source_reference="https://blinkit.com/s/?q=amul",
            artifact_id="artifact-1",
            content_digest="sha256:abc",
            storage_reference="product-intelligence/sha256-abc",
            platform=SimpleNamespace(value="BLINKIT"),
        ),
        parser_version="blinkit-parser-v1",
        normalization_version="normalization-v1",
        completeness=SimpleNamespace(basis="complete observation capture"),
        platform_identifiers=(
            ("retailer_product_id", "19512"),
            ("retailer_product_url", "https://blinkit.com/prn/amul-taaza/prid/19512"),
        ),
        evidence_references=(SimpleNamespace(source_type="raw_artifact", source_id="artifact-1"),),
        observed_selling_price=SimpleNamespace(currency="INR", minor_units=10000),
        availability_signal="available",
    )
    catalog = SimpleNamespace(
        load_state=lambda: SimpleNamespace(products=(product,), variants=(variant,))
    )
    associations = SimpleNamespace(all=lambda: (association,))
    observations = SimpleNamespace(get=lambda observation_id: observation)
    return ProductSearchService(
        catalog=catalog,
        association_registry=associations,
        observation_registry=observations,
    )


def test_search_returns_canonical_listing_and_typed_price() -> None:
    result = _service().search(ProductSearchRequest(query="amul"))

    assert result.query == "amul"
    assert len(result.items) == 1
    assert result.items[0].canonical_variant_id == "variant-1"
    assert result.items[0].price is not None
    assert result.items[0].price.minor_units == 10000
    assert result.items[0].evidence_state == "registered_governed_observation"
    assert result.items[0].parser_version == "blinkit-parser-v1"
    assert result.items[0].normalization_version == "normalization-v1"
    assert result.items[0].retailer_product_id == "19512"
    assert result.items[0].retailer_product_url.endswith("/prid/19512")
    assert result.items[0].platform_listing_id == "listing-1"
    assert result.items[0].source_reference == "https://blinkit.com/s/"
    assert result.items[0].raw_artifact_id == "artifact-1"
    assert result.items[0].evidence_references[0].source_id == "artifact-1"
    assert result.items[0].observed_at.isoformat().startswith("2026-01-01")


def test_search_preserves_old_capture_time_without_claiming_it_is_fresh() -> None:
    item = _service().search(ProductSearchRequest(query="amul")).items[0]

    assert item.observed_at == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert item.evidence_state == "registered_governed_observation"


def test_search_matches_identity_critical_product_attributes():
    assert len(_service().search(ProductSearchRequest(query="toned")).items) == 1


def test_search_excludes_unestablished_or_inactive_canonical_identity():
    service = _service()
    original = service._catalog.load_state()
    product = SimpleNamespace(**{**vars(original.products[0]), "product_identity_status": IdentityStatus.provisional})
    service._catalog.load_state = lambda: SimpleNamespace(products=(product,), variants=original.variants)

    assert service.search(ProductSearchRequest(query="amul")).items == ()


def test_search_requires_observation_platform_to_match_listing_association():
    service = _service()
    service._observation_registry.get = lambda _: SimpleNamespace(
        platform=SimpleNamespace(value="ZEPTO"),
        raw_artifact_reference=None,
        observed_selling_price=None,
        availability_signal="available",
    )

    assert service.search(ProductSearchRequest(query="amul")).items == ()


def test_search_omits_results_without_a_registered_observation():
    service = _service()
    service._observation_registry.get = lambda _: None
    assert service.search(ProductSearchRequest(query="amul")).items == ()


def test_search_omits_observation_without_raw_artifact_provenance():
    service = _service()
    observation = service._observation_registry.get("observation-1")
    observation.raw_artifact_reference = None
    service._observation_registry.get = lambda _: observation

    assert service.search(ProductSearchRequest(query="amul")).items == ()


@pytest.mark.parametrize(
    "source_reference",
    (
        "fixture://blinkit/search?q=amul",
        "https://fixture.invalid/blinkit/search?q=amul",
        "https://blinkit.test/s/?q=amul",
        "http://blinkit.com/s/?q=amul",
    ),
)
def test_search_never_exposes_fixture_or_non_blinkit_sources(source_reference):
    service = _service()
    observation = service._observation_registry.get("observation-1")
    observation.raw_artifact_reference.source_reference = source_reference
    service._observation_registry.get = lambda _: observation

    assert service.search(ProductSearchRequest(query="amul")).items == ()


@pytest.mark.parametrize("marker", ("demo", "fixture", "synthetic"))
def test_search_excludes_non_live_provenance_markers(marker):
    service = _service()
    observation = service._observation_registry.get("observation-1")
    observation.parser_version = f"{marker}-parser"
    service._observation_registry.get = lambda _: observation

    assert service.search(ProductSearchRequest(query="amul")).items == ()


def test_search_requires_native_retailer_product_identity_not_source_index():
    service = _service()
    observation = service._observation_registry.get("observation-1")
    observation.platform_identifiers = (("source_index", "1"),)
    service._observation_registry.get = lambda _: observation

    assert service.search(ProductSearchRequest(query="amul")).items == ()


def test_search_rejects_retailer_url_that_disagrees_with_observed_id():
    service = _service()
    observation = service._observation_registry.get("observation-1")
    observation.platform_identifiers = (
        ("retailer_product_id", "19512"),
        ("retailer_product_url", "https://blinkit.com/prn/amul/prid/776437"),
    )
    service._observation_registry.get = lambda _: observation

    assert service.search(ProductSearchRequest(query="amul")).items == ()


def test_search_only_returns_latest_unique_observation_for_native_listing():
    service = _service()
    old = service._observation_registry.get("observation-1")
    old.raw_artifact_reference.capture_timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new = SimpleNamespace(**vars(old))
    new.observation_id = "observation-2"
    new.raw_artifact_reference = SimpleNamespace(
        **{
            **vars(old.raw_artifact_reference),
            "capture_timestamp": datetime(2026, 1, 2, tzinfo=timezone.utc),
        }
    )
    new.observed_selling_price = SimpleNamespace(currency="INR", minor_units=12000)
    associations = (
        service._association_registry.all()[0],
        SimpleNamespace(
            **{
                **vars(service._association_registry.all()[0]),
                "platform_listing_id": "listing-2",
                "observation_id": "observation-2",
            }
        ),
    )
    service._association_registry.all = lambda: associations
    service._observation_registry.get = lambda key: {
        "observation-1": old,
        "observation-2": new,
    }.get(key)

    result = service.search(ProductSearchRequest(query="amul"))

    assert len(result.items) == 1
    assert result.items[0].observation_id == "observation-2"
    assert result.items[0].price.minor_units == 12000


def test_search_excludes_equal_time_observation_ambiguity():
    service = _service()
    first = service._observation_registry.get("observation-1")
    second = SimpleNamespace(**vars(first))
    second.observation_id = "observation-2"
    associations = (
        service._association_registry.all()[0],
        SimpleNamespace(
            **{
                **vars(service._association_registry.all()[0]),
                "platform_listing_id": "listing-2",
                "observation_id": "observation-2",
            }
        ),
    )
    service._association_registry.all = lambda: associations
    service._observation_registry.get = lambda key: {
        "observation-1": first,
        "observation-2": second,
    }.get(key)

    assert service.search(ProductSearchRequest(query="amul")).items == ()


def test_search_allows_live_source_query_containing_demo_word():
    service = _service()
    observation = service._observation_registry.get("observation-1")
    observation.raw_artifact_reference.source_reference = "https://blinkit.com/s/?q=demo-food"
    service._observation_registry.get = lambda _: observation

    assert len(service.search(ProductSearchRequest(query="amul")).items) == 1


def test_search_rejects_blank_query_and_invalid_limit() -> None:
    service = _service()

    with pytest.raises(ValueError, match="must not be blank"):
        service.search(ProductSearchRequest(query="   "))
    with pytest.raises(ValueError, match="between 1 and 100"):
        service.search(ProductSearchRequest(query="amul", limit=0))


def test_search_is_deterministic_for_identical_inputs() -> None:
    service = _service()
    request = ProductSearchRequest(query="AMUL")

    assert service.search(request) == service.search(request)
