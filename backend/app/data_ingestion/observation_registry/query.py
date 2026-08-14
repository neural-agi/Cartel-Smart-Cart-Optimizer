from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.data_ingestion.types import NormalizedObservation
from app.product_intelligence.catalog.association_storage import (
    FilesystemCanonicalListingAssociationRegistry,
)
from app.product_intelligence.catalog.resolution import CanonicalListingAssociation


class RetailObservationQueryRecord(BaseModel):
    """Read-only observation data with an optional persisted association."""

    model_config = ConfigDict(frozen=True)

    observation_id: str
    observation: NormalizedObservation
    association: CanonicalListingAssociation | None = None


class RetailObservationQueryService:
    """Query durable observations without assigning unresolved meaning."""

    def __init__(
        self,
        *,
        observation_registry: ObservationRegistry,
        association_registry: FilesystemCanonicalListingAssociationRegistry,
    ) -> None:
        self.observation_registry = observation_registry
        self.association_registry = association_registry

    def list_observations(
        self,
        *,
        canonical_product_id: str | None = None,
        canonical_variant_id: str | None = None,
    ) -> tuple[RetailObservationQueryRecord, ...]:
        associations = self._association_by_observation()
        records = (
            RetailObservationQueryRecord(
                observation_id=observation.observation_id,
                observation=observation,
                association=associations.get(observation.observation_id),
            )
            for observation in self._list_registry_observations()
        )
        return tuple(
            record
            for record in records
            if self._matches(
                record.association,
                canonical_product_id=canonical_product_id,
                canonical_variant_id=canonical_variant_id,
            )
        )

    def get_observation(self, observation_id: str) -> RetailObservationQueryRecord | None:
        observation = self.observation_registry.get(observation_id)
        if observation is None:
            return None
        return RetailObservationQueryRecord(
            observation_id=observation.observation_id,
            observation=observation,
            association=self._association_by_observation().get(observation.observation_id),
        )

    def _list_registry_observations(self) -> tuple[NormalizedObservation, ...]:
        list_all = getattr(self.observation_registry, "list_all", None)
        if list_all is None:
            raise TypeError("observation registry does not support durable listing")
        return tuple(sorted(list_all(), key=lambda item: item.observation_id))

    def _association_by_observation(self) -> dict[str, CanonicalListingAssociation]:
        return {
            association.observation_id: association
            for association in self.association_registry.all()
        }

    @staticmethod
    def _matches(
        association: CanonicalListingAssociation | None,
        *,
        canonical_product_id: str | None,
        canonical_variant_id: str | None,
    ) -> bool:
        if canonical_product_id is None and canonical_variant_id is None:
            return True
        if association is None:
            return False
        return (
            (canonical_product_id is None or association.canonical_product_id == canonical_product_id)
            and (canonical_variant_id is None or association.canonical_variant_id == canonical_variant_id)
        )
