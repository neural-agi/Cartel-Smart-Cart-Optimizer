from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.product_intelligence.catalog.types import AuthoritativeCatalogRecord


logger = get_logger(__name__)

CATALOG_ROOT_DIRNAME = "product_intelligence"
CATALOG_SUBDIR = "catalog"
CATALOG_FILENAME = "catalog.json"


class CatalogFilesystemStore:
    """Append-only filesystem persistence for the authoritative catalog."""

    def __init__(self, root_dir: Path | None = None) -> None:
        settings = get_settings()
        self.root_dir = root_dir or (
            settings.data_dir / CATALOG_ROOT_DIRNAME / CATALOG_SUBDIR
        )
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.root_dir / CATALOG_FILENAME

    def load(self) -> AuthoritativeCatalogRecord:
        if not self.catalog_path.exists():
            return AuthoritativeCatalogRecord()
        payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        return AuthoritativeCatalogRecord.model_validate(payload)

    def save(self, record: AuthoritativeCatalogRecord) -> None:
        payload = json.dumps(
            record.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        tmp_path = self.catalog_path.with_suffix(".json.tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, self.catalog_path)
        logger.info(
            "authoritative_catalog_saved products=%s variants=%s path=%s",
            len(record.products),
            len(record.variants),
            str(self.catalog_path),
        )
