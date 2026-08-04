"""
DMS API — backed by ``parrts.dms.DmsService``.

Default: SQLite under ``.parrts/dms.db``.
Postgres: set ``DMS_BACKEND=postgres`` + ``DMS_DATABASE_URL`` (or POSTGRES_*).
Run ``parrts dms migrate`` once for Alembic head on empty Postgres.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import require_permission, require_user_if_production
from app.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Root / service helpers
# ---------------------------------------------------------------------------


def resolve_monorepo_root() -> Path:
    """
    Resolve repo root that owns ``.parrts/`` (or ``src/parrts``).

    Order:
      1. ``PARRTS_ROOT`` / ``DMS_ROOT`` env
      2. Walk parents of this file
      3. cwd and its parents
    """
    for env_key in ("PARRTS_ROOT", "DMS_ROOT"):
        raw = (os.environ.get(env_key) or "").strip()
        if raw:
            p = Path(raw).expanduser().resolve()
            if p.is_dir():
                return p

    here = Path(__file__).resolve()
    candidates = list(here.parents) + [Path.cwd().resolve(), *Path.cwd().resolve().parents]
    for p in candidates:
        if (p / ".parrts").exists() or (p / "src" / "parrts").is_dir():
            return p
    # backend/app/api/v1/endpoints/dms.py → parents[5] = monorepo root
    return here.parents[5]


def get_dms_service():
    """Lazy import + construct DmsService for the monorepo root."""
    try:
        from parrts.dms import DmsService
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"parrts.dms unavailable: {exc}",
        ) from exc
    return DmsService(root=resolve_monorepo_root())


def _http_exc_from_value_error(exc: ValueError) -> HTTPException:
    from parrts.dms.service import InsufficientStockError

    if isinstance(exc, InsufficientStockError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _list_catalog(svc: Any, q: Optional[str] = None) -> list[dict[str, Any]]:
    """Catalog listing — uses service method when present, else store SQL."""
    if hasattr(svc, "list_catalog") and callable(getattr(svc, "list_catalog")):
        try:
            return list(svc.list_catalog(q=q) if q is not None else svc.list_catalog())
        except TypeError:
            return list(svc.list_catalog(q))  # type: ignore[misc]

    svc.ensure_schema()
    cols = (
        "sku, name, description, make, model, year, category, "
        "oem_brand, list_price, msrp, source"
    )
    if q and str(q).strip():
        like = f"%{str(q).strip()}%"
        rows = svc.store.fetchall(
            f"""
            SELECT {cols}
            FROM catalog_parts
            WHERE sku LIKE ? OR name LIKE ? OR description LIKE ?
               OR make LIKE ? OR model LIKE ? OR category LIKE ?
               OR oem_brand LIKE ?
            ORDER BY sku
            """,
            (like, like, like, like, like, like, like),
        )
    else:
        rows = svc.store.fetchall(f"SELECT {cols} FROM catalog_parts ORDER BY sku")
    return [dict(r) for r in rows]


def _build_oem_feed(source: str, path: Optional[str], url: Optional[str]):
    from parrts.dms.oem import FileOemFeed, HttpOemFeed, SyntheticOemFeed

    src = (source or "synthetic").strip().lower()
    if src == "synthetic":
        return SyntheticOemFeed(), "synthetic"
    if src == "file":
        if not path:
            # Default sample under monorepo if present
            root = resolve_monorepo_root()
            default = root / "data" / "oem" / "sample_oem_catalog.json"
            if default.is_file():
                path = str(default)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source=file requires body.path (or data/oem/sample_oem_catalog.json)",
                )
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = (resolve_monorepo_root() / p).resolve()
        return FileOemFeed(p), "file"
    if src == "http":
        feed_url = (url or os.environ.get("OEM_FEED_URL") or "").strip()
        if not feed_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source=http requires body.url or OEM_FEED_URL env",
            )
        token = (os.environ.get("OEM_FEED_TOKEN") or "").strip() or None
        return HttpOemFeed(feed_url, token=token), "http"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown OEM source '{source}' (use synthetic|file|http)",
    )


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class SeedBody(BaseModel):
    seed: int = 42
    n_skus: int = Field(default=40, ge=1, le=500)
    locations: int = Field(default=7, ge=1, le=20)


class OemSyncBody(BaseModel):
    source: Literal["synthetic", "file", "http"] = "synthetic"
    path: Optional[str] = None
    url: Optional[str] = None


class CustomerCreateBody(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    company: str = ""


class OrderLineBody(BaseModel):
    sku: str
    qty: int = Field(ge=1)
    location_id: Optional[int] = None
    location: Optional[str] = None
    unit_price: Optional[float] = None


class OrderCreateBody(BaseModel):
    customer_id: int
    lines: list[OrderLineBody] = Field(min_length=1)
    notes: str = ""


class ReindexBody(BaseModel):
    force: bool = True


class CatalogUpsertBody(BaseModel):
    sku: str
    name: str
    description: str = ""
    make: str = ""
    model: str = ""
    year: str = ""
    category: str = ""
    oem_brand: str = ""
    list_price: float = 0.0
    msrp: float = 0.0
    source: str = "manual"
    location_qty: Optional[dict[str, int]] = None


class CatalogCsvBody(BaseModel):
    csv_text: str
    source: str = "csv"


class OrderStatusBody(BaseModel):
    status: Literal["open", "picking", "invoiced", "completed", "cancelled"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status")
async def dms_status():
    """DMS SQLite status (catalog, inventory, customers, orders, last OEM sync)."""
    try:
        svc = get_dms_service()
        return {"success": True, **svc.status()}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS status failed: {exc}",
        ) from exc


@router.post("/seed")
async def dms_seed(
    body: Optional[SeedBody] = None,
    current_user: Optional[User] = Depends(require_permission("dms.seed")),
):
    """Seed synthetic OEM catalog + multi-location inventory."""
    _ = current_user
    body = body or SeedBody()
    try:
        svc = get_dms_service()
        result = svc.seed_demo(
            seed=body.seed,
            n_skus=body.n_skus,
            locations=body.locations,
        )
        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS seed failed: {exc}",
        ) from exc


@router.post("/oem/sync")
async def dms_oem_sync(
    body: OemSyncBody,
    current_user: Optional[User] = Depends(require_permission("dms.oem")),
):
    """
    Sync OEM catalog/inventory.

    Body: ``{source: synthetic|file|http, path?: str, url?: str}``
    """
    _ = current_user
    try:
        feed, source_name = _build_oem_feed(body.source, body.path, body.url)
        svc = get_dms_service()
        result = svc.sync_oem(feed, source=source_name)
        return {"success": True, **result}
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OEM sync failed: {exc}",
        ) from exc


@router.get("/inventory")
async def dms_inventory(
    location: Optional[str] = Query(None, description="Location code, name, or id"),
    user_key: Optional[str] = Query(None, description="ACL user key (optional)"),
    x_parts_user: Optional[str] = Header(None, alias="X-Parts-User"),
):
    """List inventory levels (optional location filter + user location ACL)."""
    try:
        svc = get_dms_service()
        acl_user = x_parts_user or user_key
        rows = svc.filter_inventory_for_user(acl_user, location=location)
        return {
            "success": True,
            "location": location,
            "inventory": rows,
            "count": len(rows),
            "acl_user": acl_user,
        }
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS inventory failed: {exc}",
        ) from exc


@router.get("/catalog")
async def dms_catalog(
    q: Optional[str] = Query(None, description="Search sku/name/make/model/…"),
):
    """List/search OEM catalog parts."""
    try:
        svc = get_dms_service()
        parts = _list_catalog(svc, q=q)
        return {
            "success": True,
            "q": q,
            "parts": parts,
            "count": len(parts),
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS catalog failed: {exc}",
        ) from exc


@router.post("/catalog")
async def dms_catalog_upsert(
    body: CatalogUpsertBody,
    current_user: Optional[User] = Depends(require_permission("catalog.write")),
):
    """Create or update a catalog SKU (optional location_qty)."""
    _ = current_user
    try:
        svc = get_dms_service()
        result = svc.upsert_catalog_part(
            sku=body.sku,
            name=body.name,
            description=body.description,
            make=body.make,
            model=body.model,
            year=body.year,
            category=body.category,
            oem_brand=body.oem_brand,
            list_price=body.list_price,
            msrp=body.msrp,
            source=body.source,
            location_qty=body.location_qty,
        )
        return {"success": True, **result}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Catalog upsert failed: {exc}",
        ) from exc


@router.post("/catalog/import-csv")
async def dms_catalog_import_csv(
    body: CatalogCsvBody,
    current_user: Optional[User] = Depends(require_permission("catalog.import")),
):
    """Bulk import catalog from CSV text (sku,name required)."""
    _ = current_user
    try:
        svc = get_dms_service()
        result = svc.import_catalog_csv(body.csv_text, source=body.source)
        return {"success": bool(result.get("ok")), **result}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV import failed: {exc}",
        ) from exc


@router.get("/customers")
async def dms_list_customers():
    """List DMS customers."""
    try:
        svc = get_dms_service()
        customers = svc.list_customers()
        return {"success": True, "customers": customers, "count": len(customers)}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS customers list failed: {exc}",
        ) from exc


@router.post("/customers")
async def dms_create_customer(
    body: CustomerCreateBody,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Create a DMS customer."""
    _ = current_user
    try:
        svc = get_dms_service()
        customer = svc.create_customer(
            name=body.name,
            email=body.email,
            phone=body.phone,
            company=body.company,
        )
        return {"success": True, "customer": customer}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS create customer failed: {exc}",
        ) from exc


