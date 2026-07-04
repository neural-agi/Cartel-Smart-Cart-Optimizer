from __future__ import annotations

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

from app.core.logging import configure_logging
from app.cost_intelligence.observation import (
    CheckoutFeeObservation,
    CheckoutLineItemObservation,
    CheckoutObservation,
    CheckoutObservationRegistrationRequest,
    CheckoutOfferObservation,
    CheckoutTotalObservation,
    DeterministicCheckoutObservationRegistry,
)
from app.cost_intelligence.shared import Money
from app.product_intelligence.models import EvidenceReference


def _money(minor_units: int, currency: str = "inr") -> Money:
    return Money(currency=currency, minor_units=minor_units)


def _evidence_reference(source_type: str, source_id: str) -> EvidenceReference:
    return EvidenceReference(
        source_type=source_type,
        source_id=source_id,
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        note="demo",
    )


def _observation() -> CheckoutObservation:
    return CheckoutObservation(
        platform="blinkit",
        source_artifact_reference="demo/checkout/blinkit/cart.html",
        capture_timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        parser_version="demo-checkout-parser-1",
        capture_context_reference="demo/location/new-delhi/session-001",
        evidence_references=(
            _evidence_reference("source_artifact", "demo/checkout/blinkit/cart.html"),
            _evidence_reference("evidence_record", "demo-evidence-1"),
        ),
        line_items=(
            CheckoutLineItemObservation(
                label="Amul Taaza Milk",
                quantity_text="500 ml",
                displayed_price=_money(3100, "inr"),
                reference_price=_money(3500, "inr"),
                raw_text="Amul Taaza Milk 500 ml ₹31",
            ),
        ),
        fees=(
            CheckoutFeeObservation(
                label="Delivery fee",
                amount=_money(2900, "inr"),
                raw_text="Delivery fee ₹29",
            ),
        ),
        offers=(
            CheckoutOfferObservation(
                label="10% off",
                amount=_money(1000, "inr"),
                raw_text="10% off up to ₹20",
            ),
        ),
        totals=(
            CheckoutTotalObservation(
                label="Cart total",
                amount=_money(8900, "inr"),
                raw_text="Cart total ₹89",
            ),
        ),
    )


async def main() -> None:
    configure_logging(log_level="INFO", json_logs=False)
    registry = DeterministicCheckoutObservationRegistry()
    observation = _observation()
    request = CheckoutObservationRegistrationRequest(observation=observation)

    first = await registry.register(request)
    second = await registry.register(
        CheckoutObservationRegistrationRequest(
            observation=observation.model_copy(deep=True)
        )
    )

    print("first_run")
    print(f"observation_id={first.observation_id}")
    print(json.dumps(first.observation.model_dump(mode="json"), indent=2, ensure_ascii=True))
    print("second_run")
    print(f"observation_id={second.observation_id}")
    print(json.dumps(second.observation.model_dump(mode="json"), indent=2, ensure_ascii=True))
    print("registry_size=", len(registry.list_checkout_observations()))


if __name__ == "__main__":
    asyncio.run(main())
