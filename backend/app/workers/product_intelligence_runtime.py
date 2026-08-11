from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.data_ingestion.observation_registry.interface import ObservationRegistry
from app.data_ingestion.types import NormalizedObservation, ScrapeJob
from app.normalization.ingestion import DeterministicIngestionNormalizer
from app.product_intelligence.catalog import (
    CanonicalListingAssociation,
    DeterministicCanonicalListingResolver,
    FilesystemAuthoritativeCatalog,
    FilesystemCanonicalListingAssociationRegistry,
    ListingResolutionResult,
    ListingResolutionStatus,
)
from app.product_intelligence.execution import (
    ProductIntelligenceExecutionResult,
    ProductIntelligenceExecutionStatus,
    ProductIntelligenceExecutionTrigger,
)
from app.workers.local_ingestion import LocalIngestionWorker


class RuntimeObservationStatus(StrEnum):
    resolved = "resolved"
    association_unresolved = "association_unresolved"
    association_persistence_failed = "association_persistence_failed"
    observation_registration_failed = "observation_registration_failed"
    evidence_publication_failed = "evidence_publication_failed"
    catalog_snapshot_failed = "catalog_snapshot_failed"
    orchestrator_failed = "orchestrator_failed"


class RuntimeObservationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_id: str
    status: RuntimeObservationStatus
    observation: NormalizedObservation | None = None
    resolution: ListingResolutionResult | None = None
    association: CanonicalListingAssociation | None = None
    execution: ProductIntelligenceExecutionResult | None = None
    rationale: tuple[str, ...] = Field(default_factory=tuple)


class ProductIntelligenceRuntimeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str
    status: str
    worker_result: object
    observations: tuple[RuntimeObservationResult, ...] = Field(default_factory=tuple)
    rationale: tuple[str, ...] = Field(default_factory=tuple)


class ProductIntelligenceRuntime:
    """Compose one ScrapeJob through ingestion and Product Intelligence."""

    def __init__(
        self,
        *,
        ingestion_worker: LocalIngestionWorker,
        normalizer: DeterministicIngestionNormalizer,
        observation_registry: ObservationRegistry,
        catalog: FilesystemAuthoritativeCatalog,
        resolver: DeterministicCanonicalListingResolver,
        association_registry: FilesystemCanonicalListingAssociationRegistry,
        execution_trigger: ProductIntelligenceExecutionTrigger,
    ) -> None:
        self.ingestion_worker = ingestion_worker
        self.normalizer = normalizer
        self.observation_registry = observation_registry
        self.catalog = catalog
        self.resolver = resolver
        self.association_registry = association_registry
        self.execution_trigger = execution_trigger

    async def execute(self, job: ScrapeJob) -> ProductIntelligenceRuntimeResult:
        worker_result = await self.ingestion_worker.execute(job)
        if worker_result.parsed_batch is None:
            return ProductIntelligenceRuntimeResult(
                job_id=worker_result.job_id,
                status="ingestion_failed",
                worker_result=worker_result,
                rationale=(worker_result.failed_stage or "ingestion failed",),
            )

        try:
            normalized = self.normalizer.normalize(worker_result.parsed_batch)
        except Exception as exc:
            return ProductIntelligenceRuntimeResult(
                job_id=worker_result.job_id,
                status="normalization_failed",
                worker_result=worker_result,
                rationale=(str(exc),),
            )

        records = tuple(
            [await self._execute_observation(observation) for observation in normalized]
        )
        statuses = {record.status for record in records}
        if not statuses:
            status = "completed"
        elif statuses == {RuntimeObservationStatus.resolved}:
            status = "completed"
        else:
            status = "completed_with_failures"
        return ProductIntelligenceRuntimeResult(
            job_id=worker_result.job_id,
            status=status,
            worker_result=worker_result,
            observations=records,
            rationale=(f"processed_observations={len(records)}",),
        )

    async def _execute_observation(
        self,
        observation: NormalizedObservation,
    ) -> RuntimeObservationResult:
        try:
            registered = self.observation_registry.register(observation)
        except Exception as exc:
            return RuntimeObservationResult(
                observation_id=observation.observation_id,
                status=RuntimeObservationStatus.observation_registration_failed,
                observation=observation,
                rationale=(str(exc),),
            )

        resolution = self.resolver.resolve(registered, self.catalog.load_state())
        if resolution.status is not ListingResolutionStatus.mapped:
            execution = await self.execution_trigger.execute_resolution(registered, resolution)
            return RuntimeObservationResult(
                observation_id=registered.observation_id,
                status=RuntimeObservationStatus.association_unresolved,
                observation=registered,
                resolution=resolution,
                execution=execution,
                rationale=resolution.rationale,
            )

        association = resolution.association
        if association is None:
            return RuntimeObservationResult(
                observation_id=registered.observation_id,
                status=RuntimeObservationStatus.association_unresolved,
                observation=registered,
                resolution=resolution,
                rationale=("mapped resolution did not include an association",),
            )
        try:
            persisted = self.association_registry.register(association)
        except Exception as exc:
            return RuntimeObservationResult(
                observation_id=registered.observation_id,
                status=RuntimeObservationStatus.association_persistence_failed,
                observation=registered,
                resolution=resolution,
                association=association,
                rationale=(str(exc),),
            )

        execution = await self.execution_trigger.execute_resolution(registered, resolution)
        status = self._execution_status(execution.status)
        return RuntimeObservationResult(
            observation_id=registered.observation_id,
            status=status,
            observation=registered,
            resolution=resolution,
            association=persisted,
            execution=execution,
            rationale=execution.rationale,
        )

    @staticmethod
    def _execution_status(
        status: ProductIntelligenceExecutionStatus,
    ) -> RuntimeObservationStatus:
        return {
            ProductIntelligenceExecutionStatus.executed: RuntimeObservationStatus.resolved,
            ProductIntelligenceExecutionStatus.evidence_publication_failed: RuntimeObservationStatus.evidence_publication_failed,
            ProductIntelligenceExecutionStatus.catalog_snapshot_failed: RuntimeObservationStatus.catalog_snapshot_failed,
            ProductIntelligenceExecutionStatus.orchestrator_failed: RuntimeObservationStatus.orchestrator_failed,
        }.get(status, RuntimeObservationStatus.association_unresolved)
