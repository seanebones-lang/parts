"""
API dependencies — auth helpers aware of AUTH_MODE + Parts RBAC.

AUTH_MODE (settings / env):
  - demo (default): mutating routes may omit Bearer; optional JWT still accepted
  - production: mutating routes require a valid JWT (same rules as get_current_user)

RBAC:
  - production: role from JWT claims (role/parts_role) then User.role / is_superuser
  - demo: role from X-Parts-Role header or PARRTS_DEFAULT_ROLE (default admin)
  - login/refresh mint role + parts_role via AuthService.create_access_token_for_user

Wire mutating handlers with::

    from app.api.deps import require_user_if_production, require_permission

    @router.post("/")
    async def create_thing(
        ...,
        current_user: Optional[User] = Depends(require_permission("catalog.write")),
    ):
        ...
"""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, status
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

    # Attach JWT claims for role override if present
    try:
        user._jwt_claims = payload  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
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


def resolve_parts_role(
    user: Optional[User] = None,
    *,
    x_parts_role: Optional[str] = None,
    claims: dict | None = None,
) -> str:
    """Resolve counter|manager|admin for the current request."""
    from parrts.rbac import role_from_claims, role_from_user

    if user is not None:
        jwt_claims = getattr(user, "_jwt_claims", None) or claims
        if isinstance(jwt_claims, dict) and (
            jwt_claims.get("role") or jwt_claims.get("parts_role")
        ):
            return role_from_claims(jwt_claims)
        return role_from_user(user)
    if x_parts_role:
        return role_from_claims({"role": x_parts_role})
    return role_from_user(None)


def require_permission(permission: str) -> Callable:
    """
    FastAPI dependency factory: auth gate + RBAC permission check.

    Demo: uses X-Parts-Role or PARRTS_DEFAULT_ROLE (default admin — open desk).
    Production: JWT user required; role from user.role / JWT claim.
    """

    async def _dep(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
        x_parts_role: Optional[str] = Header(None, alias="X-Parts-Role"),
    ) -> Optional[User]:
        from parrts.rbac import can, normalize_role

        user = await require_user_if_production(credentials=credentials)
        role = resolve_parts_role(user, x_parts_role=x_parts_role)
        if not can(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: role {normalize_role(role)!r} cannot {permission}",
            )
        return user

    # annotate for OpenAPI / tests
    _dep._parts_permission = permission  # type: ignore[attr-defined]
    return _dep