@router.get("/orders")
async def dms_list_orders():
    """List DMS orders with lines."""
    try:
        svc = get_dms_service()
        orders = svc.list_orders()
        return {"success": True, "orders": orders, "count": len(orders)}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS orders list failed: {exc}",
        ) from exc


@router.get("/orders/{order_id}")
async def dms_get_order(order_id: int):
    try:
        svc = get_dms_service()
        order = svc.get_order(order_id)
        return {"success": True, "order": order}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS get order failed: {exc}",
        ) from exc


@router.patch("/orders/{order_id}/status")
async def dms_set_order_status(
    order_id: int,
    body: OrderStatusBody,
    current_user: Optional[User] = Depends(require_user_if_production),
    x_parts_role: Optional[str] = Header(None, alias="X-Parts-Role"),
):
    """Lifecycle: open→picking→invoiced→completed; cancel restores stock."""
    from app.api.deps import resolve_parts_role
    from parrts.rbac import can, normalize_role

    _ = current_user
    role = resolve_parts_role(current_user, x_parts_role=x_parts_role)
    perm = "orders.cancel" if body.status == "cancelled" else "orders.status"
    if not can(role, perm):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role {normalize_role(role)!r} cannot {perm}",
        )
    try:
        svc = get_dms_service()
        result = svc.set_order_status(order_id, body.status)
        return {"success": True, **result}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS status update failed: {exc}",
        ) from exc


