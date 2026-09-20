"""Developer demo for PARTS transmission hard-parts vertical.

Usage:
    python -m parrts.transmission.demo
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from parrts.dms.service import DmsService
from .seed_loader import load_demo_seed
from .service import answer_transmission_inquiry


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
            "Do you have FAKE-IDENT-999?",
            "Do you have anything?",
        ]

        for q in queries:
            print(f"Query: {q}")
            answer = answer_transmission_inquiry(q, dms)
            print(f"  Status: {answer.status}")
            print(f"  SKU:    {answer.sku}")
            print(f"  Family: {answer.transmission_family}")
            print(f"  Part:   {answer.part_type}")
            print(f"  Available: {answer.inventory_available} (qty={answer.aggregate_available})")
            if answer.inventory:
                first = answer.inventory[0]
                print(f"  Location: {first.get('location')} / Bin: {first.get('bin')} ({first.get('condition')})")
            print(f"  Summary: {answer.human_readable}")
            print()


if __name__ == "__main__":
    run_demo()