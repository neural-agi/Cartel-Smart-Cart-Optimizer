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
from app.cost_intelligence.fee.orchestrator import FeeEvaluationOrchestrator
from app.cost_intelligence.observation.types import (
    CheckoutFeeObservation,
    CheckoutLineItemObservation,
    CheckoutObservation,
)
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _observation() -> CheckoutObservation:
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/fees/orchestration-demo.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        capture_context_reference="demo/location/new-delhi",
        evidence_references=(
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/fees/orchestration-demo.html",
            ),
        ),
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=Money(currency="INR", minor_units=3100),
            ),
        ),
        fees=(
            CheckoutFeeObservation(label="Delivery Fee", amount=Money(currency="INR", minor_units=2900), raw_text="Delivery Fee"),
            CheckoutFeeObservation(label="Platform Fee", amount=Money(currency="INR", minor_units=1000), raw_text="Platform Fee"),
            CheckoutFeeObservation(label="Packaging Fee", amount=Money(currency="INR", minor_units=500), raw_text="Packaging Fee"),
            CheckoutFeeObservation(label="Small Cart Fee", amount=Money(currency="INR", minor_units=1500), raw_text="Small Cart Fee"),
        ),
    )


def main() -> None:
    observation = _observation()
    context = DeterministicCostContextBuilder().build(observation)
    orchestrator = FeeEvaluationOrchestrator()

    first = orchestrator.evaluate(context)
    second = orchestrator.evaluate(context.model_copy(deep=True))

    print("Context ID:")
    print(context.context_id)
    print()
    print("Number of Fees:")
    print(len(context.checkout_observation.fees))
    print()
    for index, result in enumerate(first, start=1):
        print(f"Fee {index}")
        print("-------")
        print("Reference:")
        print(result.fee_reference)
        print("Type:")
        print(result.fee_type.value)
        print("Evaluation ID:")
        print(result.evaluation_id)
        print()
    print("Replay Equality:")
    print(first == second)


if __name__ == "__main__":
    main()
