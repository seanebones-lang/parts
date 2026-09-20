"""Synthetic demo seed data for 6L80 / 6L90 transmission hard parts.

All records are clearly marked as demo / unverified.
This is not an authoritative interchange catalog.
"""
from __future__ import annotations

DEMO_TRANSMISSION_FAMILIES = [
    {"family": "6L80", "manufacturer": "GM", "notes": "6-speed automatic (RWD/AWD)"},
    {"family": "6L90", "manufacturer": "GM", "notes": "Heavy-duty variant of 6L80"},
]

DEMO_CATALOG_PARTS = [
    {
        "sku": "6L80-PUMP-01",
        "name": "6L80 Transmission Pump Assembly",
        "description": "OEM-style pump for 6L80/6L90",
        "transmission_family": "6L80",
        "transmission_variant": "6L80",
        "category": "transmission_hard_parts",
        "oem_brand": "GM",
        "list_price": 289.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
    {
        "sku": "6L80-VB-01",
        "name": "6L80 Valve Body",
        "description": "Complete valve body assembly",
        "transmission_family": "6L80",
        "transmission_variant": "6L80",
        "category": "transmission_hard_parts",
        "oem_brand": "GM",
        "list_price": 425.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
    {
        "sku": "6L90-PUMP-01",
        "name": "6L90 Heavy Duty Pump",
        "description": "Heavy-duty pump for 6L90",
        "transmission_family": "6L90",
        "transmission_variant": "6L90",
        "category": "transmission_hard_parts",
        "oem_brand": "GM",
        "list_price": 319.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
]

DEMO_IDENTIFIERS = [
    {"sku": "6L80-PUMP-01", "identifier_type": "oem", "identifier_value": "24264418"},
    {"sku": "6L80-PUMP-01", "identifier_type": "casting", "identifier_value": "24264418"},
    {"sku": "6L80-VB-01", "identifier_type": "oem", "identifier_value": "24264419"},
    {"sku": "6L90-PUMP-01", "identifier_type": "oem", "identifier_value": "24264420"},
]

DEMO_INTERCHANGES = [
    {
        "source_sku": "6L80-PUMP-01",
        "target_sku": "6L90-PUMP-01",
        "relationship_type": "interchangeable",
        "confidence": 0.65,
        "notes": "Demo data - not verified",
        "verification_status": "unverified",
    },
]

DEMO_FITMENTS = [
    {
        "sku": "6L80-PUMP-01",
        "year_from": 2007,
        "year_to": 2014,
        "make": "Chevrolet",
        "model": "Tahoe",
        "engine": "5.3L",
        "transmission_family": "6L80",
        "verification_status": "unverified",
    },
    {
        "sku": "6L80-PUMP-01",
        "year_from": 2007,
        "year_to": 2014,
        "make": "GMC",
        "model": "Yukon",
        "engine": "5.3L",
        "transmission_family": "6L80",
        "verification_status": "unverified",
    },
]

DEMO_INVENTORY = [
    {"sku": "6L80-PUMP-01", "location": "Chicago-01", "qty": 3, "condition": "new"},
    {"sku": "6L80-PUMP-01", "location": "Dallas-02", "qty": 0, "condition": "new"},
    {"sku": "6L80-VB-01", "location": "Chicago-01", "qty": 1, "condition": "rebuilt"},
    {"sku": "6L90-PUMP-01", "location": "Dallas-02", "qty": 2, "condition": "new"},
]