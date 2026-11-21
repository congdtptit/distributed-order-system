"""Stock data: loading the seed file, stock receipts.

Section 1 of docs/02-detailed-design.md: Inventory loads ingredients, stock and recipes on its
first start only, when ``stock`` is empty, so that a restart never overwrites stock that has
changed. Stock accounting is the table in section 3.3 of docs/01-business-spec.md.
"""

from decimal import Decimal
from typing import Any

import psycopg

from common.seed import Menu
from inventory_service.checks import ensure_menu_version

_SEED_LOCK = 7_420_002
"""Advisory lock key: the two Inventory instances start at the same time."""


def load_seed(conn: psycopg.Connection[Any], menu: Menu) -> bool:
    """Load the seed when ``stock`` is empty. True if it loaded, False if stock already exists.
    Also creates the ``menu_version`` row on the first start."""
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (_SEED_LOCK,))
        ensure_menu_version(conn)
        if conn.execute("SELECT EXISTS (SELECT 1 FROM stock)").fetchone() == (True,):
            return False
        for i in menu.ingredients:
            conn.execute(
                "INSERT INTO stock (ingredient_id, name, unit, available) VALUES (%s, %s, %s, %s)",
                (i.ingredient_id, i.name, i.unit, i.stock),
            )
        for dish in menu.dishes:
            for line in dish.recipe:
                conn.execute(
                    "INSERT INTO recipes (dish_id, ingredient_id, quantity) VALUES (%s, %s, %s)",
                    (dish.dish_id, line.ingredient_id, line.quantity),
                )
    return True


def receive_stock(conn: psycopg.Connection[Any], ingredient_id: str, quantity: Decimal) -> bool:
    """Stock receipt: add to available stock (accounting table, last row). False if the
    ingredient does not exist. Runs in the caller's transaction.

    Step 3 puts this behind ``POST /stock/receipts``; phase 2 adds the dish-status computation.
    """
    if quantity <= 0:
        raise ValueError("a receipt adds a positive quantity")
    return (
        conn.execute(
            "UPDATE stock SET available = available + %s WHERE ingredient_id = %s",
            (quantity, ingredient_id),
        ).rowcount
        == 1
    )
