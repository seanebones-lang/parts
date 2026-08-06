"""High-level automation service: runs ledger, alerts, rulesets, email→order."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parrts.automation.bridge import BridgeError, draft_order_from_email
from parrts.automation.missing import hard_missing, missing_fields_for_email
from parrts.automation.rulesets import load_rulesets, save_rulesets
from parrts.automation.store import AutomationStore


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row(d: Any) -> dict[str, Any]:
    if d is None:
        return {}
    if isinstance(d, dict):
        return d
    return dict(d)


class AutomationService:
    """White-label AI workflow automation surface (offline SQLite)."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.store = AutomationStore(self.root)
        self.store.ensure_schema()

    def ensure_schema(self) -> None:
        self.store.ensure_schema()

    def get_rulesets(self) -> dict[str, Any]:
        return load_rulesets(self.root)

    def update_rulesets(self, data: dict[str, Any]) -> dict[str, Any]:
        return save_rulesets(self.root, data)

    def record_run(
        self,
        *,
        kind: str,
        source_ref: str | None = None,
        status: str = "ok",
        summary: str = "",
        detail: dict[str, Any] | None = None,
        requires_human: bool = False,
        alerts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self.ensure_schema()
        now = _utcnow()
        cur = self.store.execute(
            """
            INSERT INTO automation_runs
                (kind, source_ref, status, summary, detail_json, requires_human, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kind,
                source_ref or "",
                status,
                summary or "",
                json.dumps(detail or {}),
                1 if requires_human else 0,
                now,
            ),
        )
        run_id = int(cur.lastrowid or 0)
        alert_rows: list[dict[str, Any]] = []
        for a in alerts or []:
            ac = self.store.execute(
                """
                INSERT INTO automation_alerts
                    (run_id, severity, code, message, fields_json, resolved, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    run_id,
                    a.get("severity") or "yellow",
                    a.get("code") or "generic",
                    a.get("message") or "",
                    json.dumps(a.get("fields") or []),
                    now,
                ),
            )
            alert_rows.append(
                {
                    "id": int(ac.lastrowid or 0),
                    "run_id": run_id,
                    "severity": a.get("severity") or "yellow",
                    "code": a.get("code") or "generic",
                    "message": a.get("message") or "",
                    "fields": a.get("fields") or [],
                    "resolved": False,
                    "created_at": now,
                }
            )
        self.store.commit()
        return {
            "id": run_id,
            "kind": kind,
            "source_ref": source_ref or "",
            "status": status,
            "summary": summary or "",
            "detail": detail or {},
            "requires_human": requires_human,
            "created_at": now,
            "alerts": alert_rows,
        }

    def list_runs(
        self,
        *,
        kind: str | None = None,
        status: str | None = None,
        requires_human: bool | None = None,
        limit: int = 100,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        sql = "SELECT * FROM automation_runs WHERE 1=1"
        params: list[Any] = []
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if requires_human is not None:
            sql += " AND requires_human = ?"
            params.append(1 if requires_human else 0)
        if since:
            sql += " AND created_at >= ?"
            params.append(since)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(int(limit))
        rows = self.store.fetchall(sql, tuple(params))
        out: list[dict[str, Any]] = []
        for r in rows:
            d = _row(r)
            detail_raw = d.get("detail_json") or "{}"
            try:
                detail = json.loads(detail_raw) if isinstance(detail_raw, str) else detail_raw
            except json.JSONDecodeError:
                detail = {}
            out.append(
                {
                    "id": d.get("id"),
                    "kind": d.get("kind"),
                    "source_ref": d.get("source_ref"),
                    "status": d.get("status"),
                    "summary": d.get("summary"),
                    "detail": detail,
                    "requires_human": bool(d.get("requires_human")),
                    "created_at": d.get("created_at"),
                }
            )
        return out

    def list_alerts(
        self,
        *,
        unresolved_only: bool = True,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        sql = "SELECT * FROM automation_alerts WHERE 1=1"
        params: list[Any] = []
        if unresolved_only:
            sql += " AND resolved = 0"
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(int(limit))
        rows = self.store.fetchall(sql, tuple(params))
        out: list[dict[str, Any]] = []
        for r in rows:
            d = _row(r)
            fields_raw = d.get("fields_json") or "[]"
            try:
                fields = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw
            except json.JSONDecodeError:
                fields = []
            out.append(
                {
                    "id": d.get("id"),
                    "run_id": d.get("run_id"),
                    "severity": d.get("severity"),
                    "code": d.get("code"),
                    "message": d.get("message"),
                    "fields": fields,
                    "resolved": bool(d.get("resolved")),
                    "created_at": d.get("created_at"),
                }
            )
        return out

    def resolve_alert(self, alert_id: int) -> dict[str, Any]:
        self.ensure_schema()
        self.store.execute(
            "UPDATE automation_alerts SET resolved = 1 WHERE id = ?",
            (int(alert_id),),
        )
        self.store.commit()
        row = self.store.fetchone("SELECT * FROM automation_alerts WHERE id = ?", (int(alert_id),))
        if not row:
            raise KeyError(f"alert {alert_id} not found")
        d = _row(row)
        return {
            "id": d.get("id"),
            "resolved": True,
            "severity": d.get("severity"),
            "code": d.get("code"),
            "message": d.get("message"),
        }

    def results_summary(self, *, limit_runs: int = 50) -> dict[str, Any]:
        """Daily/always results page payload."""
        self.ensure_schema()
        runs = self.list_runs(limit=limit_runs)
        alerts = self.list_alerts(unresolved_only=True, limit=50)
        by_status: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        human = 0
        for r in runs:
            st = str(r.get("status") or "unknown")
            by_status[st] = by_status.get(st, 0) + 1
            k = str(r.get("kind") or "unknown")
            by_kind[k] = by_kind.get(k, 0) + 1
            if r.get("requires_human"):
                human += 1
        total_runs = self.store.fetchone("SELECT COUNT(*) AS c FROM automation_runs")
        open_alerts = self.store.fetchone(
            "SELECT COUNT(*) AS c FROM automation_alerts WHERE resolved = 0"
        )
        return {
            "ok": True,
            "db_path": str(self.store.db_path),
            "total_runs": int(total_runs["c"]) if total_runs else 0,
            "open_alerts": int(open_alerts["c"]) if open_alerts else 0,
            "recent_requires_human": human,
            "by_status": by_status,
            "by_kind": by_kind,
            "runs": runs,
            "alerts": alerts,
            "rulesets": self.get_rulesets(),
            "integrations": (self.get_rulesets().get("integrations") or {}),
        }

    def record_email_processed(self, email_row: dict[str, Any]) -> dict[str, Any]:
        """Hook after email pipeline — missing-field alerts + run ledger."""
        rules = self.get_rulesets()
        extracted = email_row.get("extracted") or {}
        if not isinstance(extracted, dict):
            extracted = {}
        hits = email_row.get("hits") or []
        email_type = email_row.get("email_type")
        sender = email_row.get("sender_email")
        missing = missing_fields_for_email(
            email_type=email_type,
            extracted=extracted,
            hits=hits if isinstance(hits, list) else [],
            sender_email=sender,
            rules=rules,
        )
        hard = hard_missing(missing)
        tl = email_row.get("traffic_light")
        color = tl.get("color") if isinstance(tl, dict) else tl
        err = email_row.get("error_message") or email_row.get("pipeline_error")
        status = "ok"
        requires_human = bool(email_row.get("requires_human")) or bool(hard)
        alerts: list[dict[str, Any]] = []
        alert_cfg = rules.get("alerts") or {}

        if err and alert_cfg.get("on_pipeline_error", True):
            status = "error"
            requires_human = True
            alerts.append(
                {
                    "severity": "red",
                    "code": "pipeline_error",
                    "message": str(err)[:500],
                    "fields": [],
                }
            )
        if hard and alert_cfg.get("on_missing_fields", True):
            status = "needs_input" if status == "ok" else status
            requires_human = True
            alerts.append(
                {
                    "severity": "yellow",
                    "code": "missing_fields",
                    "message": f"Missing required fields: {', '.join(hard)}",
                    "fields": hard,
                }
            )
        if color == "red" and alert_cfg.get("on_red_grade", True):
            requires_human = True
            if not any(a.get("code") == "pipeline_error" for a in alerts):
                alerts.append(
                    {
                        "severity": "red",
                        "code": "red_grade",
                        "message": (email_row.get("traffic_reason") or "red traffic light")[:300],
                        "fields": [],
                    }
                )
            if status == "ok":
                status = "escalated"

        eid = email_row.get("id")
        return self.record_run(
            kind="email_process",
            source_ref=f"email:{eid}",
            status=status,
            summary=f"{email_type or 'email'} → {color or '?'} specialist={email_row.get('specialist')}",
            detail={
                "email_id": eid,
                "email_type": email_type,
                "traffic_light": color,
                "specialist": email_row.get("specialist"),
                "missing_fields": missing,
                "subject": (email_row.get("subject") or "")[:120],
            },
            requires_human=requires_human,
            alerts=alerts,
        )

    def email_to_order(
        self,
        email_id: int,
        *,
        confirm: bool = False,
        email_service: Any | None = None,
        dms_service: Any | None = None,
    ) -> dict[str, Any]:
        rules = self.get_rulesets()
        e2o = rules.get("email_to_order") or {}
        if not e2o.get("enabled", True):
            raise BridgeError("email_to_order ruleset disabled")

        if email_service is None:
            from parrts.email import EmailService

            email_service = EmailService(root=self.root)
        if dms_service is None:
            from parrts.dms.service import DmsService

            dms_service = DmsService(root=self.root)

        email = email_service.get(int(email_id))
        if not email:
            raise KeyError(f"email {email_id} not found")

        # HIL gate
        require_hil = bool(e2o.get("require_human_confirm", True))
        if require_hil and not confirm:
            preview = draft_order_from_email(
                dms=dms_service,
                email=email,
                confirm=False,
                default_qty=int(e2o.get("default_qty") or 1),
            )
            run = self.record_run(
                kind="email_to_order_preview",
                source_ref=f"email:{email_id}",
                status="pending_hil",
                summary=f"Draft order preview for email {email_id} (awaiting confirm)",
                detail=preview,
                requires_human=True,
                alerts=[
                    {
                        "severity": "yellow",
                        "code": "hil_confirm",
                        "message": "Human must confirm email→order before stock reserve",
                        "fields": [],
                    }
                ],
            )
            preview["automation_run"] = run
            return preview

        result = draft_order_from_email(
            dms=dms_service,
            email=email,
            confirm=True,
            default_qty=int(e2o.get("default_qty") or 1),
        )
        run = self.record_run(
            kind="email_to_order",
            source_ref=f"email:{email_id}",
            status="ok",
            summary=result.get("message") or f"Order created from email {email_id}",
            detail={
                "email_id": email_id,
                "order_id": (result.get("order") or {}).get("id"),
                "lines": (result.get("order") or {}).get("lines") or result.get("lines"),
            },
            requires_human=False,
        )
        result["automation_run"] = run
        return result

    def status(self) -> dict[str, Any]:
        s = self.results_summary(limit_runs=5)
        return {
            "ok": True,
            "db_path": s["db_path"],
            "total_runs": s["total_runs"],
            "open_alerts": s["open_alerts"],
            "rulesets_version": (s.get("rulesets") or {}).get("version"),
            "integrations": s.get("integrations"),
            "min_bar": "ai_workflow_automation",
        }
