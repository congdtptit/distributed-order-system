"""Flow C at Inventory (phase 2): dish status, its version and the snapshot. Section 3.4 and 7
of docs/01-business-spec.md (BR6, BR10); section 3 of docs/02-detailed-design.md ("Lock order",
"Computing dish status", "Dish version", "Bumping epoch")."""

import threading
from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from inventory_support import (
    NOW,
    D,
    assert_invariants,
    deliver,
    order_created,
    order_record,
    outbox,
    seeded,
    set_available,
)

from common.clock import FixedClock
from inventory_service.app import app, get_clock, get_conn
from inventory_service.checks import clear_check
from inventory_service.dishes import bump_epoch, ensure_dish_status, recompute_dishes, snapshot
from inventory_service.stock import load_seed, receive_stock

CLOCK = FixedClock(NOW)
DISHES = {"PHO_BO", "BUN_CHA", "COM_TAM", "GOI_CUON", "BANH_MI_THIT", "TRA_DA"}
INGREDIENTS = {
    "BANH_PHO",
    "THIT_BO",
    "BUN",
    "THIT_LON",
    "SUON",
    "GAO",
    "TOM",
    "BANH_TRANG",
    "RAU_SONG",
    "BANH_MI",
    "LA_TRA",
    "DA",
}


@pytest.fixture
def inv(migrated: Callable[[str], str]) -> str:
    return seeded(migrated("inventory-service"))


@pytest.fixture
def api(inv: str) -> Iterator[TestClient]:
    def conn() -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(inv) as c:
            yield c

    app.dependency_overrides[get_conn] = conn
    app.dependency_overrides[get_clock] = lambda: CLOCK
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def dishes(dsn: str) -> dict[str, tuple[str, int, int]]:
    with psycopg.connect(dsn) as conn:
        rows = conn.execute("SELECT dish_id, status, epoch, seq FROM dish_status").fetchall()
    return {str(r[0]): (str(r[1]), int(r[2]), int(r[3])) for r in rows}


def status_changes(dsn: str) -> list[dict[str, Any]]:
    return [
        r.payload | {"_key": r.key, "_topic": r.topic}
        for r in outbox(dsn)
        if r.event_type == "DishStatusChanged"
    ]


def assert_statuses_match_stock(dsn: str) -> None:
    """Every stored dish status is what section 3.4 gives for the stock as it is now."""
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            """SELECT d.dish_id, d.status,
                      CASE WHEN count(r.ingredient_id) = 0 THEN 'AN'
                           WHEN bool_and(s.available >= r.quantity AND NOT s.needs_check)
                           THEN 'CON' ELSE 'HET' END
                 FROM dish_status d
                 LEFT JOIN recipes r ON r.dish_id = d.dish_id
                 LEFT JOIN stock s ON s.ingredient_id = r.ingredient_id
                GROUP BY d.dish_id, d.status"""
        ).fetchall()
    assert {str(r[0]): str(r[1]) for r in rows} == {str(r[0]): str(r[2]) for r in rows}


def test_the_first_start_gives_every_dish_a_status_at_the_starting_version(inv: str) -> None:
    """Every dish of the seed is Available at (1, 0); nothing is announced, so the first change
    still takes seq 1 (section 3 of document 02: menu_version starts at epoch 1, seq 0)."""
    assert dishes(inv) == {d: ("CON", 1, 0) for d in DISHES}
    assert status_changes(inv) == []


def test_a_reservation_that_empties_an_ingredient_makes_its_dishes_sold_out(inv: str) -> None:
    """Flow C, Inventory side, steps 1 to 3: after a reservation Inventory recomputes the dishes
    that use the reserved ingredients and announces each one whose status changed."""
    set_available(inv, "THIT_LON", D("0.2"))  # BUN_CHA takes 0.15, BANH_MI_THIT 0.08
    env = order_created(items=[("BUN_CHA", 1)])
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[0] == "DANG_GIU"
    # 0.05 left: not enough for one BUN_CHA (0.15) nor one BANH_MI_THIT (0.08).
    assert status_changes(inv) == [
        {"dish_id": "BANH_MI_THIT", "status": "HET", "epoch": 1, "seq": 1, "_key": "BANH_MI_THIT",
         "_topic": "menu-events"},
        {"dish_id": "BUN_CHA", "status": "HET", "epoch": 1, "seq": 2, "_key": "BUN_CHA",
         "_topic": "menu-events"},
    ]  # fmt: skip
    assert dishes(inv)["BUN_CHA"] == ("HET", 1, 2)
    assert dishes(inv)["PHO_BO"] == ("CON", 1, 0)  # shares RAU_SONG, still plenty
    assert_statuses_match_stock(inv)
    assert_invariants(inv)


