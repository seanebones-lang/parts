"""Synthetic demo seed data for transmission hard parts (PARTS project).

All records are clearly marked as demo / unverified.
This is not an authoritative interchange catalog.
"""
from __future__ import annotations

DEMO_TRANSMISSION_FAMILIES = [
    {"family": "6L80", "manufacturer": "GM", "notes": "6-speed automatic (RWD/AWD)"},
    {"family": "6L90", "manufacturer": "GM", "notes": "Heavy-duty variant of 6L80"},
    {"family": "4L60E", "manufacturer": "GM", "notes": "4-speed automatic"},
    {"family": "4L80E", "manufacturer": "GM", "notes": "Heavy-duty 4-speed"},
    {"family": "6R80", "manufacturer": "Ford", "notes": "6-speed automatic"},
    {"family": "10R80", "manufacturer": "Ford", "notes": "10-speed automatic"},
    {"family": "8HP70", "manufacturer": "ZF", "notes": "8-speed automatic (Chrysler applications)"},
]

DEMO_CATALOG_PARTS = [
    # Core 6L80 example (preserve accepted behavior)
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
    # 4L60E family
    {
        "sku": "4L60E-PUMP-01",
        "name": "4L60E Pump Assembly",
        "description": "Standard pump for 4L60E",
        "transmission_family": "4L60E",
        "transmission_variant": "4L60E",
        "category": "transmission_hard_parts",
        "oem_brand": "GM",
        "list_price": 195.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
    {
        "sku": "4L60E-VB-01",
        "name": "4L60E Valve Body",
        "description": "Valve body for 4L60E",
        "transmission_family": "4L60E",
        "transmission_variant": "4L60E",
        "category": "transmission_hard_parts",
        "oem_brand": "GM",
        "list_price": 310.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
    # 4L80E family
    {
        "sku": "4L80E-DRUM-01",
        "name": "4L80E Input Drum",
        "description": "Input drum assembly",
        "transmission_family": "4L80E",
        "transmission_variant": "4L80E",
        "category": "transmission_hard_parts",
        "oem_brand": "GM",
        "list_price": 265.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
    # Ford 6R80
    {
        "sku": "6R80-PUMP-01",
        "name": "6R80 Pump Assembly",
        "description": "Ford 6R80 pump",
        "transmission_family": "6R80",
        "transmission_variant": "6R80",
        "category": "transmission_hard_parts",
        "oem_brand": "Ford",
        "list_price": 275.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
    {
        "sku": "6R80-VB-01",
        "name": "6R80 Valve Body",
        "description": "6R80 valve body",
        "transmission_family": "6R80",
        "transmission_variant": "6R80",
        "category": "transmission_hard_parts",
        "oem_brand": "Ford",
        "list_price": 390.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
    # Ford 10R80
    {
        "sku": "10R80-DRUM-01",
        "name": "10R80 Reaction Drum",
        "description": "Reaction drum for 10R80",
        "transmission_family": "10R80",
        "transmission_variant": "10R80",
        "category": "transmission_hard_parts",
        "oem_brand": "Ford",
        "list_price": 340.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
    # ZF 8HP70
    {
        "sku": "8HP70-VB-01",
        "name": "8HP70 Valve Body",
        "description": "ZF 8-speed valve body",
        "transmission_family": "8HP70",
        "transmission_variant": "8HP70",
        "category": "transmission_hard_parts",
        "oem_brand": "ZF",
        "list_price": 475.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
    {
        "sku": "8HP70-PUMP-01",
        "name": "8HP70 Pump",
        "description": "ZF 8HP pump assembly",
        "transmission_family": "8HP70",
        "transmission_variant": "8HP70",
        "category": "transmission_hard_parts",
        "oem_brand": "ZF",
        "list_price": 295.00,
        "source": "demo_seed",
        "verification_status": "unverified",
    },
]

DEMO_IDENTIFIERS = [
    # 6L80-PUMP-01 (preserve accepted identifier)
    {"sku": "6L80-PUMP-01", "identifier_type": "oem", "identifier_value": "24264418"},
    {"sku": "6L80-PUMP-01", "identifier_type": "casting", "identifier_value": "24264418"},
    # Additional realistic demo identifiers
    {"sku": "6L80-VB-01", "identifier_type": "oem", "identifier_value": "24264419"},
    {"sku": "6L90-PUMP-01", "identifier_type": "oem", "identifier_value": "24264420"},
    {"sku": "4L60E-PUMP-01", "identifier_type": "casting", "identifier_value": "4L60E-867"},
    {"sku": "6R80-PUMP-01", "identifier_type": "oem", "identifier_value": "6R80-P-01"},
    {"sku": "10R80-DRUM-01", "identifier_type": "casting", "identifier_value": "10R80-RD-01"},
    {"sku": "8HP70-VB-01", "identifier_type": "oem", "identifier_value": "8HP70-VB-01"},
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
    {
        "source_sku": "6L90-PUMP-01",
        "target_sku": "6L80-PUMP-01",
        "relationship_type": "interchangeable",
        "confidence": 0.60,
        "notes": "Demo data - not verified",
        "verification_status": "unverified",
    },
]

DEMO_FITMENTS = [
    # Preserve the canonical 6L80-PUMP-01 fitment
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
    # Additional demo fitments
    {
        "sku": "4L60E-PUMP-01",
        "year_from": 1993,
        "year_to": 2007,
        "make": "Chevrolet",
        "model": "Silverado",
        "engine": "5.7L",
        "transmission_family": "4L60E",
        "verification_status": "unverified",
    },
    {
        "sku": "6R80-PUMP-01",
        "year_from": 2009,
        "year_to": 2014,
        "make": "Ford",
        "model": "F-150",
        "engine": "5.0L",
        "transmission_family": "6R80",
        "verification_status": "unverified",
    },
]

DEMO_INVENTORY = [
    # 6L80-PUMP-01 (preserve accepted inventory)
    {"sku": "6L80-PUMP-01", "location": "CHI-N", "qty": 3, "condition": "new", "bin": "A-01"},
    {"sku": "6L80-PUMP-01", "location": "OHARE", "qty": 0, "condition": "new", "bin": "B-03"},
    # Additional inventory variety
    {"sku": "6L80-VB-01", "location": "CHI-N", "qty": 1, "condition": "rebuilt", "bin": "A-02"},
    {"sku": "6L90-PUMP-01", "location": "OHARE", "qty": 2, "condition": "new", "bin": "C-01"},
    {"sku": "4L60E-PUMP-01", "location": "CHI-N", "qty": 5, "condition": "new", "bin": "D-01"},
    {"sku": "4L60E-VB-01", "location": "OHARE", "qty": 0, "condition": "used", "bin": "E-02"},
    {"sku": "6R80-PUMP-01", "location": "CHI-N", "qty": 4, "condition": "new", "bin": "F-01"},
    {"sku": "10R80-DRUM-01", "location": "OHARE", "qty": 1, "condition": "rebuilt", "bin": "G-03"},
    {"sku": "8HP70-VB-01", "location": "CHI-N", "qty": 2, "condition": "new", "bin": "H-01"},
    {"sku": "8HP70-PUMP-01", "location": "OHARE", "qty": 0, "condition": "core", "bin": "I-04"},
]