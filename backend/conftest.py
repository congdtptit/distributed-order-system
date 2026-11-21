"""Fixtures shared by every module's tests.

The tests run against the ``test-db`` PostgreSQL of docker-compose.yml (in CI, a PostgreSQL service
of the workflow), and each test gets a new, empty database in it. Tests never delete rows to
reset state: prohibition 1 in section 9 of docs/01-business-spec.md forbids deleting order
records, so a clean state means a new database (dropped as a whole after the test).

``TEST_DATABASE_URL`` points at the server's default database.

Tier 3 tests (``-m tier3``, section 3 of docs/03-implementation-plan.md) also use the running
compose cluster: the three Kafka brokers (``KAFKA_BOOTSTRAP``) and, for fault injection, the
Docker Engine API through the socket the tools container mounts.
"""

import http.client
import json
import os
import socket
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from common.kafka import create_topic, delete_topics
from common.migrate import apply_migrations

ROOT = Path(__file__).parent
DEFAULT_TEST_DATABASE_URL = "postgresql://app:app@test-db:5432/postgres"


@pytest.fixture(scope="session")
def postgres_server() -> str:
    """Connection string of the test server's default database."""
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


@pytest.fixture
def fresh_db(postgres_server: str) -> Iterator[str]:
    """Connection string of a new, empty database, dropped after the test.

    ``test-db`` keeps its data in memory; without the drop, a few hundred test databases fill
    it and PostgreSQL stops.
    """
    name = f"t_{uuid.uuid4().hex[:16]}"
    with psycopg.connect(postgres_server, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    yield make_conninfo(postgres_server, dbname=name)
    with psycopg.connect(postgres_server, autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def migrated_db(dsn: str, module: str) -> str:
    """Apply the migrations of one module (for example ``inventory-service``) to ``dsn``."""
    with psycopg.connect(dsn) as conn:
        apply_migrations(conn, ROOT / module / "migrations")
    return dsn


@pytest.fixture
def migrated(fresh_db: str) -> Callable[[str], str]:
    """``migrated("inventory-service")``: a new database with that module's schema."""
    return lambda module: migrated_db(fresh_db, module)


# ---------- tier 3: real Kafka ----------


@pytest.fixture(scope="session")
def kafka_bootstrap() -> str:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP")
    if not bootstrap:
        pytest.fail(
            "KAFKA_BOOTSTRAP is not set: tier 3 tests run in the tools container, "
            "docker compose exec tools pytest -m tier3"
        )
    return bootstrap


@pytest.fixture
def new_topic(kafka_bootstrap: str) -> Iterator[Callable[[int], str]]:
    """Factory of throwaway topics with the mandatory settings (3 replicas, min ISR 2).

    Their names start with ``test.`` so that no service subscription pattern
    (``^order-events\\..*`` …) picks them up. They are deleted after the test.
    """
    created: list[str] = []

    def make(partitions: int = 1) -> str:
        name = f"test.{uuid.uuid4().hex[:12]}"
        create_topic(kafka_bootstrap, name, partitions)
        created.append(name)
        return name

    yield make
    delete_topics(kafka_bootstrap, created)


# ---------- tier 3: fault injection on the running cluster ----------


class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path: str) -> None:
        super().__init__("localhost", timeout=60)
        self._path = path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(60)
        sock.connect(self._path)
        self.sock = sock


class DockerEngine:
    """Stops and starts services of the compose project through the Docker Engine API."""

    def __init__(self, socket_path: str, project: str) -> None:
        self._socket = socket_path
        self._project = project
        self.stopped: list[str] = []

    def _call(self, method: str, path: str) -> tuple[int, Any]:
        conn = _UnixHTTPConnection(self._socket)
        try:
            conn.request(method, path)
            response = conn.getresponse()
            body = response.read()
            return response.status, json.loads(body) if body else None
        finally:
            conn.close()

    def container_id(self, service: str) -> str:
        filters = json.dumps(
            {
                "label": [
                    f"com.docker.compose.project={self._project}",
                    f"com.docker.compose.service={service}",
                ]
            }
        )
        status, body = self._call("GET", f"/containers/json?all=1&filters={quote(filters)}")
        containers = cast(list[dict[str, Any]], body) if status == 200 else []
        if len(containers) != 1:
            raise RuntimeError(f"expected one container for {service}, found {len(containers)}")
        return str(containers[0]["Id"])

    def stop(self, service: str) -> None:
        self.stopped.append(service)
        status, body = self._call("POST", f"/containers/{self.container_id(service)}/stop?t=10")
        if status not in (204, 304):
            raise RuntimeError(f"stopping {service}: HTTP {status} {body}")

    def kill(self, service: str) -> None:
        """SIGKILL: the process gets no chance to hand over leadership or flush anything."""
        self.stopped.append(service)
        status, body = self._call("POST", f"/containers/{self.container_id(service)}/kill")
        if status != 204:
            raise RuntimeError(f"killing {service}: HTTP {status} {body}")

    def start(self, service: str) -> None:
        status, body = self._call("POST", f"/containers/{self.container_id(service)}/start")
        if status not in (204, 304):
            raise RuntimeError(f"starting {service}: HTTP {status} {body}")

    def health(self, service: str) -> str:
        _, body = self._call("GET", f"/containers/{self.container_id(service)}/json")
        state = cast(dict[str, Any], body)["State"]
        health = state.get("Health")
        return str(health["Status"]) if health else str(state["Status"])

    def wait_healthy(self, service: str, timeout_s: float = 120) -> None:
        deadline = time.monotonic() + timeout_s
        while self.health(service) != "healthy":
            if time.monotonic() > deadline:
                raise TimeoutError(f"{service} is not healthy after {timeout_s}s")
            time.sleep(1)


@pytest.fixture
def chaos() -> Iterator[DockerEngine]:
    """Stop and start containers of the cluster; whatever a test stopped is started again
    and waited for after the test, so later tests see the full cluster."""
    socket_path = "/var/run/docker.sock"
    if not Path(socket_path).exists():
        pytest.fail("the Docker socket is not mounted: run tier 3 tests in the tools container")
    engine = DockerEngine(socket_path, os.environ.get("COMPOSE_PROJECT_NAME", "order-system"))
    yield engine
    for service in engine.stopped:
        engine.start(service)
    for service in engine.stopped:
        engine.wait_healthy(service)
