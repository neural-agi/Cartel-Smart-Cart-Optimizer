"""Retailer-specific adapters into the shared canonical identity contract."""

from __future__ import annotations

import re
from typing import Protocol
from urllib.parse import urlsplit

from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.catalog.identity_contract import (
    IdentityFact,
    ProductIdentityProfile,
    RetailerProductIdentityEvidence,
)


class RetailerIdentityAdapter(Protocol):
    """Translate retailer-native evidence; never decide canonical identity."""

    platform: str

    def adapt(self, observation: NormalizedObservation) -> RetailerProductIdentityEvidence: ...


class BlinkitIdentityAdapter:
    """Expose only identity facts currently represented in Blinkit observations.

    Blinkit ingestion carries explicit title, brand, category/quantity when
    available, native product ID, and product URL. It still does not infer a
    structured pack contract from free-form quantity text.
    """

    platform = "BLINKIT"
    _PRODUCT_PATH = re.compile(r"/prn/[^/]+/prid/([^/?#]+)")

    def adapt(self, observation: NormalizedObservation) -> RetailerProductIdentityEvidence:
        if observation.platform.value != self.platform:
            raise ValueError("Blinkit adapter cannot adapt another retailer observation")

        issues: list[str] = []
        identifiers = dict(observation.platform_identifiers)
        product_id = identifiers.get("retailer_product_id")
        product_url = identifiers.get("retailer_product_url")
        artifact = observation.raw_artifact_reference
        if artifact is None:
            issues.append("raw artifact provenance missing")
        else:
            try:
                source = urlsplit(artifact.source_reference)
                source_port = source.port
            except ValueError:
                source = None
                source_port = None
            provider_source_is_supported = (
                getattr(artifact, "provider_id", None) == "quickcommerce"
                and source is not None
                and source.hostname is not None
                and source.hostname.casefold() == "api.quickcommerceapi.com"
            )
            if (
                source is None
                or source.scheme != "https"
                or not (source.hostname in {"blinkit.com", "www.blinkit.com"} or provider_source_is_supported)
                or source_port not in (None, 443)
                or source.username is not None
                or source.password is not None
                or source.fragment
            ):
                issues.append("unsupported Blinkit source provenance")
        if not product_id:
            issues.append("authoritative retailer product ID missing")
        if not product_url:
            issues.append("authoritative product URL missing")
        else:
            try:
                parsed = urlsplit(product_url)
                product_port = parsed.port
            except ValueError:
                parsed = None
                product_port = None
            match = self._PRODUCT_PATH.fullmatch(parsed.path) if parsed is not None else None
            if (
                parsed is None
                or
                parsed.scheme != "https"
                or parsed.hostname not in {"blinkit.com", "www.blinkit.com"}
                or product_port not in (None, 443)
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or match is None
                or (product_id is not None and match.group(1) != product_id)
            ):
                issues.append("retailer product URL and product ID are inconsistent")

        product_type = None
        brand = None
        observed_brand = identifiers.get("brand")
        if observed_brand:
            brand_refs = self._field_evidence(observation, "brand")
            if brand_refs:
                brand = IdentityFact(
                    name="brand", value=observed_brand, assertion_status="asserted",
                    evidence_references=brand_refs,
                )
        if observation.normalized_category:
            category_refs = self._field_evidence(observation, "raw_category")
            if category_refs:
                product_type = IdentityFact(
                    name="product_type",
                    value=observation.normalized_category,
                    assertion_status="asserted",
                    evidence_references=category_refs,
                )

        profile = ProductIdentityProfile(brand=brand, product_type=product_type)
        return RetailerProductIdentityEvidence(
            observation=observation,
            identity=profile,
            descriptive_title=observation.normalized_name,
            evidence_issues=tuple(issues),
        )

    @staticmethod
    def _field_evidence(observation: NormalizedObservation, locator_field: str) -> tuple[tuple[str, str], ...]:
        refs = {
            (field.evidence_reference.source_type, field.evidence_reference.source_id)
            for field in observation.field_references
            if field.locator.rsplit(".", 1)[-1] == locator_field
        }
        return tuple(sorted(refs))
