"""The Kitchen's main path (tier 1): table 3.2 of docs/01-business-spec.md without cancel
requests, Flow A, the ticket warning; section 4 of docs/02-detailed-design.md. The buttons run
through the HTTP API on the test DB."""

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from kitchen_support import (
    BUN_CHA_RESERVED,
    NOW,
    check_changed,
    deliver,
    order_failed,
    order_reserved,
    outbox,
    record,
    records_count,
)

from common import reasons
from common.api import get_clock, get_conn
from common.clock import FixedClock
from kitchen_service.app import app


@pytest.fixture
def kdb(migrated: Callable[[str], str]) -> str:
    return migrated("kitchen-service")


@pytest.fixture
def api(kdb: str) -> Iterator[TestClient]:
    def conn() -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(kdb) as c:
            yield c

    app.dependency_overrides[get_conn] = conn
    app.dependency_overrides[get_clock] = lambda: FixedClock(NOW)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def queued(kdb: str, **kwargs: Any) -> uuid.UUID:
    env = order_reserved(**kwargs)
    assert deliver(kdb, env)
    assert env.order_id is not None
    return env.order_id


def tickets(api: TestClient) -> dict[str, dict[str, Any]]:
    response = api.get("/tickets")
    assert response.status_code == 200
    return {t["order_id"]: t for t in response.json()}


def test_an_order_from_inventory_becomes_a_queued_ticket_with_its_reserved_ingredients(
    kdb: str, api: TestClient
) -> None:
    order_id = queued(kdb)
    rec = record(kdb, order_id)
    assert rec is not None
    assert (rec["status"], rec["origin_branch"]) == ("CHO_NAU", "POS01")
    [ticket] = tickets(api).values()
    assert ticket["status"] == "CHO_NAU"
    assert [r["ingredient_id"] for r in ticket["reserved"]] == ["BANH_PHO", "RAU_SONG", "THIT_BO"]
    assert ticket["warnings"] == []
    assert outbox(kdb) == []  # a new ticket tells nobody


def test_the_same_order_arriving_again_creates_no_second_ticket(kdb: str) -> None:
    env = order_reserved()
    assert deliver(kdb, env) is True
    assert deliver(kdb, env) is False
    assert records_count(kdb) == 1
    assert outbox(kdb) == []


def test_start_then_complete_reports_consumed_to_inventory_and_completed_to_the_branch(
    kdb: str, api: TestClient
) -> None:
    order_id = queued(kdb)
    started = api.post(f"/tickets/{order_id}/start")
    assert started.status_code == 200 and started.json()["status"] == "DANG_NAU"
    done = api.post(f"/tickets/{order_id}/complete")
    assert done.status_code == 200 and done.json()["status"] == "HOAN_TAT"
    assert [(s.topic, s.event_type, s.key) for s in outbox(kdb)] == [
        ("stock-commands", "StockConsumed", str(order_id)),
        ("status-events.POS01", "OrderCompleted", str(order_id)),
    ]
    assert tickets(api) == {}  # Completed tickets leave the list


def test_reject_releases_everything_for_equipment_failure(kdb: str, api: TestClient) -> None:
    order_id = queued(kdb)
    response = api.post(
        f"/tickets/{order_id}/reject", json={"reason_code": reasons.EQUIPMENT_FAILURE}
    )
    assert response.status_code == 200
    rec = record(kdb, order_id)
    assert rec is not None
    assert (rec["status"], rec["cancelled_by"], rec["close_reason"]) == (
        "DA_HUY",
        "KITCHEN",
        reasons.EQUIPMENT_FAILURE,
    )
    assert [(s.topic, s.event_type, s.payload) for s in outbox(kdb)] == [
        (
            "stock-commands",
            "ReleaseRequested",
            {
                "cancelled_by": "KITCHEN",
                "reason_code": reasons.EQUIPMENT_FAILURE,
                "spoiled_ingredients": [],
            },
        ),
        (
            "status-events.POS01",
            "OrderCancelled",
            {"cancelled_by": "KITCHEN", "reason_code": reasons.EQUIPMENT_FAILURE},
        ),
    ]


def test_reject_for_a_spoiled_ingredient_names_it_in_the_release_command(
    kdb: str, api: TestClient
) -> None:
    order_id = queued(kdb)
    response = api.post(
        f"/tickets/{order_id}/reject",
        json={"reason_code": reasons.SPOILED_INGREDIENT, "spoiled_ingredients": ["THIT_BO"]},
    )
    assert response.status_code == 200
    release = outbox(kdb)[0]
    assert release.payload["spoiled_ingredients"] == ["THIT_BO"]
    rec = record(kdb, order_id)
    assert rec is not None and rec["spoiled"] == ["THIT_BO"]


@pytest.mark.parametrize(
    "body",
    [
        {"reason_code": reasons.SPOILED_INGREDIENT},
        {"reason_code": reasons.SPOILED_INGREDIENT, "spoiled_ingredients": ["DA"]},
        {"reason_code": reasons.EQUIPMENT_FAILURE, "spoiled_ingredients": ["THIT_BO"]},
        {"reason_code": reasons.CHANGED_MIND},
    ],
    ids=[
        "spoiled-without-ingredient",
        "ingredient-not-on-ticket",
        "list-without-spoiled-reason",
        "not-a-kitchen-reason",
    ],
)
def test_reject_with_a_bad_reason_or_ingredient_is_refused_and_changes_nothing(
    kdb: str, api: TestClient, body: dict[str, Any]
) -> None:
    order_id = queued(kdb)
    assert api.post(f"/tickets/{order_id}/reject", json=body).status_code == 400
    rec = record(kdb, order_id)
    assert rec is not None and rec["status"] == "CHO_NAU"
    assert outbox(kdb) == []


