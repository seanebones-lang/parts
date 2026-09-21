"""DMS service layer — catalog, inventory, customers, orders, OEM sync, RAG export."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parrts.dms.backend import DmsBackendConfig, open_store, resolve_backend
from parrts.dms.oem import DEFAULT_LOCATION_CODES, OemFeed, SyntheticOemFeed
from parrts.models import LocationInventory, PartRecord


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class InsufficientStockError(ValueError):
    """Raised when an order line cannot be reserved."""


class DmsService:
    """DMS operations — SQLite embedded (default) or Postgres when DMS_BACKEND=postgres."""

    def __init__(
        self,
        root: Path | str,
        *,
        backend: str | None = None,
        database_url: str | None = None,
        config: DmsBackendConfig | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.config = config or resolve_backend(
            backend=backend,
            database_url=database_url,
            root=self.root,
        )
        self.store = open_store(self.config, self.root)
        self.backend = self.config.backend

    def ensure_schema(self) -> None:
        self.store.ensure_schema()
        self._ensure_default_locations()

    def _ensure_default_locations(self) -> None:
        for code, name in DEFAULT_LOCATION_CODES:
            row = self.store.fetchone("SELECT id FROM locations WHERE code = ?", (code,))
            if row is None:
                self.store.execute(
                    "INSERT INTO locations (code, name) VALUES (?, ?)",
                    (code, name),
                )
        self.store.commit()

    def _location_id(self, code_or_id: str | int) -> int:
        if isinstance(code_or_id, int) or (isinstance(code_or_id, str) and code_or_id.isdigit()):
            lid = int(code_or_id)
            row = self.store.fetchone("SELECT id FROM locations WHERE id = ?", (lid,))
            if row is None:
                raise ValueError(f"Unknown location id: {lid}")
            return lid
        code = str(code_or_id).strip()
        row = self.store.fetchone("SELECT id FROM locations WHERE code = ?", (code,))
        if row is None:
            # Try match by name
            row = self.store.fetchone(
                "SELECT id FROM locations WHERE lower(name) = lower(?) OR lower(name) LIKE lower(?)",
                (code, f"%{code}%"),
            )
        if row is None:
            raise ValueError(f"Unknown location: {code_or_id}")
        return int(row["id"])

    def _location_map(self) -> dict[int, tuple[str, str]]:
        rows = self.store.fetchall("SELECT id, code, name FROM locations ORDER BY id")
        return {int(r["id"]): (str(r["code"]), str(r["name"])) for r in rows}

    def status(self) -> dict[str, Any]:
        self.ensure_schema()
        parts = self.store.fetchone("SELECT COUNT(*) AS c FROM catalog_parts")
        inv = self.store.fetchone(
            "SELECT COUNT(*) AS c, COALESCE(SUM(qty), 0) AS units FROM inventory_levels"
        )
        customers = self.store.fetchone("SELECT COUNT(*) AS c FROM customers")
        orders = self.store.fetchone("SELECT COUNT(*) AS c FROM orders")
        locs = self.store.fetchone("SELECT COUNT(*) AS c FROM locations")
        adjs = self.store.fetchone("SELECT COUNT(*) AS c FROM stock_adjustments")
        last_sync = self.store.fetchone(
            "SELECT id, source, started_at, finished_at, parts_upserted, status, message "
            "FROM oem_sync_runs ORDER BY id DESC LIMIT 1"
        )
        runs = self.list_oem_sync_runs(limit=10)
        import os

        feed_url_set = bool((os.environ.get("OEM_FEED_URL") or "").strip())
        return {
            "ok": True,
            "backend": self.backend,
            "db_path": str(self.store.db_path),
            "locations": int(locs["c"]) if locs else 0,
            "catalog_parts": int(parts["c"]) if parts else 0,
            "inventory_rows": int(inv["c"]) if inv else 0,
            "inventory_units": int(inv["units"]) if inv else 0,
            "customers": int(customers["c"]) if customers else 0,
            "orders": int(orders["c"]) if orders else 0,
            "stock_adjustments": int(adjs["c"]) if adjs else 0,
            "last_oem_sync": dict(last_sync) if last_sync else None,
            "oem_sync_runs": runs,
            "oem_feed_url_set": feed_url_set,
            "oem_configured": feed_url_set,
            "oem_sync_reindex": (os.environ.get("OEM_SYNC_REINDEX") or "").strip().lower()
            in {"1", "true", "yes"},
        }

    def analytics_summary(self) -> dict[str, Any]:
        """Real operator analytics from DMS tables (no fake KPIs)."""
        self.ensure_schema()
        base = self.status()

        orders_by_status_rows = self.store.fetchall(
            "SELECT status, COUNT(*) AS c FROM orders GROUP BY status ORDER BY status"
        )
        orders_by_status = {
            str(r["status"] or "unknown"): int(r["c"] or 0) for r in orders_by_status_rows
        }

        revenue = self.store.fetchone(
            """
            SELECT
              COALESCE(SUM(ol.qty * ol.unit_price), 0) AS order_book_value,
              COALESCE(SUM(CASE WHEN lower(o.status) IN ('invoiced','completed')
                                THEN ol.qty * ol.unit_price ELSE 0 END), 0) AS realized_value,
              COALESCE(SUM(CASE WHEN lower(o.status) IN ('open','picking')
                                THEN ol.qty * ol.unit_price ELSE 0 END), 0) AS open_pipeline_value,
              COUNT(DISTINCT o.id) AS orders_with_lines
            FROM order_lines ol
            JOIN orders o ON o.id = ol.order_id
            """
        )

        transfers_rows = self.store.fetchall(
            "SELECT status, COUNT(*) AS c FROM stock_transfers GROUP BY status ORDER BY status"
        )
        transfers_by_status = {
            str(r["status"] or "unknown"): int(r["c"] or 0) for r in transfers_rows
        }

        adj_rows = self.store.fetchall(
            """
            SELECT reason,
                   COUNT(*) AS c,
                   COALESCE(SUM(delta), 0) AS delta_sum
            FROM stock_adjustments
            GROUP BY reason
            ORDER BY reason
            """
        )
        adjustments_by_reason = [
            {
                "reason": str(r["reason"] or "adjust"),
                "count": int(r["c"] or 0),
                "delta_sum": int(r["delta_sum"] or 0),
            }
            for r in adj_rows
        ]

        low_stock = self.store.fetchone(
            """
            SELECT COUNT(*) AS c
            FROM inventory_levels
            WHERE qty >= 0 AND qty <= 2
            """
        )
        zero_stock = self.store.fetchone(
            "SELECT COUNT(*) AS c FROM inventory_levels WHERE qty <= 0"
        )

        top_skus = self.store.fetchall(
            """
            SELECT sku, SUM(qty) AS units
            FROM inventory_levels
            GROUP BY sku
            ORDER BY units DESC, sku ASC
            LIMIT 10
            """
        )
        top_inventory = [
            {"sku": str(r["sku"]), "units": int(r["units"] or 0)} for r in top_skus
        ]

        # Dead stock: on-hand units with zero order_line demand ever
        dead_rows = self.store.fetchall(
            """
            SELECT i.sku, SUM(i.qty) AS units
            FROM inventory_levels i
            WHERE i.qty > 0
              AND NOT EXISTS (
                SELECT 1 FROM order_lines ol WHERE ol.sku = i.sku
              )
            GROUP BY i.sku
            ORDER BY units DESC, i.sku ASC
            LIMIT 15
            """
        )
        dead_stock_list = [
            {"sku": str(r["sku"]), "units": int(r["units"] or 0)} for r in dead_rows
        ]

        # Fill rate proxy: ordered lines that could reserve (all create_order reserves)
        # vs cancelled line qty share — honest operational proxy from DMS events only
        line_stats = self.store.fetchone(
            """
            SELECT
              COALESCE(SUM(ol.qty), 0) AS ordered_units,
              COALESCE(SUM(CASE WHEN lower(o.status) = 'cancelled' THEN ol.qty ELSE 0 END), 0)
                AS cancelled_units,
              COALESCE(SUM(CASE WHEN lower(o.status) IN ('invoiced','completed')
                                THEN ol.qty ELSE 0 END), 0) AS fulfilled_units
            FROM order_lines ol
            JOIN orders o ON o.id = ol.order_id
            """
        )
        ordered_u = int(line_stats["ordered_units"] or 0) if line_stats else 0
        fulfilled_u = int(line_stats["fulfilled_units"] or 0) if line_stats else 0
        cancelled_u = int(line_stats["cancelled_units"] or 0) if line_stats else 0
        fill_rate = {
            "ordered_units": ordered_u,
            "fulfilled_units": fulfilled_u,
            "cancelled_units": cancelled_u,
            "fulfillment_ratio": (
                round(fulfilled_u / ordered_u, 4) if ordered_u > 0 else None
            ),
            "note": "fulfilled = invoiced|completed line qty / all ordered qty",
        }

        ss_count = self.store.fetchone("SELECT COUNT(*) AS c FROM part_supersessions")
        pay_count = self.store.fetchone("SELECT COUNT(*) AS c FROM payment_events")
        ship_count = self.store.fetchone("SELECT COUNT(*) AS c FROM shipment_events")

        # created_at is ISO text from seed/service — prefix compare is enough offline
        recent_orders = self.store.fetchone(
            """
            SELECT COUNT(*) AS c
            FROM orders
            WHERE created_at >= datetime('now', '-7 days')
            """
        )
        # SQLite datetime on non-ISO may return 0; also count all as fallback signal
        recent_adjustments = self.store.fetchone(
            """
            SELECT COUNT(*) AS c
            FROM stock_adjustments
            WHERE created_at >= datetime('now', '-7 days')
            """
        )

        return {
            "ok": True,
            "source": "dms",
            "backend": base.get("backend"),
            "generated_at": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "counts": {
                "locations": int(base.get("locations") or 0),
                "catalog_parts": int(base.get("catalog_parts") or 0),
                "inventory_rows": int(base.get("inventory_rows") or 0),
                "inventory_units": int(base.get("inventory_units") or 0),
                "customers": int(base.get("customers") or 0),
                "orders": int(base.get("orders") or 0),
                "stock_adjustments": int(base.get("stock_adjustments") or 0),
                "transfers": sum(transfers_by_status.values()),
                "low_stock_rows": int(low_stock["c"]) if low_stock else 0,
                "zero_stock_rows": int(zero_stock["c"]) if zero_stock else 0,
                "orders_last_7d": int(recent_orders["c"]) if recent_orders else 0,
                "adjustments_last_7d": int(recent_adjustments["c"]) if recent_adjustments else 0,
            },
            "orders_by_status": orders_by_status,
            "transfers_by_status": transfers_by_status,
            "adjustments_by_reason": adjustments_by_reason,
            "revenue": {
                "order_book_value": float(revenue["order_book_value"] or 0) if revenue else 0.0,
                "realized_value": float(revenue["realized_value"] or 0) if revenue else 0.0,
                "open_pipeline_value": float(revenue["open_pipeline_value"] or 0) if revenue else 0.0,
                "currency": "USD",
                "note": "From order_lines × unit_price; not Stripe settlement",
            },
            "top_inventory_skus": top_inventory,
            "dead_stock": dead_stock_list,
            "fill_rate": fill_rate,
            "supersessions": {
                "mapping_count": int(ss_count["c"]) if ss_count else 0,
            },
            "payments": {
                "event_count": int(pay_count["c"]) if pay_count else 0,
                "note": "Ledger of intents/events; not bank settlement",
            },
            "shipments": {
                "event_count": int(ship_count["c"]) if ship_count else 0,
                "note": "Ledger of rates/labels; not carrier SLA",
            },
            "oem": {
                "feed_configured": bool(base.get("oem_configured")),
                "last_sync": base.get("last_oem_sync"),
                "recent_runs": base.get("oem_sync_runs") or [],
            },
        }

    def list_oem_sync_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        """Recent OEM sync run log rows (newest first)."""
        self.ensure_schema()
        lim = max(1, min(int(limit or 20), 200))
        rows = self.store.fetchall(
            "SELECT id, source, started_at, finished_at, parts_upserted, status, message "
            "FROM oem_sync_runs ORDER BY id DESC LIMIT ?",
            (lim,),
        )
        return [dict(r) for r in rows]

    def sync_oem(self, feed: OemFeed, source: str | None = None) -> dict[str, Any]:
        """Upsert catalog + inventory from an OEM feed; log oem_sync_runs."""
        self.ensure_schema()
        source_name = source or type(feed).__name__
        started = _utc_now()
        cur = self.store.execute(
            "INSERT INTO oem_sync_runs (source, started_at, status, message) VALUES (?, ?, ?, ?)",
            (source_name, started, "running", ""),
        )
        if cur.lastrowid is None:
            raise RuntimeError("failed to allocate oem_sync_runs id")
        run_id = int(cur.lastrowid)
        self.store.commit()

        upserted = 0
        try:
            # Ensure any new location codes from feed exist
            loc_by_code = {
                code: lid
                for lid, (code, _name) in self._location_map().items()
            }
            for part in feed.iter_parts():
                sku = str(part["sku"])
                self.store.execute(
                    """
                    INSERT INTO catalog_parts (
                        sku, name, description, make, model, year, category,
                        oem_brand, list_price, msrp, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sku) DO UPDATE SET
                        name=excluded.name,
                        description=excluded.description,
                        make=excluded.make,
                        model=excluded.model,
                        year=excluded.year,
                        category=excluded.category,
                        oem_brand=excluded.oem_brand,
                        list_price=excluded.list_price,
                        msrp=excluded.msrp,
                        source=excluded.source
                    """,
                    (
                        sku,
                        str(part.get("name") or sku),
                        str(part.get("description") or ""),
                        str(part.get("make") or ""),
                        str(part.get("model") or ""),
                        str(part.get("year") or ""),
                        str(part.get("category") or ""),
                        str(part.get("oem_brand") or ""),
                        float(part.get("list_price") or 0),
                        float(part.get("msrp") or 0),
                        source_name,
                    ),
                )
                location_qty = part.get("location_qty") or {}
                if not location_qty:
                    # No per-location map — put zero stock at all known locations
                    location_qty = {code: 0 for code in loc_by_code}
                list_price = float(part.get("list_price") or 0)
                cost = round(list_price * 0.65, 2)
                for loc_key, qty in location_qty.items():
                    if loc_key in loc_by_code:
                        lid = loc_by_code[loc_key]
                    elif str(loc_key).isdigit() and int(loc_key) in {
                        i for i in self._location_map()
                    }:
                        lid = int(loc_key)
                    else:
                        # Create unknown location code on the fly
                        name = str(loc_key)
                        existing = self.store.fetchone(
                            "SELECT id FROM locations WHERE code = ?", (str(loc_key),)
                        )
                        if existing:
                            lid = int(existing["id"])
                        else:
                            c = self.store.execute(
                                "INSERT INTO locations (code, name) VALUES (?, ?)",
                                (str(loc_key), name),
                            )
                            if c.lastrowid is None:
                                raise RuntimeError("failed to allocate location id")
                            lid = int(c.lastrowid)
                            loc_by_code[str(loc_key)] = lid
                    self.store.execute(
                        """
                        INSERT INTO inventory_levels (sku, location_id, qty, cost, price)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(sku, location_id) DO UPDATE SET
                            qty=excluded.qty,
                            cost=excluded.cost,
                            price=excluded.price
                        """,
                        (sku, lid, int(qty), cost, list_price),
                    )
                upserted += 1
            finished = _utc_now()
            self.store.execute(
                """
                UPDATE oem_sync_runs
                SET finished_at=?, parts_upserted=?, status=?, message=?
                WHERE id=?
                """,
                (finished, upserted, "ok", f"upserted {upserted} parts", run_id),
            )
            self.store.commit()
            return {
                "ok": True,
                "run_id": run_id,
                "source": source_name,
                "parts_upserted": upserted,
                "status": "ok",
                "started_at": started,
                "finished_at": finished,
            }
        except Exception as exc:  # noqa: BLE001 — log failure then re-raise
            finished = _utc_now()
            self.store.execute(
                """
                UPDATE oem_sync_runs
                SET finished_at=?, parts_upserted=?, status=?, message=?
                WHERE id=?
                """,
                (finished, upserted, "error", str(exc)[:500], run_id),
            )
            self.store.commit()
            raise

    def seed_demo(self, seed: int = 42, n_skus: int = 40, locations: int = 7) -> dict[str, Any]:
        """Seed catalog/inventory via SyntheticOemFeed + sample supersession when ≥2 SKUs."""
        feed = SyntheticOemFeed(seed=seed, n_skus=n_skus, locations=locations)
        result = self.sync_oem(feed, source="synthetic")
        # Sample supersession for demos (first two catalog SKUs) — ignore if already mapped
        try:
            rows = self.store.fetchall(
                "SELECT sku FROM catalog_parts ORDER BY sku LIMIT 2"
            )
            if len(rows) >= 2:
                old_s, new_s = str(rows[0]["sku"]), str(rows[1]["sku"])
                existing = self.store.fetchone(
                    "SELECT id FROM part_supersessions WHERE old_sku = ?",
                    (old_s,),
                )
                if existing is None and old_s != new_s:
                    self.set_supersession(
                        old_sku=old_s,
                        new_sku=new_s,
                        notes="demo seed supersession",
                        actor="seed",
                    )
                    result["demo_supersession"] = {"old_sku": old_s, "new_sku": new_s}
        except Exception:  # noqa: BLE001 — seed must not fail on optional demo map
            pass
        return result

    def list_inventory(self, location: str | None = None) -> list[dict[str, Any]]:
        self.ensure_schema()
        if location:
            lid = self._location_id(location)
            rows = self.store.fetchall(
                """
                SELECT i.sku, i.location_id, l.code AS location_code, l.name AS location_name,
                       i.qty, COALESCE(i.reserved_qty, 0) AS reserved_qty, i.cost, i.price,
                       i.condition, i.bin,
                       c.name, c.description, c.make, c.model, c.year, c.category, c.oem_brand,
                       c.list_price, c.msrp, c.transmission_family
                FROM inventory_levels i
                JOIN locations l ON l.id = i.location_id
                JOIN catalog_parts c ON c.sku = i.sku
                WHERE i.location_id = ?
                ORDER BY i.sku
                """,
                (lid,),
            )
        else:
            rows = self.store.fetchall(
                """
                SELECT i.sku, i.location_id, l.code AS location_code, l.name AS location_name,
                       i.qty, COALESCE(i.reserved_qty, 0) AS reserved_qty, i.cost, i.price,
                       i.condition, i.bin,
                       c.name, c.description, c.make, c.model, c.year, c.category, c.oem_brand,
                       c.list_price, c.msrp, c.transmission_family
                FROM inventory_levels i
                JOIN locations l ON l.id = i.location_id
                JOIN catalog_parts c ON c.sku = i.sku
                ORDER BY l.id, i.sku
                """
            )
        out = []
        for r in rows:
            d = dict(r)
            on_hand = int(d.get("qty") or 0)
            reserved = int(d.get("reserved_qty") or 0)
            d["on_hand"] = on_hand
            d["reserved"] = reserved
            d["available"] = max(0, on_hand - reserved)
            out.append(d)
        return out

    def list_catalog(self, q: str | None = None) -> list[dict[str, Any]]:
        """List catalog parts, optional case-insensitive substring filter on sku/name/make/model."""
        self.ensure_schema()
        if q and str(q).strip():
            like = f"%{str(q).strip()}%"
            rows = self.store.fetchall(
                """
                SELECT sku, name, description, make, model, year, category, oem_brand,
                       list_price, msrp, source
                FROM catalog_parts
                WHERE sku LIKE ? OR name LIKE ? OR make LIKE ? OR model LIKE ?
                   OR description LIKE ? OR category LIKE ?
                ORDER BY sku
                """,
                (like, like, like, like, like, like),
            )
        else:
            rows = self.store.fetchall(
                """
                SELECT sku, name, description, make, model, year, category, oem_brand,
                       list_price, msrp, source
                FROM catalog_parts
                ORDER BY sku
                """
            )
        return [dict(r) for r in rows]

    def list_customers(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        rows = self.store.fetchall(
            "SELECT id, name, email, phone, company FROM customers ORDER BY id"
        )
        return [dict(r) for r in rows]

    def create_customer(
        self,
        name: str,
        email: str = "",
        phone: str = "",
        company: str = "",
    ) -> dict[str, Any]:
        self.ensure_schema()
        if not name or not str(name).strip():
            raise ValueError("customer name is required")
        cur = self.store.execute(
            "INSERT INTO customers (name, email, phone, company) VALUES (?, ?, ?, ?)",
            (str(name).strip(), email or "", phone or "", company or ""),
        )
        self.store.commit()
        if cur.lastrowid is None:
            raise RuntimeError("failed to allocate customer id")
        cid = int(cur.lastrowid)
        return {
            "id": cid,
            "name": str(name).strip(),
            "email": email or "",
            "phone": phone or "",
            "company": company or "",
        }

    def create_order(
        self,
        customer_id: int,
        lines: list[dict[str, Any]],
        notes: str = "",
    ) -> dict[str, Any]:
        """
        Create an order and reserve stock (decrement inventory qty).

        Each line: ``{sku, location_id|location, qty}``.
        """
        self.ensure_schema()
        cust = self.store.fetchone("SELECT id FROM customers WHERE id = ?", (int(customer_id),))
        if cust is None:
            raise ValueError(f"Unknown customer_id: {customer_id}")
        if not lines:
            raise ValueError("order requires at least one line")

        # Validate stock before mutating
        prepared: list[tuple[str, int, int, float]] = []
        for line in lines:
            sku = str(line["sku"])
            qty = int(line["qty"])
            if qty <= 0:
                raise ValueError(f"line qty must be positive for sku={sku}")
            loc_ref = line.get("location_id", line.get("location"))
            if loc_ref is None:
                raise ValueError(f"line missing location_id/location for sku={sku}")
            lid = self._location_id(loc_ref)
            inv = self.store.fetchone(
                "SELECT qty, price FROM inventory_levels WHERE sku = ? AND location_id = ?",
                (sku, lid),
            )
            if inv is None:
                raise ValueError(f"No inventory for sku={sku} location_id={lid}")
            available = int(inv["qty"])
            if available < qty:
                raise InsufficientStockError(
                    f"Insufficient stock for {sku} @ location {lid}: "
                    f"need {qty}, have {available}"
                )
            unit_price = float(line.get("unit_price", inv["price"] or 0))
            prepared.append((sku, lid, qty, unit_price))

        created_at = _utc_now()
        cur = self.store.execute(
            "INSERT INTO orders (customer_id, status, created_at, notes) VALUES (?, ?, ?, ?)",
            (int(customer_id), "open", created_at, notes or ""),
        )
        if cur.lastrowid is None:
            raise RuntimeError("failed to allocate order id")
        order_id = int(cur.lastrowid)
        line_rows: list[dict[str, Any]] = []
        for sku, lid, qty, unit_price in prepared:
            # Reserve stock
            self.store.execute(
                "UPDATE inventory_levels SET qty = qty - ? WHERE sku = ? AND location_id = ?",
                (qty, sku, lid),
            )
            lc = self.store.execute(
                """
                INSERT INTO order_lines (order_id, sku, location_id, qty, unit_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, sku, lid, qty, unit_price),
            )
            if lc.lastrowid is None:
                raise RuntimeError("failed to allocate order_line id")
            line_rows.append(
                {
                    "id": int(lc.lastrowid),
                    "sku": sku,
                    "location_id": lid,
                    "qty": qty,
                    "unit_price": unit_price,
                }
            )
        self.store.commit()
        return {
            "id": order_id,
            "customer_id": int(customer_id),
            "status": "open",
            "created_at": created_at,
            "notes": notes or "",
            "lines": line_rows,
        }

    def list_orders(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        orders = self.store.fetchall(
            """
            SELECT o.id, o.customer_id, o.status, o.created_at, o.notes,
                   o.payment_status, o.last_payment_id, o.paid_amount,
                   o.ship_status, o.tracking_code, o.last_shipment_id,
                   c.name AS customer_name
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            ORDER BY o.id DESC
            """
        )
        result: list[dict[str, Any]] = []
        for o in orders:
            lines = self.store.fetchall(
                """
                SELECT id, order_id, sku, location_id, qty, unit_price
                FROM order_lines WHERE order_id = ? ORDER BY id
                """,
                (int(o["id"]),),
            )
            d = dict(o)
            d["lines"] = [dict(ln) for ln in lines]
            d["total"] = round(
                sum(float(ln["unit_price"]) * int(ln["qty"]) for ln in d["lines"]), 2
            )
            result.append(d)
        return result

    def export_parrts_inventory(self, path: Path | str | None = None) -> Path:
        """
        Write DMS stock as LocationInventory JSON for PartsRAGEngine.

        Default path: ``{root}/.parrts/inventory_from_dms.json``
        Format matches ``parrts.models.LocationInventory.to_dict()`` /
        ``inventory.json`` (location name → list of PartRecord dicts).
        """
        self.ensure_schema()
        out = Path(path) if path is not None else (self.root / ".parrts" / "inventory_from_dms.json")
        out.parent.mkdir(parents=True, exist_ok=True)

        rows = self.list_inventory()
        by_loc: dict[str, list[PartRecord]] = {}
        for r in rows:
            loc_name = str(r["location_name"])
            part = PartRecord(
                sku=str(r["sku"]),
                name=str(r["name"]),
                location=loc_name,
                stock=int(r["qty"]),
                price=float(r["price"] or r.get("list_price") or 0),
                description=str(r.get("description") or ""),
                make=str(r.get("make") or ""),
                model=str(r.get("model") or ""),
                year=str(r.get("year") or ""),
                category=str(r.get("category") or ""),
            )
            by_loc.setdefault(loc_name, []).append(part)

        inv = LocationInventory(locations=by_loc)
        with out.open("w", encoding="utf-8") as f:
            json.dump(inv.to_dict(), f, indent=2, ensure_ascii=False)
        return out

    def reindex_rag(self, force: bool = True) -> dict[str, Any]:
        """
        Export DMS inventory to inventory.json and rebuild PartsRAGEngine index.

        Soft-fails if engine import/build fails; always writes inventory export.
        """
        export_path = self.export_parrts_inventory()
        # Also write as the engine's default inventory.json so build() picks it up
        inv_path = self.root / ".parrts" / "inventory.json"
        inv_path.write_text(export_path.read_text(encoding="utf-8"), encoding="utf-8")
        try:
            from parrts.embeddings import HashingEmbedder
            from parrts.engine import PartsRAGEngine

            engine = PartsRAGEngine(root=self.root, embedder=HashingEmbedder())
            info = engine.build(force_inventory=False)
            return {
                "ok": True,
                "export_path": str(export_path),
                "inventory_path": str(inv_path),
                "index": info,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "export_path": str(export_path),
                "inventory_path": str(inv_path),
                "error": str(exc),
            }

    # ----- Catalog admin -------------------------------------------------

    def upsert_catalog_part(
        self,
        *,
        sku: str,
        name: str,
        description: str = "",
        make: str = "",
        model: str = "",
        year: str = "",
        category: str = "",
        oem_brand: str = "",
        list_price: float = 0.0,
        msrp: float = 0.0,
        source: str = "manual",
        location_qty: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Create or update a catalog SKU; optional per-location qty map."""
        self.ensure_schema()
        sku_s = str(sku or "").strip()
        name_s = str(name or "").strip()
        if not sku_s:
            raise ValueError("sku is required")
        if not name_s:
            raise ValueError("name is required")
        self.store.execute(
            """
            INSERT INTO catalog_parts (
                sku, name, description, make, model, year, category,
                oem_brand, list_price, msrp, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                make=excluded.make,
                model=excluded.model,
                year=excluded.year,
                category=excluded.category,
                oem_brand=excluded.oem_brand,
                list_price=excluded.list_price,
                msrp=excluded.msrp,
                source=excluded.source
            """,
            (
                sku_s,
                name_s,
                description or "",
                make or "",
                model or "",
                year or "",
                category or "",
                oem_brand or "",
                float(list_price or 0),
                float(msrp or 0),
                source or "manual",
            ),
        )
        inv_touched = 0
        if location_qty:
            loc_by_code = {code: lid for lid, (code, _n) in self._location_map().items()}
            cost = round(float(list_price or 0) * 0.65, 2)
            price = float(list_price or 0)
            for loc_key, qty in location_qty.items():
                key = str(loc_key).strip()
                if key in loc_by_code:
                    lid = loc_by_code[key]
                elif key.isdigit() and int(key) in self._location_map():
                    lid = int(key)
                else:
                    existing = self.store.fetchone(
                        "SELECT id FROM locations WHERE code = ?", (key,)
                    )
                    if existing:
                        lid = int(existing["id"])
                    else:
                        c = self.store.execute(
                            "INSERT INTO locations (code, name) VALUES (?, ?)",
                            (key, key),
                        )
                        if c.lastrowid is None:
                            raise RuntimeError("failed to allocate location id")
                        lid = int(c.lastrowid)
                        loc_by_code[key] = lid
                self.store.execute(
                    """
                    INSERT INTO inventory_levels (sku, location_id, qty, cost, price)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(sku, location_id) DO UPDATE SET
                        qty=excluded.qty,
                        cost=excluded.cost,
                        price=excluded.price
                    """,
                    (sku_s, lid, int(qty), cost, price),
                )
                inv_touched += 1
        self.store.commit()
        row = self.store.fetchone(
            "SELECT sku, name, description, make, model, year, category, oem_brand, "
            "list_price, msrp, source FROM catalog_parts WHERE sku = ?",
            (sku_s,),
        )
        return {"ok": True, "part": dict(row) if row else {"sku": sku_s}, "inventory_rows": inv_touched}

    def import_catalog_csv(self, csv_text: str, *, source: str = "csv") -> dict[str, Any]:
        """
        Import catalog from CSV text.

        Required columns: sku, name
        Optional: description, make, model, year, category, oem_brand, list_price, msrp
        Location qty columns: any header matching a location code (e.g. L1, CHI-N)
        """
        import csv
        import io

        self.ensure_schema()
        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        fields = [f.strip() for f in reader.fieldnames if f]
        lower_map = {f.lower(): f for f in fields}
        if "sku" not in lower_map or "name" not in lower_map:
            raise ValueError("CSV must include sku and name columns")

        loc_codes = {code for _lid, (code, _n) in self._location_map().items()}
        # also accept location codes as column headers case-insensitively
        loc_col = {}
        for f in fields:
            if f in loc_codes:
                loc_col[f] = f
            elif f.upper() in loc_codes:
                loc_col[f] = f.upper()

        upserted = 0
        errors: list[str] = []
        for i, raw in enumerate(reader, start=2):
            try:
                def g(key: str, default: str = "") -> str:
                    src_k = lower_map.get(key)
                    if not src_k:
                        return default
                    return str(raw.get(src_k) or default).strip()

                sku = g("sku")
                name = g("name")
                if not sku:
                    continue
                lq: dict[str, int] = {}
                for col, code in loc_col.items():
                    val = str(raw.get(col) or "").strip()
                    if val != "":
                        lq[code] = int(float(val))
                self.upsert_catalog_part(
                    sku=sku,
                    name=name or sku,
                    description=g("description"),
                    make=g("make"),
                    model=g("model"),
                    year=g("year"),
                    category=g("category"),
                    oem_brand=g("oem_brand"),
                    list_price=float(g("list_price") or 0 or 0),
                    msrp=float(g("msrp") or 0 or 0),
                    source=source,
                    location_qty=lq or None,
                )
                upserted += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"row {i}: {exc}")
                if len(errors) >= 25:
                    break
        return {"ok": len(errors) == 0, "upserted": upserted, "errors": errors}

    # ----- Order lifecycle -----------------------------------------------

    ORDER_TRANSITIONS: dict[str, set[str]] = {
        "open": {"picking", "cancelled"},
        "picking": {"invoiced", "cancelled"},
        "invoiced": {"completed", "cancelled"},
        "completed": set(),
        "cancelled": set(),
    }

    def get_order(self, order_id: int) -> dict[str, Any]:
        self.ensure_schema()
        o = self.store.fetchone(
            """
            SELECT o.id, o.customer_id, o.status, o.created_at, o.notes,
                   o.payment_status, o.last_payment_id, o.paid_amount,
                   o.ship_status, o.tracking_code, o.last_shipment_id,
                   c.name AS customer_name, c.email AS customer_email,
                   c.company AS customer_company
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE o.id = ?
            """,
            (int(order_id),),
        )
        if o is None:
            raise ValueError(f"Unknown order_id: {order_id}")
        lines = self.store.fetchall(
            """
            SELECT id, order_id, sku, location_id, qty, unit_price
            FROM order_lines WHERE order_id = ? ORDER BY id
            """,
            (int(order_id),),
        )
        d = dict(o)
        line_dicts = [dict(ln) for ln in lines]
        d["lines"] = line_dicts
        d["total"] = round(sum(float(ln["unit_price"]) * int(ln["qty"]) for ln in line_dicts), 2)
        d["payment_status"] = str(d.get("payment_status") or "") or None
        d["last_payment_id"] = str(d.get("last_payment_id") or "") or None
        d["paid_amount"] = float(d.get("paid_amount") or 0)
        d["ship_status"] = str(d.get("ship_status") or "") or None
        d["tracking_code"] = str(d.get("tracking_code") or "") or None
        d["last_shipment_id"] = str(d.get("last_shipment_id") or "") or None
        return d

    def set_order_status(self, order_id: int, status: str) -> dict[str, Any]:
        """Advance order lifecycle; cancel restores reserved stock."""
        self.ensure_schema()
        new_status = str(status or "").strip().lower()
        order = self.get_order(order_id)
        cur = str(order["status"] or "open").lower()
        allowed = self.ORDER_TRANSITIONS.get(cur, set())
        if new_status == cur:
            return {"ok": True, "order": order, "unchanged": True}
        if new_status not in allowed:
            raise ValueError(f"Cannot transition order {order_id} from {cur!r} to {new_status!r}")

        if new_status == "cancelled" and cur != "cancelled":
            # restore stock
            for ln in order["lines"]:
                self.store.execute(
                    "UPDATE inventory_levels SET qty = qty + ? WHERE sku = ? AND location_id = ?",
                    (int(ln["qty"]), str(ln["sku"]), int(ln["location_id"])),
                )

        self.store.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (new_status, int(order_id)),
        )
        self.store.commit()
        result = {"ok": True, "order": self.get_order(order_id), "from": cur, "to": new_status}
        # Optional customer notify (dry-run unless PARRTS_AUTO_NOTIFY + SMTP)
        try:
            import os

            if os.environ.get("PARRTS_NOTIFY_ON_STATUS", "1").strip().lower() not in {
                "0",
                "false",
                "no",
                "off",
            }:
                from parrts.notify import NotifyService

                n = NotifyService(root=self.root, dms=self)
                email = (result["order"].get("customer_email") or "").strip()
                if email and "@" in email:
                    note = n.notify_order(int(order_id), kind="order_status", dry_run=None, actor="status_hook")
                    result["notification"] = {
                        "ok": note.get("ok"),
                        "dry_run": note.get("dry_run"),
                        "sent": note.get("sent"),
                        "event_id": (note.get("event") or {}).get("id"),
                    }
        except Exception as exc:  # noqa: BLE001 — never block status on notify
            result["notification"] = {"ok": False, "error": str(exc)[:200]}
        return result

    def write_invoice_pdf(self, order_id: int, path: Path | str | None = None) -> dict[str, Any]:
        """Generate a simple PDF invoice for an order (auto-marks invoiced if open/picking)."""
        from parrts.dms.invoice_pdf import write_simple_pdf

        order = self.get_order(order_id)
        st = str(order["status"]).lower()
        if st in {"open", "picking"}:
            # open -> picking -> invoiced or open cannot go direct to invoiced
            if st == "open":
                self.set_order_status(order_id, "picking")
            self.set_order_status(order_id, "invoiced")
            order = self.get_order(order_id)

        out = (
            Path(path)
            if path is not None
            else (self.root / ".parrts" / "invoices" / f"invoice_{int(order_id)}.pdf")
        )
        lines = [
            "Parts — Invoice",
            f"Order #{order['id']}    Status: {order['status']}",
            f"Created: {order.get('created_at') or ''}",
            f"Customer: {order.get('customer_name') or order.get('customer_id')}  "
            f"{order.get('customer_email') or ''}",
            f"Company: {order.get('customer_company') or ''}",
            f"Notes: {order.get('notes') or ''}",
            "-" * 60,
            f"{'SKU':<18} {'Qty':>5} {'Unit':>10} {'Line':>10}",
        ]
        for ln in order["lines"]:
            lt = float(ln["unit_price"]) * int(ln["qty"])
            lines.append(
                f"{str(ln['sku'])[:18]:<18} {int(ln['qty']):>5} "
                f"{float(ln['unit_price']):>10.2f} {lt:>10.2f}"
            )
        lines.append("-" * 60)
        lines.append(f"TOTAL: ${float(order.get('total') or 0):.2f}")
        lines.append("Thank you — NextEleven Parts")
        write_simple_pdf(out, lines, title=f"Invoice {order_id}")
        return {
            "ok": True,
            "order_id": int(order_id),
            "path": str(out),
            "total": order.get("total"),
            "status": order.get("status"),
        }

    # ----- Multi-rooftop org + location ACL --------------------------------

    def ensure_org(self, code: str, name: str | None = None) -> dict[str, Any]:
        self.ensure_schema()
        code_s = str(code or "").strip()
        if not code_s:
            raise ValueError("org code required")
        name_s = (name or code_s).strip()
        row = self.store.fetchone("SELECT id, code, name FROM orgs WHERE code = ?", (code_s,))
        if row:
            return dict(row)
        cur = self.store.execute(
            "INSERT INTO orgs (code, name) VALUES (?, ?)", (code_s, name_s)
        )
        self.store.commit()
        oid = int(cur.lastrowid) if cur.lastrowid else None
        if oid is None:
            row = self.store.fetchone("SELECT id, code, name FROM orgs WHERE code = ?", (code_s,))
            return dict(row) if row else {"code": code_s, "name": name_s}
        return {"id": oid, "code": code_s, "name": name_s}

    def list_orgs(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        rows = self.store.fetchall("SELECT id, code, name FROM orgs ORDER BY id")
        return [dict(r) for r in rows]

    def list_locations(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        rows = self.store.fetchall(
            "SELECT id, code, name, org_id FROM locations ORDER BY id"
        )
        return [dict(r) for r in rows]

    def set_location_org(self, location_code: str, org_code: str) -> dict[str, Any]:
        self.ensure_schema()
        org = self.ensure_org(org_code)
        lid = self._location_id(location_code)
        self.store.execute(
            "UPDATE locations SET org_id = ? WHERE id = ?",
            (int(org["id"]), lid),
        )
        self.store.commit()
        row = self.store.fetchone(
            "SELECT id, code, name, org_id FROM locations WHERE id = ?", (lid,)
        )
        return {"ok": True, "location": dict(row) if row else None, "org": org}

    def set_user_location_acl(
        self, user_key: str, location_codes: list[str]
    ) -> dict[str, Any]:
        """Replace ACL rows for user_key. Empty list = clear (all locations allowed)."""
        self.ensure_schema()
        key = str(user_key or "").strip()
        if not key:
            raise ValueError("user_key required")
        self.store.execute("DELETE FROM user_location_acl WHERE user_key = ?", (key,))
        codes = [str(c).strip() for c in location_codes if str(c).strip()]
        for code in codes:
            self.store.execute(
                "INSERT INTO user_location_acl (user_key, location_code) VALUES (?, ?)",
                (key, code),
            )
        self.store.commit()
        return {"ok": True, "user_key": key, "location_codes": codes, "restricted": bool(codes)}

    def allowed_location_codes(self, user_key: str | None) -> list[str] | None:
        """
        Return allowed location codes for user_key.

        None => unrestricted (all locations).
        [] => restricted but empty (no access).
        """
        if not user_key:
            return None
        self.ensure_schema()
        rows = self.store.fetchall(
            "SELECT location_code FROM user_location_acl WHERE user_key = ? ORDER BY location_code",
            (str(user_key),),
        )
        if not rows:
            return None
        return [str(r["location_code"]) for r in rows]

    def filter_inventory_for_user(
        self, user_key: str | None, location: str | None = None
    ) -> list[dict[str, Any]]:
        rows = self.list_inventory(location=location)
        allowed = self.allowed_location_codes(user_key)
        if allowed is None:
            return rows
        allow = set(allowed)
        return [r for r in rows if str(r.get("location_code") or "") in allow]

    # --- Inter-store transfers (Wave 26) ---------------------------------

    @staticmethod
    def transfer_approval_threshold() -> int:
        """Qty at/above this needs manager+ approval (env PARRTS_TRANSFER_APPROVAL_QTY)."""
        import os

        raw = (os.environ.get("PARRTS_TRANSFER_APPROVAL_QTY") or "10").strip()
        try:
            n = int(raw)
        except ValueError:
            n = 10
        return max(1, n)

    def sku_total_qty(self, sku: str) -> int:
        self.ensure_schema()
        row = self.store.fetchone(
            "SELECT COALESCE(SUM(qty), 0) AS c FROM inventory_levels WHERE sku = ?",
            (str(sku),),
        )
        return int(row["c"]) if row else 0

    def _get_transfer_row(self, transfer_id: int) -> dict[str, Any]:
        row = self.store.fetchone(
            """
            SELECT t.id, t.sku, t.from_location_id, t.to_location_id, t.qty, t.status,
                   t.requested_by, t.approved_by, t.notes, t.created_at, t.updated_at,
                   fl.code AS from_code, tl.code AS to_code
            FROM stock_transfers t
            JOIN locations fl ON fl.id = t.from_location_id
            JOIN locations tl ON tl.id = t.to_location_id
            WHERE t.id = ?
            """,
            (int(transfer_id),),
        )
        if row is None:
            raise ValueError(f"Unknown transfer id: {transfer_id}")
        return dict(row)

    def _apply_transfer_move(self, sku: str, from_lid: int, to_lid: int, qty: int) -> None:
        """Move qty from → to; conserve total stock. Raises InsufficientStockError."""
        inv = self.store.fetchone(
            "SELECT qty FROM inventory_levels WHERE sku = ? AND location_id = ?",
            (sku, from_lid),
        )
        if inv is None or int(inv["qty"]) < qty:
            have = int(inv["qty"]) if inv else 0
            raise InsufficientStockError(
                f"Insufficient stock for transfer {sku} from location {from_lid}: "
                f"need {qty}, have {have}"
            )
        self.store.execute(
            "UPDATE inventory_levels SET qty = qty - ? WHERE sku = ? AND location_id = ?",
            (qty, sku, from_lid),
        )
        dest = self.store.fetchone(
            "SELECT qty FROM inventory_levels WHERE sku = ? AND location_id = ?",
            (sku, to_lid),
        )
        if dest is None:
            # Ensure catalog row exists
            cat = self.store.fetchone("SELECT sku FROM catalog_parts WHERE sku = ?", (sku,))
            if cat is None:
                raise ValueError(f"Unknown sku: {sku}")
            self.store.execute(
                """
                INSERT INTO inventory_levels (sku, location_id, qty, cost, price)
                VALUES (?, ?, ?, 0, 0)
                """,
                (sku, to_lid, qty),
            )
        else:
            self.store.execute(
                "UPDATE inventory_levels SET qty = qty + ? WHERE sku = ? AND location_id = ?",
                (qty, sku, to_lid),
            )

    def create_transfer(
        self,
        *,
        sku: str,
        from_location: str | int,
        to_location: str | int,
        qty: int,
        requested_by: str = "",
        notes: str = "",
        role: str | None = None,
        force_complete: bool = False,
    ) -> dict[str, Any]:
        """
        Create inter-store transfer.

        - qty < approval threshold → completed immediately (stock moved)
        - qty >= threshold → pending_approval until manager approves
        - force_complete with manager+ role also completes large moves
        Stock conservation: total qty for SKU unchanged on complete.
        """
        from parrts.rbac import can, normalize_role

        self.ensure_schema()
        sku_s = str(sku or "").strip()
        if not sku_s:
            raise ValueError("sku required")
        q = int(qty)
        if q <= 0:
            raise ValueError("qty must be positive")
        from_lid = self._location_id(from_location)
        to_lid = self._location_id(to_location)
        if from_lid == to_lid:
            raise ValueError("from_location and to_location must differ")
        cat = self.store.fetchone("SELECT sku FROM catalog_parts WHERE sku = ?", (sku_s,))
        if cat is None:
            raise ValueError(f"Unknown sku: {sku_s}")

        threshold = self.transfer_approval_threshold()
        r = normalize_role(role)
        needs_approval = q >= threshold and not (
            force_complete and can(r, "transfers.approve")
        )
        now = _utc_now()
        before_total = self.sku_total_qty(sku_s)
        status = "pending_approval" if needs_approval else "completed"

        if status == "completed":
            self._apply_transfer_move(sku_s, from_lid, to_lid, q)

        cur = self.store.execute(
            """
            INSERT INTO stock_transfers
              (sku, from_location_id, to_location_id, qty, status,
               requested_by, approved_by, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sku_s,
                from_lid,
                to_lid,
                q,
                status,
                str(requested_by or ""),
                str(requested_by or "") if status == "completed" else "",
                notes or "",
                now,
                now,
            ),
        )
        self.store.commit()
        if cur.lastrowid is None:
            raise RuntimeError("failed to allocate transfer id")
        tid = int(cur.lastrowid)
        after_total = self.sku_total_qty(sku_s)
        if status == "completed" and after_total != before_total:
            raise RuntimeError(
                f"stock conservation violated for {sku_s}: before={before_total} after={after_total}"
            )
        tr = self._get_transfer_row(tid)
        return {
            "ok": True,
            "transfer": tr,
            "approval_threshold": threshold,
            "stock_before": before_total,
            "stock_after": after_total,
            "conserved": after_total == before_total,
        }

    def approve_transfer(
        self,
        transfer_id: int,
        *,
        approved_by: str = "",
        role: str | None = None,
    ) -> dict[str, Any]:
        """Manager+ completes a pending_approval transfer (moves stock)."""
        from parrts.rbac import can, normalize_role

        self.ensure_schema()
        if not can(role, "transfers.approve"):
            raise PermissionError(
                f"role {normalize_role(role)!r} cannot transfers.approve"
            )
        tr = self._get_transfer_row(transfer_id)
        if str(tr["status"]) != "pending_approval":
            raise ValueError(
                f"transfer {transfer_id} status is {tr['status']!r}, expected pending_approval"
            )
        sku = str(tr["sku"])
        qty = int(tr["qty"])
        from_lid = int(tr["from_location_id"])
        to_lid = int(tr["to_location_id"])
        before = self.sku_total_qty(sku)
        self._apply_transfer_move(sku, from_lid, to_lid, qty)
        now = _utc_now()
        self.store.execute(
            """
            UPDATE stock_transfers
            SET status = ?, approved_by = ?, updated_at = ?
            WHERE id = ?
            """,
            ("completed", str(approved_by or ""), now, int(transfer_id)),
        )
        self.store.commit()
        after = self.sku_total_qty(sku)
        if after != before:
            raise RuntimeError(
                f"stock conservation violated for {sku}: before={before} after={after}"
            )
        return {
            "ok": True,
            "transfer": self._get_transfer_row(transfer_id),
            "stock_before": before,
            "stock_after": after,
            "conserved": True,
        }

    def cancel_transfer(
        self,
        transfer_id: int,
        *,
        role: str | None = None,
        cancelled_by: str = "",
    ) -> dict[str, Any]:
        """Cancel pending transfer (no stock change). Completed cannot cancel."""
        from parrts.rbac import can, normalize_role

        self.ensure_schema()
        if not can(role, "transfers.cancel"):
            raise PermissionError(
                f"role {normalize_role(role)!r} cannot transfers.cancel"
            )
        tr = self._get_transfer_row(transfer_id)
        st = str(tr["status"])
        if st == "completed":
            raise ValueError("cannot cancel a completed transfer")
        if st == "cancelled":
            return {"ok": True, "transfer": tr}
        now = _utc_now()
        notes = (tr.get("notes") or "") + f" [cancelled by {cancelled_by or 'system'}]"
        self.store.execute(
            "UPDATE stock_transfers SET status = ?, notes = ?, updated_at = ? WHERE id = ?",
            ("cancelled", notes.strip(), now, int(transfer_id)),
        )
        self.store.commit()
        return {"ok": True, "transfer": self._get_transfer_row(transfer_id)}

    def list_transfers(
        self, *, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        lim = max(1, min(int(limit or 50), 200))
        if status:
            rows = self.store.fetchall(
                """
                SELECT t.id, t.sku, t.from_location_id, t.to_location_id, t.qty, t.status,
                       t.requested_by, t.approved_by, t.notes, t.created_at, t.updated_at,
                       fl.code AS from_code, tl.code AS to_code
                FROM stock_transfers t
                JOIN locations fl ON fl.id = t.from_location_id
                JOIN locations tl ON tl.id = t.to_location_id
                WHERE t.status = ?
                ORDER BY t.id DESC LIMIT ?
                """,
                (str(status), lim),
            )
        else:
            rows = self.store.fetchall(
                """
                SELECT t.id, t.sku, t.from_location_id, t.to_location_id, t.qty, t.status,
                       t.requested_by, t.approved_by, t.notes, t.created_at, t.updated_at,
                       fl.code AS from_code, tl.code AS to_code
                FROM stock_transfers t
                JOIN locations fl ON fl.id = t.from_location_id
                JOIN locations tl ON tl.id = t.to_location_id
                ORDER BY t.id DESC LIMIT ?
                """,
                (lim,),
            )
        return [dict(r) for r in rows]


    # ------------------------------------------------------------------
    # Stock receive / adjust (immutable audit trail)
    # ------------------------------------------------------------------

    ADJUST_REASONS = frozenset(
        {"receive", "adjust", "cycle_count", "damage", "return", "write_off", "other"}
    )

    def adjust_stock(
        self,
        *,
        sku: str,
        location: str | int,
        delta: int,
        reason: str = "adjust",
        notes: str = "",
        actor: str = "",
        role: str | None = None,
    ) -> dict[str, Any]:
        """Apply a signed qty delta at one location and write an audit row.

        Rules:
          - qty_after must be >= 0
          - reason=receive requires delta > 0 and inventory.receive (counter+)
          - negative delta / non-receive reasons require inventory.adjust (manager+)
          - SKU must exist in catalog
        """
        from parrts.rbac import can, normalize_role

        self.ensure_schema()
        sku_s = str(sku or "").strip()
        if not sku_s:
            raise ValueError("sku is required")
        try:
            dlt = int(delta)
        except (TypeError, ValueError) as exc:
            raise ValueError("delta must be an integer") from exc
        if dlt == 0:
            raise ValueError("delta must be non-zero")

        reason_s = (reason or "adjust").strip().lower() or "adjust"
        if reason_s not in self.ADJUST_REASONS:
            raise ValueError(
                f"unknown reason {reason_s!r}; use one of {sorted(self.ADJUST_REASONS)}"
            )

        r = normalize_role(role)
        if reason_s == "receive":
            if dlt <= 0:
                raise ValueError("receive requires a positive delta")
            if not can(r, "inventory.receive"):
                raise PermissionError(f"role {r!r} cannot inventory.receive")
        else:
            if not can(r, "inventory.adjust"):
                raise PermissionError(f"role {r!r} cannot inventory.adjust")

        cat = self.store.fetchone("SELECT sku FROM catalog_parts WHERE sku = ?", (sku_s,))
        if cat is None:
            raise ValueError(f"Unknown SKU (not in catalog): {sku_s}")

        lid = self._location_id(location)
        loc_row = self.store.fetchone("SELECT code, name FROM locations WHERE id = ?", (lid,))
        loc_code = str(loc_row["code"]) if loc_row else str(location)

        inv = self.store.fetchone(
            "SELECT qty FROM inventory_levels WHERE sku = ? AND location_id = ?",
            (sku_s, lid),
        )
        before = int(inv["qty"]) if inv is not None else 0
        after = before + dlt
        if after < 0:
            raise InsufficientStockError(
                f"adjust would make qty negative for {sku_s} @ {loc_code}: "
                f"{before} + ({dlt}) = {after}"
            )

        if inv is None:
            self.store.execute(
                """
                INSERT INTO inventory_levels (sku, location_id, qty, cost, price)
                VALUES (?, ?, ?, 0, 0)
                """,
                (sku_s, lid, after),
            )
        else:
            self.store.execute(
                "UPDATE inventory_levels SET qty = ? WHERE sku = ? AND location_id = ?",
                (after, sku_s, lid),
            )

        now = _utc_now()
        cur = self.store.execute(
            """
            INSERT INTO stock_adjustments
                (sku, location_id, delta, qty_before, qty_after, reason, notes, actor, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sku_s,
                lid,
                dlt,
                before,
                after,
                reason_s,
                (notes or "").strip(),
                (actor or "").strip(),
                now,
            ),
        )
        adj_id = int(getattr(cur, "lastrowid", 0) or 0)
        self.store.commit()
        if not adj_id:
            row = self.store.fetchone(
                "SELECT id FROM stock_adjustments WHERE sku = ? AND created_at = ? "
                "ORDER BY id DESC LIMIT 1",
                (sku_s, now),
            )
            adj_id = int(row["id"]) if row else 0

        return {
            "ok": True,
            "adjustment": {
                "id": adj_id,
                "sku": sku_s,
                "location_id": lid,
                "location_code": loc_code,
                "delta": dlt,
                "qty_before": before,
                "qty_after": after,
                "reason": reason_s,
                "notes": (notes or "").strip(),
                "actor": (actor or "").strip(),
                "created_at": now,
            },
        }

    def list_stock_adjustments(
        self,
        *,
        sku: str | None = None,
        location: str | int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Recent stock adjustments (newest first)."""
        self.ensure_schema()
        lim = max(1, min(int(limit or 50), 200))
        clauses: list[str] = []
        params: list[Any] = []
        if sku and str(sku).strip():
            clauses.append("a.sku = ?")
            params.append(str(sku).strip())
        if location is not None and str(location).strip() != "":
            lid = self._location_id(location)
            clauses.append("a.location_id = ?")
            params.append(lid)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(lim)
        rows = self.store.fetchall(
            f"""
            SELECT a.id, a.sku, a.location_id, l.code AS location_code, l.name AS location_name,
                   a.delta, a.qty_before, a.qty_after, a.reason, a.notes, a.actor, a.created_at
            FROM stock_adjustments a
            JOIN locations l ON l.id = a.location_id
            {where}
            ORDER BY a.id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        return [dict(r) for r in rows]

    # ----- Supersession chains -------------------------------------------

    def set_supersession(
        self,
        *,
        old_sku: str,
        new_sku: str,
        notes: str = "",
        effective_from: str = "",
        actor: str = "",
    ) -> dict[str, Any]:
        """Map old_sku → new_sku. Refuses self-maps and cycles."""
        self.ensure_schema()
        old_s = str(old_sku or "").strip()
        new_s = str(new_sku or "").strip()
        if not old_s or not new_s:
            raise ValueError("old_sku and new_sku required")
        if old_s == new_s:
            raise ValueError("old_sku and new_sku must differ")
        for sku in (old_s, new_s):
            row = self.store.fetchone("SELECT sku FROM catalog_parts WHERE sku = ?", (sku,))
            if row is None:
                raise ValueError(f"Unknown catalog SKU: {sku}")

        # Cycle check: following new_s must not reach old_s
        seen: set[str] = set()
        cur = new_s
        while cur and cur not in seen:
            if cur == old_s:
                raise ValueError(f"Supersession cycle detected involving {old_s!r}")
            seen.add(cur)
            nxt = self.store.fetchone(
                "SELECT new_sku FROM part_supersessions WHERE old_sku = ? ORDER BY id DESC LIMIT 1",
                (cur,),
            )
            cur = str(nxt["new_sku"]) if nxt else ""

        now = _utc_now()
        # Replace prior mapping for this old_sku (single current successor)
        self.store.execute("DELETE FROM part_supersessions WHERE old_sku = ?", (old_s,))
        cur_ins = self.store.execute(
            """
            INSERT INTO part_supersessions
                (old_sku, new_sku, effective_from, notes, created_at, actor)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                old_s,
                new_s,
                (effective_from or "").strip(),
                (notes or "").strip(),
                now,
                (actor or "").strip(),
            ),
        )
        sid = int(getattr(cur_ins, "lastrowid", 0) or 0)
        self.store.commit()
        if not sid:
            row = self.store.fetchone(
                "SELECT id FROM part_supersessions WHERE old_sku = ? AND new_sku = ?",
                (old_s, new_s),
            )
            sid = int(row["id"]) if row else 0
        return {
            "ok": True,
            "supersession": {
                "id": sid,
                "old_sku": old_s,
                "new_sku": new_s,
                "effective_from": (effective_from or "").strip(),
                "notes": (notes or "").strip(),
                "created_at": now,
                "actor": (actor or "").strip(),
            },
        }

    def list_supersessions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        self.ensure_schema()
        lim = max(1, min(int(limit or 100), 500))
        rows = self.store.fetchall(
            """
            SELECT id, old_sku, new_sku, effective_from, notes, created_at, actor
            FROM part_supersessions
            ORDER BY id DESC
            LIMIT ?
            """,
            (lim,),
        )
        return [dict(r) for r in rows]

    def resolve_supersession(self, sku: str, *, max_hops: int = 20) -> dict[str, Any]:
        """Walk old→new chain to current SKU. Detects cycles."""
        self.ensure_schema()
        start = str(sku or "").strip()
        if not start:
            raise ValueError("sku required")
        chain: list[str] = [start]
        seen: set[str] = {start}
        cur = start
        hops = max(1, min(int(max_hops or 20), 50))
        for _ in range(hops):
            row = self.store.fetchone(
                "SELECT new_sku FROM part_supersessions WHERE old_sku = ? ORDER BY id DESC LIMIT 1",
                (cur,),
            )
            if row is None:
                break
            nxt = str(row["new_sku"])
            if nxt in seen:
                return {
                    "ok": False,
                    "sku": start,
                    "current_sku": cur,
                    "chain": chain,
                    "hops": len(chain) - 1,
                    "error": f"cycle at {nxt}",
                }
            chain.append(nxt)
            seen.add(nxt)
            cur = nxt
        return {
            "ok": True,
            "sku": start,
            "current_sku": cur,
            "chain": chain,
            "hops": len(chain) - 1,
            "superseded": cur != start,
        }

    def delete_supersession(self, old_sku: str) -> dict[str, Any]:
        self.ensure_schema()
        old_s = str(old_sku or "").strip()
        if not old_s:
            raise ValueError("old_sku required")
        self.store.execute("DELETE FROM part_supersessions WHERE old_sku = ?", (old_s,))
        self.store.commit()
        return {"ok": True, "old_sku": old_s, "deleted": True}

    # ----- Payment ledger (fail-closed Stripe intents recorded here) -----

    def record_payment_event(
        self,
        *,
        order_id: int,
        amount: float,
        currency: str = "usd",
        status: str = "created",
        provider: str = "stripe",
        external_id: str = "",
        configured: bool = False,
        message: str = "",
        actor: str = "",
        update_order: bool = True,
    ) -> dict[str, Any]:
        """Append payment_events row; optionally stamp order payment fields."""
        self.ensure_schema()
        order = self.get_order(int(order_id))
        now = _utc_now()
        amt = float(amount or 0)
        st = str(status or "created").strip().lower()
        cur = self.store.execute(
            """
            INSERT INTO payment_events
                (order_id, provider, external_id, amount, currency, status,
                 configured, message, actor, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(order_id),
                str(provider or "stripe"),
                str(external_id or ""),
                amt,
                str(currency or "usd").lower(),
                st,
                1 if configured else 0,
                str(message or "")[:500],
                str(actor or ""),
                now,
            ),
        )
        eid = int(getattr(cur, "lastrowid", 0) or 0)
        if update_order:
            self.store.execute(
                """
                UPDATE orders
                SET payment_status = ?, last_payment_id = ?, paid_amount = ?
                WHERE id = ?
                """,
                (st, str(external_id or ""), amt if st in {"succeeded", "paid"} else 0.0, int(order_id)),
            )
            if st in {"succeeded", "paid"} and float(order.get("paid_amount") or 0) == 0:
                # keep amount on success
                self.store.execute(
                    "UPDATE orders SET paid_amount = ? WHERE id = ?",
                    (amt, int(order_id)),
                )
        self.store.commit()
        if not eid:
            row = self.store.fetchone(
                "SELECT id FROM payment_events WHERE order_id = ? AND created_at = ? "
                "ORDER BY id DESC LIMIT 1",
                (int(order_id), now),
            )
            eid = int(row["id"]) if row else 0
        return {
            "ok": True,
            "event": {
                "id": eid,
                "order_id": int(order_id),
                "provider": str(provider or "stripe"),
                "external_id": str(external_id or ""),
                "amount": amt,
                "currency": str(currency or "usd").lower(),
                "status": st,
                "configured": bool(configured),
                "message": str(message or "")[:500],
                "actor": str(actor or ""),
                "created_at": now,
            },
            "order": self.get_order(int(order_id)),
        }

    def list_payment_events(
        self, *, order_id: int | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        lim = max(1, min(int(limit or 50), 200))
        if order_id is not None:
            rows = self.store.fetchall(
                """
                SELECT id, order_id, provider, external_id, amount, currency, status,
                       configured, message, actor, created_at
                FROM payment_events
                WHERE order_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(order_id), lim),
            )
        else:
            rows = self.store.fetchall(
                """
                SELECT id, order_id, provider, external_id, amount, currency, status,
                       configured, message, actor, created_at
                FROM payment_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (lim,),
            )
        out = []
        for r in rows:
            d = dict(r)
            d["configured"] = bool(int(d.get("configured") or 0))
            out.append(d)
        return out

    # ----- Compliance audit export ---------------------------------------

    def compliance_export(self, *, days: int = 90) -> dict[str, Any]:
        """Export last N days of mutable DMS events as JSON-serializable dict."""
        self.ensure_schema()
        d = max(1, min(int(days or 90), 365))
        # ISO prefix compare works for our _utc_now stamps; also include all if few rows
        cutoff = (
            __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .replace(microsecond=0)
            - __import__("datetime").timedelta(days=d)
        ).isoformat()

        def _since(table: str, col: str = "created_at") -> list[dict[str, Any]]:
            rows = self.store.fetchall(
                f"SELECT * FROM {table} WHERE {col} >= ? ORDER BY id DESC LIMIT 5000",
                (cutoff,),
            )
            return [dict(r) for r in rows]

        orders = [dict(r) for r in self.store.fetchall(
            "SELECT * FROM orders WHERE created_at >= ? ORDER BY id DESC LIMIT 5000",
            (cutoff,),
        )]
        order_lines = [
            dict(r)
            for r in self.store.fetchall(
                """
                SELECT ol.* FROM order_lines ol
                JOIN orders o ON o.id = ol.order_id
                WHERE o.created_at >= ?
                ORDER BY ol.id DESC LIMIT 5000
                """,
                (cutoff,),
            )
        ]
        stock_adjustments = _since("stock_adjustments")
        stock_transfers = [
            dict(r)
            for r in self.store.fetchall(
                "SELECT * FROM stock_transfers WHERE created_at >= ? ORDER BY id DESC LIMIT 5000",
                (cutoff,),
            )
        ]
        payment_events = _since("payment_events")
        shipment_events = _since("shipment_events")
        part_supersessions = _since("part_supersessions")
        oem_sync_runs = [
            dict(r)
            for r in self.store.fetchall(
                "SELECT * FROM oem_sync_runs WHERE started_at >= ? ORDER BY id DESC LIMIT 500",
                (cutoff,),
            )
        ]
        payload = {
            "ok": True,
            "exported_at": _utc_now(),
            "days": d,
            "cutoff": cutoff,
            "orders": orders,
            "order_lines": order_lines,
            "stock_adjustments": stock_adjustments,
            "stock_transfers": stock_transfers,
            "payment_events": payment_events,
            "shipment_events": shipment_events,
            "part_supersessions": part_supersessions,
            "oem_sync_runs": oem_sync_runs,
        }
        payload["counts"] = {
            k: len(payload[k])
            for k in (
                "orders",
                "order_lines",
                "stock_adjustments",
                "stock_transfers",
                "payment_events",
                "shipment_events",
                "part_supersessions",
                "oem_sync_runs",
            )
        }
        return payload

    # ----- Shipment ledger (EasyPost rates/labels — fail closed) ---------

    def record_shipment_event(
        self,
        *,
        order_id: int,
        status: str = "rates",
        provider: str = "easypost",
        external_id: str = "",
        tracking_code: str = "",
        label_url: str = "",
        carrier: str = "",
        service: str = "",
        rate: float = 0.0,
        configured: bool = False,
        message: str = "",
        actor: str = "",
        update_order: bool = True,
    ) -> dict[str, Any]:
        """Append shipment_events; stamp order ship fields on label purchase."""
        self.ensure_schema()
        self.get_order(int(order_id))
        now = _utc_now()
        st = str(status or "rates").strip().lower()
        cur = self.store.execute(
            """
            INSERT INTO shipment_events
                (order_id, provider, external_id, tracking_code, label_url,
                 carrier, service, rate, status, configured, message, actor, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(order_id),
                str(provider or "easypost"),
                str(external_id or ""),
                str(tracking_code or ""),
                str(label_url or ""),
                str(carrier or ""),
                str(service or ""),
                float(rate or 0),
                st,
                1 if configured else 0,
                str(message or "")[:500],
                str(actor or ""),
                now,
            ),
        )
        eid = int(getattr(cur, "lastrowid", 0) or 0)
        if update_order:
            self.store.execute(
                """
                UPDATE orders
                SET ship_status = ?, tracking_code = ?, last_shipment_id = ?
                WHERE id = ?
                """,
                (
                    st,
                    str(tracking_code or ""),
                    str(external_id or ""),
                    int(order_id),
                ),
            )
        self.store.commit()
        if not eid:
            row = self.store.fetchone(
                "SELECT id FROM shipment_events WHERE order_id = ? AND created_at = ? "
                "ORDER BY id DESC LIMIT 1",
                (int(order_id), now),
            )
            eid = int(row["id"]) if row else 0
        return {
            "ok": True,
            "event": {
                "id": eid,
                "order_id": int(order_id),
                "provider": str(provider or "easypost"),
                "external_id": str(external_id or ""),
                "tracking_code": str(tracking_code or ""),
                "label_url": str(label_url or ""),
                "carrier": str(carrier or ""),
                "service": str(service or ""),
                "rate": float(rate or 0),
                "status": st,
                "configured": bool(configured),
                "message": str(message or "")[:500],
                "actor": str(actor or ""),
                "created_at": now,
            },
            "order": self.get_order(int(order_id)),
        }

    def list_shipment_events(
        self, *, order_id: int | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        lim = max(1, min(int(limit or 50), 200))
        if order_id is not None:
            rows = self.store.fetchall(
                """
                SELECT id, order_id, provider, external_id, tracking_code, label_url,
                       carrier, service, rate, status, configured, message, actor, created_at
                FROM shipment_events
                WHERE order_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(order_id), lim),
            )
        else:
            rows = self.store.fetchall(
                """
                SELECT id, order_id, provider, external_id, tracking_code, label_url,
                       carrier, service, rate, status, configured, message, actor, created_at
                FROM shipment_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (lim,),
            )
        out = []
        for r in rows:
            d = dict(r)
            d["configured"] = bool(int(d.get("configured") or 0))
            out.append(d)
        return out

    # ----- Customer notifications (email ledger — fail closed) ------------

    def record_notification_event(
        self,
        *,
        order_id: int | None,
        kind: str = "order_status",
        channel: str = "email",
        to_address: str = "",
        subject: str = "",
        body: str = "",
        status: str = "drafted",
        dry_run: bool = True,
        configured: bool = False,
        message: str = "",
        actor: str = "",
    ) -> dict[str, Any]:
        self.ensure_schema()
        now = _utc_now()
        cur = self.store.execute(
            """
            INSERT INTO notification_events
                (order_id, kind, channel, to_address, subject, body,
                 status, dry_run, configured, message, actor, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(order_id) if order_id is not None else None,
                str(kind or "order_status"),
                str(channel or "email"),
                str(to_address or ""),
                str(subject or "")[:300],
                str(body or "")[:8000],
                str(status or "drafted"),
                1 if dry_run else 0,
                1 if configured else 0,
                str(message or "")[:500],
                str(actor or ""),
                now,
            ),
        )
        eid = int(getattr(cur, "lastrowid", 0) or 0)
        self.store.commit()
        if not eid:
            row = self.store.fetchone(
                "SELECT id FROM notification_events ORDER BY id DESC LIMIT 1"
            )
            eid = int(row["id"]) if row else 0
        return {
            "ok": True,
            "event": {
                "id": eid,
                "order_id": int(order_id) if order_id is not None else None,
                "kind": str(kind or "order_status"),
                "channel": str(channel or "email"),
                "to_address": str(to_address or ""),
                "subject": str(subject or "")[:300],
                "body": str(body or "")[:8000],
                "status": str(status or "drafted"),
                "dry_run": bool(dry_run),
                "configured": bool(configured),
                "message": str(message or "")[:500],
                "actor": str(actor or ""),
                "created_at": now,
            },
        }

    def list_notification_events(
        self, *, order_id: int | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        self.ensure_schema()
        lim = max(1, min(int(limit or 50), 200))
        if order_id is not None:
            rows = self.store.fetchall(
                """
                SELECT id, order_id, kind, channel, to_address, subject, body,
                       status, dry_run, configured, message, actor, created_at
                FROM notification_events
                WHERE order_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(order_id), lim),
            )
        else:
            rows = self.store.fetchall(
                """
                SELECT id, order_id, kind, channel, to_address, subject, body,
                       status, dry_run, configured, message, actor, created_at
                FROM notification_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (lim,),
            )
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["dry_run"] = bool(int(d.get("dry_run") or 0))
            d["configured"] = bool(int(d.get("configured") or 0))
            out.append(d)
        return out
