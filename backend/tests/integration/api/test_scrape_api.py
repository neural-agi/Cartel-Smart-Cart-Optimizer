from fastapi.testclient import TestClient

from app.core.config import Settings
from app.data_ingestion import FilesystemObservationRegistry
from app.main import create_application
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from app.cost_intelligence.shared.money import Money
from tests.integration.product_intelligence.test_vertical_pipeline import (
    _job,
    _resolver,
    _runtime,
)


def _client(tmp_path, *, resolver):
    runtime, _catalog, _associations = _runtime(tmp_path, resolver=resolver)
    application = create_application()
    application.state.product_intelligence_runtime = runtime
    return TestClient(application)


def test_scrape_endpoint_maps_request_and_returns_runtime_result(tmp_path) -> None:
    client = _client(tmp_path, resolver=_resolver())

    response = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["job_id"] == _job().job_id
    assert body["observations"][0]["status"] == "resolved"
    assert body["observations"][0]["execution"]["status"] == "executed"


def test_scrape_endpoint_preserves_unresolved_runtime_status(tmp_path) -> None:
    client = _client(tmp_path, resolver=_resolver(missing_product=True))

    response = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed_with_failures"
    assert body["observations"][0]["status"] == "association_unresolved"
    assert body["observations"][0]["execution"]["pipeline_result"] is None


def test_scrape_endpoint_rejects_malformed_scrape_job() -> None:
    application = create_application()
    client = TestClient(application)

    response = client.post("/api/v1/scrape", json={})

    assert response.status_code == 422


def test_health_endpoint_remains_unchanged() -> None:
    with TestClient(create_application()) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_and_readiness_expose_safe_operational_headers(tmp_path) -> None:
    application = create_application(Settings(_env_file=None, data_dir=tmp_path))

    with TestClient(application) as client:
        health = client.get("/health", headers={"X-Request-ID": "request-test-1"})
        readiness = client.get("/ready")

    assert health.status_code == 200
    assert health.headers["X-Request-ID"] == "request-test-1"
    assert health.headers["X-Content-Type-Options"] == "nosniff"
    assert health.headers["X-Frame-Options"] == "DENY"
    assert health.headers["Referrer-Policy"] == "no-referrer"
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"
    assert readiness.json()["checks"]["product_search"] == "ready"


def test_configured_cors_allows_only_declared_origin(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        cors_allowed_origins="https://app.example",
    )

    with TestClient(create_application(settings)) as client:
        allowed = client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = client.get("/api/v1/health", headers={"Origin": "https://other.example"})

    assert allowed.headers["access-control-allow-origin"] == "https://app.example"
    assert "access-control-allow-origin" not in denied.headers


def test_create_application_bootstraps_runtime_from_configured_data_root(tmp_path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path)

    application = create_application(settings)
    runtime = application.state.product_intelligence_runtime

    assert runtime is not None
    assert isinstance(runtime.observation_registry, FilesystemObservationRegistry)
    assert runtime.catalog.load_state().products == ()
    assert runtime.catalog.load_state().variants == ()
    assert runtime.catalog.store.catalog_path == (
        tmp_path / "product_intelligence" / "catalog" / "catalog.json"
    )
    assert runtime.association_registry.store.association_path == (
        tmp_path / "product_intelligence" / "catalog" / "listing_associations.json"
    )
    assert runtime.execution_trigger.evidence_publisher.registry.store.root_dir == (
        tmp_path / "product_intelligence" / "evidence"
    )
    assert runtime.ingestion_worker._artifact_store._root == tmp_path / "raw"
    assert runtime.lifecycle_store.root_dir == (
        tmp_path / "data_ingestion" / "lifecycle"
    )


def test_scrape_endpoint_is_available_from_bootstrapped_application(tmp_path) -> None:
    application = create_application(Settings(_env_file=None, data_dir=tmp_path))
    client = TestClient(application)

    response = client.post("/api/v1/scrape", json={})

    assert response.status_code == 422


