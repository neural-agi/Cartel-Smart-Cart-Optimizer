from app.workers.background_jobs import payload_hash, retry_delay


def test_payload_hash_is_order_independent():
    assert payload_hash({"b": 2, "a": 1}) == payload_hash({"a": 1, "b": 2})


def test_retry_delay_is_bounded_and_backed_off():
    assert retry_delay(1, 5, 10, random_value=0) == 5
    assert retry_delay(2, 5, 10, random_value=0) == 10
    assert retry_delay(5, 5, 10, random_value=0) == 10
