"""Put a freshly emptied cluster into a varied state, through the services' own APIs: for the
report's screenshots (step 8) and as a starting point for the demo.

    docker compose --profile full down -v && docker compose --profile full up -d --wait
    docker compose exec -T tools python scripts/demo_data.py

What it leaves: orders at POS01, POS02 and ONLINE; Queued, Cooking and Completed tickets; one
ticket rejected for a spoiled ingredient (SUON, so Inventory flags it for a stock check and the
other Cơm tấm ticket shows the red warning); one rejected for broken equipment; one order the
customer cancelled; one order that failed for lack of shrimp.
"""

import json
import time
import urllib.error
import urllib.request
from typing import Any

BRANCH = {
    "POS01": "http://pos01:8000",
    "POS02": "http://pos02:8000",
    "ONLINE": "http://online:8000",
}
KITCHEN = "http://kitchen:8000"


def call(method: str, url: str, body: Any = None) -> tuple[int, Any]:
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


def wait(what: str, check: Any, timeout_s: float = 60) -> Any:
    deadline = time.monotonic() + timeout_s
    while not (value := check()):
        if time.monotonic() > deadline:
            raise SystemExit(f"timed out waiting for {what}")
        time.sleep(0.3)
    return value


def order(branch: str, *items: tuple[str, int]) -> str:
    status, body = call(
        "POST",
        f"{BRANCH[branch]}/orders",
        {"items": [{"dish_id": d, "quantity": q} for d, q in items]},
    )
    assert status == 201, body
    order_id = body["order_id"]
    decided = wait(
        f"Inventory's answer for {order_id}",
        lambda: (
            (o := call("GET", f"{BRANCH[branch]}/orders/{order_id}")[1])["status"] != "CHO_KHO"
            and o
        ),
    )
    print(f"{branch} {order_id[:8]} {items} -> {decided['status']}")
    return order_id


def queued(order_id: str) -> None:
    def ticket_status() -> str | None:
        _, tickets = call("GET", f"{KITCHEN}/tickets")
        return next((t["status"] for t in tickets if t["order_id"] == order_id), None)

    wait(f"the ticket of {order_id}", lambda: ticket_status() == "CHO_NAU")


def kitchen(order_id: str, action: str, body: Any = None) -> None:
    status, answer = call("POST", f"{KITCHEN}/tickets/{order_id}/{action}", body)
    assert status == 200, answer
    print(f"Kitchen {action} {order_id[:8]}")


def main() -> None:
    pho = order("POS01", ("PHO_BO", 2))
    bun_tra = order("POS01", ("BUN_CHA", 1), ("TRA_DA", 2))
    com_spoiled = order("POS01", ("COM_TAM", 1))
    goi = order("POS01", ("GOI_CUON", 1))
    banh_mi = order("POS01", ("BANH_MI_THIT", 2))
    pho_cancelled = order("POS02", ("PHO_BO", 1))
    com_warned = order("POS02", ("COM_TAM", 2), ("TRA_DA", 1))
    order("POS02", ("GOI_CUON", 50))  # 3 kg of shrimp, 2 kg in stock: Failed
    bun_online = order("ONLINE", ("BUN_CHA", 2))
    banh_mi_online = order("ONLINE", ("BANH_MI_THIT", 1))
    for o in (pho, bun_tra, com_spoiled, goi, banh_mi, pho_cancelled, com_warned, bun_online):
        queued(o)
    queued(banh_mi_online)

    kitchen(pho, "start")
    kitchen(pho, "complete")
    kitchen(bun_online, "start")
    kitchen(
        com_spoiled,
        "reject",
        {"reason_code": "SPOILED_INGREDIENT", "spoiled_ingredients": ["SUON"]},
    )
    kitchen(banh_mi, "reject", {"reason_code": "EQUIPMENT_FAILURE", "spoiled_ingredients": []})

    status, body = call(
        "POST", f"{BRANCH['POS02']}/orders/{pho_cancelled}/cancel", {"reason_code": "CHANGED_MIND"}
    )
    assert status == 202, body
    wait(
        "the customer's cancel to go through",
        lambda: call("GET", f"{BRANCH['POS02']}/orders/{pho_cancelled}")[1]["status"] == "DA_HUY",
    )
    print(f"POS02 {pho_cancelled[:8]} cancelled by the customer")
    wait(
        "the warning on the other Cơm tấm ticket",
        lambda: any(
            t["order_id"] == com_warned and t["warnings"]
            for t in call("GET", f"{KITCHEN}/tickets")[1]
        ),
    )
    print("done: Kitchen shows the SUON warning; Inventory has SUON awaiting a stock check")


if __name__ == "__main__":
    main()
