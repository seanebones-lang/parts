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
            "last_oem_sync": dict(last_sync) if last_sync else None,
            "oem_sync_runs": runs,
            "oem_feed_url_set": feed_url_set,
            "oem_configured": feed_url_set,
            "oem_sync_reindex": (os.environ.get("OEM_SYNC_REINDEX") or "").strip().lower()
            in {"1", "true", "yes"},
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
        """Seed catalog/inventory via SyntheticOemFeed."""
        feed = SyntheticOemFeed(seed=seed, n_skus=n_skus, locations=locations)
        return self.sync_oem(feed, source="synthetic")

    def list_inventory(self, location: str | None = None) -> list[dict[str, Any]]:
        self.ensure_schema()
        if location:
            lid = self._location_id(location)
            rows = self.store.fetchall(
                """
                SELECT i.sku, i.location_id, l.code AS location_code, l.name AS location_name,
                       i.qty, i.cost, i.price,
                       c.name, c.description, c.make, c.model, c.year, c.category, c.oem_brand,
                       c.list_price, c.msrp
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
                       i.qty, i.cost, i.price,
                       c.name, c.description, c.make, c.model, c.year, c.category, c.oem_brand,
                       c.list_price, c.msrp
                FROM inventory_levels i
                JOIN locations l ON l.id = i.location_id
                JOIN catalog_parts c ON c.sku = i.sku
                ORDER BY l.id, i.sku
                """
            )
        return [dict(r) for r in rows]

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
        return {"ok": True, "order": self.get_order(order_id), "from": cur, "to": new_status}

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
