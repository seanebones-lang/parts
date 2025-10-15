"""
Email service for processing and managing emails.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.email import Email


class EmailService:
    """Email service for managing email operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_emails(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Email]:
        """Get emails with pagination."""
        # This will be implemented in Phase 2
        return []
    
    async def process_new_emails(self) -> int:
        """Process new emails from IMAP."""
        # This will be implemented in Phase 2
        return 0
    
    async def classify_email(self, email_id: int) -> Optional[str]:
        """Classify email using AI."""
        # This will be implemented in Phase 2
        return None
