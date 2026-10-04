from datetime import datetime, timezone
from types import SimpleNamespace

from app.product_intelligence.catalog.operator_review import OperatorReviewService
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from app.product_intelligence.catalog.identity_contract import IdentityComparison
from app.product_intelligence.models import Product, ProductVariant


def _observation():
    return SimpleNamespace(
        observation_id="obs-1", platform=SimpleNamespace(value="BLINKIT"),
        source_record_id="19512", normalized_name="Taaza Toned Milk",
        normalized_quantity="500 ml", observed_selling_price=None,
        availability_signal="12", platform_identifiers=(
            ("brand", "Amul"), ("retailer_product_id", "19512"),
            ("retailer_product_url", "https://blinkit.com/prn/x/prid/19512"),
        ), raw_artifact_reference=SimpleNamespace(
            source_reference="https://api.quickcommerceapi.com/v1/search",
            artifact_id="artifact-1", content_digest="a" * 64,
            capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            provider_id="quickcommerce", location_scope="test-location",
            provider_request_id="request-redacted",
        ),
    )


class _Registry:
    def __init__(self): self.items = []
    def register(self, association): self.items.append(association); return association


class _Resolver:
    _retailer_identity_adapters = {"BLINKIT": SimpleNamespace(adapt=lambda observation: observation)}
    def __init__(self, state): self.state = state
    def compare_identity(self, evidence, product, variant): return IdentityComparison(state=self.state, reason="test decision")


def _service(tmp_path, state="UNRESOLVED"):
    return OperatorReviewService(
        observation_registry=SimpleNamespace(get=lambda key: _observation() if key == "obs-1" else None),
        catalog=SimpleNamespace(), resolver=_Resolver(state), association_registry=_Registry(),
        audit_path=tmp_path / "review-audit.json",
    )


def _entities():
    return SimpleNamespace(canonical_product_id="product-1"), SimpleNamespace(canonical_variant_id="variant-1")


def test_inspection_exposes_real_evidence_and_provenance(tmp_path):
    detail = _service(tmp_path).inspect("obs-1")
    assert detail.retailer_product_id == "19512"
    assert detail.brand == "Amul"
    assert detail.provenance["provider_id"] == "quickcommerce"
    assert detail.provenance["location_scope"] == "test-location"


def test_non_exact_review_is_audited_without_association(tmp_path):
    service = _service(tmp_path)
    product, variant = _entities()
    audit = service.commit_existing(observation_id="obs-1", product=product, variant=variant, operator_id="operator-1")
    assert audit.decision == "rejected"
    assert audit.resolver_status == "UNRESOLVED"
    assert service.association_registry.items == []
    assert (tmp_path / "review-audit.json").exists()


def test_exact_review_creates_only_the_reviewed_association(tmp_path):
    service = _service(tmp_path, state="EXACT_MATCH")
    product, variant = _entities()
    audit = service.commit_existing(observation_id="obs-1", product=product, variant=variant, operator_id="operator-1")
    assert audit.decision == "associated"
    assert audit.association == CanonicalListingAssociation(
        observation_id="obs-1", platform="BLINKIT", platform_listing_id="19512",
        canonical_product_id="product-1", canonical_variant_id="variant-1",
    )
