"""Offline queue pure helpers — mirrors FE localStorage contract (Wave 31).

No browser; validates queue item shape + flush bookkeeping used by FE.
"""

from __future__ import annotations

import json
from typing import Any


def validate_mutation(item: dict[str, Any]) -> bool:
    if not isinstance(item, dict):
        return False
    if not str(item.get("id") or "").strip():
        return False
    kind = item.get("kind")
    if kind not in {"create_order", "create_customer"}:
        return False
    path = str(item.get("path") or "")
    if kind == "create_order" and path != "/api/v1/dms/orders":
        return False
    if kind == "create_customer" and path != "/api/v1/dms/customers":
        return False
    body = item.get("body")
    if not isinstance(body, dict):
        return False
    if kind == "create_order" and "customer_id" not in body:
        return False
    if kind == "create_customer" and not str(body.get("name") or "").strip():
        return False
    return True


def merge_queue(existing: list[dict[str, Any]], new: dict[str, Any], *, cap: int = 100) -> list[dict[str, Any]]:
    out = [x for x in existing if validate_mutation(x)]
    if validate_mutation(new):
        out.append(new)
    return out[:cap]


def test_validate_and_cap() -> None:
    good_order = {
        "id": "oq_1",
        "kind": "create_order",
        "path": "/api/v1/dms/orders",
        "body": {"customer_id": 1, "lines": [{"sku": "X", "qty": 1}]},
        "created_at": "2026-08-05T00:00:00Z",
        "attempts": 0,
    }
    good_cust = {
        "id": "oq_2",
        "kind": "create_customer",
        "path": "/api/v1/dms/customers",
        "body": {"name": "Acme"},
        "created_at": "2026-08-05T00:00:00Z",
        "attempts": 0,
    }
    bad = {"id": "x", "kind": "pay", "path": "/x", "body": {}}
    assert validate_mutation(good_order)
    assert validate_mutation(good_cust)
    assert not validate_mutation(bad)
    q = merge_queue([], good_order)
    q = merge_queue(q, good_cust)
    q = merge_queue(q, bad)
    assert len(q) == 2
    # round-trip JSON like localStorage
    raw = json.dumps(q)
    loaded = json.loads(raw)
    assert all(validate_mutation(x) for x in loaded)
