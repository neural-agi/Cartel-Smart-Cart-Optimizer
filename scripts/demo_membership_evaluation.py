from __future__ import annotations

import asyncio
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

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.membership.orchestrator import MembershipEvaluationOrchestrator
from app.cost_intelligence.observation.types import (
    CheckoutLineItemObservation,
    CheckoutMembershipObservation,
    CheckoutObservation,
)
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _observation() -> CheckoutObservation:
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/membership/orchestration-demo.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        capture_context_reference="demo/location/new-delhi",
        evidence_references=(
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/membership/orchestration-demo.html",
            ),
        ),
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=Money(currency="INR", minor_units=3100),
            ),
        ),
        memberships=(
            CheckoutMembershipObservation(
                label="Prime membership applied",
                raw_text="Prime membership applied",
            ),
            CheckoutMembershipObservation(
                label="Prime members save ₹40",
                raw_text="Prime members save ₹40",
            ),
            CheckoutMembershipObservation(
                label="Not a member",
                raw_text="Not a member",
            ),
        ),
    )


def main() -> None:
    observation = _observation()
    context = DeterministicCostContextBuilder().build(observation)
    orchestrator = MembershipEvaluationOrchestrator()

    first = orchestrator.evaluate(context)
    second = orchestrator.evaluate(context.model_copy(deep=True))

    print("Context ID:")
    print(context.context_id)
    print()
    for index, result in enumerate(first, start=1):
        print(f"Membership {index}")
        print("-----------")
        print("Reference:")
        print(result.membership_reference)
        print("Eligible:")
        print(result.eligible)
        print("Benefit Value:")
        print(None if result.benefit_value is None else result.benefit_value.model_dump(mode="json"))
        print("Evaluation ID:")
        print(result.evaluation_id)
        print()
    print("Replay Equality:")
    print(first == second)


if __name__ == "__main__":
    main()
