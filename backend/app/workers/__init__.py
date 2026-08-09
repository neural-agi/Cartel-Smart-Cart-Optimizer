"""Worker package."""

from app.workers.local_ingestion import LocalIngestionWorker

__all__ = ["LocalIngestionWorker"]
