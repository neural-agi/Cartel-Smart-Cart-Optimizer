"""Static consumer-navigation and UX-contract checks.

These guard the Phase K.4 correction: the sidebar label for each entry must
match the destination it points at, and ``/cart`` must be a persisted-list
basket rather than a dead local-cart surface. Browser rendering of the same
contract is asserted in ``tests/e2e/test_consumer_journey_browser.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND = REPO_ROOT / "frontend"


def _app_navigation() -> dict[str, str]:
    source = (FRONTEND / "components/layout/AppSidebar.tsx").read_text(encoding="utf-8")
    block = source.split("export const appNavigation = [", 1)[1].split("] as const", 1)[0]
    entries = re.findall(r'\{\s*label:\s*"([^"]+)",\s*href:\s*"([^"]+)"', block)
    assert entries, "appNavigation entries were not found"
    return dict(entries)


def test_every_navigation_label_matches_its_destination() -> None:
    navigation = _app_navigation()
    assert navigation == {
        "Home": "/home",
        "Search": "/search",
        "Lists": "/lists",
        "Cart": "/cart",
        "Optimize": "/optimize",
        "Results": "/results",
        "Wrapped": "/wrapped",
        "Profile": "/profile",
        "Settings": "/settings",
    }
    for label, href in navigation.items():
        assert href == f"/{label.lower()}", f"label {label!r} points at {href!r}"


def test_cart_is_backed_by_persisted_lists_not_local_cart_state() -> None:
    cart = (FRONTEND / "app/(app)/cart/page.tsx").read_text(encoding="utf-8")
    assert "useCartStore" not in cart
    assert "shoppingListsService" in cart
    assert "GET /api/v2/lists" in cart
    assert "/optimize?list_id=" in cart
    assert 'href="/lists"' in cart
    # No synthetic payable total, savings claim, or best-price surface.
    for forbidden in ("Subtotal", "savings", "best price", "best-price"):
        assert forbidden not in cart


def test_optimize_renders_status_guide_with_required_disclosures() -> None:
    optimize = (FRONTEND / "app/(app)/optimize/page.tsx").read_text(encoding="utf-8")
    assert "OptimizationStatusGuide" in optimize
    assert "<OptimizationStatusGuide result={consumerResult} />" in optimize

    guide = (FRONTEND / "components/consumer/OptimizationStatusGuide.tsx").read_text(
        encoding="utf-8"
    )
    assert '"ready"' in guide
    assert '"partial"' in guide
    assert '"unresolved"' in guide
    for disclosure in (
        "not a failed calculation",
        "Synthetic demo listings are simulated",
        "Real checkout totals are unavailable",
        "Fees, taxes, discounts, and serviceability are unknown",
        "does not show a payable total, savings figure, or best-price claim",
    ):
        assert disclosure in guide, disclosure
