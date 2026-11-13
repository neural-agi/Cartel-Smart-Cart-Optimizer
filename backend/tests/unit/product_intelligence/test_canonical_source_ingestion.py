from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.product_intelligence.canonical_source.providers import OpenFoodFactsProvider
from app.product_intelligence.canonical_source.service import CanonicalEvidenceIngestionService
from app.product_intelligence.canonical_source.storage import CanonicalEvidenceFilesystemStore
from app.product_intelligence.canonical_source.types import CanonicalEvidenceAdmission
from app.product_intelligence.catalog.service import FilesystemAuthoritativeCatalog
from app.product_intelligence.catalog.storage import CatalogFilesystemStore
from app.product_intelligence.models import (
    AttributeAssertion,
    BrandReference,
    CategoryReference,
    EvidenceReference,
    Measurement,
    PackConfiguration,
    PackKind,
    Product,
    ProductVariant,
    QuantityDimension,
    IdentityStatus,
    ProductLifecycleStatus,
    VariantLifecycleStatus,
)


def _payload() -> dict[str, object]:
    return {
        "status": 1,
        "product": {
            "code": "8901000000000",
            "product_name": "Example Milk",
            "brands": "Example Brand",
            "quantity": "500 ml",
            "categories": "Dairy drinks",
            "last_modified_t": 1700000000,
        },
    }


def _artifact():
    from app.product_intelligence.canonical_source.types import CanonicalEvidenceArtifact

    return CanonicalEvidenceArtifact(
        artifact_id="open_food_facts:8901000000000:1700000000:test",
        source="open_food_facts",
        source_record_id="8901000000000",
        source_revision="1700000000",
        retrieved_at=datetime.now(timezone.utc),
        content_digest="a" * 64,
        provider_version="open-food-facts-v1",
        raw_payload=_payload(),
        evidence_references=(EvidenceReference(source_type="open_food_facts", source_id="8901000000000"),),
    )


def _entities() -> tuple[Product, ProductVariant]:
    evidence = [EvidenceReference(source_type="open_food_facts", source_id="artifact-1")]
    product = Product(
        canonical_product_id="product-example-milk",
        product_identity_status=IdentityStatus.established,
        brand_reference=BrandReference(canonical_brand_name="Example Brand", display_label="Example Brand", evidence_references=evidence),
        product_type="milk",
        canonical_display_name="Example Milk",
        identity_attributes=[AttributeAssertion(name="brand", value="Example Brand", role="identity_critical", evidence_references=evidence)],
        canonical_category_reference=CategoryReference(category_id="dairy", review_state="approved"),
        lifecycle_status=ProductLifecycleStatus.active,
        catalog_revision="operator-1",
        evidence_references=evidence,
    )
    measurement = Measurement(value=Decimal("500"), unit="ml", dimension=QuantityDimension.volume, content_basis="net_content")
    variant = ProductVariant(
        canonical_variant_id="variant-example-milk-500ml",
        canonical_product_id=product.canonical_product_id,
        variant_identity_status=IdentityStatus.established,
        variant_identity_attributes=[AttributeAssertion(name="gtin", value="8901000000000", role="identity_critical", evidence_references=evidence)],
        pack_configuration=PackConfiguration(pack_kind=PackKind.single_unit, consumer_unit_count=1, content_per_consumer_unit=measurement, total_declared_content=measurement, pack_configuration_status="complete"),
        lifecycle_status=VariantLifecycleStatus.active,
        catalog_revision="operator-1",
        evidence_references=evidence,
    )
    return product, variant


class _FakeProvider:
    async def fetch(self, source_record_id: str):
        assert source_record_id == "8901000000000"
        return _artifact()

    def normalize(self, artifact):
        return OpenFoodFactsProvider.normalize(artifact)


@pytest.mark.asyncio
async def test_open_food_facts_normalization_is_source_evidence_not_canonical_identity():
    candidate = OpenFoodFactsProvider.normalize(_artifact())
    assert candidate.source_record_id == "8901000000000"
    assert candidate.candidate_id != candidate.source_record_id
    assert {claim.name for claim in candidate.claims} >= {"product_name", "brand", "quantity", "gtin"}


@pytest.mark.asyncio
async def test_ingest_requires_explicit_approval_before_catalog_admission(tmp_path):
    service = CanonicalEvidenceIngestionService(
        provider=_FakeProvider(),
        store=CanonicalEvidenceFilesystemStore(tmp_path / "evidence"),
        catalog=FilesystemAuthoritativeCatalog(CatalogFilesystemStore(tmp_path / "catalog")),
    )
    review = await service.ingest("8901000000000")
    assert review.candidate.status.value == "pending"
    with pytest.raises(ValueError, match="explicit approval"):
        service.admit(CanonicalEvidenceAdmission(candidate_id=review.candidate.candidate_id, approval_reference="approval-1", product=_entities()[0], variant=_entities()[1]))

    approved = service.approve(review.candidate.candidate_id, approval_reference="approval-1", rationale="operator verified source record")
    assert approved.decision_reference == "approval-1"
    product, variant = service.admit(CanonicalEvidenceAdmission(candidate_id=review.candidate.candidate_id, approval_reference="approval-1", product=_entities()[0], variant=_entities()[1]))
    assert product.canonical_product_id == "product-example-milk"
    assert variant.canonical_variant_id == "variant-example-milk-500ml"
    assert len(service.catalog.load_state().variants) == 1


@pytest.mark.asyncio
async def test_repeated_ingestion_is_idempotent_and_changed_artifact_identity_fails_closed(tmp_path):
    service = CanonicalEvidenceIngestionService(
        provider=_FakeProvider(),
        store=CanonicalEvidenceFilesystemStore(tmp_path / "evidence"),
        catalog=FilesystemAuthoritativeCatalog(CatalogFilesystemStore(tmp_path / "catalog")),
    )
    first = await service.ingest("8901000000000")
    second = await service.ingest("8901000000000")
    assert first == second
