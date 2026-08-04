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
    """Rate shop via EasyPost. 503 if key missing."""
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
        raise HTTPException(status_code=code, detail=result.get("error") or "rates failed")
    if body.order_id is not None:
        result["order_id"] = body.order_id
    return result


@router.post("/label")
async def shipping_label(
    body: LabelRequest,
    current_user: Optional[User] = Depends(require_user_if_production),
) -> dict[str, Any]:
    """Buy EasyPost label for shipment+rate. Fail closed without key."""
    _ = current_user
    from parrts.commerce import buy_shipping_label

    result = buy_shipping_label(shipment_id=body.shipment_id, rate_id=body.rate_id)
    if not result.get("success"):
        code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if not result.get("configured", True)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=result.get("error") or "label failed")
    if body.order_id is not None:
        result["order_id"] = body.order_id
    return result
