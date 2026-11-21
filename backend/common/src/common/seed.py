"""The dish catalogue and starting data, ``backend/seed/menu.json`` (section 1 of
docs/02-detailed-design.md). Inventory loads ingredients, stock and recipes from it; each branch
loads the dishes."""

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

SEED_FILE = Path(__file__).resolve().parents[3] / "seed" / "menu.json"


@dataclass(frozen=True)
class Ingredient:
    ingredient_id: str
    name: str
    unit: str
    stock: Decimal


@dataclass(frozen=True)
class RecipeLine:
    ingredient_id: str
    quantity: Decimal


@dataclass(frozen=True)
class Dish:
    dish_id: str
    name: str
    recipe: tuple[RecipeLine, ...]


@dataclass(frozen=True)
class Menu:
    ingredients: tuple[Ingredient, ...]
    dishes: tuple[Dish, ...]


def load_menu(path: Path = SEED_FILE) -> Menu:
    # Decimals keep quantities exact (NUMERIC(12,3) in the DB).
    data = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal, parse_int=Decimal)
    return Menu(
        ingredients=tuple(
            Ingredient(i["ingredient_id"], i["name"], i["unit"], Decimal(i["stock"]))
            for i in data["ingredients"]
        ),
        dishes=tuple(
            Dish(
                d["dish_id"],
                d["name"],
                tuple(RecipeLine(r["ingredient_id"], Decimal(r["quantity"])) for r in d["recipe"]),
            )
            for d in data["dishes"]
        ),
    )
