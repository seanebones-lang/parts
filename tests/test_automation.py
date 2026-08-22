"""Automation MIN bar — runs ledger, missing fields, email→order HIL bridge."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    return tmp_path


def test_missing_fields_detects_sku(root: Path) -> None:
    from parrts.automation.missing import hard_missing, missing_fields_for_email
    from parrts.automation.rulesets import load_rulesets

    rules = load_rulesets(root)
    miss = missing_fields_for_email(
        email_type="parts_order",
        extracted={"sku_mentions": [], "parts_requested": []},
        hits=[],
        sender_email="buyer@example.com",
        rules=rules,
    )
    assert "sku_or_parts" in hard_missing(miss)

    ok = missing_fields_for_email(
        email_type="parts_order",
        extracted={"sku_mentions": ["OEM-OF-TC-001"]},
        hits=[],
        sender_email="buyer@example.com",
        rules=rules,
    )
    assert "sku_or_parts" not in hard_missing(ok)


def test_record_run_and_results(root: Path) -> None:
    from parrts.automation import AutomationService

    svc = AutomationService(root)
    run = svc.record_run(
        kind="email_process",
        source_ref="email:1",
        status="needs_input",
        summary="test",
        requires_human=True,
        alerts=[
            {
                "severity": "yellow",
                "code": "missing_fields",
                "message": "Missing sku_or_parts",
                "fields": ["sku_or_parts"],
            }
        ],
    )
    assert run["id"]
    assert len(run["alerts"]) == 1
    summary = svc.results_summary()
    assert summary["total_runs"] >= 1
    assert summary["open_alerts"] >= 1
    alerts = svc.list_alerts(unresolved_only=True)
    assert any(a["code"] == "missing_fields" for a in alerts)
    resolved = svc.resolve_alert(int(alerts[0]["id"]))
    assert resolved["resolved"] is True
    assert svc.list_alerts(unresolved_only=True) == []


def test_rulesets_roundtrip(root: Path) -> None:
    from parrts.automation import AutomationService

    svc = AutomationService(root)
    rs = svc.get_rulesets()
    assert rs["email_to_order"]["require_human_confirm"] is True
    updated = svc.update_rulesets({"email_to_order": {"default_qty": 2}})
    assert updated["email_to_order"]["default_qty"] == 2
    assert (root / ".parrts" / "rulesets.json").is_file()


def test_email_process_writes_automation_run(root: Path) -> None:
    from parrts.automation import AutomationService
    from parrts.email import EmailService

    email = EmailService(root=root)
    row = email.ingest(
        subject="Need quote on brake pads",
        body_text="Looking for ceramic brake pads price please",
        sender_email="shop@example.com",
        sender_name="Shop",
        process=True,
    )
    assert row.get("id")
    auto = AutomationService(root)
    runs = auto.list_runs(kind="email_process", limit=20)
    assert any(str(row["id"]) in str(r.get("source_ref")) for r in runs)


def test_email_to_order_preview_and_confirm(root: Path) -> None:
    from parrts.automation import AutomationService
    from parrts.dms.service import DmsService
    from parrts.email import EmailService

    dms = DmsService(root=root)
    dms.seed_demo(seed=42, n_skus=20, locations=3)
    inv = dms.list_inventory()
    assert inv, "seed should create inventory"
    sku = str(inv[0]["sku"])
    # ensure qty
    assert int(inv[0].get("qty") or 0) >= 1

    email = EmailService(root=root)
    row = email.ingest(
        subject=f"Please order SKU {sku}",
        body_text=f"Please order qty 1 of SKU: {sku} for counter pickup.",
        sender_email="buyer@example.com",
        sender_name="Buyer",
        process=True,
    )
    eid = int(row["id"])

    auto = AutomationService(root)
    preview = auto.email_to_order(eid, confirm=False, email_service=email, dms_service=dms)
    assert preview.get("confirmed") is False
    assert preview.get("status") == "draft_preview"
    assert preview.get("lines")

    created = auto.email_to_order(eid, confirm=True, email_service=email, dms_service=dms)
    assert created.get("confirmed") is True
    assert created.get("order", {}).get("id")
    orders = dms.list_orders()
    assert any(o.get("id") == created["order"]["id"] for o in orders)


def test_automation_api_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("sqlalchemy")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    monkeypatch.setenv("PARRTS_ROOT", str(tmp_path))
    monkeypatch.setenv("AUTH_MODE", "demo")

    from app.api.deps import require_user_if_production
    from app.api.v1.endpoints import automation as auto_ep

    monkeypatch.setattr(auto_ep, "resolve_monorepo_root", lambda: tmp_path)

    app = FastAPI()
    app.include_router(auto_ep.router, prefix="/api/v1/automation")
    app.dependency_overrides[require_user_if_production] = lambda: None
    client = TestClient(app)

    r = client.get("/api/v1/automation/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("min_bar") == "ai_workflow_automation"

    # seed a run via service then list results
    from parrts.automation import AutomationService

    AutomationService(tmp_path).record_run(
        kind="test",
        status="ok",
        summary="api smoke",
    )
    res = client.get("/api/v1/automation/results")
    assert res.status_code == 200
    assert res.json().get("total_runs", 0) >= 1

    rs = client.get("/api/v1/automation/rulesets")
    assert rs.status_code == 200
    assert "email_to_order" in (rs.json().get("rulesets") or {})
