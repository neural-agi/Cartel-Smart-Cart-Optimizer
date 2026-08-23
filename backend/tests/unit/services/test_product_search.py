from types import SimpleNamespace

import pytest

from app.services.product_search import ProductSearchRequest, ProductSearchService


def _service() -> ProductSearchService:
    product = SimpleNamespace(
        canonical_product_id="product-1",
        canonical_display_name="Amul Taaza",
        product_type="milk",
        brand_reference=SimpleNamespace(display_label="Amul"),
    )
    variant = SimpleNamespace(
        canonical_variant_id="variant-1",
        canonical_product_id="product-1",
        pack_configuration=SimpleNamespace(
            total_declared_content=SimpleNamespace(value="500", unit="ml"),
            consumer_unit_count=1,
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