@pytest.mark.kb(50)
def test_reject_on_a_cooking_ticket_is_refused(kdb: str, api: TestClient) -> None:
    """Scenario 50: staff press Reject on a ticket that is already Cooking. The operation is
    rejected; the ticket stays Cooking; Inventory receives no release command."""
    order_id = queued(kdb)
    assert api.post(f"/tickets/{order_id}/start").status_code == 200
    response = api.post(f"/tickets/{order_id}/reject", json={"reason_code": reasons.SHORT_STAFFED})
    # The operation is rejected ...
    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "DANG_NAU"
    # ... the ticket stays Cooking ...
    rec = record(kdb, order_id)
    assert rec is not None and rec["status"] == "DANG_NAU"
    # ... and Inventory receives no release command.
    assert [s.event_type for s in outbox(kdb)] == ["StockConsumed"]


def test_buttons_on_the_wrong_status_or_an_unknown_order(kdb: str, api: TestClient) -> None:
    order_id = queued(kdb)
    assert api.post(f"/tickets/{order_id}/complete").status_code == 409  # not cooking yet
    assert api.post(f"/tickets/{uuid.uuid4()}/start").status_code == 404
    assert api.post("/tickets/not-a-uuid/start").status_code == 422
    assert records_count(kdb) == 1  # a button never creates a record


def test_failed_at_inventory_is_recorded_even_without_a_record(kdb: str) -> None:
    """Table 3.2 row "(none), Inventory reports Failed"; prohibition 11."""
    env = order_failed(reason=reasons.INSUFFICIENT_INGREDIENTS)
    deliver(kdb, env)
    rec = record(kdb, env.order_id)
    assert rec is not None
    assert (rec["status"], rec["origin_branch"], rec["close_reason"]) == (
        "THAT_BAI",
        "POS01",
        reasons.INSUFFICIENT_INGREDIENTS,
    )
    assert outbox(kdb) == []  # Inventory already told the branch


def test_a_repeat_reaching_a_terminal_status_gets_the_stored_result_and_no_second_release(
    kdb: str, api: TestClient
) -> None:
    env = order_reserved()
    deliver(kdb, env)
    api.post(f"/tickets/{env.order_id}/reject", json={"reason_code": reasons.EQUIPMENT_FAILURE})
    sent = len(outbox(kdb))
    again = order_reserved(env.order_id)  # the same order in a new message
    deliver(kdb, again)
    replies = outbox(kdb)[sent:]
    assert [(s.topic, s.event_type, s.causation_id) for s in replies] == [
        ("status-events.POS01", "OrderCancelled", str(again.event_id))
    ]
    assert [s.event_type for s in outbox(kdb)].count("ReleaseRequested") == 1


@pytest.mark.kb(6)
def test_queued_tickets_with_a_flagged_ingredient_show_a_warning(kdb: str, api: TestClient) -> None:
    """Scenario 6, the ticket warning part: the Kitchen rejects with the reason spoiled
    ingredient (meat) ... Queued tickets that contain meat show a warning. The flag reaches the
    Kitchen as Inventory's IngredientCheckChanged (step 3)."""
    with_meat = queued(kdb)  # PHO_BO: THIT_BO
    without_meat = queued(kdb, reserved=BUN_CHA_RESERVED, dish="BUN_CHA")
    cooking = queued(kdb)
    api.post(f"/tickets/{cooking}/start")
    deliver(kdb, check_changed("THIT_BO", True, seq=1))
    shown = tickets(api)
    assert shown[str(with_meat)]["warnings"] == ["THIT_BO"]
    assert shown[str(without_meat)]["warnings"] == []
    assert shown[str(cooking)]["warnings"] == []  # the warning is for Queued tickets
    # The warning is only a warning: the ticket is not cancelled by itself (Flow A rules).
    rec = record(kdb, with_meat)
    assert rec is not None and rec["status"] == "CHO_NAU"


@pytest.mark.kb(48)
def test_the_warning_disappears_when_the_flag_is_cleared(kdb: str, api: TestClient) -> None:
    """Scenario 48, the warning part: meat is flagged and a Queued ticket that contains meat
    is showing a warning; Inventory confirms that the stock check is done. The warning on the
    ticket disappears."""
    order_id = queued(kdb)
    deliver(kdb, check_changed("THIT_BO", True, seq=1))
    assert tickets(api)[str(order_id)]["warnings"] == ["THIT_BO"]
    deliver(kdb, check_changed("THIT_BO", False, seq=2))
    assert tickets(api)[str(order_id)]["warnings"] == []


def test_an_older_flag_message_does_not_overwrite_a_newer_one(kdb: str, api: TestClient) -> None:
    order_id = queued(kdb)
    deliver(kdb, check_changed("THIT_BO", False, seq=5))
    deliver(kdb, check_changed("THIT_BO", True, seq=4))  # arrives late
    assert tickets(api)[str(order_id)]["warnings"] == []
    deliver(kdb, check_changed("THIT_BO", True, seq=1, epoch=2))  # a new epoch wins
    assert tickets(api)[str(order_id)]["warnings"] == ["THIT_BO"]
