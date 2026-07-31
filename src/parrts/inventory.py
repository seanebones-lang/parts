"""Deterministic multi-location Chicago parts inventory."""

from __future__ import annotations

import json
import random
from pathlib import Path

from parrts.models import LocationInventory, PartRecord

# Default data root under CWD / project
DEFAULT_DATA_DIR = Path(".parrts")
INVENTORY_FILENAME = "inventory.json"

CHICAGO_LOCATIONS: list[str] = [
    "Chicago North",
    "O'Hare Auto",
    "Logan Square Motors",
    "Wrigley Dealership",
    "South Side Parts",
    "Loop Luxury Autos",
    "West Town Wheels",
]

# ~25 part type templates (make/model/year/category/base name/sku prefix/base price)
_PART_TEMPLATES: list[dict[str, str | float]] = [
    {
        "name": "Brake Pads 2019 Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2019",
        "category": "brakes",
        "sku_prefix": "BP-HC19",
        "price": 45.0,
        "description": "Ceramic front brake pads for 2019 Honda Civic",
    },
    {
        "name": "Brake Pads 2018 Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2018",
        "category": "brakes",
        "sku_prefix": "BP-HC18",
        "price": 42.0,
        "description": "Ceramic front brake pads for 2018 Honda Civic",
    },
    {
        "name": "Brake Rotors Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2018-2020",
        "category": "brakes",
        "sku_prefix": "BR-HC",
        "price": 75.0,
        "description": "Ventilated front brake rotors Honda Civic",
    },
    {
        "name": "Air Filter Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "filters",
        "sku_prefix": "AF-HC",
        "price": 18.0,
        "description": "Engine air filter Honda Civic",
    },
    {
        "name": "Oil Filter Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "filters",
        "sku_prefix": "OF-HC",
        "price": 12.0,
        "description": "Spin-on oil filter Honda Civic",
    },
    {
        "name": "Spark Plugs Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "ignition",
        "sku_prefix": "SP-HC",
        "price": 25.0,
        "description": "Iridium spark plugs set Honda Civic",
    },
    {
        "name": "Alternator 2018 Ford F-150",
        "make": "Ford",
        "model": "F-150",
        "year": "2018",
        "category": "electrical",
        "sku_prefix": "ALT-F150",
        "price": 120.0,
        "description": "Reman alternator 2018 Ford F-150",
    },
    {
        "name": "Brake Pads Ford F-150",
        "make": "Ford",
        "model": "F-150",
        "year": "2015-2020",
        "category": "brakes",
        "sku_prefix": "BP-F150",
        "price": 65.0,
        "description": "Heavy-duty brake pads Ford F-150",
    },
    {
        "name": "Oil Filter Ford F-150",
        "make": "Ford",
        "model": "F-150",
        "year": "2015-2020",
        "category": "filters",
        "sku_prefix": "OF-F150",
        "price": 14.0,
        "description": "Oil filter Ford F-150",
    },
    {
        "name": "Oil Filter Toyota Camry",
        "make": "Toyota",
        "model": "Camry",
        "year": "2018-2022",
        "category": "filters",
        "sku_prefix": "OF-TC",
        "price": 12.0,
        "description": "Oil filter Toyota Camry",
    },
    {
        "name": "Brake Pads Toyota Camry",
        "make": "Toyota",
        "model": "Camry",
        "year": "2018-2022",
        "category": "brakes",
        "sku_prefix": "BP-TC",
        "price": 38.0,
        "description": "Ceramic brake pads Toyota Camry",
    },
    {
        "name": "Alternator Toyota Camry",
        "make": "Toyota",
        "model": "Camry",
        "year": "2018-2022",
        "category": "electrical",
        "sku_prefix": "ALT-TC",
        "price": 95.0,
        "description": "Alternator Toyota Camry",
    },
    {
        "name": "Turbocharger 1998 Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "1998",
        "category": "performance",
        "sku_prefix": "TURBO-HC98",
        "price": 350.0,
        "description": "Aftermarket turbocharger kit 1998 Honda Civic",
    },
    {
        "name": "Exhaust System Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "exhaust",
        "sku_prefix": "EX-HC",
        "price": 180.0,
        "description": "Cat-back exhaust system Honda Civic",
    },
    {
        "name": "Transmission Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2019",
        "category": "drivetrain",
        "sku_prefix": "TR-HC",
        "price": 450.0,
        "description": "Reman CVT transmission Honda Civic",
    },
    {
        "name": "Wheel Bearings Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "suspension",
        "sku_prefix": "WB-HC",
        "price": 85.0,
        "description": "Front wheel bearing hub Honda Civic",
    },
    {
        "name": "Shock Absorbers Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "suspension",
        "sku_prefix": "SA-HC",
        "price": 120.0,
        "description": "Front shock absorbers pair Honda Civic",
    },
    {
        "name": "Clutch Kit Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "drivetrain",
        "sku_prefix": "CK-HC",
        "price": 280.0,
        "description": "Complete clutch kit manual Honda Civic",
    },
    {
        "name": "Premium Brake Pads BMW 3 Series",
        "make": "BMW",
        "model": "3 Series",
        "year": "2019-2023",
        "category": "brakes",
        "sku_prefix": "PBP-BMW3",
        "price": 180.0,
        "description": "Premium ceramic brake pads BMW 3 Series",
    },
    {
        "name": "Luxury Air Filter BMW 3 Series",
        "make": "BMW",
        "model": "3 Series",
        "year": "2019-2023",
        "category": "filters",
        "sku_prefix": "LAF-BMW3",
        "price": 45.0,
        "description": "Cabin and engine air filter set BMW 3 Series",
    },
    {
        "name": "Performance Exhaust BMW 3 Series",
        "make": "BMW",
        "model": "3 Series",
        "year": "2019-2023",
        "category": "exhaust",
        "sku_prefix": "PE-BMW3",
        "price": 850.0,
        "description": "Performance exhaust system BMW 3 Series",
    },
    {
        "name": "Alloy Wheels Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "wheels",
        "sku_prefix": "AW-HC",
        "price": 320.0,
        "description": "17-inch alloy wheel set Honda Civic",
    },
    {
        "name": "Winter Tires Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "tires",
        "sku_prefix": "WT-HC",
        "price": 180.0,
        "description": "Winter tire set Honda Civic",
    },
    {
        "name": "Cabin Filter Toyota Camry",
        "make": "Toyota",
        "model": "Camry",
        "year": "2018-2022",
        "category": "filters",
        "sku_prefix": "CF-TC",
        "price": 16.0,
        "description": "Cabin air filter Toyota Camry",
    },
    {
        "name": "Battery Ford F-150",
        "make": "Ford",
        "model": "F-150",
        "year": "2015-2020",
        "category": "electrical",
        "sku_prefix": "BAT-F150",
        "price": 140.0,
        "description": "AGM battery Ford F-150",
    },
    {
        "name": "Front Brake Rotors 2018 Ford F-150",
        "make": "Ford",
        "model": "F-150",
        "year": "2018",
        "category": "brakes",
        "sku_prefix": "BR-F150",
        "price": 95.0,
        "description": "OEM front brake rotors 2018 Ford F-150",
    },
    {
        "name": "Cabin Air Filter Honda Accord",
        "make": "Honda",
        "model": "Accord",
        "year": "2018-2022",
        "category": "filters",
        "sku_prefix": "CAF-HA",
        "price": 19.0,
        "description": "Cabin air filter Honda Accord OEM style",
    },
    {
        "name": "Wiper Blades 22 Inch Universal",
        "make": "Universal",
        "model": "Universal",
        "year": "any",
        "category": "exterior",
        "sku_prefix": "WB-22",
        "price": 24.0,
        "description": "22 inch beam wiper blades pair universal fit",
    },
    {
        "name": "Serpentine Belt Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "engine",
        "sku_prefix": "SB-HC",
        "price": 32.0,
        "description": "Drive belt serpentine belt Honda Civic Gates style",
    },
    {
        "name": "Coolant Thermostat Toyota Camry",
        "make": "Toyota",
        "model": "Camry",
        "year": "2018-2022",
        "category": "cooling",
        "sku_prefix": "CT-TC",
        "price": 38.0,
        "description": "Engine coolant thermostat Toyota Camry",
    },
    {
        "name": "Headlight Bulb H11 Universal",
        "make": "Universal",
        "model": "Universal",
        "year": "any",
        "category": "electrical",
        "sku_prefix": "HL-H11",
        "price": 22.0,
        "description": "Headlight bulb H11 halogen/LED compatible universal",
    },
    {
        "name": "Brake Fluid DOT 4",
        "make": "Universal",
        "model": "Universal",
        "year": "any",
        "category": "fluids",
        "sku_prefix": "BF-DOT4",
        "price": 12.0,
        "description": "Brake fluid DOT 4 1 quart bottle",
    },
    {
        "name": "Tire 225/60R16 Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "tires",
        "sku_prefix": "TR-22560",
        "price": 145.0,
        "description": "All-season tire 225/60R16 Honda Civic fitment",
    },
    {
        "name": "Battery Group 51R Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "electrical",
        "sku_prefix": "BAT-51R",
        "price": 165.0,
        "description": "Group 51R AGM battery Honda Civic",
    },
    {
        "name": "Spark Plugs NGK Honda Civic",
        "make": "Honda",
        "model": "Civic",
        "year": "2016-2021",
        "category": "ignition",
        "sku_prefix": "SP-NGK-HC",
        "price": 28.0,
        "description": "NGK iridium spark plugs set Honda Civic",
    },
]


