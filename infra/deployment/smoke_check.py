#!/usr/bin/env python3
"""Cartel hosted smoke check (read-only; no credentials, no mutations).

Run only after the frontend and backend are deployed and approved:

    python3 infra/deployment/smoke_check.py \
      --frontend https://<vercel-project>.vercel.app \
      --backend https://<render-service>.onrender.com

This script proves reachability, the same-origin /api rewrite, readiness of
PostgreSQL AND Redis, disabled docs, and the absence of the Docker-only hostname
in the served HTML/JS. It does not prove login, cross-user isolation, or
persistence; those require the browser journey with two real accounts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit


def get(url: str, timeout: float = 20.0):
    request = urllib.request.Request(url, headers={"User-Agent": "cartel-k5-smoke/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend", required=True)
    parser.add_argument("--backend", required=True)
    args = parser.parse_args()

    frontend = args.frontend.rstrip("/")
    backend = args.backend.rstrip("/")
    results: dict[str, object] = {}

    status, _, body = get(f"{backend}/health")
    results["backend_health_status"] = status
    results["backend_health"] = json.loads(body.decode()) if status == 200 else None

    status, _, body = get(f"{backend}/ready")
    readiness = json.loads(body.decode()) if body else {}
    results["backend_ready_status"] = status
    results["backend_ready"] = readiness
    checks = readiness.get("checks", {}) if isinstance(readiness, dict) else {}
    results["postgres_ready"] = checks.get("database") == "ready"
    results["redis_ready"] = checks.get("redis") == "ready"

    for path in ("/docs", "/redoc", "/api/v1/openapi.json"):
        status, _, _ = get(f"{backend}{path}")
        results[f"backend{path}_status"] = status

    status, _, body = get(f"{frontend}/")
    results["frontend_status"] = status
    html = body.decode("utf-8", errors="replace") if body else ""

    status, _, body = get(f"{frontend}/api/v2/auth/providers")
    results["frontend_api_rewrite_status"] = status
    try:
        results["frontend_api_rewrite_body"] = json.loads(body.decode())
    except Exception:
        results["frontend_api_rewrite_body"] = None

    asset_urls = sorted(
        {
            urljoin(f"{frontend}/", match)
            for match in re.findall(r'(?:src|href)="([^"]+\.(?:js|css))"', html)
        }
    )
    docker_only = False
    asset_count = 0
    for asset_url in asset_urls:
        parsed = urlsplit(asset_url)
        if parsed.netloc and parsed.netloc != urlsplit(frontend).netloc:
            continue
        asset_count += 1
        status, _, asset_body = get(asset_url)
        if status == 200 and b"api:8000" in asset_body:
            docker_only = True
    results["frontend_asset_count_scanned"] = asset_count
    results["docker_only_hostname_in_assets"] = docker_only

    print(json.dumps(results, indent=2, sort_keys=True))
    ok = (
        results["backend_health_status"] == 200
        and results["backend_ready_status"] == 200
        and results["postgres_ready"] is True
        and results["redis_ready"] is True
        and results["backend/docs_status"] == 404
        and results["backend/redoc_status"] == 404
        and results["backend/api/v1/openapi.json_status"] in (401, 404)
        and results["frontend_status"] == 200
        and results["frontend_api_rewrite_status"] == 200
        and results["docker_only_hostname_in_assets"] is False
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
