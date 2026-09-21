"""High-level email desk service (offline SQLite + specialist pipeline + mailbox)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from parrts.email.mail_io import MailboxConfig, fetch_imap_messages, mailbox_status
from parrts.email.pipeline import EmailPipeline
from parrts.email.polish import llm_polish_available
from parrts.email.store import EmailStore


class EmailService:
    """Product email desk: ingest, auto-answer, traffic-light, searchable store, IMAP/SMTP."""

    def __init__(self, root: Path | str, engine: Any | None = None) -> None:
        self.root = Path(root).resolve()
        self.store = EmailStore(self.root)
        self.store.ensure_schema()
        self._engine = engine
        self._pipeline: EmailPipeline | None = None

    def _get_engine(self) -> Any | None:
        if self._engine is not None:
            return self._engine
        try:
            from parrts.embeddings import HashingEmbedder
            from parrts.engine import PartsRAGEngine

            eng = PartsRAGEngine(root=self.root, embedder=HashingEmbedder())
            try:
                eng.ensure_ready()
            except Exception:
                pass
            self._engine = eng
            return eng
        except Exception:
            return None

    @property
    def pipeline(self) -> EmailPipeline:
        if self._pipeline is None:
            self._pipeline = EmailPipeline(self.store, engine=self._get_engine())
        return self._pipeline

    def ensure_schema(self) -> None:
        self.store.ensure_schema()

    def status(self) -> dict[str, Any]:
        self.ensure_schema()
        total = self.store.fetchone("SELECT COUNT(*) AS c FROM emails")
        by_color = self.store.fetchall(
            """
            SELECT COALESCE(traffic_light, 'none') AS color, COUNT(*) AS c
            FROM emails GROUP BY COALESCE(traffic_light, 'none')
            """
        )
        by_status = self.store.fetchall("SELECT status, COUNT(*) AS c FROM emails GROUP BY status")
        human = self.store.fetchone("SELECT COUNT(*) AS c FROM emails WHERE requires_human = 1")
        sent = self.store.fetchone("SELECT COUNT(*) AS c FROM emails WHERE response_sent = 1")
        mb = mailbox_status()
        return {
            "ok": True,
            "db_path": str(self.store.db_path),
            "total": int(total["c"]) if total else 0,
            "requires_human": int(human["c"]) if human else 0,
            "response_sent": int(sent["c"]) if sent else 0,
            "by_traffic_light": {r["color"]: int(r["c"]) for r in by_color},
            "by_status": {r["status"]: int(r["c"]) for r in by_status},
            "specialists": [
                "parts_quote",
                "parts_order",
                "inventory",
                "shipping",
                "payment",
                "complaint",
                "customer_service",
                "general",
            ],
            "mailbox": {
                "imap_configured": mb.get("imap_configured"),
                "smtp_configured": mb.get("smtp_configured"),
                "auto_send": mb.get("auto_send"),
                "imap_host": mb.get("imap_host"),
                "smtp_host": mb.get("smtp_host"),
            },
            "llm_polish_available": llm_polish_available(),
            "production_ready": True,
            "selling_point": "inbound parts email auto-answer + green/yellow/red desk",
        }

    def seed_demo(
        self,
        *,
        process: bool = True,
        clear: bool = False,
        vertical: str | None = None,
    ) -> dict[str, Any]:
        from parrts.email.seed_data import demo_emails_for_vertical

        self.ensure_schema()
        if clear:
            self.store.execute("DELETE FROM emails")
            try:
                self.store.execute("DELETE FROM emails_fts")
            except Exception:
                pass
            self.store.commit()

        created = 0
        results = []
        seed_rows = demo_emails_for_vertical(vertical)
        for item in seed_rows:
            row = self.pipeline.ingest(
                subject=item["subject"],
                body_text=item["body"],
                sender_email=item["sender_email"],
                sender_name=item.get("sender_name", ""),
                message_id=item.get("message_id"),
                process=process,
            )
            created += 1
            results.append(
                {
                    "id": row.get("id"),
                    "subject": row.get("subject"),
                    "traffic_light": (row.get("traffic_light") or {}).get("color")
                    if isinstance(row.get("traffic_light"), dict)
                    else row.get("traffic_light"),
                    "email_type": row.get("email_type"),
                    "specialist": row.get("specialist"),
                }
            )
        st = self.status()
        return {
            "ok": True,
            "seeded": created,
            "vertical": (vertical or "default").strip().lower() or "default",
            "emails": results,
            "status": st,
        }

    def ingest(self, **kwargs: Any) -> dict[str, Any]:
        return self.pipeline.ingest(**kwargs)

    def process(self, email_id: int | None = None, limit: int = 50) -> dict[str, Any]:
        if email_id is not None:
            return {"processed": 1, "results": [self.pipeline.process_id(int(email_id))]}
        return self.pipeline.process_pending(limit=limit)

    def list(
        self,
        *,
        status: str | None = None,
        traffic_light: str | None = None,
        email_type: str | None = None,
        requires_human: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return self.pipeline.list_emails(
            status=status,
            traffic_light=traffic_light,
            email_type=email_type,
            requires_human=requires_human,
            limit=limit,
            offset=offset,
        )

    def search(self, q: str, limit: int = 50) -> list[dict[str, Any]]:
        return self.pipeline.search(q, limit=limit)

    def get(self, email_id: int) -> dict[str, Any] | None:
        return self.pipeline.get(email_id)

    def fetch_imap(self, *, limit: int = 20, process: bool = True, unseen_only: bool = True) -> dict[str, Any]:
        """Pull from IMAP when credentials set; ingest + process each message."""
        msgs = fetch_imap_messages(limit=limit, unseen_only=unseen_only)
        ingested = []
        for m in msgs:
            row = self.ingest(
                subject=m.get("subject") or "",
                body_text=m.get("body_text") or "",
                sender_email=m.get("sender_email") or "unknown@local",
                sender_name=m.get("sender_name") or "",
                message_id=m.get("message_id"),
                thread_id=m.get("thread_id"),
                received_at=m.get("received_at"),
                process=process,
            )
            ingested.append(
                {
                    "id": row.get("id"),
                    "message_id": row.get("message_id"),
                    "subject": row.get("subject"),
                    "traffic_light": (row.get("traffic_light") or {}).get("color")
                    if isinstance(row.get("traffic_light"), dict)
                    else row.get("traffic_light"),
                }
            )
        return {
            "ok": True,
            "fetched": len(msgs),
            "ingested": len(ingested),
            "emails": ingested,
            "mailbox": MailboxConfig.from_env().status(),
            "status": self.status(),
        }

    def approve_and_send(
        self,
        email_id: int,
        *,
        body: str | None = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if dry_run:
            if body is not None:
                self.pipeline.update_draft(email_id, body)
            row = self.pipeline.mark_sent(email_id, via="dry_run")
            row["smtp_skipped"] = True
            row["reason"] = "dry_run"
            return row
        if not MailboxConfig.from_env().smtp_configured():
            raise RuntimeError(
                "SMTP not configured — set EMAIL_USER + EMAIL_PASSWORD, or use dry_run=true"
            )
        return self.pipeline.send_reply(email_id, body=body, force=force)

    def override(
        self,
        email_id: int,
        *,
        color: str,
        requires_human: bool | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return self.pipeline.override_grade(
            email_id, color=color, requires_human=requires_human, notes=notes
        )

    def update_draft(self, email_id: int, suggested_response: str) -> dict[str, Any]:
        return self.pipeline.update_draft(email_id, suggested_response)

    def polish(self, email_id: int) -> dict[str, Any]:
        from parrts.email.polish import maybe_polish

        row = self.get(email_id)
        if not row:
            raise KeyError(f"email {email_id} not found")
        new_draft = maybe_polish(row)
        if new_draft != (row.get("suggested_response") or ""):
            row = self.pipeline.update_draft(email_id, new_draft)
            self.store.execute("UPDATE emails SET polished = 1 WHERE id = ?", (email_id,))
            self.store.commit()
            row = self.get(email_id) or row
            row["polished_now"] = True
        else:
            row["polished_now"] = False
            row["llm_polish_available"] = llm_polish_available()
        return row
