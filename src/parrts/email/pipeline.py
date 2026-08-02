"""End-to-end inbound email pipeline: classify → specialist → grade → persist."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from parrts.email.classify import classify_email
from parrts.email.policy import grade_email
from parrts.email.specialists import run_specialist
from parrts.email.store import EmailStore


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    d = dict(row)
    for key in ("extracted_json", "hits_json", "actions_json", "agents_invoked_json"):
        raw = d.get(key)
        if isinstance(raw, str) and raw:
            try:
                d[key.replace("_json", "")] = json.loads(raw)
            except json.JSONDecodeError:
                d[key.replace("_json", "")] = {}
        elif key in d:
            d[key.replace("_json", "")] = [] if "json" in key and "extracted" not in key else {}
    d["requires_human"] = bool(d.get("requires_human"))
    d["ai_processed"] = bool(d.get("ai_processed"))
    d["response_sent"] = bool(d.get("response_sent"))
    # public aliases
    d["traffic_light"] = {
        "color": d.get("traffic_light"),
        "confidence": d.get("traffic_confidence"),
        "reason": d.get("traffic_reason"),
        "requires_human": d["requires_human"],
        "actions": d.get("actions") or [],
    }
    return d


class EmailPipeline:
    """Orchestrates specialized agents for the email desk selling point."""

    def __init__(self, store: EmailStore, engine: Any | None = None) -> None:
        self.store = store
        self.engine = engine
        self.store.ensure_schema()

    def ingest(
        self,
        *,
        subject: str,
        body_text: str,
        sender_email: str,
        sender_name: str = "",
        recipient_email: str = "parts@dealership.local",
        message_id: str | None = None,
        thread_id: str | None = None,
        received_at: str | None = None,
        process: bool = True,
    ) -> dict[str, Any]:
        now = _utcnow()
        mid = message_id or f"msg-{uuid.uuid4().hex[:16]}"
        existing = self.store.fetchone("SELECT id FROM emails WHERE message_id = ?", (mid,))
        if existing:
            eid = int(existing["id"])
            if process:
                return self.process_id(eid)
            return self.get(eid) or {"id": eid, "message_id": mid}

        self.store.execute(
            """
            INSERT INTO emails (
                message_id, thread_id, subject, sender_email, sender_name, recipient_email,
                body_text, received_at, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'received', ?, ?)
            """,
            (
                mid,
                thread_id,
                subject or "",
                sender_email or "",
                sender_name or "",
                recipient_email or "parts@dealership.local",
                body_text or "",
                received_at or now,
                now,
                now,
            ),
        )
        self.store.commit()
        row = self.store.fetchone("SELECT id FROM emails WHERE message_id = ?", (mid,))
        eid = int(row["id"])  # type: ignore[index]
        if process:
            return self.process_id(eid)
        return self.get(eid) or {"id": eid}

    def process_id(self, email_id: int) -> dict[str, Any]:
        row = self.store.fetchone("SELECT * FROM emails WHERE id = ?", (email_id,))
        if row is None:
            raise KeyError(f"email {email_id} not found")
        d = dict(row)
        now = _utcnow()
        self.store.execute(
            "UPDATE emails SET status = 'processing', updated_at = ? WHERE id = ?",
            (now, email_id),
        )
        self.store.commit()

        agents: list[str] = ["classifier"]
        err: str | None = None
        try:
            clf = classify_email(
                subject=d.get("subject") or "",
                body=d.get("body_text") or "",
                sender_email=d.get("sender_email") or "",
            )
            clf_d = clf.to_dict()
            agents.append(clf.specialist)
            spec = run_specialist(
                clf.specialist,
                subject=d.get("subject") or "",
                body=d.get("body_text") or "",
                classification=clf_d,
                engine=self.engine,
            )
            tl = grade_email(
                classification=clf.classification,
                class_confidence=clf.confidence,
                priority=clf.priority,
                specialist_ok=spec.ok,
                parts_tl_color=spec.parts_traffic_light,
                parts_sim=spec.parts_similarity,
                parts_stock=spec.parts_stock,
                error=None if spec.ok else (spec.message or "specialist failed"),
            )
            status = "processed"
            if tl.color == "green" and tl.auto_send_allowed:
                status = "responded"  # auto-handled desk state
            elif tl.color == "red":
                status = "escalated"

            self.store.execute(
                """
                UPDATE emails SET
                    status = ?,
                    email_type = ?,
                    priority = ?,
                    department = ?,
                    classification_confidence = ?,
                    traffic_light = ?,
                    traffic_confidence = ?,
                    traffic_reason = ?,
                    requires_human = ?,
                    specialist = ?,
                    suggested_response = ?,
                    extracted_json = ?,
                    hits_json = ?,
                    actions_json = ?,
                    agents_invoked_json = ?,
                    ai_processed = 1,
                    response_sent = ?,
                    error_message = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    clf.classification,
                    clf.priority,
                    clf.department,
                    clf.confidence,
                    tl.color,
                    tl.confidence,
                    tl.reason,
                    1 if tl.requires_human else 0,
                    spec.specialist,
                    spec.suggested_response or "",
                    json.dumps(clf.extracted_info or {}),
                    json.dumps(spec.hits or []),
                    json.dumps(tl.actions or []),
                    json.dumps(agents),
                    1 if (tl.color == "green" and tl.auto_send_allowed) else 0,
                    now,
                    email_id,
                ),
            )
            self.store.commit()
        except Exception as exc:  # noqa: BLE001 — desk must never lose the message
            err = str(exc)
            tl = grade_email(
                classification="unknown",
                class_confidence=0.1,
                priority="high",
                specialist_ok=False,
                error=err,
            )
            self.store.execute(
                """
                UPDATE emails SET
                    status = 'error',
                    traffic_light = ?,
                    traffic_confidence = ?,
                    traffic_reason = ?,
                    requires_human = 1,
                    error_message = ?,
                    agents_invoked_json = ?,
                    ai_processed = 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    tl.color,
                    tl.confidence,
                    tl.reason,
                    err,
                    json.dumps(agents + ["error"]),
                    now,
                    email_id,
                ),
            )
            self.store.commit()

        out = self.get(email_id) or {}
        out["pipeline_error"] = err
        return out

    def process_pending(self, limit: int = 50) -> dict[str, Any]:
        rows = self.store.fetchall(
            """
            SELECT id FROM emails
            WHERE status IN ('received', 'error') OR ai_processed = 0
            ORDER BY id ASC
            LIMIT ?
            """,
            (int(limit),),
        )
        results = []
        for r in rows:
            results.append(self.process_id(int(r["id"])))
        return {"processed": len(results), "results": results}

    def get(self, email_id: int) -> dict[str, Any] | None:
        row = self.store.fetchone("SELECT * FROM emails WHERE id = ?", (email_id,))
        return _row_to_dict(row) if row else None

    def list_emails(
        self,
        *,
        status: str | None = None,
        traffic_light: str | None = None,
        email_type: str | None = None,
        requires_human: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if traffic_light:
            clauses.append("traffic_light = ?")
            params.append(traffic_light)
        if email_type:
            clauses.append("email_type = ?")
            params.append(email_type)
        if requires_human is not None:
            clauses.append("requires_human = ?")
            params.append(1 if requires_human else 0)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.extend([int(limit), int(offset)])
        rows = self.store.fetchall(
            f"""
            SELECT * FROM emails
            {where}
            ORDER BY
              CASE traffic_light WHEN 'red' THEN 0 WHEN 'yellow' THEN 1 WHEN 'green' THEN 2 ELSE 3 END,
              received_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )
        return [_row_to_dict(r) for r in rows]

    def search(self, q: str, limit: int = 50) -> list[dict[str, Any]]:
        q = (q or "").strip()
        if not q:
            return self.list_emails(limit=limit)
        # FTS5 — quote tokens lightly
        safe = " ".join(t for t in q.split() if t)
        try:
            rows = self.store.fetchall(
                """
                SELECT e.* FROM emails e
                JOIN emails_fts f ON f.rowid = e.id
                WHERE emails_fts MATCH ?
                ORDER BY e.received_at DESC
                LIMIT ?
                """,
                (safe, int(limit)),
            )
        except Exception:
            like = f"%{q}%"
            rows = self.store.fetchall(
                """
                SELECT * FROM emails
                WHERE subject LIKE ? OR body_text LIKE ? OR sender_email LIKE ?
                   OR suggested_response LIKE ?
                ORDER BY received_at DESC
                LIMIT ?
                """,
                (like, like, like, like, int(limit)),
            )
        return [_row_to_dict(r) for r in rows]
