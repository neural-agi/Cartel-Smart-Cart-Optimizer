"""Import one locally supplied Blinkit evidence artifact through Product Intelligence."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.core.config import Settings, get_settings
from app.data_ingestion.operator_evidence import import_validated_evidence, load_operator_evidence


async def import_evidence(
    manifest_path: Path,
    *,
    settings: Settings | None = None,
) -> dict[str, object]:
    evidence = load_operator_evidence(manifest_path)
    result = await import_validated_evidence(evidence, settings=settings or get_settings())
    observations = [
        {
            "observation_id": record.observation_id,
            "status": record.status.value,
            "resolution": record.resolution.status.value if record.resolution else None,
            "association_created": record.association is not None,
        }
        for record in result.observations
    ]
    return {
        "status": result.status,
        "evidence_digest": evidence.evidence_digest,
        "raw_artifact_id": (
            result.worker_result.artifact_reference.artifact_id
            if result.worker_result.artifact_reference is not None
            else None
        ),
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import a validated local Blinkit evidence manifest; performs no network access"
    )
    parser.add_argument("manifest", type=Path, help="local JSON evidence manifest")
    args = parser.parse_args()
    try:
        summary = asyncio.run(import_evidence(args.manifest))
    except Exception as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] in {"completed", "completed_with_failures"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