def data_dir(root: Path | str | None = None) -> Path:
    base = Path(root) if root is not None else Path.cwd()
    return base / ".parrts"


def inventory_path(root: Path | str | None = None) -> Path:
    return data_dir(root) / INVENTORY_FILENAME


def generate_catalog(seed: int = 42) -> LocationInventory:
    """Build ~25 part types × 7 locations with deterministic stock levels."""
    rng = random.Random(seed)
    locations: dict[str, list[PartRecord]] = {loc: [] for loc in CHICAGO_LOCATIONS}

    for loc_idx, location in enumerate(CHICAGO_LOCATIONS):
        for tmpl in _PART_TEMPLATES:
            # Deterministic but varied stock: some zeros, some low, some healthy
            roll = rng.randint(0, 20)
            if roll == 0:
                stock = 0
            elif roll <= 3:
                stock = rng.randint(1, 2)
            else:
                stock = rng.randint(3, 18)

            # Luxury location skews BMW higher stock; South Side Civic focus
            if location == "Loop Luxury Autos" and tmpl["make"] == "BMW":
                stock = max(stock, rng.randint(2, 8))
            if location == "Wrigley Dealership" and "Turbo" in str(tmpl["name"]):
                stock = 0  # classic out-of-stock demo case

            sku = f"{tmpl['sku_prefix']}-L{loc_idx + 1}"
            # Slight price variance by location
            price = float(tmpl["price"]) * (1.0 + (loc_idx - 3) * 0.02)
            price = round(price, 2)

            part = PartRecord(
                sku=sku,
                name=str(tmpl["name"]),
                location=location,
                stock=stock,
                price=price,
                description=str(tmpl["description"]),
                make=str(tmpl["make"]),
                model=str(tmpl["model"]),
                year=str(tmpl["year"]),
                category=str(tmpl["category"]),
            )
            locations[location].append(part)

    return LocationInventory(locations=locations)


def save_inventory(
    inventory: LocationInventory,
    root: Path | str | None = None,
    path: Path | str | None = None,
) -> Path:
    out = Path(path) if path is not None else inventory_path(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(inventory.to_dict(), f, indent=2, ensure_ascii=False)
    return out


def load_inventory(
    root: Path | str | None = None,
    path: Path | str | None = None,
) -> LocationInventory:
    src = Path(path) if path is not None else inventory_path(root)
    with src.open(encoding="utf-8") as f:
        data = json.load(f)
    return LocationInventory.from_dict(data)


def ensure_inventory(
    root: Path | str | None = None,
    seed: int = 42,
    force: bool = False,
) -> LocationInventory:
    """Load existing inventory JSON or generate + save a seed catalog."""
    path = inventory_path(root)
    if path.exists() and not force:
        return load_inventory(path=path)
    inv = generate_catalog(seed=seed)
    save_inventory(inv, path=path)
    return inv
