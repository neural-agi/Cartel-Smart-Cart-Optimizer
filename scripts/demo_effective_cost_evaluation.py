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
from app.cost_intelligence.effective_cost.orchestrator import (
    EffectiveCostEvaluationOrchestrator,
)
from app.cost_intelligence.evaluation.types import (
    FeeEvaluationResult,
    MembershipEvaluationResult,
    OfferEvaluationResult,
    OfferType,
)
from app.cost_intelligence.fee.types import FeeType
from app.cost_intelligence.observation.types import (
    CheckoutLineItemObservation,
    CheckoutObservation,
    CheckoutTotalObservation,
)
from app.cost_intelligence.shared.money import Money
from app.product_intelligence.models import EvidenceReference


def _context() -> tuple[DeterministicCostContextBuilder, CheckoutObservation]:
    observation = CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/raw/blinkit/effective-cost/demo.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-parser-v1",
        capture_context_reference="demo/location/new-delhi",
        evidence_references=(
            EvidenceReference(
                source_type="source_artifact",
                source_id="demo/raw/blinkit/effective-cost/demo.html",
            ),
        ),
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=Money(currency="INR", minor_units=3100),
            ),
        ),
        totals=(
            CheckoutTotalObservation(
                label="Subtotal",
                amount=Money(currency="INR", minor_units=1000),
            ),
        ),
    )
    builder = DeterministicCostContextBuilder()
    return builder, observation


def main() -> None:
    builder, observation = _context()
    context = builder.build(observation)
    orchestrator = EffectiveCostEvaluationOrchestrator()

    shared = tuple(context.evidence_references)
    offer_results = (
        OfferEvaluationResult(
            evaluation_id="offer-1",
            offer_reference="offer-1",
            offer_type=OfferType.FIXED_DISCOUNT,
            applicable=True,
            immediate_discount=Money(currency="INR", minor_units=100),
            evidence_references=shared,
        ),
        OfferEvaluationResult(
            evaluation_id="offer-2",
            offer_reference="offer-2",
            offer_type=OfferType.CASHBACK,
            applicable=True,
            deferred_value=Money(currency="INR", minor_units=50),
            evidence_references=shared,
        ),
    )
    fee_results = (
        FeeEvaluationResult(
            evaluation_id="fee-1",
            fee_reference="fee-1",
            fee_type=FeeType.DELIVERY,
            applicable=True,
            fee_amount=Money(currency="INR", minor_units=20),
            evidence_references=shared,
        ),
        FeeEvaluationResult(
            evaluation_id="fee-2",
            fee_reference="fee-2",
            fee_type=FeeType.PLATFORM,
            applicable=True,
            fee_amount=Money(currency="INR", minor_units=5),
            evidence_references=shared,
        ),
    )
    membership_results = (
        MembershipEvaluationResult(
            evaluation_id="membership-1",
            membership_reference="membership-1",
            eligible=True,
            benefit_value=Money(currency="INR", minor_units=10),
            evidence_references=shared,
        ),
    )

    first = orchestrator.evaluate(context, offer_results, fee_results, membership_results)
    second = orchestrator.evaluate(
        context.model_copy(deep=True),
        tuple(result.model_copy(deep=True) for result in offer_results),
        tuple(result.model_copy(deep=True) for result in fee_results),
        tuple(result.model_copy(deep=True) for result in membership_results),
    )

    print("Evaluation ID:")
    print(first.evaluation_id)
    print()
    print("Effective Cost:")
    print(None if first.effective_cost is None else first.effective_cost.model_dump(mode="json"))
    print()
    print("Deferred Value:")
    print(None if first.deferred_value is None else first.deferred_value.model_dump(mode="json"))
    print()
    print("Immediate Discounts:")
    print([money.model_dump(mode="json") for money in first.immediate_discounts])
    print()
    print("Fees:")
    print([money.model_dump(mode="json") for money in first.fees])
    print()
    print("Unknown Components:")
    print(list(first.unknown_components))
    print()
    print("Replay Equality:")
    print(first == second)


if __name__ == "__main__":
    main()
