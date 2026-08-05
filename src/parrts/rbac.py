"""Lightweight RBAC for Parts operator roles.

Roles (ascending privilege): counter < manager < admin

Sources (first match wins for request resolution helpers):
  1. Authenticated user.role / is_superuser (JWT path)
  2. Request header X-Parts-Role (demo / tooling)
  3. PARRTS_DEFAULT_ROLE (default admin in open demo)
"""

from __future__ import annotations

import os
from typing import Any

ROLES = ("counter", "manager", "admin")
_RANK = {r: i for i, r in enumerate(ROLES)}

# App/JWT role names → Parts RBAC role
ROLE_ALIASES: dict[str, str] = {
    "counter": "counter",
    "user": "counter",
    "staff": "counter",
    "parts": "counter",
    "manager": "manager",
    "supervisor": "manager",
    "admin": "admin",
    "administrator": "admin",
    "superuser": "admin",
    "super_admin": "admin",
    "owner": "admin",
}

# permission -> minimum role
PERMISSIONS: dict[str, str] = {
    "catalog.read": "counter",
    "catalog.write": "manager",
    "catalog.import": "manager",
    "catalog.supersession": "manager",
    "orders.read": "counter",
    "orders.write": "counter",
    "orders.status": "counter",
    "orders.cancel": "manager",
    "orders.invoice": "counter",
    "customers.write": "counter",
    "dms.seed": "admin",
    "dms.reindex": "manager",
    "dms.oem": "manager",
    "orgs.manage": "admin",
    "acl.manage": "admin",
    "transfers.read": "counter",
    "transfers.write": "counter",
    "transfers.approve": "manager",
    "transfers.cancel": "manager",
    "inventory.read": "counter",
    "inventory.receive": "counter",
    "inventory.adjust": "manager",
    "analytics.read": "counter",
    "compliance.export": "manager",
    "payments.create": "counter",
    "payments.read": "counter",
    "shipping.create": "counter",
    "admin": "admin",
}


def map_app_role(role: str | None) -> str:
    """Map JWT/app role string onto counter|manager|admin."""
    r = (role or "").strip().lower()
    if r in ROLE_ALIASES:
        return ROLE_ALIASES[r]
    if r in _RANK:
        return r
    return (os.environ.get("PARRTS_DEFAULT_ROLE") or "admin").strip().lower()


def normalize_role(role: str | None) -> str:
    return map_app_role(role)


def role_from_user(user: Any | None) -> str:
    """Extract Parts role from a User-like object."""
    if user is None:
        return normalize_role(None)
    if bool(getattr(user, "is_superuser", False)):
        return "admin"
    return map_app_role(getattr(user, "role", None))


def role_from_claims(claims: dict[str, Any] | None) -> str:
    if not claims:
        return normalize_role(None)
    if claims.get("is_superuser") or claims.get("superuser"):
        return "admin"
    return map_app_role(
        claims.get("role") or claims.get("parts_role") or claims.get("partsRole")
    )


def role_at_least(role: str, minimum: str) -> bool:
    return _RANK.get(normalize_role(role), -1) >= _RANK.get(normalize_role(minimum), 99)


def can(role: str | None, permission: str) -> bool:
    need = PERMISSIONS.get(permission, "admin")
    return role_at_least(role or "", need)


def require(role: str | None, permission: str) -> None:
    if not can(role, permission):
        raise PermissionError(f"role {normalize_role(role)!r} cannot {permission}")


def describe(role: str | None = None) -> dict[str, Any]:
    r = normalize_role(role)
    allowed = [p for p in PERMISSIONS if can(r, p)]
    return {
        "role": r,
        "permissions": allowed,
        "roles": list(ROLES),
        "aliases": dict(ROLE_ALIASES),
    }