def test_observation_query_endpoint_returns_persisted_observation_with_association(tmp_path) -> None:
    runtime, _catalog, associations = _runtime(tmp_path, resolver=_resolver())
    application = create_application(runtime=runtime)
    client = TestClient(application)

    scrape = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))
    assert scrape.status_code == 200
    observation_id = client.get("/api/v1/observations").json()[0]["observation_id"]

    exact = client.get(f"/api/v1/observations/{observation_id}")
    assert exact.status_code == 200
    assert exact.json()["observation_id"] == observation_id
    assert exact.json()["association"]["canonical_product_id"] == "product-amul-taaza"

    filtered = client.get(
        "/api/v1/observations",
        params={"canonical_variant_id": "variant-amul-taaza-500ml"},
    )
    assert filtered.status_code == 200
    assert [item["observation_id"] for item in filtered.json()] == [observation_id]

    assert associations.all()


def test_product_search_returns_governed_catalog_listing_after_ingestion(tmp_path) -> None:
    runtime, _catalog, _associations = _runtime(tmp_path, resolver=_resolver())
    client = TestClient(create_application(runtime=runtime))

    scrape = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))
    assert scrape.status_code == 200

    response = client.get("/api/v1/products/search", params={"query": "amul"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "amul"
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["canonical_product_id"] == "product-amul-taaza"
    assert item["canonical_variant_id"] == "variant-amul-taaza-500ml"
    assert item["platform"] == "BLINKIT"
    assert item["platform_listing_id"]
    assert item["observation_id"]
    assert "price" in item


def test_product_search_rejects_blank_query(tmp_path) -> None:
    application = create_application(Settings(_env_file=None, data_dir=tmp_path))

    response = TestClient(application).get(
        "/api/v1/products/search", params={"query": "   "}
    )

    assert response.status_code == 422


def test_observation_query_endpoint_returns_null_association_for_unresolved_observation(tmp_path) -> None:
    runtime, _catalog, _associations = _runtime(tmp_path, resolver=_resolver(missing_product=True))
    application = create_application(runtime=runtime)
    client = TestClient(application)

    scrape = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))
    observation_id = client.get("/api/v1/observations").json()[0]["observation_id"]

    exact = client.get(f"/api/v1/observations/{observation_id}")
    assert exact.status_code == 200
    assert exact.json()["observation_id"] == observation_id
    assert exact.json()["association"] is None
    assert client.get(
        "/api/v1/observations",
        params={"canonical_product_id": "product-amul-taaza"},
    ).json() == []


