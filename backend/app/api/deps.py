"""
API dependencies — auth helpers aware of AUTH_MODE.

AUTH_MODE (settings / env):
  - demo (default): mutating routes may omit Bearer; optional JWT still accepted
  - production: mutating routes require a valid JWT (same rules as get_current_user)

Wire mutating handlers with::

    from app.api.deps import require_user_if_production
    from app.models.user import User
    from typing import Optional

    @router.post("/")
    async def create_thing(
        ...,
        current_user: Optional[User] = Depends(require_user_if_production),
    ):
        ...
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService

# auto_error=False so missing Authorization is not a hard 403 before our logic runs
optional_bearer = HTTPBearer(auto_error=False)


def _is_demo_mode() -> bool:
    mode = (getattr(settings, "AUTH_MODE", None) or "demo").strip().lower()
    return mode == "demo"


async def _resolve_user_from_credentials(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
    *,
    raise_on_invalid: bool,
) -> Optional[User]:
    """Validate Bearer token and load User. Optionally raise 401 on failure."""
    auth_service = AuthService(db)
    token = credentials.credentials
    payload = auth_service.verify_token(token)

    if payload is None:
        if raise_on_invalid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    user_id = payload.get("sub")
    if user_id is None:
        if raise_on_invalid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    user = await auth_service.get_user_by_id(int(user_id))
    if user is None:
        if raise_on_invalid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Always-optional JWT.

    Returns User when a valid Bearer token is present; None when missing or invalid.
    Does not enforce AUTH_MODE (use require_user_if_production on writes).
    """
    if credentials is None:
        return None
    return await _resolve_user_from_credentials(
        credentials, db, raise_on_invalid=False
    )


async def require_user_if_production(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
) -> Optional[User]:
    """
    Demo-aware gate for mutating routes.

    - AUTH_MODE=demo: no Bearer required (returns None). Does **not** open
      Postgres/get_db — critical for offline DMS + pilot demos.
    - AUTH_MODE=production: valid JWT required via get_db + AuthService.
    """
    if _is_demo_mode():
        # Offline-friendly: never touch Postgres in demo mode.
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Production only: open DB session for JWT → user resolve
    async for db in get_db():
        return await _resolve_user_from_credentials(
            credentials, db, raise_on_invalid=True
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database unavailable for auth",
    )
