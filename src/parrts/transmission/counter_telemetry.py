"""JP counter search pilot telemetry (operational, not resolver accuracy).

Persists every counter API search mode and lot selections for inventory_matches.
Offline evals that call answer_transmission_inquiry / counter_search directly
do NOT write telemetry — only the API orchestration layer and explicit helpers.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from parrts.dms.service import DmsService

TELEMETRY_SOURCES = frozenset({"jp_real_pilot", "jp_demo", "test"})
SELECTION_ACTIONS = frozenset({"ADD_TO_QUOTE", "RESERVE"})
SEARCH_MODES = frozenset({"exact_match", "inventory_matches", "needs_review"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_telemetry_source(explicit: str | None = None) -> str:
    """Resolve traffic source. Default local/dev is jp_demo — never silent real pilot."""
    if explicit:
        s = str(explicit).strip().lower()
        if s in TELEMETRY_SOURCES:
            return s
        if s in ("real", "pilot", "jp_pilot"):
            return "jp_real_pilot"
        if s in ("demo", "development", "dev"):
            return "jp_demo"
        if s in ("test", "pytest", "ci"):
            return "test"
    env_src = (os.environ.get("COUNTER_TELEMETRY_SOURCE") or "").strip().lower()
    if env_src in TELEMETRY_SOURCES:
        return env_src
    mode = (os.environ.get("JP_PILOT_MODE") or "").strip().lower()
    if mode in ("real", "jp_real_pilot", "pilot"):
        return "jp_real_pilot"
    if mode in ("test", "pytest"):
        return "test"
    # Explicit opt-out or default
    if mode in ("demo", "jp_demo", "", "off", "0", "false"):
        return "jp_demo"
    return "jp_demo"


def new_search_id() -> str:
    return f"css_{uuid.uuid4().hex}"


def record_counter_search(
    dms: DmsService,
    *,
    query_text: str,
    search_mode: str,
    search_id: str | None = None,
    request_id: str | None = None,
    proposed_sku: str | None = None,
    transmission_family: str | None = None,
    part_category: str | None = None,
    candidate_count: int = 0,
    total_available: int = 0,
    elapsed_ms: float | None = None,
    source: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Insert one counter search session. Idempotent on search_id (reuse = no second row)."""
    mode = (search_mode or "").strip()
    if mode not in SEARCH_MODES:
        raise ValueError(f"invalid search_mode: {search_mode!r}")
    sid = (search_id or new_search_id()).strip()
    src = resolve_telemetry_source(source)
    # inventory_matches must never carry a fabricated proposed winner
    prop = None if mode == "inventory_matches" else (proposed_sku or None)
    if prop is not None:
        prop = str(prop).strip() or None

    existing = dms.store.fetchone(
        "SELECT id, search_mode FROM counter_search_sessions WHERE id = ?",
        (sid,),
    )
    if existing is not None:
        return {
            "ok": True,
            "search_id": sid,
            "idempotent": True,
            "search_mode": str(existing["search_mode"]),
            "source": src,
        }

    dms.store.execute(
        """
        INSERT INTO counter_search_sessions (
            id, created_at, query_text, search_mode,
            request_id, proposed_sku,
            transmission_family, part_category,
            candidate_count, total_available,
            elapsed_ms, source, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sid,
            _utc_now(),
            str(query_text or "").strip(),
            mode,
            (str(request_id).strip() if request_id else None),
            prop,
            (str(transmission_family).strip() if transmission_family else None),
            (str(part_category).strip() if part_category else None),
            int(candidate_count or 0),
            int(total_available or 0),
            float(elapsed_ms) if elapsed_ms is not None else None,
            src,
            str(notes or ""),
        ),
    )
    dms.store.commit()
    return {
        "ok": True,
        "search_id": sid,
        "idempotent": False,
        "search_mode": mode,
        "source": src,
    }


def record_counter_search_from_result(
    dms: DmsService,
    result: Any,
    *,
    source: str | None = None,
    search_id: str | None = None,
) -> dict[str, Any]:
    """Map a CounterSearchResult (or duck-type) into a telemetry row."""
    mode = getattr(result, "search_mode", None) or "needs_review"
    disc = getattr(result, "discovery", None) or {}
    if not isinstance(disc, dict):
        disc = {}
    cand = int(disc.get("candidate_count") or 0)
    avail = int(disc.get("total_available") or 0)
    family = getattr(result, "transmission_family", None) or disc.get("family")
    part = getattr(result, "part_type", None) or disc.get("part_type")
    notes = ""
    if mode == "needs_review":
        notes = (getattr(result, "human_readable", None) or "")[:500]
    return record_counter_search(
        dms,
        query_text=getattr(result, "query", "") or "",
        search_mode=mode,
        search_id=search_id,
        request_id=getattr(result, "request_id", None),
        proposed_sku=getattr(result, "sku", None),
        transmission_family=family,
        part_category=part,
        candidate_count=cand,
        total_available=avail,
        elapsed_ms=getattr(result, "elapsed_ms", None),
        source=source,
        notes=notes,
    )


def _get_session(dms: DmsService, search_id: str) -> Any:
    row = dms.store.fetchone(
        "SELECT * FROM counter_search_sessions WHERE id = ?",
        (str(search_id).strip(),),
    )
    return row


def record_lot_selection(
    dms: DmsService,
    search_id: str,
    *,
    sku: str,
    location: str,
    action: str,
    quote_id: int | None = None,
    reservation_id: int | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Record ADD_TO_QUOTE / RESERVE on an inventory_matches session after business success."""
    act = (action or "").strip().upper()
    if act not in SELECTION_ACTIONS:
        raise ValueError(f"action must be one of {sorted(SELECTION_ACTIONS)}")
    sid = str(search_id).strip()
    row = _get_session(dms, sid)
    if row is None:
        raise LookupError(f"counter search session not found: {sid}")
    mode = str(row["search_mode"] or "")
    if mode != "inventory_matches":
        raise ValueError(
            f"lot selection only valid for inventory_matches (got {mode})"
        )

    sku_s = str(sku).strip()
    loc_s = str(location).strip()
    if not sku_s or not loc_s:
        raise ValueError("sku and location are required")

    # Validate SKU exists
    cat = dms.store.fetchone(
        "SELECT sku, transmission_family FROM catalog_parts WHERE sku = ?",
        (sku_s,),
    )
    if cat is None:
        raise ValueError(f"SKU not found: {sku_s}")

    # Validate location + inventory row
    try:
        lid = dms._location_id(loc_s)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    inv = dms.store.fetchone(
        "SELECT sku FROM inventory_levels WHERE sku = ? AND location_id = ?",
        (sku_s, lid),
    )
    if inv is None:
        raise ValueError(f"No inventory row for {sku_s} at {loc_s}")

    # Soft consistency with search family/category when stored
    fam_sess = (row["transmission_family"] or "").strip().upper()
    fam_sku = (cat["transmission_family"] or "").strip().upper()
    if fam_sess and fam_sku:
        # Allow workbook family groups loosely: same token or either contains other group
        from parrts.transmission.discovery import FAMILY_GROUPS

        allowed = set()
        for k, vals in FAMILY_GROUPS.items():
            if fam_sess == k or fam_sess in vals:
                allowed.update(vals)
                allowed.add(k)
        if not allowed:
            allowed = {fam_sess}
        if fam_sku not in allowed and fam_sku != fam_sess:
            raise ValueError(
                f"SKU family {fam_sku} inconsistent with search family {fam_sess}"
            )

    # Prefer location code for storage
    loc_row = dms.store.fetchone("SELECT code FROM locations WHERE id = ?", (lid,))
    loc_code = str(loc_row["code"]) if loc_row else loc_s

    already = bool(row["selected_sku"]) and bool(row["finalized_at"])
    dms.store.execute(
        """
        UPDATE counter_search_sessions SET
            selected_sku = ?,
            selected_location = ?,
            selected_action = ?,
            quote_id = COALESCE(?, quote_id),
            reservation_id = COALESCE(?, reservation_id),
            finalized_at = COALESCE(finalized_at, ?),
            notes = CASE
                WHEN ? != '' THEN trim(COALESCE(notes,'') || ' ' || ?)
                ELSE notes
            END
        WHERE id = ?
        """,
        (
            sku_s,
            loc_code,
            act,
            int(quote_id) if quote_id is not None else None,
            int(reservation_id) if reservation_id is not None else None,
            _utc_now(),
            str(notes or ""),
            str(notes or ""),
            sid,
        ),
    )
    dms.store.commit()
    return {
        "ok": True,
        "search_id": sid,
        "selected_sku": sku_s,
        "selected_location": loc_code,
        "selected_action": act,
        "finalized": True,
        "replaced_prior_selection": already,
    }


def finalize_session_from_uow_feedback(
    dms: DmsService,
    *,
    request_id: str,
    feedback_action: str,
) -> dict[str, Any]:
    """Mark exact/needs_review sessions finalized when UoW feedback is recorded.

    ACCEPT/CORRECT finalize exact_match; RESOLVE finalizes needs_review.
    inventory_matches rows are not finalized here.
    """
    rid = str(request_id or "").strip()
    if not rid:
        return {"ok": False, "error": "missing request_id", "updated": 0}
    act = (feedback_action or "").strip().lower()
    rows = dms.store.fetchall(
        """
        SELECT id, search_mode, finalized_at FROM counter_search_sessions
        WHERE request_id = ?
        """,
        (rid,),
    )
    updated = 0
    for r in rows:
        mode = str(r["search_mode"] or "")
        if mode == "inventory_matches":
            continue
        if mode == "exact_match" and act not in ("accept", "correct"):
            continue
        if mode == "needs_review" and act != "resolve":
            continue
        if r["finalized_at"]:
            continue
        dms.store.execute(
            """
            UPDATE counter_search_sessions
            SET finalized_at = ?, selected_action = ?
            WHERE id = ?
            """,
            (_utc_now(), act.upper(), str(r["id"])),
        )
        updated += 1
    if updated:
        dms.store.commit()
    return {"ok": True, "updated": updated, "request_id": rid, "feedback_action": act}


def list_sessions(
    dms: DmsService,
    *,
    source: str | None = "jp_real_pilot",
    finalized_only: bool = False,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM counter_search_sessions WHERE 1=1"
    params: list[Any] = []
    if source:
        sql += " AND source = ?"
        params.append(source)
    if finalized_only:
        sql += " AND finalized_at IS NOT NULL AND finalized_at != ''"
    sql += " ORDER BY created_at ASC, id ASC"
    rows = dms.store.fetchall(sql, tuple(params))
    return [dict(r) for r in rows]


def build_pilot_report(
    dms: DmsService,
    *,
    source: str = "jp_real_pilot",
    target_finalized: int = 50,
) -> dict[str, Any]:
    """Honest operational report. Never mixes discovery browse with resolver accuracy."""
    rows = list_sessions(dms, source=source, finalized_only=False)
    total = len(rows)
    finalized = [r for r in rows if r.get("finalized_at")]
    by_mode = {"exact_match": 0, "inventory_matches": 0, "needs_review": 0}
    for r in rows:
        m = r.get("search_mode") or ""
        if m in by_mode:
            by_mode[m] += 1

    exact = [r for r in rows if r.get("search_mode") == "exact_match"]
    needs = [r for r in rows if r.get("search_mode") == "needs_review"]
    disc = [r for r in rows if r.get("search_mode") == "inventory_matches"]

    def _act(r: dict[str, Any]) -> str:
        return str(r.get("selected_action") or "").upper()

    exact_accepted = sum(1 for r in exact if r.get("finalized_at") and _act(r) == "ACCEPT")
    exact_corrected = sum(1 for r in exact if r.get("finalized_at") and _act(r) == "CORRECT")
    exact_unfinal = sum(1 for r in exact if not r.get("finalized_at"))

    needs_resolved = sum(1 for r in needs if r.get("finalized_at") and _act(r) == "RESOLVE")
    needs_unresolved = sum(1 for r in needs if not r.get("finalized_at"))

    disc_selected = sum(1 for r in disc if r.get("finalized_at") and r.get("selected_sku"))
    disc_quote = sum(1 for r in disc if _act(r) == "ADD_TO_QUOTE")
    disc_reserve = sum(1 for r in disc if _act(r) == "RESERVE")
    disc_unselected = sum(1 for r in disc if not r.get("selected_sku"))

    n_fin = len(finalized)
    # Operational rates over all real searches of source (not only finalized)
    quote_n = sum(
        1
        for r in rows
        if _act(r) == "ADD_TO_QUOTE" or (r.get("quote_id") is not None and r.get("selected_sku"))
    )
    reserve_n = sum(
        1
        for r in rows
        if _act(r) == "RESERVE" or (r.get("reservation_id") is not None and r.get("selected_sku"))
    )
    # Also count exact path that later becomes quote outside telemetry — only selection-linked
    search_to_quote = (quote_n / total) if total else 0.0
    search_to_reserve = (reserve_n / total) if total else 0.0

    return {
        "source": source,
        "total_searches": total,
        "finalized_real_requests": n_fin,
        "target_finalized": target_finalized,
        "progress": f"{n_fin} / {target_finalized} finalized real requests",
        "by_mode": by_mode,
        "exact_path": {
            "total": len(exact),
            "accepted": exact_accepted,
            "corrected": exact_corrected,
            "unfinalized": exact_unfinal,
        },
        "needs_review_path": {
            "total": len(needs),
            "resolved": needs_resolved,
            "unresolved": needs_unresolved,
        },
        "discovery_path": {
            "total": len(disc),
            "lot_selected": disc_selected,
            "add_to_quote": disc_quote,
            "direct_reserve": disc_reserve,
            "unselected": disc_unselected,
            "note": "Discovery lot selection is operational usefulness, not resolver accuracy.",
        },
        "operational": {
            "search_to_quote_rate": round(search_to_quote, 4),
            "search_to_reserve_rate": round(search_to_reserve, 4),
        },
        "honesty": {
            "overall_accuracy_not_computed": True,
            "reason": "Do not mix inventory_matches browse with exact resolver truth.",
            "structured_catalog_part_type": False,
            "type_classification": "name + SKU convention (synthetic pilot)",
        },
    }


def sessions_to_csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        out.append(
            {
                "search_id": r.get("id"),
                "created_at": r.get("created_at"),
                "query_text": r.get("query_text"),
                "search_mode": r.get("search_mode"),
                "request_id": r.get("request_id") or "",
                "proposed_sku": r.get("proposed_sku") or "",
                "selected_sku": r.get("selected_sku") or "",
                "selected_location": r.get("selected_location") or "",
                "human_action": r.get("selected_action") or "",
                "family": r.get("transmission_family") or "",
                "part_category": r.get("part_category") or "",
                "candidate_count": r.get("candidate_count") or 0,
                "total_available": r.get("total_available") or 0,
                "finalized_at": r.get("finalized_at") or "",
                "source": r.get("source") or "",
                "quote_id": r.get("quote_id") or "",
                "reservation_id": r.get("reservation_id") or "",
            }
        )
    return out


def write_csv(path: str | Any, rows: list[dict[str, Any]]) -> None:
    import csv
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        fields = [
            "search_id",
            "created_at",
            "query_text",
            "search_mode",
            "request_id",
            "proposed_sku",
            "selected_sku",
            "selected_location",
            "human_action",
            "family",
            "part_category",
            "candidate_count",
            "total_available",
            "finalized_at",
            "source",
            "quote_id",
            "reservation_id",
        ]
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
        return
    fields = list(rows[0].keys())
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