def test_displayed_price_comparison_endpoint_returns_explicit_empty_result(tmp_path) -> None:
    application = create_application(Settings(_env_file=None, data_dir=tmp_path))
    client = TestClient(application)

    response = client.get(
        "/api/v1/comparisons/variants/unknown-variant/displayed-price"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "no_comparable_observations"


def test_cart_resolution_resolves_variant_and_listing_items_in_input_order(tmp_path) -> None:
    runtime, _catalog, _associations = _runtime(tmp_path, resolver=_resolver())
    client = TestClient(create_application(runtime=runtime))
    scrape = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))
    assert scrape.status_code == 200
    observation = client.get("/api/v1/observations").json()[0]
    association = observation["association"]

    response = client.post(
        "/api/v1/cart/resolve",
        json={
            "items": [
                {
                    "item_id": "second",
                    "quantity": 3,
                    "canonical_variant_id": association["canonical_variant_id"],
                },
                {
                    "item_id": "first",
                    "quantity": 2,
                    "platform": association["platform"],
                    "platform_listing_id": association["platform_listing_id"],
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()["items"]
    assert [item["item_id"] for item in body] == ["second", "first"]
    assert [item["quantity"] for item in body] == [3, 2]
    assert body[0]["status"] == "resolved"
    assert body[0]["canonical_variant_id"] == association["canonical_variant_id"]
    assert body[1]["observation_id"] == observation["observation_id"]
    assert body[1]["observation"] is not None


def test_cart_resolution_reports_unknown_variant_and_listing(tmp_path) -> None:
    runtime, _catalog, _associations = _runtime(tmp_path, resolver=_resolver())
    client = TestClient(create_application(runtime=runtime))

    response = client.post(
        "/api/v1/cart/resolve",
        json={
            "items": [
                {"item_id": "variant", "quantity": 1, "canonical_variant_id": "missing"},
                {
                    "item_id": "listing",
                    "quantity": 1,
                    "platform": "blinkit",
                    "platform_listing_id": "missing",
                },
            ]
        },
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["status"] == items[1]["status"] == "unresolved"
    assert items[0]["reason"] == "canonical Variant was not found"
    assert items[1]["reason"] == "listing association was not found"


def test_cart_resolution_reports_missing_observation(tmp_path) -> None:
    runtime, _catalog, associations = _runtime(tmp_path, resolver=_resolver())
    associations.register(
        CanonicalListingAssociation(
            observation_id="missing-observation",
            platform="blinkit",
            platform_listing_id="missing-observation-listing",
            canonical_product_id="product-amul-taaza",
            canonical_variant_id="variant-amul-taaza-500ml",
        )
    )
    client = TestClient(create_application(runtime=runtime))

    response = client.post(
        "/api/v1/cart/resolve",
        json={
            "items": [
                {
                    "item_id": "missing-observation",
                    "quantity": 1,
                    "platform": "blinkit",
                    "platform_listing_id": "missing-observation-listing",
                }
            ]
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["status"] == "unresolved"
    assert item["reason"] == "listing association references a missing observation"


def test_cart_resolution_rejects_item_without_backend_identity() -> None:
    client = TestClient(create_application())

    response = client.post(
        "/api/v1/cart/resolve",
        json={"items": [{"item_id": "frontend-only", "quantity": 1}]},
    )

    assert response.status_code == 422


def test_cart_candidate_discovery_returns_persisted_listing_candidate(tmp_path) -> None:
    runtime, _catalog, associations = _runtime(tmp_path, resolver=_resolver())
    client = TestClient(create_application(runtime=runtime))
    scrape = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))
    assert scrape.status_code == 200
    resolved = client.get("/api/v1/observations").json()[0]
    association = resolved["association"]
    observation = runtime.observation_registry.get(resolved["observation_id"])
    priced = observation.model_copy(
        update={
            "source_record_id": "valid-priced-record",
            "observed_selling_price": Money(currency="INR", minor_units=10000),
        }
    )
    runtime.observation_registry.register(priced)
    associations.register(
        CanonicalListingAssociation(
            observation_id=priced.observation_id,
            platform=association["platform"],
            platform_listing_id="valid-priced-listing",
            canonical_product_id=association["canonical_product_id"],
            canonical_variant_id=association["canonical_variant_id"],
        )
    )

    response = client.post(
        "/api/v1/cart/candidates",
        json={
            "items": [
                {
                    "item_id": "milk",
                    "quantity": 2,
                    "canonical_product_id": association["canonical_product_id"],
                    "canonical_variant_id": association["canonical_variant_id"],
                }
            ]
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["status"] == "candidates_available"
    candidate = next(
        candidate
        for candidate in item["candidates"]
        if candidate["platform_listing_id"] == "valid-priced-listing"
    )
    assert candidate["observation_id"] == priced.observation_id
    assert candidate["platform"] == association["platform"]
    assert candidate["readiness"] == "ready_for_allocation"


def test_cart_candidate_discovery_preserves_deterministic_item_and_candidate_order(tmp_path) -> None:
    runtime, _catalog, associations = _runtime(tmp_path, resolver=_resolver())
    client = TestClient(create_application(runtime=runtime))
    scrape = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))
    assert scrape.status_code == 200
    resolved = client.get("/api/v1/observations").json()[0]
    association = resolved["association"]
    second_observation = runtime.observation_registry.get(resolved["observation_id"]).model_copy(
        update={"source_record_id": "listing-a"}
    )
    runtime.observation_registry.register(second_observation)
    associations.register(
        CanonicalListingAssociation(
            observation_id=second_observation.observation_id,
            platform=association["platform"],
            platform_listing_id="listing-a",
            canonical_product_id=association["canonical_product_id"],
            canonical_variant_id=association["canonical_variant_id"],
        )
    )

    payload = {
        "items": [
            {
                "item_id": "second",
                "quantity": 2,
                "canonical_product_id": association["canonical_product_id"],
                "canonical_variant_id": association["canonical_variant_id"],
            },
            {
                "item_id": "first",
                "quantity": 1,
                "canonical_product_id": association["canonical_product_id"],
                "canonical_variant_id": association["canonical_variant_id"],
            },
        ]
    }
    response = client.post("/api/v1/cart/candidates", json=payload)

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["item_id"] for item in items] == ["second", "first"]
    assert [candidate["platform_listing_id"] for candidate in items[0]["candidates"]] == sorted(
        candidate["platform_listing_id"] for candidate in items[0]["candidates"]
    )


def test_cart_candidate_discovery_reports_no_candidates_and_rejects_invalid_input(tmp_path) -> None:
    application = create_application(Settings(_env_file=None, data_dir=tmp_path))
    client = TestClient(application)

    response = client.post(
        "/api/v1/cart/candidates",
        json={
            "items": [
                {
                    "item_id": "unknown",
                    "quantity": 1,
                    "canonical_product_id": "missing-product",
                    "canonical_variant_id": "missing-variant",
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "no_candidates"

    invalid = client.post("/api/v1/cart/candidates", json={"items": [{}]})
    assert invalid.status_code == 422


def test_cart_candidate_discovery_marks_missing_typed_price_not_ready(tmp_path) -> None:
    runtime, _catalog, associations = _runtime(tmp_path, resolver=_resolver())
    client = TestClient(create_application(runtime=runtime))
    scrape = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))
    assert scrape.status_code == 200
    resolved = client.get("/api/v1/observations").json()[0]
    association = resolved["association"]
    observation = runtime.observation_registry.get(resolved["observation_id"])
    unpriced = observation.model_copy(
        update={"source_record_id": "unpriced-record", "observed_selling_price": None}
    )
    runtime.observation_registry.register(unpriced)
    associations.register(
        CanonicalListingAssociation(
            observation_id=unpriced.observation_id,
            platform=association["platform"],
            platform_listing_id="unpriced-listing",
            canonical_product_id=association["canonical_product_id"],
            canonical_variant_id=association["canonical_variant_id"],
        )
    )

    response = client.post(
        "/api/v1/cart/candidates",
        json={
            "items": [
                {
                    "item_id": "milk",
                    "quantity": 1,
                    "canonical_product_id": association["canonical_product_id"],
                    "canonical_variant_id": association["canonical_variant_id"],
                }
            ]
        },
    )

    assert response.status_code == 200
    items = response.json()["items"]
    unpriced_candidate = next(
        candidate
        for candidate in items[0]["candidates"]
        if candidate["platform_listing_id"] == "unpriced-listing"
    )
    assert items[0]["status"] == "candidates_not_ready"
    assert unpriced_candidate["readiness"] == "not_ready_for_allocation"
    assert unpriced_candidate["readiness_reason"] == (
        "observation has no typed observed selling price"
    )


def test_cart_candidate_discovery_marks_unsupported_price_currency_not_ready(tmp_path) -> None:
    runtime, _catalog, associations = _runtime(tmp_path, resolver=_resolver())
    client = TestClient(create_application(runtime=runtime))
    scrape = client.post("/api/v1/scrape", json=_job().model_dump(mode="json"))
    assert scrape.status_code == 200
    resolved = client.get("/api/v1/observations").json()[0]
    association = resolved["association"]
    observation = runtime.observation_registry.get(resolved["observation_id"])
    unsupported = observation.model_copy(
        update={
            "source_record_id": "unsupported-currency-record",
            "observed_selling_price": Money(currency="USD", minor_units=1000),
        }
    )
    runtime.observation_registry.register(unsupported)
    associations.register(
        CanonicalListingAssociation(
            observation_id=unsupported.observation_id,
            platform=association["platform"],
            platform_listing_id="unsupported-currency-listing",
            canonical_product_id=association["canonical_product_id"],
            canonical_variant_id=association["canonical_variant_id"],
        )
    )

    response = client.post(
        "/api/v1/cart/candidates",
        json={
            "items": [
                {
                    "item_id": "milk",
                    "quantity": 1,
                    "canonical_product_id": association["canonical_product_id"],
                    "canonical_variant_id": association["canonical_variant_id"],
                }
            ]
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["status"] == "candidates_not_ready"
    candidate = next(
        candidate
        for candidate in item["candidates"]
        if candidate["platform_listing_id"] == "unsupported-currency-listing"
    )
    assert candidate["readiness"] == "not_ready_for_allocation"
    assert candidate["readiness_reason"] == (
        "observed selling price uses an unsupported currency"
    )
