from app.core.metrics import Metrics, normalized_route


def test_routes_are_normalized_before_metric_labels():
    assert normalized_route("/api/v2/lists/123e4567-e89b-12d3-a456-426614174000") == "/api/v2/lists/:id"


def test_metrics_render_bounded_prometheus_text():
    registry = Metrics()
    registry.inc("cartel_http_requests_total", method="GET", route="/health", status_class="2xx")
    registry.observe("cartel_http_request_duration_ms", 3.5, route="/health")
    output = registry.prometheus()
    assert "cartel_http_requests_total" in output
    assert "route=\"/health\"" in output
    assert "3.500000" in output