@router.post("/orders/{order_id}/invoice")
async def dms_order_invoice(
    order_id: int,
    current_user: Optional[User] = Depends(require_permission("orders.invoice")),
):
    """Generate invoice PDF (advances to invoiced). Returns path metadata."""
    _ = current_user
    try:
        svc = get_dms_service()
        result = svc.write_invoice_pdf(order_id)
        return {"success": True, **result}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invoice failed: {exc}",
        ) from exc


@router.get("/orders/{order_id}/invoice.pdf")
async def dms_order_invoice_pdf(order_id: int):
    """Download invoice PDF (generates if missing)."""
    try:
        svc = get_dms_service()
        result = svc.write_invoice_pdf(order_id)
        path = Path(result["path"])
        if not path.is_file():
            raise HTTPException(status_code=500, detail="invoice file missing after write")
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=path.name,
        )
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invoice PDF failed: {exc}",
        ) from exc


@router.get("/rbac")
async def dms_rbac(
    role: Optional[str] = Query(None),
    x_parts_role: Optional[str] = Header(None, alias="X-Parts-Role"),
):
    """Describe role permissions (query role, X-Parts-Role, or default)."""
    from app.api.deps import resolve_parts_role
    from parrts.rbac import describe

    resolved = role or resolve_parts_role(None, x_parts_role=x_parts_role)
    return {"success": True, **describe(resolved)}


