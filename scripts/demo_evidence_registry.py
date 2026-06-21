import asyncio
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

if sys.platform.startswith("win"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.product_intelligence.evidence import FilesystemEvidenceRegistry
from app.product_intelligence.evidence.types import EvidenceRegistrationRequest


async def main() -> None:
    settings = get_settings()
    configure_logging(log_level=settings.log_level, json_logs=settings.log_json)

    registry = FilesystemEvidenceRegistry()
    request = EvidenceRegistrationRequest(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/milk/rendered.html",
        parser_version="demo-parser-1",
        capture_timestamp=datetime.now(timezone.utc),
        capture_context_reference="demo/location/new-delhi/session-001",
    )

    registration = await registry.register(request)
    bundle = await registry.assemble(registration.evidence_bundle)

    print("registration:")
    print(
        json.dumps(
            registration.model_dump(mode="json"),
            indent=2,
            ensure_ascii=True,
        )
    )
    print("bundle:")
    print(json.dumps(bundle.model_dump(mode="json"), indent=2, ensure_ascii=True))


if __name__ == "__main__":
    asyncio.run(main())
