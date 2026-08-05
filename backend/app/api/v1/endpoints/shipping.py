"""
Shipping API — EasyPost key-gated rates + labels.

No fake labels. Soft-loaded via api_router. Does not require Postgres for config/rates/label.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import require_user_if_production
from app.models.user import User

router = APIRouter()


class AddressIn(BaseModel):
    name: str = ""
    street1: str
    street2: str = ""
    city: str
    state: str
    zip: str
    country: str = "US"
    phone: str = ""


class ParcelIn(BaseModel):
    weight: float = Field(16.0, description="Weight in ounces")
    length: float | None = None
    width: float | None = None
    height: float | None = None


class RatesRequest(BaseModel):
    from_address: AddressIn
    to_address: AddressIn
    parcel: ParcelIn | None = None
    order_id: str | int | None = None


class LabelRequest(BaseModel):
    shipment_id: str
    rate_id: str
    order_id: str | int | None = None


def _addr(a: AddressIn) -> dict[str, str]:
    d = {
        "name": a.name or "Parts",
        "street1": a.street1,
        "city": a.city,
        "state": a.state,
        "zip": a.zip,
        "country": a.country or "US",
    }
    if a.street2:
        d["street2"] = a.street2
    if a.phone:
        d["phone"] = a.phone
    return d


@router.get("/config")
async def shipping_config() -> dict[str, Any]:
    from parrts.commerce import shipping_status

    return shipping_status()


@router.post("/rates")
async def shipping_rates(
    body: RatesRequest,
    current_user: Optional[User] = Depends(require_user_if_production),
) -> dict[str, Any]:
    """Rate shop via EasyPost. 503 if key missing. Records DMS shipment ledger when order_id int."""
    _ = current_user
    from parrts.commerce import get_shipping_rates

    parcel: dict[str, Any] = {"weight": (body.parcel.weight if body.parcel else 16.0)}
    if body.parcel:
        for k in ("length", "width", "height"):
            v = getattr(body.parcel, k, None)
            if v is not None:
                parcel[k] = v

    result = get_shipping_rates(
        from_address=_addr(body.from_address),
        to_address=_addr(body.to_address),
        parcel=parcel,
    )
    if not result.get("success"):
        code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if not result.get("configured", True)
            else status.HTTP_400_BAD_REQUEST
        )
        _maybe_record_shipment(
            body.order_id,
            status="rates_failed",
            configured=bool(result.get("configured")),
            message=str(result.get("error") or "rates failed")[:500],
            external_id="",
        )
        raise HTTPException(status_code=code, detail=result.get("error") or "rates failed")
    if body.order_id is not None:
        result["order_id"] = body.order_id
    _maybe_record_shipment(
        body.order_id,
        status="rates",
        configured=True,
        external_id=str(result.get("shipment_id") or ""),
        message=f"rates={result.get('total_options') or len(result.get('rates') or [])}",
    )
    return result


@router.post("/label")
async def shipping_label(
    body: LabelRequest,
    current_user: Optional[User] = Depends(require_user_if_production),
) -> dict[str, Any]:
    """Buy EasyPost label for shipment+rate. Fail closed without key. Ledger on success/fail."""
    _ = current_user
    from parrts.commerce import buy_shipping_label

    result = buy_shipping_label(shipment_id=body.shipment_id, rate_id=body.rate_id)
    if not result.get("success"):
        code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if not result.get("configured", True)
            else status.HTTP_400_BAD_REQUEST
        )
        _maybe_record_shipment(
            body.order_id,
            status="label_failed",
            configured=bool(result.get("configured")),
            external_id=str(body.shipment_id or ""),
            message=str(result.get("error") or "label failed")[:500],
        )
        raise HTTPException(status_code=code, detail=result.get("error") or "label failed")
    if body.order_id is not None:
        result["order_id"] = body.order_id
    rate_val = 0.0
    try:
        rate_val = float(result.get("rate") or 0)
    except (TypeError, ValueError):
        rate_val = 0.0
    _maybe_record_shipment(
        body.order_id,
        status="labeled",
        configured=True,
        external_id=str(result.get("shipment_id") or body.shipment_id or ""),
        tracking_code=str(result.get("tracking_code") or ""),
        label_url=str(result.get("label_url") or ""),
        carrier=str(result.get("carrier") or ""),
        service=str(result.get("service") or ""),
        rate=rate_val,
    )
    return result


def _maybe_record_shipment(
    order_id: str | int | None,
    *,
    status: str,
    configured: bool = False,
    external_id: str = "",
    tracking_code: str = "",
    label_url: str = "",
    carrier: str = "",
    service: str = "",
    rate: float = 0.0,
    message: str = "",
) -> None:
    if order_id is None:
        return
    try:
        oid = int(order_id)
    except (TypeError, ValueError):
        return
    try:
        from app.api.v1.endpoints.dms import get_dms_service

        svc = get_dms_service()
        svc.record_shipment_event(
            order_id=oid,
            status=status,
            configured=configured,
            external_id=external_id,
            tracking_code=tracking_code,
            label_url=label_url,
            carrier=carrier,
            service=service,
            rate=rate,
            message=message,
            actor="shipping.api",
        )
    except Exception:  # noqa: BLE001 — ledger secondary
        pass
