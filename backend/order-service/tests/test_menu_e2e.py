"""Scenario 18 on the running cluster (tier 3): Inventory restarts, then a dish changes status.
The version keeps increasing; POS receives the update immediately, through ``menu-events``.

The dish change is a real one through Inventory's API: a stock count of shrimp too low for one
portion of GOI_CUON (``clear-check`` with ``counted_on_hand``), undone afterwards with a stock
receipt. Needs the compose cluster up."""

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from decimal import Decimal
from typing import Any, Protocol

import psycopg
import pytest

pytestmark = pytest.mark.tier3

INVENTORY = "http://inventory-1:8000"
POS01 = "http://pos01:8000"
INVENTORY_DB = "postgresql://app:app@inventory-db:5432/inventory"
POS01_DB = "postgresql://app:app@pos01-db:5432/branch"


class Chaos(Protocol):
    """The ``chaos`` fixture of backend/conftest.py."""

    def stop(self, service: str) -> None: ...
    def start(self, service: str) -> None: ...
    def wait_healthy(self, service: str, timeout_s: float = 120) -> None: ...
    def health(self, service: str) -> str: ...


def http(method: str, url: str, body: Any = None) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def wait_for(what: str, timeout_s: float, check: Callable[[], Any]) -> Any:
    deadline = time.monotonic() + timeout_s
    while True:
        value = check()
        if value:
            return value
        assert time.monotonic() < deadline, f"timed out waiting for {what}"
        time.sleep(0.2)


def inventory_version() -> tuple[int, int]:
    with psycopg.connect(INVENTORY_DB) as conn:
        row = conn.execute("SELECT epoch, seq FROM menu_version").fetchone()
    assert row is not None
    return int(row[0]), int(row[1])


def cached(dish_id: str) -> tuple[str, int, int] | None:
    with psycopg.connect(POS01_DB) as conn:
        row = conn.execute(
            "SELECT status, epoch, seq FROM menu_cache WHERE dish_id = %s", (dish_id,)
        ).fetchone()
    return None if row is None else (str(row[0]), int(row[1]), int(row[2]))


def shrimp() -> tuple[Decimal, Decimal]:
    status, items = http("GET", f"{INVENTORY}/stock")
    assert status == 200
    [tom] = [i for i in items if i["ingredient_id"] == "TOM"]
    return Decimal(tom["available"]), Decimal(tom["reserved"])


def running_inventories(chaos: Chaos) -> list[str]:
    running: list[str] = []
    for service in ("inventory-1", "inventory-2"):
        try:
            if chaos.health(service) == "healthy":
                running.append(service)
        except RuntimeError:  # inventory-2 exists only with --profile full
            pass
    return running


@pytest.mark.kb(18)
def test_after_inventory_restarts_a_dish_change_reaches_pos_at_once_with_a_greater_version(
    chaos: Chaos,
) -> None:
    status, menu = http("GET", f"{POS01}/menu")
    assert status == 200
    assert menu["stale"] is False, "POS01 has not heard from Inventory: is the cluster up?"
    if cached("GOI_CUON") is None or cached("GOI_CUON")[0] != "CON":  # type: ignore[index]
        available, _ = shrimp()
        http("POST", f"{INVENTORY}/stock/receipts", {"ingredient_id": "TOM", "quantity": "1"})
        assert shrimp()[0] > available
        wait_for(
            "GOI_CUON Available at POS01", 30, lambda: (cached("GOI_CUON") or ("",))[0] == "CON"
        )

    # Inventory restarts.
    before = inventory_version()
    instances = running_inventories(chaos)
    assert instances, "no Inventory instance is running, so nothing would restart"
    for service in instances:
        chaos.stop(service)
    for service in instances:
        chaos.start(service)
    for service in instances:
        chaos.wait_healthy(service)

    # Then a dish changes status: a count leaves too little shrimp for one GOI_CUON (0.06 kg).
    available, reserved = shrimp()
    try:
        status, body = http(
            "POST",
            f"{INVENTORY}/ingredients/TOM/clear-check",
            {"counted_on_hand": str(reserved + Decimal("0.01"))},
        )
        assert status == 200, body
        started = time.monotonic()
        # POS receives the update immediately ...
        status_at_pos = wait_for(
            "GOI_CUON Sold out at POS01",
            15,
            lambda: (c := cached("GOI_CUON")) is not None and c[0] == "HET" and c,
        )
        took = time.monotonic() - started
        # ... and the version keeps increasing across the restart.
        assert (status_at_pos[1], status_at_pos[2]) > before
        assert took < 10, f"POS01 heard after {took:.1f} s"
    finally:
        # Put the shrimp back with a receipt, which recomputes GOI_CUON (Flow C).
        now_available, _ = shrimp()
        if now_available < available:
            http(
                "POST",
                f"{INVENTORY}/stock/receipts",
                {"ingredient_id": "TOM", "quantity": str(available - now_available)},
            )
    wait_for(
        "GOI_CUON Available again at POS01", 30, lambda: (cached("GOI_CUON") or ("",))[0] == "CON"
    )