def test_a_reservation_that_changes_no_dish_announces_nothing(inv: str) -> None:
    """Flow C, step 2: stock changes but no dish changes status, so nothing is published."""
    deliver(inv, order_created(items=[("PHO_BO", 1)]))
    assert status_changes(inv) == []
    assert dishes(inv)["PHO_BO"] == ("CON", 1, 0)
    assert_invariants(inv)


def test_a_failed_order_changes_no_stock_and_announces_nothing(inv: str) -> None:
    set_available(inv, "TOM", D("0"))
    env = order_created(items=[("GOI_CUON", 1)])
    deliver(inv, env)
    record = order_record(inv, env.order_id)
    assert record is not None and record[0] == "THAT_BAI"
    assert status_changes(inv) == []


def test_a_stock_receipt_brings_a_dish_back(inv: str) -> None:
    set_available(inv, "SUON", D("0"))
    with psycopg.connect(inv) as conn:
        recompute_dishes(conn, ["SUON"], CLOCK)
    assert dishes(inv)["COM_TAM"] == ("HET", 1, 1)
    with psycopg.connect(inv) as conn:
        assert receive_stock(conn, "SUON", D("1"), CLOCK)
    assert dishes(inv)["COM_TAM"] == ("CON", 1, 2)
    assert [c["status"] for c in status_changes(inv)] == ["HET", "CON"]
    assert_statuses_match_stock(inv)


def test_a_count_below_one_portion_through_clear_check_makes_the_dish_sold_out(inv: str) -> None:
    with psycopg.connect(inv) as conn:
        clear_check(conn, "GAO", D("0.1"), CLOCK)  # COM_TAM needs 0.15
    assert dishes(inv)["COM_TAM"][0] == "HET"
    assert_statuses_match_stock(inv)


@pytest.mark.kb(18)
def test_versions_keep_increasing_after_a_restart(inv: str) -> None:
    """Scenario 18, the Inventory part: Inventory restarts, then a dish changes status. The
    version keeps increasing: seq lives in menu_version, not in the process."""
    set_available(inv, "SUON", D("0"))
    with psycopg.connect(inv) as conn:
        recompute_dishes(conn, ["SUON"], CLOCK)
    before = dishes(inv)["COM_TAM"]
    # A restart: a new process runs the start-up steps again on the same database.
    with psycopg.connect(inv, autocommit=True) as conn:
        from common.seed import load_menu

        assert load_seed(conn, load_menu()) is False
    with psycopg.connect(inv) as conn:
        ensure_dish_status(conn)
        assert receive_stock(conn, "SUON", D("1"), CLOCK)
    after = dishes(inv)["COM_TAM"]
    assert after[0] == "CON"
    assert (after[1], after[2]) > (before[1], before[2])
    assert [(c["epoch"], c["seq"]) for c in status_changes(inv)] == [(1, 1), (1, 2)]
    assert_statuses_match_stock(inv)
    assert_invariants(inv)


def test_the_snapshot_holds_every_dish_with_its_version_and_the_epoch(
    inv: str, api: TestClient
) -> None:
    """Flow C, step 5: the status and version of every dish, Hidden ones included."""
    with psycopg.connect(inv) as conn:
        conn.execute("DELETE FROM recipes WHERE dish_id = 'TRA_DA'")  # the dish is removed
        recompute_dishes(conn, [], CLOCK, dish_ids=["TRA_DA"])  # a recipe change names its dish
    response = api.get("/menu/snapshot")
    assert response.status_code == 200
    body = response.json()
    assert body["epoch"] == 1
    by_dish = {d["dish_id"]: d for d in body["dishes"]}
    assert set(by_dish) == DISHES
    assert by_dish["TRA_DA"] == {"dish_id": "TRA_DA", "status": "AN", "epoch": 1, "seq": 1}
    assert by_dish["PHO_BO"] == {"dish_id": "PHO_BO", "status": "CON", "epoch": 1, "seq": 0}
    with psycopg.connect(inv) as conn:
        assert snapshot(conn).epoch == 1


