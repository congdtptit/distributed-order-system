"""Loading the seed file into Inventory (section 1 of docs/02-detailed-design.md): first start
only, never over stock that has changed, once even when both instances start together."""

import threading
from collections.abc import Callable

import psycopg
from inventory_support import D, stock

from common.seed import load_menu
from inventory_service.stock import load_seed, receive_stock


def test_the_seed_loads_into_an_empty_db_and_never_over_changed_stock(
    migrated: Callable[[str], str],
) -> None:
    dsn = migrated("inventory-service")
    menu = load_menu()
    with psycopg.connect(dsn, autocommit=True) as conn:
        assert load_seed(conn, menu) is True
        loaded = stock(dsn)
        assert {i.ingredient_id: i.stock for i in menu.ingredients} == {
            k: v.available for k, v in loaded.items()
        }
        recipes = conn.execute("SELECT count(*) FROM recipes").fetchone()
        assert recipes == (sum(len(d.recipe) for d in menu.dishes),)
        names = dict(conn.execute("SELECT ingredient_id, name FROM stock").fetchall())
        assert names["THIT_BO"] == "Thịt bò"

        with conn.transaction():
            assert receive_stock(conn, "THIT_BO", D("1"))
        assert load_seed(conn, menu) is False  # a restart
    assert stock(dsn)["THIT_BO"].available == loaded["THIT_BO"].available + 1


def test_two_instances_starting_together_load_the_seed_once(migrated: Callable[[str], str]) -> None:
    dsn = migrated("inventory-service")
    menu = load_menu()
    barrier = threading.Barrier(2)
    results: list[bool] = []

    def start() -> None:
        with psycopg.connect(dsn, autocommit=True) as conn:
            barrier.wait()
            results.append(load_seed(conn, menu))

    threads = [threading.Thread(target=start) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert sorted(results) == [False, True]
    assert len(stock(dsn)) == len(menu.ingredients)


def test_a_receipt_for_an_unknown_ingredient_changes_nothing(
    migrated: Callable[[str], str],
) -> None:
    dsn = migrated("inventory-service")
    with psycopg.connect(dsn, autocommit=True) as conn:
        assert receive_stock(conn, "KHONG_CO", D("1")) is False
