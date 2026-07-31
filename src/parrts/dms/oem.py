"""OEM feed adapters — protocol + synthetic / file / HTTP sources."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any, Iterable, Iterator, Protocol, runtime_checkable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Match core inventory location set (7 Chicago dealerships).
DEFAULT_LOCATION_CODES: list[tuple[str, str]] = [
    ("CHI-N", "Chicago North"),
    ("OHARE", "O'Hare Auto"),
    ("LOGAN", "Logan Square Motors"),
    ("WRIG", "Wrigley Dealership"),
    ("SOUTH", "South Side Parts"),
    ("LOOP", "Loop Luxury Autos"),
    ("WEST", "West Town Wheels"),
]

_PART_SEEDS: list[dict[str, Any]] = [
    {"name": "Brake Pads Front", "make": "Honda", "model": "Civic", "year": "2019", "category": "brakes", "prefix": "OEM-BP-HC19"},
    {"name": "Brake Pads Rear", "make": "Honda", "model": "Civic", "year": "2019", "category": "brakes", "prefix": "OEM-BP-HC19R"},
    {"name": "Brake Rotor Front", "make": "Honda", "model": "Civic", "year": "2018-2020", "category": "brakes", "prefix": "OEM-BR-HC"},
    {"name": "Air Filter", "make": "Honda", "model": "Civic", "year": "2016-2021", "category": "filters", "prefix": "OEM-AF-HC"},
    {"name": "Oil Filter", "make": "Honda", "model": "Civic", "year": "2016-2021", "category": "filters", "prefix": "OEM-OF-HC"},
    {"name": "Cabin Air Filter", "make": "Honda", "model": "Accord", "year": "2018-2022", "category": "filters", "prefix": "OEM-CAF-HA"},
    {"name": "Spark Plugs Iridium", "make": "Honda", "model": "Civic", "year": "2016-2021", "category": "ignition", "prefix": "OEM-SP-HC"},
    {"name": "Alternator", "make": "Ford", "model": "F-150", "year": "2018", "category": "electrical", "prefix": "OEM-ALT-F150"},
    {"name": "Brake Pads HD", "make": "Ford", "model": "F-150", "year": "2015-2020", "category": "brakes", "prefix": "OEM-BP-F150"},
    {"name": "Oil Filter", "make": "Ford", "model": "F-150", "year": "2015-2020", "category": "filters", "prefix": "OEM-OF-F150"},
    {"name": "Serpentine Belt", "make": "Ford", "model": "F-150", "year": "2015-2020", "category": "belts", "prefix": "OEM-SB-F150"},
    {"name": "Brake Pads Ceramic", "make": "Toyota", "model": "Camry", "year": "2018-2022", "category": "brakes", "prefix": "OEM-BP-TC"},
    {"name": "Oil Filter", "make": "Toyota", "model": "Camry", "year": "2018-2022", "category": "filters", "prefix": "OEM-OF-TC"},
    {"name": "Alternator", "make": "Toyota", "model": "Camry", "year": "2018-2022", "category": "electrical", "prefix": "OEM-ALT-TC"},
    {"name": "Coolant Thermostat", "make": "Toyota", "model": "Camry", "year": "2018-2022", "category": "cooling", "prefix": "OEM-TH-TC"},
    {"name": "Water Pump", "make": "Toyota", "model": "Camry", "year": "2018-2022", "category": "cooling", "prefix": "OEM-WP-TC"},
    {"name": "Brake Pads M Performance", "make": "BMW", "model": "3 Series", "year": "2019-2022", "category": "brakes", "prefix": "OEM-BP-BMW3"},
    {"name": "Oil Filter", "make": "BMW", "model": "3 Series", "year": "2019-2022", "category": "filters", "prefix": "OEM-OF-BMW3"},
    {"name": "Cabin Filter", "make": "BMW", "model": "5 Series", "year": "2017-2023", "category": "filters", "prefix": "OEM-CAF-BMW5"},
    {"name": "Battery AGM", "make": "Honda", "model": "Civic", "year": "2016-2021", "category": "electrical", "prefix": "OEM-BAT-HC"},
]


@runtime_checkable
class OemFeed(Protocol):
    """Yields part dicts for DMS catalog/inventory upsert."""

    def iter_parts(self) -> Iterable[dict[str, Any]]:
        """
        Yield dicts with keys:
          sku, name, description, make, model, year, category, oem_brand,
          list_price, msrp, and optional location_qty: {location_code: qty}.
        """
        ...


def _normalize_part(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize heterogeneous feed rows to the canonical part shape."""
    sku = str(raw.get("sku") or raw.get("SKU") or "").strip()
    if not sku:
        raise ValueError(f"OEM part missing sku: {raw!r}")

    location_qty: dict[str, int] = {}
    lq = raw.get("location_qty") or raw.get("location_qty_map") or raw.get("qty_by_location")
    if isinstance(lq, dict):
        location_qty = {str(k): int(v) for k, v in lq.items()}
    # Flat CSV-style qty columns: qty_CHI-N, qty_OHARE, ...
    for k, v in raw.items():
        key = str(k)
        if key.startswith("qty_") and v not in (None, ""):
            location_qty[key[4:]] = int(float(v))
        elif key.startswith("location_qty.") and v not in (None, ""):
            location_qty[key.split(".", 1)[1]] = int(float(v))

    list_price = float(raw.get("list_price") or raw.get("price") or 0 or 0)
    msrp = float(raw.get("msrp") or list_price or 0)

    name = str(raw.get("name") or raw.get("part_name") or sku)
    make = str(raw.get("make") or "")
    model = str(raw.get("model") or "")
    year = str(raw.get("year") or "")
    description = str(raw.get("description") or f"{name} {make} {model} {year}".strip())

    return {
        "sku": sku,
        "name": name,
        "description": description,
        "make": make,
        "model": model,
        "year": year,
        "category": str(raw.get("category") or ""),
        "oem_brand": str(raw.get("oem_brand") or raw.get("brand") or make or "OEM"),
        "list_price": list_price,
        "msrp": msrp,
        "location_qty": location_qty,
    }


