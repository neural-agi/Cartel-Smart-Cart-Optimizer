from app.normalization.pricing import GovernedRetailPriceParser


def test_parser_accepts_governed_inr_values_without_float_conversion() -> None:
    parser = GovernedRetailPriceParser()

    assert parser.parse("₹100", currency_code="INR").minor_units == 10000
    assert parser.parse("INR 10.25", currency_code="INR").minor_units == 1025


def test_parser_fails_closed_for_missing_ambiguous_or_unsupported_values() -> None:
    parser = GovernedRetailPriceParser()

    for value, currency in ((None, "INR"), ("₹1,000", "INR"), ("₹10.999", "INR"), ("$10", "INR"), ("10", "USD")):
        assert parser.parse(value, currency_code=currency) is None
