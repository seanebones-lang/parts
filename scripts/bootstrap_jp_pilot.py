#!/usr/bin/env python3
"""Bootstrap an isolated JP pilot DMS root with baseline + 503-line synthetic inventory.

Does NOT touch the developer's default .parrts/dms.db.
Does NOT auto-run on app start.

Usage:
  PYTHONPATH=src:backend /tmp/phase4-integrated-venv/bin/python scripts/bootstrap_jp_pilot.py \\
    --root /path/to/repo/.pilot/jp --reset
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CSV_PATH = REPO / "data" / "jp_demo" / "jp_demo_inventory_seed.csv"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Bootstrap isolated JP pilot SQLite DMS")
    ap.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Pilot data root (e.g. <repo>/.pilot/jp). DMS lives at <root>/.parrts/dms.db",
    )
    ap.add_argument(
        "--reset",
        action="store_true",
        help="Allow overwrite of existing pilot DB (timestamped backup first)",
    )
    ap.add_argument(
        "--csv",
        type=Path,
        default=CSV_PATH,
        help="JP synthetic inventory CSV path",
    )
    args = ap.parse_args()
    root = args.root.expanduser().resolve()
    csv_path = args.csv.expanduser().resolve()
    if not csv_path.is_file():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        return 2

    db = root / ".parrts" / "dms.db"
    if db.exists() and not args.reset:
        # Refuse if already has catalog rows
        try:
            import sqlite3

            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            n = con.execute("SELECT COUNT(*) FROM catalog_parts").fetchone()[0]
            con.close()
            if n > 0:
                print(
                    f"ERROR: pilot DB already populated ({n} catalog rows) at {db}\n"
                    f"Pass --reset to backup and rebuild.",
                    file=sys.stderr,
                )
                return 3
        except Exception:
            print(
                f"ERROR: existing pilot DB at {db}; pass --reset to rebuild.",
                file=sys.stderr,
            )
            return 3

    if db.exists() and args.reset:
        bak = db.with_name(f"dms.db.bak.{_utc()}")
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db, bak)
        print(f"Backup: {bak}")
        db.unlink()
        auto = root / ".parrts" / "automation.db"
        if auto.exists():
            shutil.copy2(auto, auto.with_name(f"automation.db.bak.{_utc()}"))
            auto.unlink()

    root.mkdir(parents=True, exist_ok=True)
    (root / ".parrts").mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(REPO / "src"))
    sys.path.insert(0, str(REPO / "backend"))

    from parrts.dms.service import DmsService
    from parrts.transmission.seed_loader import load_demo_seed
    from parrts.transmission.importer import build_import_plan, commit_import_plan
    from parrts.transmission.counter_search import counter_search

    dms = DmsService(root)
    dms.ensure_schema()
    load_demo_seed(dms)

    text = csv_path.read_text(encoding="utf-8")
    plan = build_import_plan(text, dms, source="jp_demo_inventory", allow_new_locations=False)
    if plan.invalid_rows:
        print(f"ERROR: {plan.invalid_rows} invalid rows — refuse commit", file=sys.stderr)
        for r in plan.rows:
            if r.status == "invalid":
                print(f"  row {r.row_number}: {r.errors}", file=sys.stderr)
        return 4
    commit = commit_import_plan(plan, dms)
    if not getattr(commit, "committed", False):
        print(f"ERROR: commit failed: {getattr(commit, 'commit_result', commit)}", file=sys.stderr)
        return 5

    cat_n = int(dms.store.fetchone("SELECT COUNT(*) AS n FROM catalog_parts")["n"])
    inv_n = int(dms.store.fetchone("SELECT COUNT(*) AS n FROM inventory_levels")["n"])
    locs = dms.store.fetchall("SELECT code, name FROM locations ORDER BY code")
    loc_s = ", ".join(f"{r['code']}={r['name']}" for r in locs)

    print("=== JP pilot bootstrap OK ===")
    print(f"root: {root}")
    print(f"db:   {db}")
    print(f"catalog_parts: {cat_n}")
    print(f"inventory_levels: {inv_n}")
    print(f"locations: {loc_s}")
    cr = getattr(commit, "commit_result", None) or {}
    print(f"import: committed={commit.committed} run={cr.get('import_run_id')}")

    checks = [
        "4L60E valve body",
        "6R80 pump",
        "Need a 6L80 core",
        "6L80 torque converter",
        "10R80 core",
        "24264418",
        "6L80-PUMP-01",
        "6L80 or 6R80 pump which one?",
        "6L80 pump and valve body",
    ]
    print("--- representative counter_search ---")
    for q in checks:
        r = counter_search(q, dms)
        n = (r.discovery or {}).get("candidate_count", 0) if r.discovery else 0
        print(f"  {q!r} → {r.search_mode} n={n} sku={r.sku}")

    # Prove real pilot count is zero on fresh DB
    n_real = dms.store.fetchone(
        "SELECT COUNT(*) AS n FROM counter_search_sessions WHERE source = 'jp_real_pilot'"
    )
    print(f"jp_real_pilot sessions: {int(n_real['n']) if n_real else 0} (must be 0)")

    dms.store.close()

    print()
    print("=== startup (copy/paste) ===")
    print(f"export PARRTS_ROOT={root}")
    print("export PARRTS_VERTICAL=transmission")
    print("export JP_PILOT_MODE=real")
    print("export COUNTER_TELEMETRY_SOURCE=jp_real_pilot")
    print("export AUTH_MODE=demo ENVIRONMENT=development DEBUG=true JEV_DECISION_ENABLED=0")
    print(
        f"PYTHONPATH={REPO}/backend:{REPO}/src /tmp/phase4-integrated-venv/bin/python "
        f"-m uvicorn main:app --host 127.0.0.1 --port 8000 --app-dir {REPO}/backend"
    )
    print(
        f"cd {REPO}/frontend && NEXT_PUBLIC_DEMO_VERTICAL=transmission "
        f"NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 NEXT_PUBLIC_JP_PILOT_MODE=real "
        f"npm run dev -- -p 3000 -H 127.0.0.1"
    )
    print()
    print("Demo/test (do not contaminate real pilot):")
    print("  unset JP_PILOT_MODE; export COUNTER_TELEMETRY_SOURCE=jp_demo")
    print("  # or FE: NEXT_PUBLIC_JP_PILOT_MODE=demo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
