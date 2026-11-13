"""End-to-end consumer journey browser coverage.

This test drives the real Next.js frontend and the real FastAPI backend. It is
skipped unless ``E2E_BASE_URL`` points at a running frontend and
``E2E_DATABASE_URL`` points at the isolated ``cartel_test`` database used by that
backend. The harness in ``scripts/e2e/run_consumer_journey.py`` starts both.

The journey deliberately uses the checked-in ``CARTEL_DEMO`` synthetic fixture
dataset. Synthetic prices and availability must never be presented as live
retailer evidence, and the optimization must never produce a payable plan from
them.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Browser, Page, expect, sync_playwright
from sqlalchemy import create_engine, text

BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")
BACKEND_URL = os.environ.get("E2E_BACKEND_URL", "").rstrip("/")
DATABASE_URL = os.environ.get("E2E_DATABASE_URL", "")
PASSWORD = "correct-horse-battery-staple-1"
LIST_NAME = "Synthetic Demo Journey List"
REQUEST_LOG = os.environ.get("E2E_REQUEST_LOG", "")

# Hosts and paths that would indicate a retailer-bound call. The showcase must
# never reach any of these; the synthetic catalog is local fixture data.
RETAILER_MARKERS = (
    "blinkit",
    "swiggy",
    "instamart",
    "zepto",
    "bigbasket",
    "jiomart",
    "dunzo",
    "amazon.",
    "flipkart",
)
OPERATOR_ONLY_PATHS = ("/api/v1/cart/optimize", "/api/v1/retailer", "/api/v1/scrape")

NAVIGATION = {
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

pytestmark = pytest.mark.skipif(
    not BASE_URL or not DATABASE_URL,
    reason="set E2E_BASE_URL and E2E_DATABASE_URL to run the browser journey",
)


def _database_url() -> str:
    if DATABASE_URL.startswith("postgresql://"):
        return DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    return DATABASE_URL


@pytest.fixture(scope="module")
def engine():
    engine = create_engine(_database_url(), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment guard
        engine.dispose()
        pytest.fail(f"E2E database is not reachable: {type(exc).__name__}")
    yield engine
    engine.dispose()


def _outbox_token(engine, email: str) -> str:
    deadline = time.monotonic() + 20
    with engine.connect() as connection:
        while time.monotonic() < deadline:
            body = connection.execute(
                text(
                    "SELECT body FROM email_outbox_events "
                    "WHERE lower(recipient) = lower(:recipient) "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"recipient": email},
            ).scalar()
            if body:
                match = re.search(r"#token=([A-Za-z0-9_-]+)", body)
                if match:
                    return match.group(1)
            connection.rollback()
            time.sleep(0.25)
    pytest.fail("verification email was not queued in the outbox")


def _signup(page: Page, email: str) -> None:
    page.goto(f"{BASE_URL}/signup")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_role("status")).to_contain_text("If this email can be verified")


def _verify(page: Page, token: str) -> None:
    page.goto(f"{BASE_URL}/verify-email#token={token}")
    page.wait_for_url(re.compile(r"/home$"), timeout=30_000)


def _create_verified_user(page: Page, engine, prefix: str) -> str:
    email = f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"
    _signup(page, email)
    _verify(page, _outbox_token(engine, email))
    return email


def _assert_session_restored(page: Page) -> None:
    page.reload()
    page.wait_for_url(re.compile(r"/home$"), timeout=30_000)
    expect(
        page.get_by_role("heading", name=re.compile("Tell Cartel what you need", re.I))
    ).to_be_visible()


def _list_items(engine, list_id: str) -> list[dict]:
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT query, resolution_status, canonical_product_id, "
                    "canonical_variant_id, display_name_snapshot, source_platform, "
                    "source_listing_id, source_observation_id "
                    "FROM shopping_list_items "
                    "WHERE list_id = CAST(:list_id AS uuid)"
                ),
                {"list_id": list_id},
            ).mappings()
        ]


def _optimization_record(engine, request_id: str) -> dict:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT shopping_list_id::text AS shopping_list_id, list_revision, "
                "status, result_snapshot "
                "FROM optimization_requests WHERE request_id = :request_id"
            ),
            {"request_id": request_id},
        ).mappings().one()
        plan_count = connection.execute(
            text(
                "SELECT count(*) FROM optimization_plans p "
                "JOIN optimization_requests r ON r.id = p.request_record_id "
                "WHERE r.request_id = :request_id"
            ),
            {"request_id": request_id},
        ).scalar_one()
    record = dict(row)
    record["plan_count"] = plan_count
    return record


def _search(page: Page, query: str, expected_count: int) -> None:
    page.get_by_role("textbox", name="Search groceries").fill(query)
    page.get_by_role("button", name="Search", exact=True).click()
    expect(page.get_by_test_id("search-result")).to_have_count(expected_count)


def _add_first_result(page: Page) -> None:
    first = page.get_by_test_id("search-result").first
    first.get_by_label("Select this exact variant").check()
    first.get_by_role("button", name="Add selected variant to list").click()
    expect(first.get_by_role("status")).to_contain_text(f"Saved to {LIST_NAME}.")


class RequestRecorder:
    """Records browser network requests for the step-15 egress guard."""

    def __init__(self) -> None:
        self.urls: list[str] = []
        self.retailer_bound: list[str] = []
        self.operator_only: list[str] = []

    def record(self, request) -> None:
        url = request.url
        self.urls.append(url)
        lowered = url.lower()
        if any(marker in lowered for marker in RETAILER_MARKERS):
            self.retailer_bound.append(url)
        if any(path in lowered for path in OPERATOR_ONLY_PATHS):
            self.operator_only.append(url)

    def attach(self, page: Page) -> None:
        page.on("request", self.record)

    def write(self) -> None:
        if REQUEST_LOG:
            Path(REQUEST_LOG).write_text("\n".join(self.urls), encoding="utf-8")


def _run_journey(browser: Browser, engine) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.set_default_timeout(20_000)
    recorder = RequestRecorder()
    recorder.attach(page)

    # Signup, email verification, and reload-based session restoration.
    _create_verified_user(page, engine, "journey-a")
    _assert_session_restored(page)

    # Create a persistent list and add an explicitly unresolved request.
    page.goto(f"{BASE_URL}/lists")
    expect(page.get_by_role("heading", name="Shopping lists")).to_be_visible()
    page.get_by_label("New list name").fill(LIST_NAME)
    page.get_by_role("button", name="Create list").click()
    expect(page.get_by_role("heading", name=LIST_NAME)).to_be_visible()

    page.get_by_label("Item to add").fill("Cartel Demo Unmatched Item")
    page.get_by_label("Quantity", exact=True).fill("1")
    page.get_by_role("button", name="Add item").click()
    unmatched = page.get_by_test_id("shopping-list-item").filter(
        has_text="Cartel Demo Unmatched Item"
    )
    expect(unmatched).to_be_visible()
    expect(unmatched).to_contain_text("product match still unresolved")

    # Search and select an exact synthetic variant. The synthetic lane must be
    # visibly labelled and must not be described as live retailer evidence.
    page.goto(f"{BASE_URL}/search")
    list_select = page.locator("#shopping-list-target")
    expect(list_select).to_be_enabled()
    list_id = list_select.input_value()
    assert list_id

    _search(page, "500 ml", 2)
    expect(
        page.get_by_role("status").filter(has_text="synthetic")
    ).to_be_visible()
    first_milk = page.get_by_test_id("search-result").first
    expect(first_milk).to_contain_text("Synthetic demo · not live retailer evidence")
    expect(first_milk).to_contain_text("Synthetic price INR 28.00")
    expect(first_milk).to_contain_text("Simulated availability: available")
    _add_first_result(page)

    # A second exact variant with an honest unavailable state.
    _search(page, "Cartel Demo Basmati Rice", 4)
    results_rice = page.get_by_test_id("search-result")
    expect(results_rice.filter(has_text="Simulated availability: unavailable")).to_have_count(1)
    _add_first_result(page)

    # Persistence and exact variant identity are verified in PostgreSQL, not
    # just in React state.
    items = _list_items(engine, list_id)
    assert len(items) == 3, items
    by_name = {item["display_name_snapshot"] or item["query"]: item for item in items}
    assert set(by_name) == {
        "Cartel Demo Toned Milk",
        "Cartel Demo Basmati Rice",
        "Cartel Demo Unmatched Item",
    }

    exact_milk = by_name["Cartel Demo Toned Milk"]
    assert exact_milk["resolution_status"] == "exact_confirmed"
    assert exact_milk["canonical_product_id"] == "cartel-demo-product-milk"
    assert exact_milk["canonical_variant_id"] == "cartel-demo-variant-milk-500ml"
    assert exact_milk["source_platform"] == "CARTEL_DEMO"
    assert exact_milk["source_listing_id"] == "cartel-demo-listing-milk-500ml-a"
    assert exact_milk["source_observation_id"]

    exact_rice = by_name["Cartel Demo Basmati Rice"]
    assert exact_rice["resolution_status"] == "exact_confirmed"
    assert exact_rice["canonical_product_id"] == "cartel-demo-product-rice"
    assert exact_rice["canonical_variant_id"] == "cartel-demo-variant-rice-1kg"
    assert exact_rice["source_platform"] == "CARTEL_DEMO"
    assert exact_rice["source_listing_id"] == "cartel-demo-listing-rice-1kg-a"
    assert exact_rice["source_observation_id"]

    unmatched = by_name["Cartel Demo Unmatched Item"]
    assert unmatched["resolution_status"] == "unresolved"
    assert unmatched["canonical_product_id"] is None
    assert unmatched["canonical_variant_id"] is None
    assert unmatched["source_observation_id"] is None

    # A browser reload must restore the persisted list, including synthetic
    # labels and the unresolved request.
    page.goto(f"{BASE_URL}/lists")
    page.reload()
    persisted = page.get_by_test_id("shopping-list-item")
    expect(persisted).to_have_count(3)
    expect(persisted.filter(has_text="Cartel Demo Toned Milk")).to_contain_text(
        "Synthetic demo selection · not live retailer evidence"
    )
    expect(persisted.filter(has_text="Cartel Demo Basmati Rice")).to_contain_text(
        "Synthetic demo"
    )
    expect(persisted.filter(has_text="Cartel Demo Unmatched Item")).to_contain_text(
        "product match still unresolved"
    )

    # Optimize the persisted revision. Synthetic evidence may produce observed
    # synthetic prices, but never a payable plan, fees, or checkout total.
    page.get_by_test_id("optimize-list").click()
    page.wait_for_url(re.compile(r"/optimize\?list_id=.*revision=\d+"))
    page.get_by_test_id("optimize-revision").click()
    result = page.get_by_test_id("consumer-optimization-result")
    expect(result).to_be_visible()
    expect(page.get_by_test_id("consumer-optimization-status")).to_have_text(
        "Some items need review"
    )
    expect(
        result.get_by_role("status").filter(has_text="Cartel Demo synthetic catalog")
    ).to_be_visible()
    expect(result).to_contain_text("Synthetic observed unit price")
    expect(result).to_contain_text("Fees and taxes: unknown")
    expect(result).to_contain_text("checkout totals are unknown")
    expect(result).not_to_contain_text("A plan is ready to review")
    expect(result).not_to_contain_text("Selected retailer groups")

    page.wait_for_url(re.compile(r"request_id=[0-9a-f-]+"))
    request_id = parse_qs(urlparse(page.url).query)["request_id"][0]

    # Reload the persisted request URL; the same honest result must return.
    page.reload()
    expect(page.get_by_test_id("consumer-optimization-result")).to_be_visible()
    expect(page.get_by_test_id("consumer-optimization-status")).to_have_text(
        "Some items need review"
    )
    assert request_id in page.url

    # The status guide must explain ready, partial, and unresolved results, and
    # state the synthetic / checkout / unknown / not-a-failure disclosures.
    guide = page.get_by_test_id("optimization-status-guide")
    expect(guide).to_be_visible()
    expect(page.get_by_test_id("optimization-status-current")).to_have_text("unresolved")
    expect(page.get_by_test_id("status-guide-ready")).to_contain_text("Ready")
    expect(page.get_by_test_id("status-guide-partial")).to_contain_text("Partial")
    expect(page.get_by_test_id("status-guide-partial")).to_contain_text(
        "not a failed calculation"
    )
    expect(page.get_by_test_id("status-guide-unresolved")).to_contain_text("Unresolved")
    expect(page.get_by_test_id("status-guide-synthetic")).to_contain_text("simulated")
    expect(page.get_by_test_id("status-guide-checkout")).to_contain_text(
        "checkout totals are unavailable"
    )
    expect(page.get_by_test_id("status-guide-unknowns")).to_contain_text("unknown")
    expect(page.get_by_test_id("status-guide-not-failure")).to_be_visible()
    expect(page.get_by_test_id("status-guide-no-claims")).to_contain_text(
        "does not show a payable total"
    )
    # No synthetic payable total, savings figure, or best-price claim is rendered.
    expect(page.locator('[data-testid="payable-total"]')).to_have_count(0)
    expect(page.locator('[data-testid="savings-figure"]')).to_have_count(0)
    expect(page.locator('[data-testid="best-price"]')).to_have_count(0)
    expect(result).not_to_contain_text("You save")
    expect(result).not_to_contain_text("Best price")

    # Navigation labels must match their destinations.
    page.goto(f"{BASE_URL}/home")
    navigation = page.get_by_role("navigation", name="Application navigation")
    for label, href in NAVIGATION.items():
        expect(navigation.get_by_role("link", name=label, exact=True)).to_have_attribute(
            "href", href
        )

    # /cart is a persisted-list basket, not a dead local cart.
    page.goto(f"{BASE_URL}/cart")
    expect(page.get_by_test_id("cart-data-source")).to_contain_text("GET /api/v2/lists")
    expect(page.get_by_test_id("cart-list")).to_have_count(1)
    expect(page.get_by_test_id("cart-item")).to_have_count(3)
    expect(
        page.get_by_test_id("cart-item").filter(has_text="Cartel Demo Toned Milk")
    ).to_be_visible()
    expect(
        page.get_by_test_id("cart-item").filter(has_text="Cartel Demo Unmatched Item")
    ).to_contain_text("Product match unresolved")
    expect(page.get_by_test_id("cart-synthetic-notice")).to_be_visible()
    expect(page.get_by_test_id("cart-optimize-list")).to_have_attribute(
        "href", re.compile(r"/optimize\?list_id=.*&revision=\d+")
    )
    expect(page.get_by_text("Subtotal")).to_have_count(0)

    # Step 15: prove no retailer-bound or operator-only request was made. The
    # browser log is written for the report; the backend readiness probe and
    # database provenance are checked alongside it.
    assert recorder.urls, "no browser network requests were recorded"
    assert recorder.retailer_bound == [], recorder.retailer_bound
    assert recorder.operator_only == [], recorder.operator_only
    if BACKEND_URL:
        with urllib.request.urlopen(f"{BACKEND_URL}/ready", timeout=10) as response:
            readiness = json.load(response)
        assert readiness["checks"]["checkout_capture"] == "unavailable"
        assert readiness["checks"]["database"] == "ready"
        assert readiness["checks"]["rate_limiter"] == "ready"
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM retailer_connections")
        ).scalar_one() == 0

    record = _optimization_record(engine, request_id)
    assert record["shopping_list_id"] == list_id
    assert record["status"] == "unresolved"
    assert record["plan_count"] == 0
    snapshot = record["result_snapshot"]
    assert snapshot["completeness"] == "partial"
    assert snapshot["optimizer_result"] is None
    assert snapshot["offers"], snapshot["offers"]
    assert all(offer["is_synthetic"] for offer in snapshot["offers"])
    assert all(offer["evidence_class"] == "synthetic_demo" for offer in snapshot["offers"])
    assert all(
        offer["observation_state"] == "synthetic_demo_observation"
        for offer in snapshot["offers"]
    )
    assert all(offer["tax_status"] == "UNKNOWN" for offer in snapshot["offers"])
    assert all(offer["fees_status"] == "unknown" for offer in snapshot["offers"])
    assert all(offer["checkout_total"] is None for offer in snapshot["offers"])
    assert {offer["canonical_variant_id"] for offer in snapshot["offers"]} == {
        "cartel-demo-variant-milk-500ml",
        "cartel-demo-variant-rice-1kg",
    }
    assert all(
        offer["platform_listing_id"] != "cartel-demo-listing-rice-1kg-a"
        for offer in snapshot["offers"]
    )
    assert snapshot["requested_items"]
    assert all(
        item["evidence_class"] == "synthetic_demo"
        for item in snapshot["requested_items"]
        if item["resolution_status"] == "exact_confirmed"
    )
    assert any(
        item["evidence_class"] == "synthetic_demo"
        for item in snapshot["unresolved_items"]
    )
    assert any(
        item["query"] == "Cartel Demo Unmatched Item"
        and item["resolution_status"] == "unresolved"
        for item in snapshot["unresolved_items"]
    )

    # A second verified user must not see the first user's list or result.
    context_b = browser.new_context(viewport={"width": 1280, "height": 900})
    page_b = context_b.new_page()
    page_b.set_default_timeout(20_000)
    recorder.attach(page_b)
    try:
        _create_verified_user(page_b, engine, "journey-b")
        page_b.goto(f"{BASE_URL}/lists")
        expect(page_b.get_by_text("Your first list is ready to create")).to_be_visible()
        expect(page_b.get_by_text(LIST_NAME)).to_have_count(0)

        assert page_b.request.get(f"{BASE_URL}/api/v2/lists/{list_id}").status == 404
        assert (
            page_b.request.get(f"{BASE_URL}/api/v2/optimizations/{request_id}").status
            == 404
        )

        page_b.goto(
            f"{BASE_URL}/optimize?list_id={list_id}"
            f"&revision={record['list_revision']}&request_id={request_id}"
        )
        expect(
            page_b.get_by_role("alert").filter(
                has_text="That Cartel page or resource is not available."
            )
        ).to_be_visible()
        expect(page_b.get_by_test_id("consumer-optimization-result")).to_have_count(0)
        expect(page_b.get_by_text("Cartel Demo Toned Milk")).to_have_count(0)
        expect(page_b.get_by_text("Synthetic demo evidence")).to_have_count(0)
    finally:
        context_b.close()
    # Re-check after the second user's session so both contexts are covered.
    assert recorder.retailer_bound == [], recorder.retailer_bound
    assert recorder.operator_only == [], recorder.operator_only
    recorder.write()
    context.close()


def test_consumer_journey_browser(engine) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        try:
            _run_journey(browser, engine)
        finally:
            browser.close()
