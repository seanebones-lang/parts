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
            draft = spec.suggested_response or ""
            polished_flag = 0
            # Optional LLM polish (no-op without keys)
            try:
                from parrts.email.polish import polish_response

                polished = polish_response(
                    subject=d.get("subject") or "",
                    inbound_body=d.get("body_text") or "",
                    draft=draft,
                    classification=clf.classification,
                    traffic_light=tl.color,
                )
                if polished and polished.strip() and polished.strip() != draft.strip():
                    draft = polished
                    polished_flag = 1
                    agents.append("llm_polish")
            except Exception:
                pass

            status = "processed"
            if tl.color == "green" and tl.auto_send_allowed:
                status = "ready"  # auto-handled draft; SMTP may still be pending
            elif tl.color == "red":
                status = "escalated"
            elif tl.requires_human:
                status = "review"

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
                    polished = ?,
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
                    draft,
                    json.dumps(clf.extracted_info or {}),
                    json.dumps(spec.hits or []),
                    json.dumps(tl.actions or []),
                    json.dumps(agents),
                    polished_flag,
                    now,
                    email_id,
                ),
            )
            self.store.commit()

            # Optional auto-send greens when SMTP + EMAIL_AUTO_SEND
            try:
                from parrts.email.mail_io import MailboxConfig, send_smtp_reply

                mcfg = MailboxConfig.from_env()
                if (
                    mcfg.auto_send
                    and mcfg.smtp_configured()
                    and tl.color == "green"
                    and tl.auto_send_allowed
                    and draft
                ):
                    send_smtp_reply(
                        to_address=str(d.get("sender_email") or ""),
                        subject=str(d.get("subject") or ""),
                        body=draft,
                        cfg=mcfg,
                        in_reply_to=d.get("message_id"),
                    )
                    self.store.execute(
                        """
                        UPDATE emails SET
                            response_sent = 1,
                            response_sent_at = ?,
                            status = 'responded',
                            last_send_error = NULL,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now, now, email_id),
                    )
                    self.store.commit()
                    agents.append("smtp_auto_send")
                    self.store.execute(
                        "UPDATE emails SET agents_invoked_json = ?, updated_at = ? WHERE id = ?",
                        (json.dumps(agents), now, email_id),
                    )
                    self.store.commit()
            except Exception as send_exc:
                self.store.execute(
                    """
                    UPDATE emails SET last_send_error = ?, updated_at = ? WHERE id = ?
                    """,
                    (str(send_exc), now, email_id),
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
        # Automation ledger + missing-field alerts (workflow MIN bar)
        try:
            from parrts.automation.service import AutomationService

            root = getattr(self.store, "root", None)
            if root is not None:
                AutomationService(root).record_email_processed(out)
        except Exception:
            pass
        return out

    def update_draft(self, email_id: int, suggested_response: str) -> dict[str, Any]:
        now = _utcnow()
        self.store.execute(
            """
            UPDATE emails SET suggested_response = ?, updated_at = ? WHERE id = ?
            """,
            (suggested_response, now, email_id),
        )
        self.store.commit()
        row = self.get(email_id)
        if not row:
            raise KeyError(f"email {email_id} not found")
        return row

    def override_grade(
        self,
        email_id: int,
        *,
        color: str,
        requires_human: bool | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        color = (color or "").lower().strip()
        if color not in ("green", "yellow", "red"):
            raise ValueError("color must be green|yellow|red")
        now = _utcnow()
        rh = requires_human
        if rh is None:
            rh = color != "green"
        status = "ready" if color == "green" and not rh else ("escalated" if color == "red" else "review")
        self.store.execute(
            """
            UPDATE emails SET
                traffic_light = ?,
                traffic_reason = COALESCE(?, traffic_reason),
                requires_human = ?,
                status = ?,
                human_notes = COALESCE(?, human_notes),
                updated_at = ?
            WHERE id = ?
            """,
            (
                color,
                f"Human override → {color}",
                1 if rh else 0,
                status,
                notes,
                now,
                email_id,
            ),
        )
        self.store.commit()
        row = self.get(email_id)
        if not row:
            raise KeyError(f"email {email_id} not found")
        return row

    def mark_sent(self, email_id: int, *, via: str = "manual") -> dict[str, Any]:
        now = _utcnow()
        self.store.execute(
            """
            UPDATE emails SET
                response_sent = 1,
                response_sent_at = ?,
                status = 'responded',
                last_send_error = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, email_id),
        )
        self.store.commit()
        row = self.get(email_id)
        if not row:
            raise KeyError(f"email {email_id} not found")
        row["sent_via"] = via
        return row

    def send_reply(
        self,
        email_id: int,
        *,
        body: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """SMTP send (requires credentials). Blocks red unless force=True."""
        from parrts.email.mail_io import MailboxConfig, send_smtp_reply

        row = self.get(email_id)
        if not row:
            raise KeyError(f"email {email_id} not found")
        tl = row.get("traffic_light")
        color = tl.get("color") if isinstance(tl, dict) else tl
        if color == "red" and not force:
            raise ValueError("refusing to send red/urgent without force=true")
        draft = body if body is not None else (row.get("suggested_response") or "")
        if not draft.strip():
            raise ValueError("empty suggested_response")
        cfg = MailboxConfig.from_env()
        try:
            result = send_smtp_reply(
                to_address=str(row.get("sender_email") or ""),
                subject=str(row.get("subject") or ""),
                body=draft,
                cfg=cfg,
                in_reply_to=row.get("message_id"),
            )
            if body is not None:
                self.update_draft(email_id, draft)
            sent = self.mark_sent(email_id, via="smtp")
            sent["smtp"] = result
            return sent
        except Exception as exc:
            now = _utcnow()
            self.store.execute(
                "UPDATE emails SET last_send_error = ?, updated_at = ? WHERE id = ?",
                (str(exc), now, email_id),
            )
            self.store.commit()
            raise

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
