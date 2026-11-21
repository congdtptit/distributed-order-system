"""backend/seed/menu.json is consistent (section 1 of docs/02-detailed-design.md)."""

import json
import re
from pathlib import Path
from typing import Any

SEED = Path(__file__).resolve().parents[2] / "seed" / "menu.json"
CODE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _load() -> dict[str, Any]:
    return json.loads(SEED.read_text(encoding="utf-8"))


def test_ids_are_unique_codes() -> None:
    seed = _load()
    ingredient_ids = [i["ingredient_id"] for i in seed["ingredients"]]
    dish_ids = [d["dish_id"] for d in seed["dishes"]]
    for ids in (ingredient_ids, dish_ids):
        assert len(ids) == len(set(ids))
        assert all(CODE.match(i) for i in ids), ids


def test_every_ingredient_has_a_name_a_unit_and_non_negative_stock() -> None:
    for ingredient in _load()["ingredients"]:
        assert ingredient["name"].strip()
        assert ingredient["unit"].strip()
        assert ingredient["stock"] >= 0


def test_every_dish_has_a_name_and_a_recipe_of_known_ingredients() -> None:
    seed = _load()
    known = {i["ingredient_id"] for i in seed["ingredients"]}
    for dish in seed["dishes"]:
        assert dish["name"].strip()
        lines = [line["ingredient_id"] for line in dish["recipe"]]
        assert lines, f"{dish['dish_id']} has no recipe"
        assert len(lines) == len(set(lines)), f"{dish['dish_id']} lists an ingredient twice"
        assert set(lines) <= known, f"{dish['dish_id']} uses {set(lines) - known}"
        assert all(line["quantity"] > 0 for line in dish["recipe"])