class OrgBody(BaseModel):
    code: str
    name: str = ""


class LocationOrgBody(BaseModel):
    org_code: str


class AclBody(BaseModel):
    location_codes: list[str] = Field(default_factory=list)


@router.get("/orgs")
async def dms_list_orgs():
    svc = get_dms_service()
    orgs = svc.list_orgs()
    return {"success": True, "orgs": orgs, "count": len(orgs)}


@router.post("/orgs")
async def dms_create_org(
    body: OrgBody,
    current_user: Optional[User] = Depends(require_permission("orgs.manage")),
):
    _ = current_user
    try:
        svc = get_dms_service()
        org = svc.ensure_org(body.code, body.name or None)
        return {"success": True, "org": org}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc


@router.get("/locations")
async def dms_list_locations():
    svc = get_dms_service()
    locs = svc.list_locations()
    return {"success": True, "locations": locs, "count": len(locs)}


@router.put("/locations/{location_code}/org")
async def dms_set_location_org(
    location_code: str,
    body: LocationOrgBody,
    current_user: Optional[User] = Depends(require_permission("orgs.manage")),
):
    _ = current_user
    try:
        svc = get_dms_service()
        result = svc.set_location_org(location_code, body.org_code)
        return {"success": True, **result}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc


@router.get("/acl/{user_key}")
async def dms_get_acl(user_key: str):
    svc = get_dms_service()
    allowed = svc.allowed_location_codes(user_key)
    return {
        "success": True,
        "user_key": user_key,
        "location_codes": allowed,
        "restricted": allowed is not None,
    }


@router.put("/acl/{user_key}")
async def dms_set_acl(
    user_key: str,
    body: AclBody,
    current_user: Optional[User] = Depends(require_permission("acl.manage")),
):
    _ = current_user
    try:
        svc = get_dms_service()
        result = svc.set_user_location_acl(user_key, body.location_codes)
        return {"success": True, **result}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc


@router.post("/orders")
async def dms_create_order(
    body: OrderCreateBody,
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Create order and reserve stock."""
    _ = current_user
    lines: list[dict[str, Any]] = []
    for ln in body.lines:
        d: dict[str, Any] = {"sku": ln.sku, "qty": ln.qty}
        if ln.location_id is not None:
            d["location_id"] = ln.location_id
        if ln.location is not None:
            d["location"] = ln.location
        if ln.unit_price is not None:
            d["unit_price"] = ln.unit_price
        lines.append(d)
    try:
        svc = get_dms_service()
        order = svc.create_order(
            customer_id=body.customer_id,
            lines=lines,
            notes=body.notes,
        )
        return {"success": True, "order": order}
    except ValueError as exc:
        raise _http_exc_from_value_error(exc) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS create order failed: {exc}",
        ) from exc


@router.post("/reindex")
async def dms_reindex(
    body: Optional[ReindexBody] = None,
    current_user: Optional[User] = Depends(require_permission("dms.reindex")),
):
    """Export DMS inventory to RAG inventory.json and rebuild index."""
    _ = current_user
    body = body or ReindexBody()
    try:
        svc = get_dms_service()
        if hasattr(svc, "reindex_rag"):
            result = svc.reindex_rag(force=body.force)
        else:
            export_path = svc.export_parrts_inventory()
            result = {
                "ok": True,
                "export_path": str(export_path),
                "note": "reindex_rag not available; exported inventory only",
            }
        return {"success": bool(result.get("ok", True)), **result}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DMS reindex failed: {exc}",
        ) from exc


