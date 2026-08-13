from fastapi.testclient import TestClient

from app.core.config import Settings
from app.data_ingestion import FilesystemObservationRegistry
from app.main import create_application
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
