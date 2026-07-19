from __future__ import annotations

from datetime import datetime, timezone

from app.cost_intelligence.context import DeterministicCostContextBuilder
from app.cost_intelligence.observation.types import (
    CheckoutObservation,
    CheckoutOfferObservation,
)
from app.cost_intelligence.offer import OfferEvaluationService
from app.product_intelligence.models import EvidenceReference


def main() -> None:
    observation = CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="raw/checkout/demo.json",
        capture_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        parser_version="checkout-v1",
        evidence_references=(EvidenceReference(source_type="artifact", source_id="demo"),),
        offers=(CheckoutOfferObservation(label="₹100 OFF"),),
    )
    context = DeterministicCostContextBuilder().build(observation)
    service = OfferEvaluationService()
    offer = observation.offers[0]
    first = service.evaluate(context, offer)
    second = service.evaluate(context, offer)

    print("context_id:", context.context_id)
    print("evaluation_id:", first.evaluation_id)
    print("offer_type:", first.offer_type.value)
    print("applicable:", first.applicable)
    print("immediate_discount:", first.immediate_discount)
    print("percentage_discount:", first.percentage_discount)
    print("deferred_value:", first.deferred_value)
    print("evidence_references:", first.evidence_references)
    print("replay_identical:", first == second)


if __name__ == "__main__":
    main()
