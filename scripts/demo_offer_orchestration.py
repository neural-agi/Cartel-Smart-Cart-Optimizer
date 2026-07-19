from __future__ import annotations

from datetime import datetime, timezone

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.observation.types import (
    CheckoutObservation,
    CheckoutOfferObservation,
)
from app.cost_intelligence.offer import OfferEvaluationOrchestrator
from app.product_intelligence.models import EvidenceReference


def main() -> None:
    observation = CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="raw/checkout/demo-orchestration.json",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="checkout-v1",
        evidence_references=(EvidenceReference(source_type="artifact", source_id="demo-orchestration"),),
        offers=(
            CheckoutOfferObservation(label="₹100 OFF"),
            CheckoutOfferObservation(label="10% OFF"),
            CheckoutOfferObservation(label="₹150 Cashback"),
        ),
    )
    context = DeterministicCostContextBuilder().build(observation)
    orchestrator = OfferEvaluationOrchestrator()
    first = orchestrator.evaluate(context)
    second = orchestrator.evaluate(context)

    print("context_id:", context.context_id)
    print("number_of_offers:", len(first))
    for result in first:
        print(
            result.evaluation_id,
            result.offer_reference,
            result.offer_type.value,
        )
    print("replay_equality:", first == second)


if __name__ == "__main__":
    main()
