"""High-level email desk service (offline SQLite + specialist pipeline)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from parrts.email.pipeline import EmailPipeline
from parrts.email.seed_data import DEMO_EMAILS
from parrts.email.store import EmailStore


class EmailService:
    """Product email desk: ingest, auto-answer, traffic-light, searchable store."""

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
        by_status = self.store.fetchall(
            "SELECT status, COUNT(*) AS c FROM emails GROUP BY status"
        )
        human = self.store.fetchone(
            "SELECT COUNT(*) AS c FROM emails WHERE requires_human = 1"
        )
        return {
            "ok": True,
            "db_path": str(self.store.db_path),
            "total": int(total["c"]) if total else 0,
            "requires_human": int(human["c"]) if human else 0,
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
            "selling_point": "inbound parts email auto-answer + green/yellow/red desk",
        }

    def seed_demo(self, *, process: bool = True, clear: bool = False) -> dict[str, Any]:
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
        for item in DEMO_EMAILS:
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
        return {"ok": True, "seeded": created, "emails": results, "status": st}

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
