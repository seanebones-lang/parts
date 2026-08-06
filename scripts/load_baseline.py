#!/usr/bin/env python3
"""Offline load baseline for Parts core paths (no live dealer traffic).

Measures sequential timings for:
  - hybrid RAG query (hash embedder)
  - DMS seed + list inventory
  - order create
  - email process
  - automation results

Writes docs/LOAD_BASELINE.md and .parrts/load_baseline_last.json
Exit 0 always when measurements complete (honest numbers, not SLAs).
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000.0, 2)


def main() -> int:
    work = ROOT / ".parrts" / "load_baseline_work"
    if work.exists():
        import shutil

        shutil.rmtree(work)
    work.mkdir(parents=True)

    results: dict = {
        "ok": True,
        "measured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "host_note": "local offline baseline — not production SLA",
        "samples": {},
        "summary_ms": {},
    }

    from parrts.automation import AutomationService
    from parrts.dms.service import DmsService
    from parrts.email import EmailService
    from parrts.embeddings import HashingEmbedder
    from parrts.engine import PartsRAGEngine

    # --- DMS seed ---
    dms = DmsService(root=work)
    t0 = time.perf_counter()
    dms.seed_demo(n_skus=40, locations=5)
    results["samples"]["dms_seed_ms"] = _ms(t0)

    t0 = time.perf_counter()
    inv = dms.list_inventory()
    results["samples"]["dms_list_inventory_ms"] = _ms(t0)
    results["samples"]["inventory_rows"] = len(inv)

    # --- RAG ---
    eng = PartsRAGEngine(root=work, embedder=HashingEmbedder())
    t0 = time.perf_counter()
    eng.build(force_inventory=True)
    results["samples"]["rag_build_ms"] = _ms(t0)

    queries = [
        "brake pads honda civic",
        "oil filter camry",
        "alternator",
        "cabin filter",
        "coolant thermostat",
    ]
    q_ms = []
    for q in queries:
        t0 = time.perf_counter()
        eng.query(text=q, top_k=5, use_llm=False)
        q_ms.append(_ms(t0))
    results["samples"]["query_ms"] = q_ms
    results["summary_ms"]["query_p50"] = round(statistics.median(q_ms), 2)
    results["summary_ms"]["query_p95"] = round(sorted(q_ms)[max(0, int(len(q_ms) * 0.95) - 1)], 2)
    results["summary_ms"]["query_mean"] = round(statistics.mean(q_ms), 2)

    # --- Orders ---
    cust = dms.create_customer(name="Load Baseline", email="load@example.com")
    row = next(r for r in inv if int(r["qty"]) >= 1)
    o_ms = []
    for _ in range(5):
        t0 = time.perf_counter()
        dms.create_order(
            customer_id=int(cust["id"]),
            lines=[{"sku": row["sku"], "location_id": row["location_id"], "qty": 1}],
        )
        # refresh stock pick if depleted
        row = next((r for r in dms.list_inventory() if int(r["qty"]) >= 1), row)
        o_ms.append(_ms(t0))
    results["samples"]["order_create_ms"] = o_ms
    results["summary_ms"]["order_create_mean"] = round(statistics.mean(o_ms), 2)

    # --- Email + automation ---
    email = EmailService(root=work)
    t0 = time.perf_counter()
    email.seed_demo(clear=True, process=True)
    results["samples"]["email_seed_process_ms"] = _ms(t0)
    auto = AutomationService(work)
    t0 = time.perf_counter()
    summary = auto.results_summary(limit_runs=20)
    results["samples"]["automation_results_ms"] = _ms(t0)
    results["samples"]["automation_total_runs"] = summary.get("total_runs")

    # notify dry-run
    from parrts.notify import NotifyService

    orders = dms.list_orders()
    if orders:
        n = NotifyService(root=work, dms=dms)
        t0 = time.perf_counter()
        n.notify_order(int(orders[0]["id"]), dry_run=True)
        results["samples"]["notify_dry_run_ms"] = _ms(t0)

    out_json = ROOT / ".parrts" / "load_baseline_last.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    md = ROOT / "docs" / "LOAD_BASELINE.md"
    lines = [
        "# Parts — Load baseline (offline)",
        "",
        f"**Measured:** `{results['measured_at']}`  ",
        f"**Note:** {results['host_note']}",
        "",
        "Re-run:",
        "```bash",
        "python scripts/load_baseline.py",
        "```",
        "",
        "## Summary (ms)",
        "",
        "| Metric | ms |",
        "|--------|---:|",
    ]
    for k, v in sorted(results["summary_ms"].items()):
        lines.append(f"| `{k}` | {v} |")
    lines += [
        "",
        "## Samples",
        "",
        "```json",
        json.dumps(results["samples"], indent=2),
        "```",
        "",
        "Not a multi-user load test. Partner OEM / HA still gated.",
        "",
    ]
    md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(out_json), "md": str(md), **results["summary_ms"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
