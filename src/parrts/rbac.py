"""Lightweight RBAC for Parts operator roles.

Roles (ascending privilege): counter < manager < admin
Env:
  PARRTS_DEFAULT_ROLE=admin|manager|counter  (demo default: admin)
Request header (demo / API tools): X-Parts-Role
"""

from __future__ import annotations

import os

ROLES = ("counter", "manager", "admin")
_RANK = {r: i for i, r in enumerate(ROLES)}

# permission -> minimum role
PERMISSIONS: dict[str, str] = {
    "catalog.read": "counter",
    "catalog.write": "manager",
    "catalog.import": "manager",
    "orders.read": "counter",
    "orders.write": "counter",
    "orders.status": "counter",
    "orders.cancel": "manager",
    "orders.invoice": "counter",
    "customers.write": "counter",
    "dms.seed": "admin",
    "dms.reindex": "manager",
    "payments.create": "counter",
    "shipping.create": "counter",
    "admin": "admin",
}


def normalize_role(role: str | None) -> str:
    r = (role or "").strip().lower()
    if r in _RANK:
        return r
    return (os.environ.get("PARRTS_DEFAULT_ROLE") or "admin").strip().lower()


def role_at_least(role: str, minimum: str) -> bool:
    return _RANK.get(normalize_role(role), -1) >= _RANK.get(normalize_role(minimum), 99)


def can(role: str | None, permission: str) -> bool:
    need = PERMISSIONS.get(permission, "admin")
    return role_at_least(role or "", need)


def require(role: str | None, permission: str) -> None:
    if not can(role, permission):
        raise PermissionError(f"role {normalize_role(role)!r} cannot {permission}")


def describe(role: str | None = None) -> dict:
    r = normalize_role(role)
    allowed = [p for p in PERMISSIONS if can(r, p)]
    return {"role": r, "permissions": allowed, "roles": list(ROLES)}