@pytest.mark.kb(20)
def test_bumping_the_epoch_rewrites_every_dish_and_resends_every_flag(
    inv: str, api: TestClient
) -> None:
    """Scenario 20, the Inventory part: after a restore from backup Inventory bumps the epoch.
    Every dish is rewritten with the new epoch and seq, unchanged ones too; the Kitchen gets
    IngredientCheckChanged for every ingredient; no DishStatusChanged is sent (branches see
    the new epoch in the next heartbeat and fetch the snapshot)."""
    set_available(inv, "SUON", D("0"))  # COM_TAM is Sold out in the restored data
    with psycopg.connect(inv) as conn:
        conn.execute("DELETE FROM recipes WHERE dish_id = 'TRA_DA'")  # not in the new generation
    before_changes = len(status_changes(inv))
    response = api.post("/admin/epoch/bump")
    assert response.status_code == 200
    assert response.json() == {"epoch": 2}
    rows = dishes(inv)
    assert {v[1:] for v in rows.values()} == {(2, 1)}
    assert rows["COM_TAM"][0] == "HET"
    assert rows["TRA_DA"][0] == "AN"
    assert rows["PHO_BO"][0] == "CON"
    assert len(status_changes(inv)) == before_changes  # no DishStatusChanged
    flags = [r for r in outbox(inv) if r.event_type == "IngredientCheckChanged"]
    assert {r.payload["ingredient_id"] for r in flags} == INGREDIENTS
    assert {(r.payload["epoch"], r.payload["seq"]) for r in flags} == {(2, 1)}
    assert_statuses_match_stock(inv)
    assert_invariants(inv)
    # The snapshot carries the new generation.
    snap = api.get("/menu/snapshot").json()
    assert snap["epoch"] == 2
    assert {(d["epoch"], d["seq"]) for d in snap["dishes"]} == {(2, 1)}
    with psycopg.connect(inv) as conn:
        assert bump_epoch(conn, CLOCK) == 3


def recompute_race(dsn: str, conns: list[psycopg.Connection[Any]]) -> None:
    """A receipt of SUON and a recount of GAO, both ingredients of COM_TAM, at the same moment."""
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def receipt() -> None:
        try:
            barrier.wait()
            with conns[0].transaction():
                receive_stock(conns[0], "SUON", D("1"), CLOCK)
        except BaseException as exc:
            errors.append(exc)

    def recount() -> None:
        try:
            barrier.wait()
            with conns[1].transaction():
                clear_check(conns[1], "GAO", D("0.1"), CLOCK)
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=receipt), threading.Thread(target=recount)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert not any(t.is_alive() for t in threads), "a transaction hung (a deadlock?)"
    assert errors == []


def test_two_changes_to_two_ingredients_of_one_dish_at_once_leave_the_right_status(
    inv: str,
) -> None:
    """Tier 2. COM_TAM needs GAO and SUON. SUON is out (Sold out); a receipt of SUON and a
    recount that leaves too little GAO run at the same moment. The right end is Sold out
    (too little GAO). Without locking dish_status before reading stock, the receipt could read
    the old GAO and write Available last (section 3 of document 02, "Computing dish status")."""
    conns = [psycopg.connect(inv, autocommit=True) for _ in range(2)]
    try:
        for _ in range(100):
            with psycopg.connect(inv) as conn:
                conn.execute("UPDATE stock SET available = 0 WHERE ingredient_id = 'SUON'")
                conn.execute("UPDATE stock SET available = 10 WHERE ingredient_id = 'GAO'")
                recompute_dishes(conn, ["SUON", "GAO"], CLOCK)
            assert dishes(inv)["COM_TAM"][0] == "HET"
            recompute_race(inv, conns)
            assert dishes(inv)["COM_TAM"][0] == "HET"
            assert_statuses_match_stock(inv)
            assert_invariants(inv)
    finally:
        for c in conns:
            c.close()
