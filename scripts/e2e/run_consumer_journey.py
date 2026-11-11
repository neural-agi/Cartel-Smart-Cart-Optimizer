#!/usr/bin/env python3
"""Run the reproducible consumer-journey browser test.

The harness starts a disposable stack on the existing isolated Docker network:

* Redis
* the API image running the current backend code against ``cartel_test``
* a frontend image built from the current frontend source
* a Playwright runner that drives the real browser journey

It never targets the ``cartel`` database. It reads the test password from the
same secret file used by the isolated backend runner, writes it to a mode-600
temporary env file, and removes that file on exit.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NETWORK = "cartel-smart-cart-optimizer_cartel"
DEFAULT_API_IMAGE = "cartel-smart-cart-optimizer-api:latest"
DEFAULT_FRONTEND_IMAGE = "cartel-e2e-frontend:local"
DEFAULT_SECRET = Path.home() / ".cartel-test-secrets" / "cartel-test-secret"
FIXTURE_DIR = ROOT / "backend" / "tests" / "fixtures" / "synthetic_demo"
RESET_SCHEMA_CODE = """
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"], isolation_level="AUTOCOMMIT")
with engine.connect() as connection:
    database, user = connection.execute(text(
        "SELECT current_database(), current_user"
    )).one()
    if (database, user) != ("cartel_test", "cartel_test_runner"):
        raise SystemExit(f"refusing to reset unexpected database/role: {database}/{user}")
    connection.execute(text("DROP SCHEMA public CASCADE"))
    connection.execute(text("CREATE SCHEMA public"))
