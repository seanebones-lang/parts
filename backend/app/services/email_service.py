"""Email service facade — prefer parrts.email.EmailService (offline desk)."""

from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class EmailService:
    """
    Legacy SQLAlchemy-shaped facade.

    Product path is ``parrts.email.EmailService`` (SQLite desk). This class remains
    so older imports do not break; methods delegate when possible.
    """

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    def _core(self):
        import os
        from pathlib import Path

        from parrts.email import EmailService as Core

        root = Path(os.environ.get("PARRTS_ROOT") or Path.cwd()).resolve()
        return Core(root=root)

    async def get_emails(self, skip: int = 0, limit: int = 100) -> List[Any]:
        try:
            return self._core().list(limit=limit, offset=skip)
        except Exception:
            return []

    async def process_new_emails(self) -> int:
        try:
            out = self._core().process(limit=100)
            return int(out.get("processed") or 0)
        except Exception:
            return 0

    async def classify_email(self, email_id: int) -> Optional[str]:
        try:
            row = self._core().process(email_id=email_id)
            results = row.get("results") or []
            if results:
                return results[0].get("email_type")
        except Exception:
            return None
        return None
