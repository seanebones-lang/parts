"""Developer demo for PARTS transmission hard-parts vertical.

Usage:
    python -m parrts.transmission.demo
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from parrts.dms.service import DmsService
from .seed_loader import load_demo_seed
from .resolver import resolve_inquiry


def run_demo():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        dms = DmsService(root)
        dms.ensure_schema()

        print("Seeding demo data...")
        counts = load_demo_seed(dms)
        print(f"Seed counts: {counts}\n")

        queries = [
            "Do you have a pump for a 2011 Tahoe 6L80?",
            "Do you have 24264418?",
            "Do you have a valve body for a 6L90?",
            "Do you have anything for a 2025 F-150 10R80?",
            "Do you have a pump for a 2011 Tahoe 6L80 that is used?",
        ]

        for q in queries:
            print(f"Query: {q}")
            result = resolve_inquiry(q, dms)
            print(f"  Family: {result.transmission_family}")
            print(f"  Part:   {result.part_type}")
            print(f"  SKUs:   {result.matched_skus}")
            print(f"  Fitment:{result.fitment_status}")
            print(f"  Stock:  {result.inventory_available}")
            print(f"  Notes:  {result.notes}")
            print(f"  Aliases:{result.aliases_found}")
            print(f"  Interchange: {result.interchange_candidates}")
            print(f"  Uncertainty: {result.uncertainty}")
            print()


if __name__ == "__main__":
    run_demo()