"""The fixed reason codes of section 10 of docs/01-business-spec.md (codes in section 1 of
docs/02-detailed-design.md). There is no free-text reason anywhere."""

from typing import Final

# Inventory fails an order (table 3.3, BR11, BR12, BR6).
INSUFFICIENT_INGREDIENTS: Final = "INSUFFICIENT_INGREDIENTS"
AWAITING_STOCK_CHECK: Final = "AWAITING_STOCK_CHECK"
NO_RECIPE: Final = "NO_RECIPE"
ORDER_EXPIRED: Final = "ORDER_EXPIRED"
FUTURE_CREATION_TIME: Final = "FUTURE_CREATION_TIME"
INVALID_ORDER_DATA: Final = "INVALID_ORDER_DATA"

# The Kitchen rejects a ticket (Flow A).
EQUIPMENT_FAILURE: Final = "EQUIPMENT_FAILURE"
SHORT_STAFFED: Final = "SHORT_STAFFED"
SPOILED_INGREDIENT: Final = "SPOILED_INGREDIENT"

# The customer cancels (Flow B). Proposed values, still to be confirmed (section 11).
CHANGED_MIND: Final = "CHANGED_MIND"
WAITED_TOO_LONG: Final = "WAITED_TOO_LONG"
WRONG_ORDER_ENTERED: Final = "WRONG_ORDER_ENTERED"

INVENTORY_FAILURE: Final = frozenset(
    {
        INSUFFICIENT_INGREDIENTS,
        AWAITING_STOCK_CHECK,
        NO_RECIPE,
        ORDER_EXPIRED,
        FUTURE_CREATION_TIME,
        INVALID_ORDER_DATA,
    }
)
KITCHEN_REJECTION: Final = frozenset({EQUIPMENT_FAILURE, SHORT_STAFFED, SPOILED_INGREDIENT})
CUSTOMER_CANCEL: Final = frozenset({CHANGED_MIND, WAITED_TOO_LONG, WRONG_ORDER_ENTERED})
