"""Inventory operations + quotes/orders lifecycle for JP / DMS pilot.

Event-based mutations. On hand vs reserved. SQLite-safe concurrency via
BEGIN IMMEDIATE. Does not touch transmission resolver semantics.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from parrts.dms.service import DmsService, InsufficientStockError


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class OpsConflictError(ValueError):
    """Availability / state conflict (HTTP 409)."""


class OpsValidationError(ValueError):
    """Operator-facing validation error (HTTP 400)."""


ADJUST_REASONS = {
    "physical_count",
    "damaged",
    "scrapped",
    "found",
    "data_correction",
    "other",
    "receive",  # alias path
}

EVENT_RECEIVE = "RECEIVE"
EVENT_ADJUST = "ADJUST"
EVENT_TRANSFER_OUT = "TRANSFER_OUT"
EVENT_TRANSFER_IN = "TRANSFER_IN"
EVENT_RESERVE = "RESERVE"
EVENT_RELEASE = "RELEASE"
EVENT_SALE = "SALE"
EVENT_RETURN = "RETURN"

QUOTE_DRAFT = "draft"
QUOTE_OPEN = "open"
QUOTE_RESERVED = "reserved"
QUOTE_CONVERTED = "converted"
QUOTE_CANCELLED = "cancelled"

ORDER_OPEN = "open"
ORDER_COMPLETED = "completed"
ORDER_CANCELLED = "cancelled"

RES_ACTIVE = "active"
RES_RELEASED = "released"
RES_CONSUMED = "consumed"


class InventoryOps:
    """Business operations on a DmsService (SQLite pilot path)."""

    def __init__(self, dms: DmsService) -> None:
        self.dms = dms
        self.store = dms.store

    # ----- helpers ---------------------------------------------------------

    def ensure(self) -> None:
        self.dms.ensure_schema()

    def _begin(self) -> None:
        self.store.execute("BEGIN IMMEDIATE")

    def _commit(self) -> None:
        self.store.commit()

    def _rollback(self) -> None:
        try:
            self.store.execute("ROLLBACK")
        except Exception:
            pass

    def _loc(self, location: str | int) -> int:
        return self.dms._location_id(location)

    def _loc_code(self, lid: int) -> str:
        row = self.store.fetchone("SELECT code FROM locations WHERE id = ?", (lid,))
        return str(row["code"]) if row else str(lid)

    def _require_sku(self, sku: str) -> dict[str, Any]:
        sku_s = str(sku or "").strip()
        if not sku_s:
            raise OpsValidationError("SKU is required")
        row = self.store.fetchone(
            "SELECT sku, name, description, transmission_family, list_price FROM catalog_parts WHERE sku = ?",
            (sku_s,),
        )
        if row is None:
            raise OpsValidationError(f"Unknown SKU: {sku_s}")
        return dict(row)

    def _inv_row(self, sku: str, lid: int) -> tuple[int, int]:
        """Return (on_hand, reserved)."""
        row = self.store.fetchone(
            "SELECT qty, COALESCE(reserved_qty, 0) AS reserved_qty "
            "FROM inventory_levels WHERE sku = ? AND location_id = ?",
            (sku, lid),
        )
        if row is None:
            return 0, 0
        return int(row["qty"] or 0), int(row["reserved_qty"] or 0)

    def _set_inv(self, sku: str, lid: int, on_hand: int, reserved: int) -> None:
        if on_hand < 0 or reserved < 0:
            raise OpsValidationError("Inventory cannot be negative")
        if reserved > on_hand:
            raise OpsValidationError("Reserved cannot exceed on-hand")
        exists = self.store.fetchone(
            "SELECT 1 FROM inventory_levels WHERE sku = ? AND location_id = ?",
            (sku, lid),
        )
        if exists is None:
            self.store.execute(
                """
                INSERT INTO inventory_levels (sku, location_id, qty, cost, price, reserved_qty)
                VALUES (?, ?, ?, 0, 0, ?)
                """,
                (sku, lid, on_hand, reserved),
            )
        else:
            self.store.execute(
                "UPDATE inventory_levels SET qty = ?, reserved_qty = ? "
                "WHERE sku = ? AND location_id = ?",
                (on_hand, reserved, sku, lid),
            )

    def _idem_lookup(self, key: str | None) -> dict[str, Any] | None:
        """Return prior ops_idempotency_keys row for a request key, if any."""
        if not key:
            return None
        row = self.store.fetchone(
            "SELECT * FROM ops_idempotency_keys WHERE idempotency_key = ?",
            (str(key),),
        )
        return dict(row) if row is not None else None

    def _idem_put(
        self,
        *,
        key: str | None,
        action: str,
        entity_type: str,
        entity_id: int,
    ) -> None:
        if not key:
            return
        self.store.execute(
            """
            INSERT OR IGNORE INTO ops_idempotency_keys
              (idempotency_key, action, entity_type, entity_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(key), action, entity_type, int(entity_id), _utc_now()),
        )

    def _record_event(
        self,
        *,
        event_type: str,
        sku: str,
        location_id: int | None,
        on_hand_before: int,
        on_hand_after: int,
        reserved_before: int,
        reserved_after: int,
        reason: str = "",
        notes: str = "",
        actor: str = "",
        ref_type: str = "",
        ref_id: str = "",
        idempotency_key: str | None = None,
    ) -> int:
        key = idempotency_key
        if key:
            existing = self.store.fetchone(
                "SELECT id FROM inventory_events WHERE idempotency_key = ?",
                (key,),
            )
            if existing is not None:
                return int(existing["id"])
        cur = self.store.execute(
            """
            INSERT INTO inventory_events (
                event_type, sku, location_id,
                qty_on_hand_delta, qty_reserved_delta,
                on_hand_before, on_hand_after, reserved_before, reserved_after,
                reason, notes, actor, ref_type, ref_id, idempotency_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                sku,
                location_id,
                on_hand_after - on_hand_before,
                reserved_after - reserved_before,
                on_hand_before,
                on_hand_after,
                reserved_before,
                reserved_after,
                reason or "",
                notes or "",
                actor or "",
                ref_type or "",
                str(ref_id or ""),
                key,
                _utc_now(),
            ),
        )
        return int(getattr(cur, "lastrowid", 0) or 0)

    def _activity(self, kind: str, summary: str, detail: dict | None = None, requires_human: bool = False) -> None:
        try:
            from parrts.automation.service import AutomationService

            AutomationService(self.dms.root).record_run(
                kind=kind,
                status="ok",
                summary=summary,
                detail=detail or {},
                requires_human=requires_human,
            )
        except Exception:
            pass

    def stock_view(self, sku: str | None = None, location: str | int | None = None) -> list[dict[str, Any]]:
        self.ensure()
        clauses: list[str] = []
        params: list[Any] = []
        if sku:
            clauses.append("i.sku = ?")
            params.append(str(sku).strip())
        if location is not None and str(location).strip() != "":
            clauses.append("i.location_id = ?")
            params.append(self._loc(location))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.store.fetchall(
            f"""
            SELECT i.sku, i.location_id, l.code AS location_code, l.name AS location_name,
                   i.qty AS on_hand, COALESCE(i.reserved_qty, 0) AS reserved,
                   i.condition, i.bin, i.price,
                   c.name, c.description, c.transmission_family
            FROM inventory_levels i
            JOIN locations l ON l.id = i.location_id
            LEFT JOIN catalog_parts c ON c.sku = i.sku
            {where}
            ORDER BY i.sku, l.code
            """,
            tuple(params),
        )
        out = []
        for r in rows:
            d = dict(r)
            on_hand = int(d.get("on_hand") or 0)
            reserved = int(d.get("reserved") or 0)
            d["available"] = max(0, on_hand - reserved)
            out.append(d)
        return out

    # ----- receive / adjust / transfer ------------------------------------

    def receive(
        self,
        *,
        sku: str,
        location: str | int,
        qty: int,
        notes: str = "",
        reference: str = "",
        actor: str = "counter",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.ensure()
        cat = self._require_sku(sku)
        q = int(qty)
        if q <= 0:
            raise OpsValidationError("Receive quantity must be positive")
        lid = self._loc(location)
        key = idempotency_key or f"receive:{sku}:{lid}:{q}:{reference}:{uuid.uuid4().hex[:8]}"
        try:
            self._begin()
            if idempotency_key:
                ex = self.store.fetchone(
                    "SELECT id FROM inventory_events WHERE idempotency_key = ?",
                    (idempotency_key,),
                )
                if ex is not None:
                    self._commit()
                    return {"ok": True, "idempotent": True, "event_id": int(ex["id"])}
            oh_b, res_b = self._inv_row(cat["sku"], lid)
            oh_a, res_a = oh_b + q, res_b
            self._set_inv(cat["sku"], lid, oh_a, res_a)
            eid = self._record_event(
                event_type=EVENT_RECEIVE,
                sku=cat["sku"],
                location_id=lid,
                on_hand_before=oh_b,
                on_hand_after=oh_a,
                reserved_before=res_b,
                reserved_after=res_a,
                reason="receive",
                notes=notes or reference,
                actor=actor,
                ref_type="receive",
                ref_id=reference,
                idempotency_key=key if idempotency_key else None,
            )
            # also write stock_adjustments for legacy audit readers
            self.store.execute(
                """
                INSERT INTO stock_adjustments
                  (sku, location_id, delta, qty_before, qty_after, reason, notes, actor, created_at)
                VALUES (?, ?, ?, ?, ?, 'receive', ?, ?, ?)
                """,
                (cat["sku"], lid, q, oh_b, oh_a, notes or reference, actor, _utc_now()),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        code = self._loc_code(lid)
        self._activity(
            "inventory_receive",
            f"Inventory received · {cat['sku']} · +{q} · {code}",
            {"sku": cat["sku"], "qty": q, "location": code, "event_id": eid},
        )
        return {
            "ok": True,
            "sku": cat["sku"],
            "location_code": code,
            "on_hand": oh_a,
            "reserved": res_a,
            "available": oh_a - res_a,
            "event_id": eid,
        }

    def adjust(
        self,
        *,
        sku: str,
        location: str | int,
        delta: int | None = None,
        final_qty: int | None = None,
        reason: str,
        notes: str = "",
        actor: str = "counter",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.ensure()
        cat = self._require_sku(sku)
        reason_s = (reason or "").strip().lower().replace(" ", "_")
        if reason_s not in ADJUST_REASONS or reason_s == "receive":
            # map friendly labels
            aliases = {
                "physical_count_correction": "physical_count",
                "physical_count": "physical_count",
                "damaged": "damaged",
                "scrapped": "scrapped",
                "found_inventory": "found",
                "found": "found",
                "data_correction": "data_correction",
                "other": "other",
            }
            reason_s = aliases.get(reason_s, reason_s)
        if reason_s not in ADJUST_REASONS or reason_s == "receive":
            raise OpsValidationError(
                "Adjustment requires a reason: physical count correction, damaged, "
                "scrapped, found inventory, data correction, or other."
            )
        lid = self._loc(location)
        try:
            self._begin()
            if idempotency_key:
                ex = self.store.fetchone(
                    "SELECT id FROM inventory_events WHERE idempotency_key = ?",
                    (idempotency_key,),
                )
                if ex is not None:
                    self._commit()
                    return {"ok": True, "idempotent": True, "event_id": int(ex["id"])}
            oh_b, res_b = self._inv_row(cat["sku"], lid)
            if final_qty is not None:
                oh_a = int(final_qty)
                dlt = oh_a - oh_b
            else:
                if delta is None:
                    raise OpsValidationError("Provide a quantity change or final quantity")
                dlt = int(delta)
                oh_a = oh_b + dlt
            if dlt == 0:
                raise OpsValidationError("Adjustment quantity change cannot be zero")
            if oh_a < 0:
                raise OpsValidationError(
                    f"This adjustment would make inventory negative "
                    f"(on hand {oh_b}, change {dlt})."
                )
            if oh_a < res_b:
                raise OpsValidationError(
                    f"Cannot reduce on-hand below reserved quantity ({res_b}). "
                    "Release reservations first."
                )
            self._set_inv(cat["sku"], lid, oh_a, res_b)
            eid = self._record_event(
                event_type=EVENT_ADJUST,
                sku=cat["sku"],
                location_id=lid,
                on_hand_before=oh_b,
                on_hand_after=oh_a,
                reserved_before=res_b,
                reserved_after=res_b,
                reason=reason_s,
                notes=notes,
                actor=actor,
                idempotency_key=idempotency_key,
            )
            self.store.execute(
                """
                INSERT INTO stock_adjustments
                  (sku, location_id, delta, qty_before, qty_after, reason, notes, actor, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (cat["sku"], lid, dlt, oh_b, oh_a, reason_s, notes, actor, _utc_now()),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        code = self._loc_code(lid)
        sign = f"+{dlt}" if dlt > 0 else str(dlt)
        self._activity(
            "inventory_adjust",
            f"Stock adjusted · {cat['sku']} · {sign} · {code} · {reason_s.replace('_', ' ')}",
            {"sku": cat["sku"], "delta": dlt, "location": code, "reason": reason_s},
        )
        return {
            "ok": True,
            "sku": cat["sku"],
            "location_code": code,
            "delta": dlt,
            "on_hand": oh_a,
            "reserved": res_b,
            "available": oh_a - res_b,
            "event_id": eid,
        }

    def transfer(
        self,
        *,
        sku: str,
        from_location: str | int,
        to_location: str | int,
        qty: int,
        notes: str = "",
        actor: str = "counter",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.ensure()
        cat = self._require_sku(sku)
        q = int(qty)
        if q <= 0:
            raise OpsValidationError("Transfer quantity must be positive")
        from_lid = self._loc(from_location)
        to_lid = self._loc(to_location)
        if from_lid == to_lid:
            raise OpsValidationError("From and to locations must be different")
        try:
            self._begin()
            if idempotency_key:
                ex = self.store.fetchone(
                    "SELECT id FROM inventory_events WHERE idempotency_key = ?",
                    (idempotency_key,),
                )
                if ex is not None:
                    self._commit()
                    return {"ok": True, "idempotent": True, "event_id": int(ex["id"])}
            oh_f, res_f = self._inv_row(cat["sku"], from_lid)
            avail = oh_f - res_f
            if q > avail:
                raise OpsConflictError(
                    f"Only {avail} units are available to move from "
                    f"{self._loc_code(from_lid)}. You attempted to move {q}."
                )
            oh_t, res_t = self._inv_row(cat["sku"], to_lid)
            self._set_inv(cat["sku"], from_lid, oh_f - q, res_f)
            self._set_inv(cat["sku"], to_lid, oh_t + q, res_t)
            e_out = self._record_event(
                event_type=EVENT_TRANSFER_OUT,
                sku=cat["sku"],
                location_id=from_lid,
                on_hand_before=oh_f,
                on_hand_after=oh_f - q,
                reserved_before=res_f,
                reserved_after=res_f,
                notes=notes,
                actor=actor,
                ref_type="transfer",
                ref_id=str(to_lid),
                idempotency_key=idempotency_key,
            )
            self._record_event(
                event_type=EVENT_TRANSFER_IN,
                sku=cat["sku"],
                location_id=to_lid,
                on_hand_before=oh_t,
                on_hand_after=oh_t + q,
                reserved_before=res_t,
                reserved_after=res_t,
                notes=notes,
                actor=actor,
                ref_type="transfer",
                ref_id=str(from_lid),
            )
            # legacy transfer row as completed
            self.store.execute(
                """
                INSERT INTO stock_transfers
                  (sku, from_location_id, to_location_id, qty, status,
                   requested_by, approved_by, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'completed', ?, ?, ?, ?, ?)
                """,
                (
                    cat["sku"],
                    from_lid,
                    to_lid,
                    q,
                    actor,
                    actor,
                    notes,
                    _utc_now(),
                    _utc_now(),
                ),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        fc, tc = self._loc_code(from_lid), self._loc_code(to_lid)
        self._activity(
            "inventory_transfer",
            f"Stock transferred · {cat['sku']} · {q} units · {fc} → {tc}",
            {"sku": cat["sku"], "qty": q, "from": fc, "to": tc},
        )
        return {
            "ok": True,
            "sku": cat["sku"],
            "qty": q,
            "from_location": fc,
            "to_location": tc,
            "event_id": e_out,
        }

    # ----- reservations ----------------------------------------------------

    def reserve(
        self,
        *,
        sku: str,
        location: str | int,
        qty: int,
        quote_id: int | None = None,
        quote_line_id: int | None = None,
        notes: str = "",
        actor: str = "counter",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.ensure()
        cat = self._require_sku(sku)
        q = int(qty)
        if q <= 0:
            raise OpsValidationError("Reserve quantity must be positive")
        lid = self._loc(location)
        try:
            self._begin()
            if idempotency_key:
                ex = self.store.fetchone(
                    "SELECT id, status FROM inventory_reservations WHERE idempotency_key = ?",
                    (idempotency_key,),
                )
                if ex is not None:
                    self._commit()
                    return {"ok": True, "idempotent": True, "reservation_id": int(ex["id"])}
            oh, res = self._inv_row(cat["sku"], lid)
            avail = oh - res
            if q > avail:
                raise OpsConflictError(
                    f"Only {avail} units are available. You attempted to reserve {q}."
                )
            self._set_inv(cat["sku"], lid, oh, res + q)
            cur = self.store.execute(
                """
                INSERT INTO inventory_reservations
                  (sku, location_id, qty, status, quote_id, quote_line_id,
                   actor, notes, idempotency_key, created_at)
                VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
                """,
                (
                    cat["sku"],
                    lid,
                    q,
                    quote_id,
                    quote_line_id,
                    actor,
                    notes,
                    idempotency_key,
                    _utc_now(),
                ),
            )
            rid = int(getattr(cur, "lastrowid", 0) or 0)
            self._record_event(
                event_type=EVENT_RESERVE,
                sku=cat["sku"],
                location_id=lid,
                on_hand_before=oh,
                on_hand_after=oh,
                reserved_before=res,
                reserved_after=res + q,
                notes=notes,
                actor=actor,
                ref_type="reservation",
                ref_id=str(rid),
                idempotency_key=f"evt-res-{idempotency_key}" if idempotency_key else None,
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        code = self._loc_code(lid)
        self._activity(
            "inventory_reserve",
            f"Inventory reserved · {cat['sku']} · {q} unit{'s' if q != 1 else ''} · {code}"
            + (f" · Quote linked" if quote_id else ""),
            {"sku": cat["sku"], "qty": q, "location": code, "reservation_id": rid},
        )
        return {
            "ok": True,
            "reservation_id": rid,
            "sku": cat["sku"],
            "location_code": code,
            "qty": q,
            "on_hand": oh,
            "reserved": res + q,
            "available": oh - (res + q),
        }

    def release_reservation(
        self,
        *,
        reservation_id: int,
        actor: str = "counter",
        notes: str = "",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.ensure()
        try:
            self._begin()
            prior = self._idem_lookup(idempotency_key)
            if prior is not None and prior.get("action") == "reservation_release":
                self._commit()
                return {
                    "ok": True,
                    "idempotent": True,
                    "reservation_id": int(prior["entity_id"]),
                }
            row = self.store.fetchone(
                "SELECT * FROM inventory_reservations WHERE id = ?",
                (int(reservation_id),),
            )
            if row is None:
                raise OpsValidationError("Reservation not found")
            if str(row["status"]) != RES_ACTIVE:
                raise OpsConflictError("This reservation has already been released.")
            sku = str(row["sku"])
            lid = int(row["location_id"])
            q = int(row["qty"])
            oh, res = self._inv_row(sku, lid)
            new_res = max(0, res - q)
            self._set_inv(sku, lid, oh, new_res)
            self.store.execute(
                "UPDATE inventory_reservations SET status = ?, released_at = ?, notes = ? WHERE id = ?",
                (RES_RELEASED, _utc_now(), notes or row["notes"] or "", int(reservation_id)),
            )
            self._record_event(
                event_type=EVENT_RELEASE,
                sku=sku,
                location_id=lid,
                on_hand_before=oh,
                on_hand_after=oh,
                reserved_before=res,
                reserved_after=new_res,
                notes=notes,
                actor=actor,
                ref_type="reservation",
                ref_id=str(reservation_id),
                idempotency_key=f"evt-rel-{idempotency_key}" if idempotency_key else None,
            )
            self._idem_put(
                key=idempotency_key,
                action="reservation_release",
                entity_type="reservation",
                entity_id=int(reservation_id),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        code = self._loc_code(lid)
        self._activity(
            "inventory_release",
            f"Reservation released · {sku} · {q} · {code}",
            {"sku": sku, "qty": q, "reservation_id": reservation_id},
        )
        return {"ok": True, "reservation_id": reservation_id, "available": oh - new_res}

    # ----- quotes ----------------------------------------------------------

    def _next_quote_number(self) -> str:
        row = self.store.fetchone("SELECT COUNT(*) AS c FROM quotes")
        n = int(row["c"] or 0) + 1
        return f"Q-{n:04d}"

    def _next_order_number(self) -> str:
        row = self.store.fetchone("SELECT COUNT(*) AS c FROM orders")
        n = int(row["c"] or 0) + 1
        return f"O-{n:04d}"

    def create_quote(
        self,
        *,
        customer_label: str = "",
        customer_contact: str = "",
        notes: str = "",
        actor: str = "counter",
    ) -> dict[str, Any]:
        self.ensure()
        now = _utc_now()
        qn = self._next_quote_number()
        # ensure unique
        while self.store.fetchone("SELECT 1 FROM quotes WHERE quote_number = ?", (qn,)):
            qn = f"Q-{uuid.uuid4().hex[:6].upper()}"
        cur = self.store.execute(
            """
            INSERT INTO quotes
              (quote_number, status, customer_label, customer_contact, notes, actor, created_at, updated_at)
            VALUES (?, 'draft', ?, ?, ?, ?, ?, ?)
            """,
            (qn, customer_label or "Walk-in", customer_contact or "", notes or "", actor, now, now),
        )
        qid = int(getattr(cur, "lastrowid", 0) or 0)
        self.store.commit()
        self._activity(
            "quote_created",
            f"Quote created · {qn}",
            {"quote_id": qid, "quote_number": qn},
        )
        return self.get_quote(qid)

    def get_quote(self, quote_id: int) -> dict[str, Any]:
        self.ensure()
        q = self.store.fetchone("SELECT * FROM quotes WHERE id = ?", (int(quote_id),))
        if q is None:
            raise OpsValidationError("Quote not found")
        lines = self.store.fetchall(
            """
            SELECT ql.*, l.code AS location_code, l.name AS location_name
            FROM quote_lines ql
            JOIN locations l ON l.id = ql.location_id
            WHERE ql.quote_id = ?
            ORDER BY ql.id
            """,
            (int(quote_id),),
        )
        line_out = []
        total = 0
        for ln in lines:
            d = dict(ln)
            cents = int(d.get("unit_price_cents") or 0)
            qty = int(d.get("qty") or 0)
            line_total = cents * qty
            total += line_total
            d["unit_price"] = cents / 100.0
            d["line_total_cents"] = line_total
            d["line_total"] = line_total / 100.0
            line_out.append(d)
        out = dict(q)
        out["lines"] = line_out
        out["total_cents"] = total
        out["total"] = total / 100.0
        return out

    def list_quotes(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        self.ensure()
        lim = max(1, min(int(limit or 100), 200))
        if status:
            rows = self.store.fetchall(
                "SELECT * FROM quotes WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, lim),
            )
        else:
            rows = self.store.fetchall(
                "SELECT * FROM quotes ORDER BY id DESC LIMIT ?",
                (lim,),
            )
        return [self.get_quote(int(r["id"])) for r in rows]

    def add_quote_line(
        self,
        *,
        quote_id: int,
        sku: str,
        location: str | int,
        qty: int = 1,
        unit_price_cents: int | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        self.ensure()
        q = self.get_quote(quote_id)
        if q["status"] not in (QUOTE_DRAFT, QUOTE_OPEN):
            raise OpsConflictError("This quote can no longer be edited.")
        cat = self._require_sku(sku)
        lid = self._loc(location)
        qn = int(qty)
        if qn <= 0:
            raise OpsValidationError("Line quantity must be positive")
        if unit_price_cents is None:
            # prefer inventory price then list_price — convert dollars to cents carefully
            inv = self.store.fetchone(
                "SELECT price FROM inventory_levels WHERE sku = ? AND location_id = ?",
                (cat["sku"], lid),
            )
            dollars = float(inv["price"]) if inv and inv["price"] else float(cat.get("list_price") or 0)
            unit_price_cents = int(round(dollars * 100))
        cents = int(unit_price_cents)
        if cents < 0:
            raise OpsValidationError("Price cannot be negative")
        desc = description or str(cat.get("name") or cat["sku"])
        self.store.execute(
            """
            INSERT INTO quote_lines
              (quote_id, sku, location_id, qty, unit_price_cents, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(quote_id), cat["sku"], lid, qn, cents, desc),
        )
        if q["status"] == QUOTE_DRAFT:
            self.store.execute(
                "UPDATE quotes SET status = ?, updated_at = ? WHERE id = ?",
                (QUOTE_OPEN, _utc_now(), int(quote_id)),
            )
        else:
            self.store.execute(
                "UPDATE quotes SET updated_at = ? WHERE id = ?",
                (_utc_now(), int(quote_id)),
            )
        self.store.commit()
        return self.get_quote(quote_id)

    def update_quote_line(
        self,
        *,
        quote_id: int,
        line_id: int,
        qty: int | None = None,
        unit_price_cents: int | None = None,
    ) -> dict[str, Any]:
        self.ensure()
        q = self.get_quote(quote_id)
        if q["status"] not in (QUOTE_DRAFT, QUOTE_OPEN):
            raise OpsConflictError("This quote can no longer be edited.")
        if q["status"] == QUOTE_RESERVED:
            raise OpsConflictError("Release the reservation before editing lines.")
        line = self.store.fetchone(
            "SELECT * FROM quote_lines WHERE id = ? AND quote_id = ?",
            (int(line_id), int(quote_id)),
        )
        if line is None:
            raise OpsValidationError("Quote line not found")
        new_qty = int(qty) if qty is not None else int(line["qty"])
        new_cents = int(unit_price_cents) if unit_price_cents is not None else int(line["unit_price_cents"])
        if new_qty <= 0:
            raise OpsValidationError("Line quantity must be positive")
        if new_cents < 0:
            raise OpsValidationError("Price cannot be negative")
        self.store.execute(
            "UPDATE quote_lines SET qty = ?, unit_price_cents = ? WHERE id = ?",
            (new_qty, new_cents, int(line_id)),
        )
        self.store.execute(
            "UPDATE quotes SET updated_at = ? WHERE id = ?",
            (_utc_now(), int(quote_id)),
        )
        self.store.commit()
        return self.get_quote(quote_id)

    def remove_quote_line(self, *, quote_id: int, line_id: int) -> dict[str, Any]:
        self.ensure()
        q = self.get_quote(quote_id)
        if q["status"] not in (QUOTE_DRAFT, QUOTE_OPEN):
            raise OpsConflictError("This quote can no longer be edited.")
        self.store.execute(
            "DELETE FROM quote_lines WHERE id = ? AND quote_id = ?",
            (int(line_id), int(quote_id)),
        )
        self.store.execute(
            "UPDATE quotes SET updated_at = ? WHERE id = ?",
            (_utc_now(), int(quote_id)),
        )
        self.store.commit()
        return self.get_quote(quote_id)

    def reserve_quote(
        self, *, quote_id: int, actor: str = "counter", idempotency_key: str | None = None
    ) -> dict[str, Any]:
        self.ensure()
        prior = self._idem_lookup(idempotency_key)
        if prior is not None and prior.get("action") == "quote_reserve":
            q = self.get_quote(int(prior["entity_id"]))
            q = dict(q)
            q["ok"] = True
            q["idempotent"] = True
            return q
        q = self.get_quote(quote_id)
        if q["status"] == QUOTE_RESERVED:
            q = dict(q)
            q["ok"] = True
            q["idempotent"] = True
            # Bind key to existing reserved quote so retries with the same key stay safe.
            if idempotency_key:
                try:
                    self._begin()
                    self._idem_put(
                        key=idempotency_key,
                        action="quote_reserve",
                        entity_type="quote",
                        entity_id=int(quote_id),
                    )
                    self._commit()
                except Exception:
                    self._rollback()
                    raise
            return q
        if q["status"] not in (QUOTE_OPEN, QUOTE_DRAFT):
            raise OpsConflictError("Only open quotes can reserve inventory.")
        if not q["lines"]:
            raise OpsValidationError("Add at least one part before reserving.")
        # reserve each line under one transaction by calling reserve internals carefully
        try:
            self._begin()
            # re-check key inside txn (race)
            prior2 = self._idem_lookup(idempotency_key)
            if prior2 is not None and prior2.get("action") == "quote_reserve":
                self._commit()
                out = self.get_quote(int(prior2["entity_id"]))
                out = dict(out)
                out["ok"] = True
                out["idempotent"] = True
                return out
            # re-read status
            st = self.store.fetchone("SELECT status FROM quotes WHERE id = ?", (int(quote_id),))
            if st is None or str(st["status"]) not in (QUOTE_OPEN, QUOTE_DRAFT):
                raise OpsConflictError("Quote state changed. Refresh and try again.")
            for ln in q["lines"]:
                sku = str(ln["sku"])
                lid = int(ln["location_id"])
                qty = int(ln["qty"])
                oh, res = self._inv_row(sku, lid)
                avail = oh - res
                if qty > avail:
                    raise OpsConflictError(
                        f"Only {avail} units of {sku} are available at "
                        f"{self._loc_code(lid)}. You need {qty}."
                    )
                self._set_inv(sku, lid, oh, res + qty)
                cur = self.store.execute(
                    """
                    INSERT INTO inventory_reservations
                      (sku, location_id, qty, status, quote_id, quote_line_id, actor, created_at)
                    VALUES (?, ?, ?, 'active', ?, ?, ?, ?)
                    """,
                    (sku, lid, qty, int(quote_id), int(ln["id"]), actor, _utc_now()),
                )
                rid = int(getattr(cur, "lastrowid", 0) or 0)
                self._record_event(
                    event_type=EVENT_RESERVE,
                    sku=sku,
                    location_id=lid,
                    on_hand_before=oh,
                    on_hand_after=oh,
                    reserved_before=res,
                    reserved_after=res + qty,
                    actor=actor,
                    ref_type="quote",
                    ref_id=str(quote_id),
                    idempotency_key=(
                        f"evt-qres-{idempotency_key}-{ln['id']}" if idempotency_key else None
                    ),
                )
            self.store.execute(
                "UPDATE quotes SET status = ?, updated_at = ? WHERE id = ?",
                (QUOTE_RESERVED, _utc_now(), int(quote_id)),
            )
            self._idem_put(
                key=idempotency_key,
                action="quote_reserve",
                entity_type="quote",
                entity_id=int(quote_id),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        self._activity(
            "quote_reserved",
            f"Inventory reserved · Quote {q['quote_number']} · {len(q['lines'])} line(s)",
            {"quote_id": quote_id, "quote_number": q["quote_number"]},
        )
        return self.get_quote(quote_id)

    def cancel_quote(
        self, *, quote_id: int, actor: str = "counter", idempotency_key: str | None = None
    ) -> dict[str, Any]:
        self.ensure()
        prior = self._idem_lookup(idempotency_key)
        if prior is not None and prior.get("action") == "quote_cancel":
            q = self.get_quote(int(prior["entity_id"]))
            q = dict(q)
            q["ok"] = True
            q["idempotent"] = True
            return q
        q = self.get_quote(quote_id)
        if q["status"] == QUOTE_CANCELLED:
            q = dict(q)
            q["ok"] = True
            q["idempotent"] = True
            if idempotency_key:
                try:
                    self._begin()
                    self._idem_put(
                        key=idempotency_key,
                        action="quote_cancel",
                        entity_type="quote",
                        entity_id=int(quote_id),
                    )
                    self._commit()
                except Exception:
                    self._rollback()
                    raise
            return q
        if q["status"] == QUOTE_CONVERTED:
            raise OpsConflictError("This quote is already closed.")
        try:
            self._begin()
            prior2 = self._idem_lookup(idempotency_key)
            if prior2 is not None and prior2.get("action") == "quote_cancel":
                self._commit()
                out = self.get_quote(int(prior2["entity_id"]))
                out = dict(out)
                out["ok"] = True
                out["idempotent"] = True
                return out
            # release active reservations
            rows = self.store.fetchall(
                "SELECT * FROM inventory_reservations WHERE quote_id = ? AND status = 'active'",
                (int(quote_id),),
            )
            for row in rows:
                sku = str(row["sku"])
                lid = int(row["location_id"])
                qty = int(row["qty"])
                oh, res = self._inv_row(sku, lid)
                new_res = max(0, res - qty)
                self._set_inv(sku, lid, oh, new_res)
                self.store.execute(
                    "UPDATE inventory_reservations SET status = ?, released_at = ? WHERE id = ?",
                    (RES_RELEASED, _utc_now(), int(row["id"])),
                )
                self._record_event(
                    event_type=EVENT_RELEASE,
                    sku=sku,
                    location_id=lid,
                    on_hand_before=oh,
                    on_hand_after=oh,
                    reserved_before=res,
                    reserved_after=new_res,
                    actor=actor,
                    ref_type="quote",
                    ref_id=str(quote_id),
                    idempotency_key=(
                        f"evt-qcan-{idempotency_key}-{row['id']}" if idempotency_key else None
                    ),
                )
            self.store.execute(
                "UPDATE quotes SET status = ?, updated_at = ? WHERE id = ?",
                (QUOTE_CANCELLED, _utc_now(), int(quote_id)),
            )
            self._idem_put(
                key=idempotency_key,
                action="quote_cancel",
                entity_type="quote",
                entity_id=int(quote_id),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        self._activity(
            "quote_cancelled",
            f"Quote cancelled · {q['quote_number']}",
            {"quote_id": quote_id},
        )
        return self.get_quote(quote_id)

    def convert_quote_to_order(
        self, *, quote_id: int, actor: str = "counter", idempotency_key: str | None = None
    ) -> dict[str, Any]:
        self.ensure()
        prior = self._idem_lookup(idempotency_key)
        if prior is not None and prior.get("action") == "quote_convert":
            out = self.get_order(int(prior["entity_id"]))
            out = dict(out)
            out["ok"] = True
            out["idempotent"] = True
            return out
        q = self.get_quote(quote_id)
        if q["status"] == QUOTE_CONVERTED:
            existing = self.store.fetchone(
                "SELECT id FROM orders WHERE quote_id = ? ORDER BY id DESC LIMIT 1",
                (int(quote_id),),
            )
            if existing is None:
                raise OpsConflictError("Quote is converted but order is missing.")
            out = self.get_order(int(existing["id"]))
            out = dict(out)
            out["ok"] = True
            out["idempotent"] = True
            if idempotency_key:
                try:
                    self._begin()
                    self._idem_put(
                        key=idempotency_key,
                        action="quote_convert",
                        entity_type="order",
                        entity_id=int(existing["id"]),
                    )
                    self._commit()
                except Exception:
                    self._rollback()
                    raise
            return out
        if q["status"] != QUOTE_RESERVED:
            raise OpsConflictError("Reserve inventory on the quote before converting to an order.")
        if not q["lines"]:
            raise OpsValidationError("Quote has no lines")
        try:
            self._begin()
            prior2 = self._idem_lookup(idempotency_key)
            if prior2 is not None and prior2.get("action") == "quote_convert":
                self._commit()
                out = self.get_order(int(prior2["entity_id"]))
                out = dict(out)
                out["ok"] = True
                out["idempotent"] = True
                return out
            st = self.store.fetchone("SELECT status FROM quotes WHERE id = ?", (int(quote_id),))
            if st is None or str(st["status"]) != QUOTE_RESERVED:
                raise OpsConflictError("Quote state changed. Refresh and try again.")
            # ensure customer
            label = str(q.get("customer_label") or "Walk-in")
            cust = self.store.fetchone(
                "SELECT id FROM customers WHERE name = ? LIMIT 1",
                (label,),
            )
            if cust is None:
                cur = self.store.execute(
                    "INSERT INTO customers (name, email, phone, company) VALUES (?, ?, '', ?)",
                    (label, str(q.get("customer_contact") or ""), label),
                )
                customer_id = int(getattr(cur, "lastrowid", 0) or 0)
            else:
                customer_id = int(cust["id"])
            on = self._next_order_number()
            while self.store.fetchone("SELECT 1 FROM orders WHERE order_number = ?", (on,)):
                on = f"O-{uuid.uuid4().hex[:6].upper()}"
            now = _utc_now()
            cur = self.store.execute(
                """
                INSERT INTO orders
                  (customer_id, status, created_at, notes, quote_id, order_number, customer_label, actor)
                VALUES (?, 'open', ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer_id,
                    now,
                    str(q.get("notes") or ""),
                    int(quote_id),
                    on,
                    label,
                    actor,
                ),
            )
            oid = int(getattr(cur, "lastrowid", 0) or 0)
            for ln in q["lines"]:
                self.store.execute(
                    """
                    INSERT INTO order_lines (order_id, sku, location_id, qty, unit_price)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        oid,
                        str(ln["sku"]),
                        int(ln["location_id"]),
                        int(ln["qty"]),
                        float(ln.get("unit_price_cents") or 0) / 100.0,
                    ),
                )
            # attach reservations to order
            self.store.execute(
                "UPDATE inventory_reservations SET order_id = ? WHERE quote_id = ? AND status = 'active'",
                (oid, int(quote_id)),
            )
            self.store.execute(
                "UPDATE quotes SET status = ?, updated_at = ? WHERE id = ?",
                (QUOTE_CONVERTED, now, int(quote_id)),
            )
            self._idem_put(
                key=idempotency_key,
                action="quote_convert",
                entity_type="order",
                entity_id=oid,
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        self._activity(
            "order_created",
            f"Order created · {on} · from {q['quote_number']}",
            {"order_id": oid, "order_number": on, "quote_id": quote_id},
        )
        return self.get_order(oid)

    def get_order(self, order_id: int) -> dict[str, Any]:
        self.ensure()
        o = self.store.fetchone(
            """
            SELECT o.*, c.name AS customer_name
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE o.id = ?
            """,
            (int(order_id),),
        )
        if o is None:
            raise OpsValidationError("Order not found")
        lines = self.store.fetchall(
            """
            SELECT ol.*, l.code AS location_code
            FROM order_lines ol
            JOIN locations l ON l.id = ol.location_id
            WHERE ol.order_id = ?
            """,
            (int(order_id),),
        )
        line_out = []
        total = 0.0
        for ln in lines:
            d = dict(ln)
            lt = float(d.get("unit_price") or 0) * int(d.get("qty") or 0)
            d["line_total"] = lt
            total += lt
            line_out.append(d)
        out = dict(o)
        out["lines"] = line_out
        out["total"] = total
        return out

    def list_orders(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        self.ensure()
        lim = max(1, min(int(limit or 100), 200))
        if status:
            rows = self.store.fetchall(
                "SELECT id FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, lim),
            )
        else:
            rows = self.store.fetchall(
                "SELECT id FROM orders ORDER BY id DESC LIMIT ?",
                (lim,),
            )
        return [self.get_order(int(r["id"])) for r in rows]

    def complete_order(
        self, *, order_id: int, actor: str = "counter", idempotency_key: str | None = None
    ) -> dict[str, Any]:
        self.ensure()
        try:
            self._begin()
            prior = self._idem_lookup(idempotency_key)
            if prior is not None and prior.get("action") == "order_complete":
                self._commit()
                out = self.get_order(int(prior["entity_id"]))
                out["ok"] = True
                out["idempotent"] = True
                return out
            o = self.store.fetchone("SELECT * FROM orders WHERE id = ?", (int(order_id),))
            if o is None:
                raise OpsValidationError("Order not found")
            if str(o["status"]) == ORDER_COMPLETED:
                # Double-submit safe: inventory already consumed once.
                self._idem_put(
                    key=idempotency_key,
                    action="order_complete",
                    entity_type="order",
                    entity_id=int(order_id),
                )
                self._commit()
                out = self.get_order(order_id)
                out["ok"] = True
                out["idempotent"] = True
                return out
            if str(o["status"]) == ORDER_CANCELLED:
                raise OpsConflictError("Cancelled orders cannot be completed.")
            # consume reservations if any
            res_rows = self.store.fetchall(
                "SELECT * FROM inventory_reservations WHERE order_id = ? AND status = 'active'",
                (int(order_id),),
            )
            if res_rows:
                for row in res_rows:
                    sku = str(row["sku"])
                    lid = int(row["location_id"])
                    qty = int(row["qty"])
                    oh, res = self._inv_row(sku, lid)
                    if oh < qty or res < qty:
                        raise OpsConflictError(
                            f"Inventory changed while completing the sale for {sku}. "
                            "Refresh and try again."
                        )
                    self._set_inv(sku, lid, oh - qty, res - qty)
                    self.store.execute(
                        "UPDATE inventory_reservations SET status = ?, released_at = ? WHERE id = ?",
                        (RES_CONSUMED, _utc_now(), int(row["id"])),
                    )
                    self._record_event(
                        event_type=EVENT_SALE,
                        sku=sku,
                        location_id=lid,
                        on_hand_before=oh,
                        on_hand_after=oh - qty,
                        reserved_before=res,
                        reserved_after=res - qty,
                        actor=actor,
                        ref_type="order",
                        ref_id=str(order_id),
                        idempotency_key=(
                            f"evt-sale-{idempotency_key}-{row['id']}" if idempotency_key else None
                        ),
                    )
            else:
                # fallback: decrement from order lines (legacy path without reservation)
                lines = self.store.fetchall(
                    "SELECT * FROM order_lines WHERE order_id = ?",
                    (int(order_id),),
                )
                for ln in lines:
                    sku = str(ln["sku"])
                    lid = int(ln["location_id"])
                    qty = int(ln["qty"])
                    oh, res = self._inv_row(sku, lid)
                    avail = oh - res
                    if qty > avail:
                        raise OpsConflictError(
                            f"Only {avail} units of {sku} are available to sell."
                        )
                    self._set_inv(sku, lid, oh - qty, res)
                    self._record_event(
                        event_type=EVENT_SALE,
                        sku=sku,
                        location_id=lid,
                        on_hand_before=oh,
                        on_hand_after=oh - qty,
                        reserved_before=res,
                        reserved_after=res,
                        actor=actor,
                        ref_type="order",
                        ref_id=str(order_id),
                        idempotency_key=(
                            f"evt-sale-{idempotency_key}-ol-{ln['id']}"
                            if idempotency_key
                            else None
                        ),
                    )
            self.store.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (ORDER_COMPLETED, int(order_id)),
            )
            self._idem_put(
                key=idempotency_key,
                action="order_complete",
                entity_type="order",
                entity_id=int(order_id),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        order = self.get_order(order_id)
        self._activity(
            "order_completed",
            f"Order completed · {order.get('order_number') or order_id} · ${order.get('total', 0):.2f}",
            {"order_id": order_id, "total": order.get("total")},
        )
        return order

    def cancel_order(
        self, *, order_id: int, actor: str = "counter", idempotency_key: str | None = None
    ) -> dict[str, Any]:
        self.ensure()
        try:
            self._begin()
            prior = self._idem_lookup(idempotency_key)
            if prior is not None and prior.get("action") == "order_cancel":
                self._commit()
                out = self.get_order(int(prior["entity_id"]))
                out["ok"] = True
                out["idempotent"] = True
                return out
            o = self.store.fetchone("SELECT * FROM orders WHERE id = ?", (int(order_id),))
            if o is None:
                raise OpsValidationError("Order not found")
            if str(o["status"]) == ORDER_COMPLETED:
                raise OpsConflictError(
                    "Completed sales cannot be cancelled here. Use a return/correction if needed."
                )
            if str(o["status"]) == ORDER_CANCELLED:
                self._idem_put(
                    key=idempotency_key,
                    action="order_cancel",
                    entity_type="order",
                    entity_id=int(order_id),
                )
                self._commit()
                out = self.get_order(order_id)
                out["ok"] = True
                out["idempotent"] = True
                return out
            rows = self.store.fetchall(
                "SELECT * FROM inventory_reservations WHERE order_id = ? AND status = 'active'",
                (int(order_id),),
            )
            for row in rows:
                sku = str(row["sku"])
                lid = int(row["location_id"])
                qty = int(row["qty"])
                oh, res = self._inv_row(sku, lid)
                new_res = max(0, res - qty)
                self._set_inv(sku, lid, oh, new_res)
                self.store.execute(
                    "UPDATE inventory_reservations SET status = ?, released_at = ? WHERE id = ?",
                    (RES_RELEASED, _utc_now(), int(row["id"])),
                )
                self._record_event(
                    event_type=EVENT_RELEASE,
                    sku=sku,
                    location_id=lid,
                    on_hand_before=oh,
                    on_hand_after=oh,
                    reserved_before=res,
                    reserved_after=new_res,
                    actor=actor,
                    ref_type="order",
                    ref_id=str(order_id),
                    idempotency_key=(
                        f"evt-ocan-{idempotency_key}-{row['id']}" if idempotency_key else None
                    ),
                )
            self.store.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (ORDER_CANCELLED, int(order_id)),
            )
            self._idem_put(
                key=idempotency_key,
                action="order_cancel",
                entity_type="order",
                entity_id=int(order_id),
            )
            self._commit()
        except Exception:
            self._rollback()
            raise
        order = self.get_order(order_id)
        self._activity(
            "order_cancelled",
            f"Order cancelled · {order.get('order_number') or order_id}",
            {"order_id": order_id},
        )
        return order


    def list_reservations(
        self,
        *,
        sku: str | None = None,
        location: str | int | None = None,
        status: str | None = "active",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        self.ensure()
        lim = max(1, min(int(limit or 50), 200))
        clauses: list[str] = []
        params: list[Any] = []
        if sku:
            clauses.append("r.sku = ?")
            params.append(str(sku).strip())
        if location is not None and str(location).strip() != "":
            lid = self._loc(location)
            clauses.append("r.location_id = ?")
            params.append(lid)
        if status:
            clauses.append("r.status = ?")
            params.append(str(status))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(lim)
        rows = self.store.fetchall(
            f"""
            SELECT r.*, l.code AS location_code,
                   q.quote_number AS quote_number,
                   o.order_number AS order_number
            FROM inventory_reservations r
            LEFT JOIN locations l ON l.id = r.location_id
            LEFT JOIN quotes q ON q.id = r.quote_id
            LEFT JOIN orders o ON o.id = r.order_id
            {where}
            ORDER BY r.id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        return [dict(r) for r in rows]

    def list_events(
        self,
        *,
        sku: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        self.ensure()
        lim = max(1, min(int(limit or 50), 200))
        if sku:
            rows = self.store.fetchall(
                """
                SELECT e.*, l.code AS location_code
                FROM inventory_events e
                LEFT JOIN locations l ON l.id = e.location_id
                WHERE e.sku = ?
                ORDER BY e.id DESC LIMIT ?
                """,
                (str(sku).strip(), lim),
            )
        else:
            rows = self.store.fetchall(
                """
                SELECT e.*, l.code AS location_code
                FROM inventory_events e
                LEFT JOIN locations l ON l.id = e.location_id
                ORDER BY e.id DESC LIMIT ?
                """,
                (lim,),
            )
        return [dict(r) for r in rows]

    def overview_stats(self) -> dict[str, Any]:
        self.ensure()
        open_quotes = self.store.fetchone(
            "SELECT COUNT(*) AS c FROM quotes WHERE status IN ('open','draft','reserved')"
        )
        reserved_units = self.store.fetchone(
            "SELECT COALESCE(SUM(qty),0) AS c FROM inventory_reservations WHERE status = 'active'"
        )
        open_orders = self.store.fetchone(
            "SELECT COUNT(*) AS c FROM orders WHERE status = 'open'"
        )
        completed = self.store.fetchone(
            "SELECT COUNT(*) AS c FROM orders WHERE status = 'completed'"
        )
        return {
            "open_quotes": int(open_quotes["c"] if open_quotes else 0),
            "reserved_units": int(reserved_units["c"] if reserved_units else 0),
            "open_orders": int(open_orders["c"] if open_orders else 0),
            "completed_orders": int(completed["c"] if completed else 0),
        }
