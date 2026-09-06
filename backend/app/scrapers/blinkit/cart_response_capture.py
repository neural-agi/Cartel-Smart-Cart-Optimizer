"""Bounded, sanitized persistence for natural Blinkit cart responses."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_SENSITIVE = {
    "authorization", "cookie", "cookies", "set-cookie", "token", "access_token",
    "refresh_token", "session", "session_id", "localstorage", "payment", "password",
}
_SAFE_HEADERS = {"content-type", "content-length", "retry-after", "etag"}


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if str(key).lower().replace("-", "_") in _SENSITIVE else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _artifact_name(request_id: str, plan_id: str) -> str:
    key = f"{request_id}\0{plan_id}".encode("utf-8")
    return f"cart-{hashlib.sha256(key).hexdigest()}.json"


def persist_cart_response(
    *,
    root: Path,
    request_id: str,
    plan_id: str,
    retailer_product_id: str,
    status_code: int,
    endpoint_path: str,
    headers: Mapping[str, str] | None = None,
    body: Any = None,
    max_body_bytes: int = 64_000,
) -> Path:
    """Persist only bounded, replayable cart evidence and return its path."""
    if max_body_bytes < 1:
        raise ValueError("max_body_bytes must be positive")
    if isinstance(body, (bytes, bytearray)):
        raw = bytes(body)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = {"body_unavailable": True, "body_bytes": len(raw)}
    sanitized_body = _sanitize(body)
    encoded = json.dumps(sanitized_body, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > max_body_bytes:
        sanitized_body = {"body_truncated": True, "body_bytes": len(encoded)}
    payload = {
        "request_id": request_id,
        "plan_id": plan_id,
        "retailer_product_id": retailer_product_id,
        "status_code": status_code,
        "endpoint_path": endpoint_path,
        "headers": {
            key.lower(): value for key, value in (headers or {}).items()
            if key.lower() in _SAFE_HEADERS
        },
        "body": sanitized_body,
    }
    root.mkdir(parents=True, exist_ok=True)
    path = root / _artifact_name(request_id, plan_id)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return path