engine.dispose()
"""


def run(command: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def docker(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return run(["docker", *args], check=check, capture=capture)


def container_running(name: str) -> bool:
    result = docker("inspect", "-f", "{{.State.Running}}", name, check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def wait_for(name: str, command: list[str], timeout: float = 120.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not container_running(name):
            logs = docker("logs", "--tail", "40", name, check=False).stdout or ""
            raise SystemExit(f"container {name} stopped unexpectedly\n{logs}")
        if run(command, check=False).returncode == 0:
            return
        time.sleep(1.0)
    logs = docker("logs", "--tail", "40", name, check=False).stdout or ""
    raise SystemExit(f"container {name} did not become ready\n{logs}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", default=os.environ.get("CARTEL_E2E_NETWORK", DEFAULT_NETWORK))
    parser.add_argument("--api-image", default=os.environ.get("CARTEL_E2E_API_IMAGE", DEFAULT_API_IMAGE))
    parser.add_argument(
        "--frontend-image",
        default=os.environ.get("CARTEL_E2E_FRONTEND_IMAGE", DEFAULT_FRONTEND_IMAGE),
    )
    parser.add_argument(
        "--secret-file",
        type=Path,
        default=Path(os.environ.get("CARTEL_TEST_SECRET_FILE", DEFAULT_SECRET)),
    )
    parser.add_argument("--skip-frontend-build", action="store_true")
    parser.add_argument("--keep-images", action="store_true")
    parser.add_argument("--keep-stack", action="store_true")
    args = parser.parse_args()

    if not args.secret_file.is_file():
        raise SystemExit(f"test secret file not found: {args.secret_file}")
    if not FIXTURE_DIR.is_dir():
        raise SystemExit(f"demo fixture dataset not found: {FIXTURE_DIR}")

    password = args.secret_file.read_text(encoding="utf-8").rstrip("\r\n")
    if not password:
        raise SystemExit("test secret file is empty")
    encoded_password = urllib.parse.quote(password, safe="")
    database_url = (
        "postgresql+psycopg://cartel_test_runner:"
        f"{encoded_password}@postgres:5432/cartel_test"
    )

    suffix = uuid.uuid4().hex[:8]
    redis_name = f"cartel-e2e-{suffix}-redis"
    api_name = f"cartel-e2e-{suffix}-api"
    frontend_name = f"cartel-e2e-{suffix}-frontend"
    temp_root = Path(tempfile.mkdtemp(prefix="cartel-e2e-"))
    data_dir = temp_root / "data"
    env_file = temp_root / "runtime.env"
    started: list[str] = []

    def reset_schema() -> None:
        docker(
            "run",
            "--rm",
            "--network",
            args.network,
            "--env-file",
            str(env_file),
            "--entrypoint",
            "python",
            args.api_image,
            "-c",
            RESET_SCHEMA_CODE,
        )

    def cleanup() -> None:
        if not args.keep_stack:
            for name in reversed(started):
                docker("rm", "-f", name, check=False)
            try:
                reset_schema()
            except Exception:
                pass
        shutil.rmtree(temp_root, ignore_errors=True)
        if not args.keep_images and not args.skip_frontend_build:
            docker("image", "rm", "-f", args.frontend_image, check=False)

    try:
        docker("network", "inspect", args.network)
        shutil.copytree(FIXTURE_DIR, data_dir)
        env_file.write_text(
            f"DATABASE_URL={database_url}\nE2E_DATABASE_URL={database_url}\n",
            encoding="utf-8",
        )
        env_file.chmod(0o600)
        temp_root.chmod(0o700)

        if not args.skip_frontend_build:
            print("Building frontend image from current source...", flush=True)
            docker(
                "build",
                "-f",
                str(ROOT / "frontend" / "Dockerfile"),
                "--build-arg",
                "BACKEND_INTERNAL_URL=http://api:8000",
                "-t",
                args.frontend_image,
                str(ROOT / "frontend"),
                capture=False,
            )

        print("Resetting the isolated cartel_test schema...", flush=True)
        reset_schema()

        print("Starting disposable Redis, API, and frontend containers...", flush=True)
        docker(
            "run",
            "-d",
            "--rm",
            "--name",
            redis_name,
            "--network",
            args.network,
            "redis:7-alpine",
        )
        started.append(redis_name)

        docker(
            "run",
            "-d",
            "--name",
            api_name,
            "--network",
            args.network,
            "--network-alias",
            "api",
            "--env-file",
            str(env_file),
            "-e",
            "APP_ENV=development",
            "-e",
            "APP_DEBUG=false",
            "-e",
            "DOCS_ENABLED=false",
            "-e",
            "DATABASE_REQUIRED=true",
            "-e",
            f"REDIS_URL=redis://{redis_name}:6379/0",
            "-e",
            "AUTH_REQUIRED=true",
            "-e",
            "AUTH_TOKENS=operator=cartel-e2e-operator",
            "-e",
            "AUTH_COOKIE_SECURE=false",
            "-e",
            "PUBLIC_ORIGIN=http://frontend:3000",
            "-e",
            "CORS_ALLOWED_ORIGINS=http://frontend:3000",
            "-e",
            "EMAIL_DELIVERY_MODE=file",
            "-e",
            "LOCAL_EMAIL_DIR=/tmp/cartel-email",
            "-e",
            "DEMO_FIXTURES_ENABLED=true",
            "-e",
            "DATA_DIR=/app/data",
            "-e",
            "AUTH_RATE_LIMIT_REQUESTS=1000",
            "-e",
            "RATE_LIMIT_REQUESTS=100000",
            "-e",
            "RATE_LIMIT_WINDOW_SECONDS=60",
            "-e",
            "CHECKOUT_OBSERVATION_PROVIDER_MODE=unavailable",
            "-e",
            "CHECKOUT_CAPTURE_ADAPTER_MODE=unavailable",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-v",
            f"{ROOT / 'backend'}:/app/backend:ro",
            "-v",
            f"{data_dir}:/app/data",
            args.api_image,
        )
        started.append(api_name)

        docker(
            "run",
            "-d",
            "--name",
            frontend_name,
            "--network",
            args.network,
            "--network-alias",
            "frontend",
            "-e",
            "BACKEND_INTERNAL_URL=http://api:8000",
            "-e",
            "NEXT_TELEMETRY_DISABLED=1",
            args.frontend_image,
        )
        started.append(frontend_name)

        print("Waiting for the API and frontend...", flush=True)
        wait_for(
            api_name,
            [
                "docker",
                "exec",
                api_name,
                "python",
                "-c",
                "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)",
            ],
        )
        wait_for(
            frontend_name,
            [
                "docker",
                "exec",
                frontend_name,
                "wget",
                "--spider",
                "--quiet",
                "http://127.0.0.1:3000/home",
            ],
        )

        print("Running the browser journey...", flush=True)
        result = docker(
            "run",
            "--rm",
            "--network",
            args.network,
            "--env-file",
            str(env_file),
            "-e",
            "E2E_BASE_URL=http://frontend:3000",
            "-e",
            "PYTHONPATH=/app/backend",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-v",
            f"{ROOT / 'backend'}:/app/backend:ro",
            "--entrypoint",
            "sh",
            args.api_image,
            "-c",
            "pip install --quiet pytest >/dev/null && "
            "python -m pytest tests/e2e/test_consumer_journey_browser.py "
            "-q -p no:cacheprovider",
            check=False,
        )
        if result.stdout:
            print(result.stdout, end="", flush=True)
        if result.returncode != 0:
            print("E2E FAIL", flush=True)
            return result.returncode
        print("E2E PASS", flush=True)
        return 0
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
