from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation
from app.product_intelligence.catalog.types import CatalogConflictError


class PersistedListingAssociations(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    associations: list[CanonicalListingAssociation] = Field(default_factory=list)


class FilesystemCanonicalListingAssociationStore:
    """Durable association records stored beside the authoritative catalog."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or (get_settings().data_dir / "product_intelligence" / "catalog")
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.association_path = self.root_dir / "listing_associations.json"

    def load(self) -> PersistedListingAssociations:
        if not self.association_path.exists():
            return PersistedListingAssociations()
        return PersistedListingAssociations.model_validate(
            json.loads(self.association_path.read_text(encoding="utf-8"))
        )

    def save(self, record: PersistedListingAssociations) -> None:
        temp_path = self.association_path.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps(record.model_dump(mode="json"), sort_keys=True, indent=2),
            encoding="utf-8",
        )
        os.replace(temp_path, self.association_path)


class FilesystemCanonicalListingAssociationRegistry:
    """Idempotent, fail-closed persistence for resolved listing associations."""

    def __init__(self, store: FilesystemCanonicalListingAssociationStore | None = None) -> None:
        self.store = store or FilesystemCanonicalListingAssociationStore()

    def register(self, association: CanonicalListingAssociation) -> CanonicalListingAssociation:
        record = self.store.load()
        self._validate_existing_record(record.associations)

        listing_key = self._listing_key(association)
        for existing in record.associations:
            if self._listing_key(existing) == listing_key:
                if self._mapping(existing) != self._mapping(association):
                    raise CatalogConflictError(
                        "listing association conflict; reassignment is not permitted"
                    )
                if existing == association:
                    return existing

            if existing.observation_id == association.observation_id and existing != association:
                raise CatalogConflictError(
                    f"conflicting association for observation_id={association.observation_id}"
                )

        updated = list(record.associations)
        updated.append(association.model_copy(deep=True))
        self.store.save(
            PersistedListingAssociations(schema_version=record.schema_version, associations=updated)
        )
        return association

    def get(self, platform: str, platform_listing_id: str) -> CanonicalListingAssociation | None:
        matches = [
            item for item in self.store.load().associations
            if self._listing_key(item) == (platform, platform_listing_id)
        ]
        self._validate_existing_record(matches)
        return matches[0] if matches else None

    def list_for_listing(
        self,
        platform: str,
        platform_listing_id: str,
    ) -> tuple[CanonicalListingAssociation, ...]:
        matches = tuple(
            item for item in self.store.load().associations
            if self._listing_key(item) == (platform, platform_listing_id)
        )
        self._validate_existing_record(matches)
        return tuple(sorted(matches, key=lambda item: item.observation_id))

    def all(self) -> tuple[CanonicalListingAssociation, ...]:
        associations = tuple(self.store.load().associations)
        self._validate_existing_record(associations)
        return tuple(
            sorted(associations, key=lambda item: (item.platform, item.platform_listing_id, item.observation_id))
        )

    @staticmethod
    def _listing_key(association: CanonicalListingAssociation) -> tuple[str, str]:
        return association.platform, association.platform_listing_id

    @staticmethod
    def _mapping(association: CanonicalListingAssociation) -> tuple[str, str]:
        return association.canonical_product_id, association.canonical_variant_id

    @classmethod
    def _validate_existing_record(cls, associations: tuple[CanonicalListingAssociation, ...] | list[CanonicalListingAssociation]) -> None:
        by_listing: dict[tuple[str, str], tuple[str, str]] = {}
        by_observation: dict[str, CanonicalListingAssociation] = {}
        for association in associations:
            listing_key = cls._listing_key(association)
            mapping = cls._mapping(association)
            previous_mapping = by_listing.get(listing_key)
            if previous_mapping is not None and previous_mapping != mapping:
                raise CatalogConflictError("persisted listing associations contain a reassignment conflict")
            previous_observation = by_observation.get(association.observation_id)
            if previous_observation is not None and previous_observation != association:
                raise CatalogConflictError(
                    f"persisted listing associations conflict for observation_id={association.observation_id}"
                )
            by_listing[listing_key] = mapping
            by_observation[association.observation_id] = association
