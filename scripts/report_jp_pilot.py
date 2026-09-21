#!/usr/bin/env python3
"""Report JP counter pilot telemetry from an isolated pilot root.

Only counts source=jp_real_pilot by default.
Does not invent overall accuracy across discovery + exact paths.

Usage:
  PYTHONPATH=src:backend python scripts/report_jp_pilot.py --root .pilot/jp
  PYTHONPATH=src:backend python scripts/report_jp_pilot.py --root .pilot/jp --csv /tmp/jp_pilot.csv
  PYTHONPATH=src:backend python scripts/report_jp_pilot.py --root .pilot/jp --source jp_demo
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="JP pilot counter telemetry report")
    ap.add_argument("--root", type=Path, required=True, help="Pilot PARRTS_ROOT")
    ap.add_argument(
        "--source",
        default="jp_real_pilot",
        help="Telemetry source filter (default jp_real_pilot)",
    )
    ap.add_argument("--csv", type=Path, default=None, help="Optional CSV export path")
    ap.add_argument("--target", type=int, default=50, help="Finalized target (default 50)")
    ap.add_argument("--json", action="store_true", help="Print full JSON report")
    args = ap.parse_args()

    root = args.root.expanduser().resolve()
    db = root / ".parrts" / "dms.db"
    if not db.is_file():
        print(f"ERROR: no DMS at {db}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(REPO / "src"))
    from parrts.dms.service import DmsService
    from parrts.transmission.counter_telemetry import (
        build_pilot_report,
        list_sessions,
        sessions_to_csv_rows,
        write_csv,
    )

    dms = DmsService(root)
    dms.ensure_schema()
    report = build_pilot_report(dms, source=args.source, target_finalized=args.target)
    rows = list_sessions(dms, source=args.source, finalized_only=False)

    if args.csv:
        write_csv(args.csv, sessions_to_csv_rows(rows))
        print(f"CSV: {args.csv.resolve()} ({len(rows)} rows)")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"source:              {report['source']}")
        print(f"total searches:      {report['total_searches']}")
        print(f"finalized:           {report['progress']}")
        print(f"modes:               {report['by_mode']}")
        print(f"exact path:          {report['exact_path']}")
        print(f"needs_review path:   {report['needs_review_path']}")
        print(f"discovery path:      {report['discovery_path']}")
        print(f"operational rates:   {report['operational']}")
        print(f"honesty:             {report['honesty']}")

    dms.store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
