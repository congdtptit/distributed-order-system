"""Topic names of section 13.1 of docs/01-business-spec.md.

The branch that sent a message is derived from the topic name, never from ``branch_id`` in the
message body (section 9 of the specification).
"""

KITCHEN_ORDERS = "kitchen-orders"
STOCK_COMMANDS = "stock-commands"
MENU_EVENTS = "menu-events"
DLQ = "dlq"

# Topic families that carry the branch in their name: <family>.<branch>.
BRANCH_FAMILIES = ("order-events", "cancel-events", "status-events")


def order_events(branch: str) -> str:
    return f"order-events.{branch}"


def cancel_events(branch: str) -> str:
    return f"cancel-events.{branch}"


def status_events(branch: str) -> str:
    return f"status-events.{branch}"


def branch_from_topic(topic: str) -> str | None:
    """``order-events.POS01`` -> ``POS01``; a topic without a branch in its name -> None."""
    family, dot, branch = topic.partition(".")
    if dot and family in BRANCH_FAMILIES and branch and "." not in branch:
        return branch
    return None
