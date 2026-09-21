"""Safe pilot CSV import for the transmission hard-parts vertical.

Preview is always read-only. Commit requires an explicit call/flag.

Canonical write targets:
  - catalog_parts (identity)
  - inventory_levels (physical stock)
  - part_identifiers (optional)
  - transmission_families (ensure family row exists)
  - locations (only if allow_new_locations=True)

Does NOT invent fitment or interchange.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from parrts.dms.service import DmsService

RowStatus = Literal["valid", "warning", "invalid"]

ALLOWED_CONDITIONS = frozenset({"new", "used", "rebuilt", "core"})
ALLOWED_VERIFICATION = frozenset({"unverified", "verified", "demo"})
# part_type values the resolver currently understands (text match)
KNOWN_PART_TYPES = ("pump", "valve body", "drum")

REQUIRED_COLUMNS = ("sku", "name", "transmission_family", "location", "qty")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def dms_initialization_error(dms: DmsService) -> str | None:
    """Return an error message if DMS is not ready for import ops.

    Must not create DB files, tables, or default locations.
    """
    store = dms.store
    db_path = getattr(store, "db_path", None)
    if db_path is not None:
        path = Path(db_path)
        if not path.exists():
            return "DMS is not initialized"
        # Read-only open: do not mkdir; file already exists.
        try:
            import sqlite3

            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                row = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_parts'"
                ).fetchone()
                if row is None:
                    return "DMS is not initialized"
                row2 = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='locations'"
                ).fetchone()
                if row2 is None:
                    return "DMS is not initialized"
            finally:
                conn.close()
        except Exception:
            return "DMS is not initialized"
        return None

    # Non-SQLite backends: attempt a non-mutating probe via existing connection.
    try:
        dms.store.fetchone("SELECT 1 AS ok")
    except Exception:
        return "DMS is not initialized"
    return None


def _norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower()).strip("_")


def _header_map(fieldnames: list[str] | None) -> dict[str, str]:
    """normalized_name -> original header"""
    out: dict[str, str] = {}
    for raw in fieldnames or []:
        if raw is None:
            continue
        key = _norm_header(str(raw))
        if not key:
            continue
        # aliases
        if key in ("location_code", "loc", "location_id"):
            key = "location"
        if key in ("quantity", "qty_on_hand", "on_hand"):
            key = "qty"
        if key in ("part_name", "title"):
            key = "name"
        if key in ("family", "trans_family"):
            key = "transmission_family"
        if key in ("variant", "trans_variant"):
            key = "transmission_variant"
        if key in ("ident_type", "id_type"):
            key = "identifier_type"
        if key in ("ident_value", "id_value", "identifier", "casting", "oem"):
            # only map generic "identifier" if type also present later
            if key in ("ident_value", "id_value", "identifier"):
                key = "identifier_value"
            elif key == "casting":
                # casting alone is value; type defaults later
                key = "identifier_value"
            elif key == "oem":
                key = "identifier_value"
        out[key] = str(raw)
    return out


@dataclass
class RowPlan:
    row_number: int
    status: RowStatus
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sku: str = ""
    name: str = ""
    transmission_family: str = ""
    transmission_variant: str = ""
    category: str = "transmission_hard_parts"
    description: str = ""
    oem_brand: str = ""
    list_price: float = 0.0
    verification_status: str = "unverified"
    source: str = ""
    location: str = ""
    qty: int = 0
    condition: str = "new"
    bin: str = ""
    identifier_type: str = ""
    identifier_value: str = ""
    catalog_action: str = "none"  # insert | preserve | none | conflict
    inventory_action: str = "none"  # insert | update | none
    identifier_action: str = "none"  # insert | none
    location_action: str = "none"  # create | none
    existing_sku: bool = False


@dataclass
class ImportPlan:
    mode: str  # preview | commit
    source_label: str
    allow_new_locations: bool
    total_rows: int = 0
    valid_rows: int = 0
    warning_rows: int = 0
    invalid_rows: int = 0
    new_sku_count: int = 0
    existing_sku_count: int = 0
    inventory_inserts: int = 0
    inventory_updates: int = 0
    catalog_inserts: int = 0
    catalog_updates: int = 0
    identifier_inserts: int = 0
    locations_to_create: int = 0
    locations_referenced: list[str] = field(default_factory=list)
    unknown_locations: list[str] = field(default_factory=list)
    rows: list[RowPlan] = field(default_factory=list)
    file_errors: list[str] = field(default_factory=list)
    committed: bool = False
    commit_result: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_rows: bool = True, max_rows: int = 100) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": len(self.file_errors) == 0 and self.invalid_rows == 0,
            "mode": self.mode,
            "source_label": self.source_label,
            "allow_new_locations": self.allow_new_locations,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "warning_rows": self.warning_rows,
            "invalid_rows": self.invalid_rows,
            "new_sku_count": self.new_sku_count,
            "existing_sku_count": self.existing_sku_count,
            "catalog_inserts": self.catalog_inserts,
            "catalog_updates": self.catalog_updates,
            "inventory_inserts": self.inventory_inserts,
            "inventory_updates": self.inventory_updates,
            "identifier_inserts": self.identifier_inserts,
            "locations_to_create": self.locations_to_create,
            "locations_referenced": sorted(set(self.locations_referenced)),
            "unknown_locations": sorted(set(self.unknown_locations)),
            "file_errors": self.file_errors[:50],
            "committed": self.committed,
        }
        if self.commit_result:
            payload["commit_result"] = self.commit_result
        if include_rows:
            payload["rows"] = [
                {
                    "row_number": r.row_number,
                    "status": r.status,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "sku": r.sku,
                    "name": r.name,
                    "transmission_family": r.transmission_family,
                    "location": r.location,
                    "qty": r.qty,
                    "condition": r.condition,
                    "bin": r.bin,
                    "catalog_action": r.catalog_action,
                    "inventory_action": r.inventory_action,
                    "identifier_action": r.identifier_action,
                    "location_action": r.location_action,
                    "existing_sku": r.existing_sku,
                }
                for r in self.rows[:max_rows]
            ]
            if len(self.rows) > max_rows:
                payload["rows_truncated"] = len(self.rows) - max_rows
        return payload


def _cell(raw: dict[str, Any], headers: dict[str, str], key: str, default: str = "") -> str:
    src = headers.get(key)
    if not src:
        return default
    return str(raw.get(src) or default).strip()


def _parse_qty(raw: str) -> tuple[int | None, str | None]:
    s = (raw or "").strip()
    if s == "":
        return None, "qty is required"
    try:
        # reject scientific / non-finite via float then int exactness
        f = float(s)
    except ValueError:
        return None, f"qty is not numeric: {raw!r}"
    if f != f or f in (float("inf"), float("-inf")):
        return None, f"qty is not a finite number: {raw!r}"
    if f < 0:
        return None, f"qty must not be negative: {raw!r}"
    if abs(f - round(f)) > 1e-9:
        return None, f"qty must be a whole number: {raw!r}"
    return int(round(f)), None


def _has_part_type_hint(text: str) -> bool:
    t = (text or "").lower()
    return any(pt in t for pt in KNOWN_PART_TYPES)


def build_import_plan(
    csv_text: str,
    dms: DmsService,
    *,
    source: str = "pilot_csv",
    allow_new_locations: bool = False,
    mode: str = "preview",
) -> ImportPlan:
    """Parse + validate CSV against current DMS. Never writes."""
    init_err = dms_initialization_error(dms)
    source_label = source if source.startswith("pilot_csv") else f"pilot_csv:{source}"
    plan = ImportPlan(
        mode=mode,
        source_label=source_label,
        allow_new_locations=allow_new_locations,
    )
    if init_err:
        plan.file_errors.append(init_err)
        return plan

    try:
        reader = csv.DictReader(io.StringIO(csv_text))
    except Exception as exc:  # noqa: BLE001
        plan.file_errors.append(f"CSV parse failed: {exc}")
        return plan

    if not reader.fieldnames:
        plan.file_errors.append("CSV has no header row")
        return plan

    headers = _header_map(list(reader.fieldnames))
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        plan.file_errors.append(f"missing required columns: {', '.join(missing)}")
        return plan

    # Known locations
    loc_rows = dms.store.fetchall("SELECT id, code, name FROM locations")
    loc_by_code = {str(r["code"]): int(r["id"]) for r in loc_rows}

    # Existing catalog
    cat_rows = dms.store.fetchall(
        "SELECT sku, name, transmission_family, transmission_variant, category, "
        "description, verification_status, source FROM catalog_parts"
    )
    cat_by_sku = {str(r["sku"]): dict(r) for r in cat_rows}

    # Existing inventory keys
    inv_rows = dms.store.fetchall(
        "SELECT i.sku, l.code AS location_code, i.qty "
        "FROM inventory_levels i JOIN locations l ON l.id = i.location_id"
    )
    inv_keys = {(str(r["sku"]), str(r["location_code"])) for r in inv_rows}

    # Existing identifiers
    id_rows = dms.store.fetchall(
        "SELECT sku, identifier_type, identifier_value FROM part_identifiers"
    )
    id_keys = {
        (str(r["sku"]), str(r["identifier_type"]), str(r["identifier_value"]))
        for r in id_rows
    }

    seen_inv_keys: dict[tuple[str, str], int] = {}
    seen_skus_in_file: dict[str, list[RowPlan]] = {}

    for i, raw in enumerate(reader, start=2):
        plan.total_rows += 1
        row = RowPlan(row_number=i, status="valid")

        row.sku = _cell(raw, headers, "sku")
        row.name = _cell(raw, headers, "name")
        row.transmission_family = _cell(raw, headers, "transmission_family")
        row.transmission_variant = _cell(raw, headers, "transmission_variant") or row.transmission_family
        row.location = _cell(raw, headers, "location")
        qty_raw = _cell(raw, headers, "qty")
        row.condition = (_cell(raw, headers, "condition") or "new").strip().lower()
        row.bin = _cell(raw, headers, "bin")
        row.description = _cell(raw, headers, "description")
        row.category = _cell(raw, headers, "category") or "transmission_hard_parts"
        row.oem_brand = _cell(raw, headers, "oem_brand")
        part_type = _cell(raw, headers, "part_type").strip().lower().replace("_", " ")
        row.identifier_type = _cell(raw, headers, "identifier_type")
        row.identifier_value = _cell(raw, headers, "identifier_value")
        ver = (_cell(raw, headers, "verification_status") or "unverified").strip().lower()
        row.source = source_label

        if not row.sku:
            row.errors.append("sku is required")
        if not row.name:
            row.errors.append("name is required")
        if not row.transmission_family:
            row.errors.append("transmission_family is required")
        if not row.location:
            row.errors.append("location is required")

        qty, qty_err = _parse_qty(qty_raw)
        if qty_err:
            row.errors.append(qty_err)
        else:
            row.qty = int(qty or 0)

        if row.condition not in ALLOWED_CONDITIONS:
            row.errors.append(
                f"condition must be one of {sorted(ALLOWED_CONDITIONS)}: {row.condition!r}"
            )

        if ver not in ALLOWED_VERIFICATION:
            row.errors.append(
                f"verification_status must be one of {sorted(ALLOWED_VERIFICATION)}: {ver!r}"
            )
        else:
            # imported pilot data defaults to unverified even if file says verified
            # unless explicitly verified — still allow verified only if stated
            row.verification_status = ver if ver else "unverified"

        # part type resolvability
        type_text = " ".join([row.name, row.description, part_type, row.category])
        if part_type:
            if part_type not in KNOWN_PART_TYPES:
                row.warnings.append(
                    f"part_type {part_type!r} is not one of known resolver types "
                    f"{list(KNOWN_PART_TYPES)}; stored but may not match NL queries"
                )
            # ensure description carries the type for LIKE matching
            if part_type not in (row.description or "").lower():
                row.description = (
                    f"{row.description} {part_type}".strip()
                    if row.description
                    else part_type
                )
        elif not _has_part_type_hint(type_text):
            row.warnings.append(
                "name/description do not clearly include a known part type "
                f"({', '.join(KNOWN_PART_TYPES)}); natural-language resolution may fail"
            )

        # location policy
        if row.location:
            plan.locations_referenced.append(row.location)
            if row.location in loc_by_code:
                row.location_action = "none"
            else:
                plan.unknown_locations.append(row.location)
                if allow_new_locations:
                    row.location_action = "create"
                    row.warnings.append(
                        f"location {row.location!r} will be created"
                    )
                else:
                    row.errors.append(
                        f"unknown location {row.location!r} "
                        "(pass allow_new_locations to create)"
                    )

        # identifier pair
        if row.identifier_value and not row.identifier_type:
            row.identifier_type = "oem"
            row.warnings.append("identifier_type defaulted to 'oem'")
        if row.identifier_type and not row.identifier_value:
            row.errors.append("identifier_value required when identifier_type is set")

        list_price_raw = _cell(raw, headers, "list_price")
        if list_price_raw:
            try:
                row.list_price = float(list_price_raw)
                if row.list_price < 0:
                    row.errors.append("list_price must not be negative")
            except ValueError:
                row.errors.append(f"list_price is not numeric: {list_price_raw!r}")

        # existing SKU identity checks
        if row.sku and row.sku in cat_by_sku:
            row.existing_sku = True
            existing = cat_by_sku[row.sku]
            ex_fam = str(existing.get("transmission_family") or "")
            ex_var = str(existing.get("transmission_variant") or "")
            ex_name = str(existing.get("name") or "")
            ex_cat = str(existing.get("category") or "")
            conflicts = []
            if ex_fam and row.transmission_family and ex_fam != row.transmission_family:
                conflicts.append(
                    f"transmission_family conflict existing={ex_fam!r} incoming={row.transmission_family!r}"
                )
            if ex_var and row.transmission_variant and ex_var != row.transmission_variant:
                conflicts.append(
                    f"transmission_variant conflict existing={ex_var!r} incoming={row.transmission_variant!r}"
                )
            if ex_name and row.name and ex_name.lower() != row.name.lower():
                conflicts.append(
                    f"name conflict existing={ex_name!r} incoming={row.name!r}"
                )
            if conflicts:
                row.errors.extend(conflicts)
                row.catalog_action = "conflict"
            else:
                # Compatible existing SKU: preserve all canonical catalog metadata.
                row.catalog_action = "preserve"
                if (
                    headers.get("category")
                    and row.category
                    and ex_cat
                    and row.category != ex_cat
                ):
                    row.warnings.append(
                        f"incoming category {row.category!r} ignored; "
                        f"existing canonical category {ex_cat!r} preserved"
                    )
                if headers.get("description") and row.description:
                    row.warnings.append(
                        "incoming description ignored; existing canonical description preserved"
                    )
                if headers.get("verification_status"):
                    row.warnings.append(
                        "incoming verification_status ignored; existing verification preserved"
                    )
        elif row.sku:
            row.catalog_action = "insert"

        # inventory action
        if row.sku and row.location and not row.errors:
            key = (row.sku, row.location)
            if key in seen_inv_keys:
                prev = seen_inv_keys[key]
                row.errors.append(
                    f"duplicate sku/location {key!r} also on row {prev}; "
                    "conflicting duplicates are rejected"
                )
            else:
                seen_inv_keys[key] = i
                if key in inv_keys:
                    row.inventory_action = "update"
                else:
                    row.inventory_action = "insert"

        # identifier action
        if (
            row.sku
            and row.identifier_type
            and row.identifier_value
            and not any("identifier" in e for e in row.errors)
        ):
            ik = (row.sku, row.identifier_type, row.identifier_value)
            if ik not in id_keys:
                row.identifier_action = "insert"
            else:
                row.identifier_action = "none"

        # track multi-row same SKU identity consistency inside file
        if row.sku:
            seen_skus_in_file.setdefault(row.sku, []).append(row)

        if row.errors:
            row.status = "invalid"
            plan.invalid_rows += 1
        elif row.warnings:
            row.status = "warning"
            plan.warning_rows += 1
            plan.valid_rows += 1
        else:
            row.status = "valid"
            plan.valid_rows += 1

        plan.rows.append(row)

    # Cross-row identity consistency for same SKU
    for sku, rows in seen_skus_in_file.items():
        if len(rows) < 2:
            continue
        families = {r.transmission_family for r in rows if r.transmission_family}
        names = {r.name.lower() for r in rows if r.name}
        if len(families) > 1 or len(names) > 1:
            for r in rows:
                if r.status != "invalid":
                    # demote if needed
                    msg = (
                        f"SKU {sku!r} appears with inconsistent identity fields "
                        "across rows in this file"
                    )
                    if msg not in r.errors:
                        r.errors.append(msg)
                    if r.status != "invalid":
                        if r.status == "valid":
                            plan.valid_rows -= 1
                        elif r.status == "warning":
                            plan.warning_rows -= 1
                            plan.valid_rows -= 1
                        r.status = "invalid"
                        plan.invalid_rows += 1
                    r.catalog_action = "conflict"

    # Aggregate planned actions (only non-invalid)
    skus_counted: set[str] = set()
    for r in plan.rows:
        if r.status == "invalid":
            continue
        if r.sku and r.sku not in skus_counted:
            skus_counted.add(r.sku)
            if r.existing_sku:
                plan.existing_sku_count += 1
            else:
                plan.new_sku_count += 1
            if r.catalog_action == "insert":
                plan.catalog_inserts += 1
            # preserve/none/conflict: no catalog mutation planned
        if r.inventory_action == "insert":
            plan.inventory_inserts += 1
        elif r.inventory_action == "update":
            plan.inventory_updates += 1
        if r.identifier_action == "insert":
            plan.identifier_inserts += 1
        if r.location_action == "create":
            plan.locations_to_create += 1

    # de-dup location create count
    create_locs = {
        r.location
        for r in plan.rows
        if r.status != "invalid" and r.location_action == "create"
    }
    plan.locations_to_create = len(create_locs)

    return plan


def commit_import_plan(plan: ImportPlan, dms: DmsService) -> ImportPlan:
    """Apply a previously built plan. Refuses if any invalid rows/file errors."""
    plan.mode = "commit"
    if plan.file_errors or plan.invalid_rows:
        plan.committed = False
        plan.commit_result = {
            "committed": False,
            "reason": "validation errors present; refuse commit",
            "invalid_rows": plan.invalid_rows,
            "file_errors": plan.file_errors,
        }
        return plan

    init_err = dms_initialization_error(dms)
    if init_err:
        plan.committed = False
        plan.commit_result = {
            "committed": False,
            "reason": init_err,
        }
        return plan

    store = dms.store
    conn = store.connect()

    catalog_inserts = catalog_updates = 0
    inventory_inserts = inventory_updates = 0
    identifier_inserts = locations_created = 0

    try:
        conn.execute("BEGIN")
        # location map may grow
        loc_rows = store.fetchall("SELECT id, code FROM locations")
        loc_by_code = {str(r["code"]): int(r["id"]) for r in loc_rows}

        applied_skus: set[str] = set()

        for r in plan.rows:
            if r.status == "invalid":
                continue

            # ensure transmission family row
            if r.transmission_family:
                existing_fam = store.fetchone(
                    "SELECT family FROM transmission_families WHERE family = ?",
                    (r.transmission_family,),
                )
                if existing_fam is None:
                    store.execute(
                        "INSERT INTO transmission_families "
                        "(family, manufacturer, notes, created_at) VALUES (?, ?, ?, ?)",
                        (r.transmission_family, "", "pilot import", _now()),
                    )

            # location create
            if r.location_action == "create" and r.location not in loc_by_code:
                cur = store.execute(
                    "INSERT INTO locations (code, name) VALUES (?, ?)",
                    (r.location, r.location),
                )
                loc_by_code[r.location] = int(cur.lastrowid or 0)
                locations_created += 1

            lid = loc_by_code.get(r.location)
            if lid is None:
                raise RuntimeError(f"location missing after plan: {r.location}")

            # catalog once per SKU
            if r.sku not in applied_skus:
                applied_skus.add(r.sku)
                existing = store.fetchone(
                    "SELECT sku FROM catalog_parts WHERE sku = ?", (r.sku,)
                )
                if existing is None:
                    store.execute(
                        """
                        INSERT INTO catalog_parts (
                            sku, name, description, category, oem_brand, list_price,
                            source, transmission_family, transmission_variant,
                            verification_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            r.sku,
                            r.name,
                            r.description,
                            r.category,
                            r.oem_brand,
                            float(r.list_price or 0),
                            r.source,
                            r.transmission_family,
                            r.transmission_variant,
                            r.verification_status,
                        ),
                    )
                    catalog_inserts += 1
                else:
                    # Existing compatible SKU: never rewrite canonical catalog metadata.
                    # Inventory/identifiers may still update below.
                    pass

            # inventory
            existing_inv = store.fetchone(
                "SELECT qty FROM inventory_levels WHERE sku = ? AND location_id = ?",
                (r.sku, lid),
            )
            if existing_inv is None:
                store.execute(
                    """
                    INSERT INTO inventory_levels
                        (sku, location_id, qty, condition, bin)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (r.sku, lid, int(r.qty), r.condition, r.bin or None),
                )
                inventory_inserts += 1
            else:
                store.execute(
                    """
                    UPDATE inventory_levels
                    SET qty = ?, condition = ?, bin = COALESCE(NULLIF(?, ''), bin)
                    WHERE sku = ? AND location_id = ?
                    """,
                    (int(r.qty), r.condition, r.bin, r.sku, lid),
                )
                inventory_updates += 1

            # identifier
            if r.identifier_action == "insert" and r.identifier_type and r.identifier_value:
                existing_id = store.fetchone(
                    """
                    SELECT id FROM part_identifiers
                    WHERE sku = ? AND identifier_type = ? AND identifier_value = ?
                    """,
                    (r.sku, r.identifier_type, r.identifier_value),
                )
                if existing_id is None:
                    store.execute(
                        """
                        INSERT INTO part_identifiers
                            (sku, identifier_type, identifier_value, notes, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            r.sku,
                            r.identifier_type,
                            r.identifier_value,
                            "pilot import",
                            _now(),
                        ),
                    )
                    identifier_inserts += 1

        conn.commit()
        plan.committed = True
        plan.commit_result = {
            "committed": True,
            "catalog_inserts": catalog_inserts,
            "catalog_updates": catalog_updates,
            "inventory_inserts": inventory_inserts,
            "inventory_updates": inventory_updates,
            "identifier_inserts": identifier_inserts,
            "locations_created": locations_created,
            "rows_processed": plan.valid_rows,
        }
        # refresh plan tallies to actuals
        plan.catalog_inserts = catalog_inserts
        plan.catalog_updates = catalog_updates
        plan.inventory_inserts = inventory_inserts
        plan.inventory_updates = inventory_updates
        plan.identifier_inserts = identifier_inserts
        plan.locations_to_create = locations_created

        # best-effort automation audit (non-authoritative)
        try:
            from parrts.automation.service import AutomationService

            AutomationService(dms.root).record_run(
                kind="transmission_import",
                source_ref=plan.source_label,
                status="ok",
                summary=(
                    f"import ok rows={plan.valid_rows} "
                    f"cat+={catalog_inserts} inv+={inventory_inserts}"
                ),
                detail={
                    "source_label": plan.source_label,
                    "valid_rows": plan.valid_rows,
                    "warning_rows": plan.warning_rows,
                    "catalog_inserts": catalog_inserts,
                    "catalog_updates": catalog_updates,
                    "inventory_inserts": inventory_inserts,
                    "inventory_updates": inventory_updates,
                    "identifier_inserts": identifier_inserts,
                    "locations_created": locations_created,
                },
                requires_human=False,
            )
        except Exception:
            pass

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        plan.committed = False
        plan.commit_result = {
            "committed": False,
            "reason": f"commit failed: {exc}",
        }
        try:
            from parrts.automation.service import AutomationService

            AutomationService(dms.root).record_run(
                kind="transmission_import",
                source_ref=plan.source_label,
                status="error",
                summary=f"import failed: {exc}",
                detail={"error": str(exc)[:500], "source_label": plan.source_label},
                requires_human=True,
            )
        except Exception:
            pass

    return plan


def preview_transmission_import(
    csv_text: str,
    dms: DmsService,
    *,
    source: str = "pilot_csv",
    allow_new_locations: bool = False,
) -> dict[str, Any]:
    plan = build_import_plan(
        csv_text,
        dms,
        source=source,
        allow_new_locations=allow_new_locations,
        mode="preview",
    )
    return plan.to_dict()


def commit_transmission_import(
    csv_text: str,
    dms: DmsService,
    *,
    source: str = "pilot_csv",
    allow_new_locations: bool = False,
) -> dict[str, Any]:
    plan = build_import_plan(
        csv_text,
        dms,
        source=source,
        allow_new_locations=allow_new_locations,
        mode="preview",
    )
    plan = commit_import_plan(plan, dms)
    return plan.to_dict()
