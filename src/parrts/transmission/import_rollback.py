"""Reversible transmission pilot import journals (Phase 11).

Journals live in the automation ledger (``.parrts/automation.db``), kind
``transmission_import``. DMS remains canonical; journals are operational metadata.

Rollback is optimistic and refuse-first: only reverse mutations whose current
DMS state still matches the journaled after-state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parrts.automation.service import AutomationService
from parrts.dms.service import DmsService

KIND = "transmission_import"
SCHEMA_VERSION = "transmission_import.v2"


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _detail(run: dict[str, Any]) -> dict[str, Any]:
    d = run.get("detail")
    return d if isinstance(d, dict) else {}


def list_transmission_import_history(
    root: Path | str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Newest-first import history summaries."""
    runs = AutomationService(root).list_runs(kind=KIND, limit=int(limit))
    out: list[dict[str, Any]] = []
    for run in runs:
        d = _detail(run)
        if d.get("schema") not in (SCHEMA_VERSION, "transmission_import.v1", None):
            # still surface older simple audits without rollback
            pass
        rb = d.get("rollback_status") or (
            "available"
            if d.get("mutations")
            else "unavailable"
        )
        counts = d.get("counts") or {}
        out.append(
            {
                "import_run_id": run.get("id"),
                "created_at": run.get("created_at"),
                "source_label": d.get("source_label") or run.get("source_ref"),
                "status": run.get("status"),
                "summary": run.get("summary"),
                "valid_rows": d.get("valid_rows"),
                "warning_rows": d.get("warning_rows"),
                "catalog_inserts": counts.get("catalog_inserts", d.get("catalog_inserts")),
                "inventory_inserts": counts.get(
                    "inventory_inserts", d.get("inventory_inserts")
                ),
                "inventory_updates": counts.get(
                    "inventory_updates", d.get("inventory_updates")
                ),
                "identifier_inserts": counts.get(
                    "identifier_inserts", d.get("identifier_inserts")
                ),
                "locations_created": counts.get(
                    "locations_created", d.get("locations_created")
                ),
                "mutation_count": len(d.get("mutations") or []),
                "rollback_status": rb,
                "rollback_available": rb == "available",
                "rolled_back_at": d.get("rolled_back_at"),
                "backend": d.get("backend"),
                "schema": d.get("schema"),
            }
        )
    return out


def _get_run(root: Path | str, run_id: int) -> dict[str, Any] | None:
    runs = AutomationService(root).list_runs(kind=KIND, limit=5000)
    for r in runs:
        if int(r.get("id") or 0) == int(run_id):
            return r
    return None


def _inv_row(dms: DmsService, sku: str, location_id: int) -> dict[str, Any] | None:
    row = dms.store.fetchone(
        "SELECT qty, condition, bin FROM inventory_levels "
        "WHERE sku = ? AND location_id = ?",
        (sku, location_id),
    )
    return dict(row) if row else None


