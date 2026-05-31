import json
from datetime import datetime, timezone
from pathlib import Path
from re import sub

from app.core.config import get_settings
from app.core.logging import get_logger
from app.scrapers.base.types import RawHttpResponse


logger = get_logger(__name__)


def _slugify(value: str) -> str:
    slug = sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "query"


def persist_raw_response(
    *,
    platform: str,
    query: str,
    response: RawHttpResponse,
    extension: str = "html",
) -> Path:
    settings = get_settings()
    target_dir = settings.raw_data_dir / platform
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(query)
    body_path = target_dir / f"{timestamp}_{slug}.{extension}"
    metadata_path = target_dir / f"{timestamp}_{slug}.meta.json"

    body_path.write_bytes(response.body)
    metadata_path.write_text(
        json.dumps(
            {
                "platform": platform,
                "query": query,
                "url": response.url,
                "status_code": response.status_code,
                "content_type": response.content_type,
                "headers": dict(response.headers),
                "saved_at": timestamp,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    logger.info(
        "scraper_raw_persisted platform=%s query=%s path=%s",
        platform,
        query,
        str(body_path),
    )
    return body_path


def persist_debug_artifact(
    *,
    platform: str,
    query: str,
    suffix: str,
    content: bytes,
) -> Path:
    settings = get_settings()
    target_dir = settings.raw_data_dir / platform
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(query)
    artifact_path = target_dir / f"{timestamp}_{slug}.{suffix}"
    artifact_path.write_bytes(content)

    logger.info(
        "scraper_debug_artifact_persisted platform=%s query=%s path=%s",
        platform,
        query,
        str(artifact_path),
    )
    return artifact_path