class SyntheticOemFeed:
    """Deterministic synthetic OEM catalog for demos and offline tests."""

    def __init__(
        self,
        seed: int = 42,
        n_skus: int = 40,
        locations: int = 7,
    ) -> None:
        self.seed = seed
        self.n_skus = n_skus
        self.locations = max(1, min(locations, len(DEFAULT_LOCATION_CODES)))

    def iter_parts(self) -> Iterator[dict[str, Any]]:
        rng = random.Random(self.seed)
        loc_codes = [c for c, _ in DEFAULT_LOCATION_CODES[: self.locations]]
        for i in range(self.n_skus):
            base = _PART_SEEDS[i % len(_PART_SEEDS)]
            variant = (i // len(_PART_SEEDS)) + 1
            sku = f"{base['prefix']}-S{variant:02d}" if variant > 1 else f"{base['prefix']}-S01"
            # Ensure unique SKUs when n_skus > len seeds
            if i >= len(_PART_SEEDS):
                sku = f"{base['prefix']}-S{i + 1:02d}"
            list_price = round(20.0 + rng.random() * 180.0, 2)
            msrp = round(list_price * (1.05 + rng.random() * 0.15), 2)
            location_qty: dict[str, int] = {}
            for code in loc_codes:
                roll = rng.randint(0, 20)
                if roll == 0:
                    qty = 0
                elif roll <= 3:
                    qty = rng.randint(1, 2)
                else:
                    qty = rng.randint(3, 20)
                location_qty[code] = qty
            name = str(base["name"])
            make = str(base["make"])
            model = str(base["model"])
            year = str(base["year"])
            yield {
                "sku": sku,
                "name": f"{name} {year} {make} {model}".strip(),
                "description": f"OEM {name} for {year} {make} {model}",
                "make": make,
                "model": model,
                "year": year,
                "category": str(base["category"]),
                "oem_brand": make,
                "list_price": list_price,
                "msrp": msrp,
                "location_qty": location_qty,
            }


class FileOemFeed:
    """Load OEM parts from a JSON list or CSV file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def iter_parts(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            raise FileNotFoundError(f"OEM feed file not found: {self.path}")
        suffix = self.path.suffix.lower()
        if suffix == ".json":
            with self.path.open(encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "parts" in data:
                rows = data["parts"]
            elif isinstance(data, list):
                rows = data
            else:
                raise ValueError(
                    f"OEM JSON must be a list or object with 'parts' key: {self.path}"
                )
            for row in rows:
                yield _normalize_part(dict(row))
            return

        if suffix == ".csv":
            with self.path.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield _normalize_part(dict(row))
            return

        raise ValueError(f"Unsupported OEM feed format (use .json or .csv): {self.path}")


class HttpOemFeed:
    """GET JSON OEM catalog from a URL (optional Bearer token)."""

    def __init__(self, url: str, token: str | None = None, timeout: float = 15.0) -> None:
        self.url = url
        self.token = token
        self.timeout = timeout

    def iter_parts(self) -> Iterator[dict[str, Any]]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = Request(self.url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 — intentional HTTP feed
                body = resp.read().decode("utf-8")
        except HTTPError as exc:
            raise RuntimeError(
                f"OEM HTTP feed failed HTTP {exc.code} for {self.url}: {exc.reason}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"OEM HTTP feed unreachable (no network or bad host): {self.url} — {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError(
                f"OEM HTTP feed timed out after {self.timeout}s: {self.url}"
            ) from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OEM HTTP feed returned non-JSON from {self.url}") from exc

        if isinstance(data, dict) and "parts" in data:
            rows = data["parts"]
        elif isinstance(data, list):
            rows = data
        else:
            raise RuntimeError(
                f"OEM HTTP feed JSON must be a list or object with 'parts': {self.url}"
            )
        for row in rows:
            yield _normalize_part(dict(row))