def _norm_bin(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _inv_matches(row: dict[str, Any] | None, expected: dict[str, Any]) -> bool:
    if row is None:
        return False
    return (
        int(row.get("qty") or 0) == int(expected.get("qty") or 0)
        and str(row.get("condition") or "") == str(expected.get("condition") or "")
        and _norm_bin(row.get("bin")) == _norm_bin(expected.get("bin"))
    )


def preview_transmission_import_rollback(
    dms: DmsService,
    import_run_id: int,
) -> dict[str, Any]:
    """Read-only safety preview for rolling back one import run."""
    root = dms.root
    run = _get_run(root, import_run_id)
    if run is None:
        return {
            "eligible": False,
            "import_run_id": import_run_id,
            "reason": "import run not found",
            "conflicts": [],
            "actions": [],
        }

    d = _detail(run)
    backend = d.get("backend") or getattr(dms, "backend", None) or "sqlite"
    if backend != "sqlite":
        return {
            "eligible": False,
            "import_run_id": import_run_id,
            "source_label": d.get("source_label"),
            "reason": f"rollback supported only for sqlite pilot backend (got {backend!r})",
            "conflicts": [],
            "actions": [],
            "backend": backend,
        }

    if run.get("status") != "ok":
        return {
            "eligible": False,
            "import_run_id": import_run_id,
            "reason": f"import status is {run.get('status')!r}, not ok",
            "conflicts": [],
            "actions": [],
        }

    rb = d.get("rollback_status") or "unavailable"
    if rb == "rolled_back":
        return {
            "eligible": False,
            "import_run_id": import_run_id,
            "reason": "import already rolled back",
            "rollback_status": rb,
            "rolled_back_at": d.get("rolled_back_at"),
            "conflicts": [],
            "actions": [],
        }
    if rb != "available" or not d.get("mutations"):
        return {
            "eligible": False,
            "import_run_id": import_run_id,
            "reason": "no reversible journal available for this import",
            "rollback_status": rb,
            "conflicts": [],
            "actions": [],
        }

    mutations = list(d.get("mutations") or [])
    conflicts: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    preserve: list[dict[str, Any]] = []

    # Verify each mutation against current DMS
    for m in mutations:
        mtype = m.get("type")
        if mtype == "inventory_update":
            sku = str(m.get("sku"))
            lid = int(m.get("location_id"))
            loc = str(m.get("location_code") or "")
            after = m.get("after") or {}
            before = m.get("before") or {}
            cur = _inv_row(dms, sku, lid)
            if not _inv_matches(cur, after):
                conflicts.append(
                    {
                        "type": "inventory_update",
                        "sku": sku,
                        "location": loc,
                        "reason": "inventory state changed after import",
                        "expected_after": after,
                        "current": {
                            "qty": None if cur is None else cur.get("qty"),
                            "condition": None if cur is None else cur.get("condition"),
                            "bin": None if cur is None else cur.get("bin"),
                        },
                    }
                )
            else:
                actions.append(
                    {
                        "type": "restore_inventory",
                        "sku": sku,
                        "location": loc,
                        "location_id": lid,
                        "to": before,
                    }
                )
        elif mtype == "inventory_insert":
            sku = str(m.get("sku"))
            lid = int(m.get("location_id"))
            loc = str(m.get("location_code") or "")
            after = m.get("after") or {}
            cur = _inv_row(dms, sku, lid)
            if cur is None:
                # already gone — nothing to do
                actions.append(
                    {
                        "type": "noop_inventory_missing",
                        "sku": sku,
                        "location": loc,
                    }
                )
            elif not _inv_matches(cur, after):
                conflicts.append(
                    {
                        "type": "inventory_insert",
                        "sku": sku,
                        "location": loc,
                        "reason": "inventory state changed after import",
                        "expected_after": after,
                        "current": {
                            "qty": cur.get("qty"),
                            "condition": cur.get("condition"),
                            "bin": cur.get("bin"),
                        },
                    }
                )
            else:
                actions.append(
                    {
                        "type": "delete_inventory",
                        "sku": sku,
                        "location": loc,
                        "location_id": lid,
                    }
                )
        elif mtype == "identifier_insert":
            sku = str(m.get("sku"))
            itype = str(m.get("identifier_type"))
            ival = str(m.get("identifier_value"))
            row = dms.store.fetchone(
                "SELECT id FROM part_identifiers "
                "WHERE sku = ? AND identifier_type = ? AND identifier_value = ?",
                (sku, itype, ival),
            )
            if row is None:
                actions.append(
                    {
                        "type": "noop_identifier_missing",
                        "sku": sku,
                        "identifier_type": itype,
                        "identifier_value": ival,
                    }
                )
            else:
                actions.append(
                    {
                        "type": "delete_identifier",
                        "sku": sku,
                        "identifier_type": itype,
                        "identifier_value": ival,
                    }
                )
        elif mtype == "catalog_insert":
            sku = str(m.get("sku"))
            after = m.get("after") or {}
            row = dms.store.fetchone(
                "SELECT sku, name, transmission_family, transmission_variant, "
                "category, description, source, verification_status "
                "FROM catalog_parts WHERE sku = ?",
                (sku,),
            )
            if row is None:
                actions.append({"type": "noop_catalog_missing", "sku": sku})
            else:
                # Require key identity fields still match import-created values
                mismatches = []
                for k in (
                    "name",
                    "transmission_family",
                    "transmission_variant",
                    "source",
                    "verification_status",
                ):
                    if after.get(k) is not None and str(row[k] or "") != str(after.get(k) or ""):
                        mismatches.append(k)
                # Dependent inventory not owned by this import blocks catalog delete
                other_inv = dms.store.fetchall(
                    "SELECT location_id, qty FROM inventory_levels WHERE sku = ?",
                    (sku,),
                )
                owned_lids = {
                    int(x.get("location_id"))
                    for x in mutations
                    if x.get("type") in ("inventory_insert", "inventory_update")
                    and str(x.get("sku")) == sku
                    and x.get("location_id") is not None
                }
                for inv in other_inv:
                    if int(inv["location_id"]) not in owned_lids:
                        mismatches.append("unrelated_inventory")
                        break
                if mismatches:
                    conflicts.append(
                        {
                            "type": "catalog_insert",
                            "sku": sku,
                            "reason": "catalog/dependencies changed after import",
                            "mismatches": mismatches,
                            "expected_after": after,
                            "current": dict(row),
                        }
                    )
                else:
                    actions.append({"type": "delete_catalog", "sku": sku})
        elif mtype == "location_insert":
            code = str(m.get("location_code"))
            lid = int(m.get("location_id"))
            # Defer actual eligibility until after inventory deletes are known
            actions.append(
                {
                    "type": "maybe_delete_location",
                    "location_code": code,
                    "location_id": lid,
                }
            )
        elif mtype == "family_insert":
            fam = str(m.get("family"))
            actions.append({"type": "maybe_delete_family", "family": fam})

    # Resolve maybe_delete_location after inventory actions
    resolved_actions: list[dict[str, Any]] = []
    for a in actions:
        if a.get("type") != "maybe_delete_location":
            resolved_actions.append(a)
            continue
        lid = int(a["location_id"])
        code = a["location_code"]
        # remaining inventory at location after planned deletes?
        # If conflicts already exist, we won't execute — still report intention.
        remaining = dms.store.fetchone(
            "SELECT COUNT(*) AS c FROM inventory_levels WHERE location_id = ?",
            (lid,),
        )
        # Count rows that will be deleted by this rollback
        deleting = sum(
            1
            for x in actions
            if x.get("type") == "delete_inventory" and int(x.get("location_id") or 0) == lid
        )
        current_count = int(remaining["c"]) if remaining else 0
        if current_count - deleting <= 0 and not any(
            c.get("location") == code for c in conflicts
        ):
            resolved_actions.append(
                {"type": "delete_location", "location_code": code, "location_id": lid}
            )
        else:
            preserve.append(
                {
                    "type": "location",
                    "location_code": code,
                    "reason": "location still referenced or conflicts present",
                }
            )

    # family delete resolution
    final_actions: list[dict[str, Any]] = []
    for a in resolved_actions:
        if a.get("type") != "maybe_delete_family":
            final_actions.append(a)
            continue
        fam = a["family"]
        # after planned catalog deletes, any remaining catalog with this family?
        cats = dms.store.fetchall(
            "SELECT sku FROM catalog_parts WHERE transmission_family = ?",
            (fam,),
        )
        delete_skus = {
            str(x.get("sku")) for x in resolved_actions if x.get("type") == "delete_catalog"
        }
        remaining_skus = [str(c["sku"]) for c in cats if str(c["sku"]) not in delete_skus]
        if not remaining_skus and not conflicts:
            final_actions.append({"type": "delete_family", "family": fam})
        else:
            preserve.append(
                {
                    "type": "family",
                    "family": fam,
                    "reason": "family still referenced by catalog",
                    "remaining_skus": remaining_skus[:20],
                }
            )

    eligible = len(conflicts) == 0
    return {
        "eligible": eligible,
        "import_run_id": import_run_id,
        "source_label": d.get("source_label"),
        "created_at": run.get("created_at"),
        "backend": backend,
        "mutation_count": len(mutations),
        "actions": final_actions,
        "preserve": preserve,
        "conflicts": conflicts,
        "reason": None if eligible else "one or more mutations are no longer safe to reverse",
        "inventory_restores": sum(
            1 for a in final_actions if a.get("type") == "restore_inventory"
        ),
        "rows_to_delete": sum(
            1
            for a in final_actions
            if a.get("type")
            in ("delete_inventory", "delete_identifier", "delete_catalog", "delete_location", "delete_family")
        ),
    }


def rollback_transmission_import(
    dms: DmsService,
    import_run_id: int,
    *,
    actor: str = "operator",
) -> dict[str, Any]:
    """Execute a safe rollback for one import run. Never force."""
    preview = preview_transmission_import_rollback(dms, import_run_id)
    if not preview.get("eligible"):
        return {
            "ok": False,
            "rolled_back": False,
            "import_run_id": import_run_id,
            "reason": preview.get("reason") or "not eligible",
            "preview": preview,
        }

    # Independent re-check already done inside preview; re-run once more for safety
    preview2 = preview_transmission_import_rollback(dms, import_run_id)
    if not preview2.get("eligible"):
        return {
            "ok": False,
            "rolled_back": False,
            "import_run_id": import_run_id,
            "reason": preview2.get("reason") or "became ineligible",
            "preview": preview2,
        }

    store = dms.store
    conn = store.connect()
    actions = list(preview2.get("actions") or [])
    use_savepoint = bool(getattr(conn, "in_transaction", False))

    try:
        if use_savepoint:
            conn.execute("SAVEPOINT p11_rollback")
        else:
            conn.execute("BEGIN")
        # Order: identifiers → inventory restores/deletes → catalog → location → family
        order = {
            "delete_identifier": 10,
            "restore_inventory": 20,
            "delete_inventory": 30,
            "delete_catalog": 40,
            "delete_location": 50,
            "delete_family": 60,
            "noop_inventory_missing": 90,
            "noop_identifier_missing": 90,
            "noop_catalog_missing": 90,
        }
        actions_sorted = sorted(
            actions, key=lambda a: order.get(str(a.get("type")), 80)
        )

        for a in actions_sorted:
            t = a.get("type")
            if t == "delete_identifier":
                store.execute(
                    "DELETE FROM part_identifiers "
                    "WHERE sku = ? AND identifier_type = ? AND identifier_value = ?",
                    (a["sku"], a["identifier_type"], a["identifier_value"]),
                )
            elif t == "restore_inventory":
                to = a.get("to") or {}
                # re-verify after-state still holds
                cur = _inv_row(dms, str(a["sku"]), int(a["location_id"]))
                # We trust preview2 but still check exists
                if cur is None:
                    raise RuntimeError(
                        f"inventory missing during rollback for {a['sku']}/{a['location']}"
                    )
                store.execute(
                    "UPDATE inventory_levels "
                    "SET qty = ?, condition = ?, bin = ? "
                    "WHERE sku = ? AND location_id = ?",
                    (
                        int(to.get("qty") or 0),
                        str(to.get("condition") or "new"),
                        to.get("bin") or None,
                        a["sku"],
                        int(a["location_id"]),
                    ),
                )
            elif t == "delete_inventory":
                store.execute(
                    "DELETE FROM inventory_levels WHERE sku = ? AND location_id = ?",
                    (a["sku"], int(a["location_id"])),
                )
            elif t == "delete_catalog":
                store.execute(
                    "DELETE FROM catalog_parts WHERE sku = ?",
                    (a["sku"],),
                )
            elif t == "delete_location":
                # final safety: no inventory left
                left = store.fetchone(
                    "SELECT COUNT(*) AS c FROM inventory_levels WHERE location_id = ?",
                    (int(a["location_id"]),),
                )
                if left and int(left["c"]) > 0:
                    raise RuntimeError(
                        f"location {a['location_code']} still has inventory"
                    )
                store.execute(
                    "DELETE FROM locations WHERE id = ?",
                    (int(a["location_id"]),),
                )
            elif t == "delete_family":
                left = store.fetchone(
                    "SELECT COUNT(*) AS c FROM catalog_parts WHERE transmission_family = ?",
                    (a["family"],),
                )
                if left and int(left["c"]) > 0:
                    raise RuntimeError(f"family {a['family']} still referenced")
                store.execute(
                    "DELETE FROM transmission_families WHERE family = ?",
                    (a["family"],),
                )
            # noops ignored

        if use_savepoint:
            conn.execute("RELEASE SAVEPOINT p11_rollback")
            conn.commit()
        else:
            conn.commit()
    except Exception as exc:
        try:
            if use_savepoint:
                conn.execute("ROLLBACK TO SAVEPOINT p11_rollback")
                conn.execute("RELEASE SAVEPOINT p11_rollback")
            else:
                conn.rollback()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        return {
            "ok": False,
            "rolled_back": False,
            "import_run_id": import_run_id,
            "reason": f"rollback failed: {exc}",
            "preview": preview2,
        }

    # Mark journal rolled back (best-effort update via new audit + mutate detail)
    rolled_at = _utcnow()
    try:
        auto = AutomationService(dms.root)
        # Update by rewriting detail on a follow-up note is awkward without UPDATE API.
        # Use direct store update on automation_runs.
        run = _get_run(dms.root, import_run_id)
        d = _detail(run or {})
        d["rollback_status"] = "rolled_back"
        d["rolled_back_at"] = rolled_at
        d["rolled_back_by"] = actor
        import json

        auto.store.execute(
            "UPDATE automation_runs SET detail_json = ?, summary = ? WHERE id = ?",
            (
                json.dumps(d),
                f"rolled back at {rolled_at}",
                int(import_run_id),
            ),
        )
        auto.store.commit()
        auto.record_run(
            kind="transmission_import_rollback",
            source_ref=str(import_run_id),
            status="ok",
            summary=f"rolled back import {import_run_id}",
            detail={
                "import_run_id": import_run_id,
                "actor": actor,
                "rolled_back_at": rolled_at,
                "actions": actions_sorted,
            },
            requires_human=False,
        )
    except Exception:
        # DMS already reversed; journal mark failed — still report success with warning
        return {
            "ok": True,
            "rolled_back": True,
            "import_run_id": import_run_id,
            "rolled_back_at": rolled_at,
            "warning": "DMS reversed but journal status update failed",
            "actions": actions,
        }

    return {
        "ok": True,
        "rolled_back": True,
        "import_run_id": import_run_id,
        "rolled_back_at": rolled_at,
        "actions": actions,
    }
