import json
from types import SimpleNamespace

from app.product_intelligence.catalog.population import (
    CatalogPopulationManifest,
    GovernedCatalogPopulationService,
)


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
