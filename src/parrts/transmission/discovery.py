"""Deterministic inventory discovery for dense transmission catalogs.

Separate from the frozen resolver:
  resolver  = can we safely identify one canonical meaning?
  discovery = which sellable inventory lots match a clear product class?

No LLM. No external APIs. Does not modify resolver.py / decision.py.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from parrts.dms.service import DmsService

# ---------------------------------------------------------------------------
# Taxonomy (explicit synonyms only)
# ---------------------------------------------------------------------------

PART_CATEGORY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "pump": (
        "pump assembly",
        "pump assy",
        "front pump",
        "oil pump",
        "pump",
    ),
    "valve body": (
        "valve body",
        "valvebody",
        "vb ",
        " vb",
    ),
    "complete core": (
        "complete core",
        "complete transmission",
        "transmission core",
        "rebuildable core",
        "core assembly",
        " core",
        "cores",
    ),
    "torque converter": (
        "torque converter",
        "torque converters",
        "converter",
        "converters",
        "t/c",
    ),
    "sun shell": (
        "sun shell",
        "reaction shell",
        "sun/reaction",
        "sun reaction",
        "shell",
    ),
    "planetary": (
        "planetary assembly",
        "planetary",
        "planet",
        "gear set",
        "gearset",
    ),
    "input drum": (
        "input drum",
        "reverse input drum",
        "clutch drum",
        "drum",
    ),
    "case": (
        "case / housing",
        "case/housing",
        "extension housing",
        "bellhousing",
        "bell housing",
        "housing",
        "case",
    ),
    "input shaft": ("input shaft",),
    "output shaft": ("output shaft",),
    "shaft": ("input shaft", "output shaft", " shaft"),
    "servo": ("servo assembly", "servo"),
    "tehcm": ("tehcm", "control module", "tcm"),
}

# Prefer more specific categories when multiple match
_CATEGORY_PRIORITY = (
    "valve body",
    "torque converter",
    "complete core",
    "sun shell",
    "planetary",
    "input drum",
    "input shaft",
    "output shaft",
    "pump",
    "servo",
    "tehcm",
    "case",
    "shaft",
)

FAMILY_TOKENS: tuple[str, ...] = (
    "4l60e",
    "4l65e",
    "4l70e",
    "4l80e",
    "6l80",
    "6l90",
    "6r80",
    "10r80",
    "10l80",
    "10l90",
    "8hp70",
    "68rfe",
    "allison 1000",
    "allison1000",
    "5r55s",
    "4r70w",
)

# Query family → catalog family values that count as the same product class
FAMILY_GROUPS: dict[str, tuple[str, ...]] = {
    "4L60E": ("4L60E", "4L65E", "4L70E"),
    "4L65E": ("4L60E", "4L65E", "4L70E"),
    "4L70E": ("4L60E", "4L65E", "4L70E"),
    "4L80E": ("4L80E", "4L85E"),
    "6L80": ("6L80", "6L80E"),
    "6L90": ("6L90", "6L90E"),
    "6R80": ("6R80",),
    "10R80": ("10R80",),
    "10L80": ("10L80", "10L90"),
    "10L90": ("10L80", "10L90"),
    "8HP70": ("8HP70",),
    "68RFE": ("68RFE",),
    "Allison 1000": ("Allison 1000", "ALLISON 1000", "Allison1000"),
    "5R55S": ("5R55S",),
    "4R70W": ("4R70W",),
}


@dataclass
class InventoryCandidate:
    sku: str
    name: str
    transmission_family: str
    transmission_variant: str
    part_type_label: str
    condition: str
    location_code: str
    location_name: str
    bin: str
    on_hand: int
    reserved: int
    available: int
    list_price: float | None
    verification_status: str
    casting_or_id: str
    description: str
    rank_key: tuple = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("rank_key", None)
        return d


@dataclass
class DiscoveryResult:
    family: str | None
    part_category: str | None
    candidate_count: int
    total_on_hand: int
    total_reserved: int
    total_available: int
    candidates: list[InventoryCandidate] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "part_type": self.part_category,
            "candidate_count": self.candidate_count,
            "total_on_hand": self.total_on_hand,
            "total_reserved": self.total_reserved,
            "total_available": self.total_available,
            "candidates": [c.to_dict() for c in self.candidates],
            "notes": self.notes,
        }


def normalize_query(q: str) -> str:
    return re.sub(r"\s+", " ", (q or "").strip().lower())


def families_in_query(q: str) -> list[str]:
    ql = normalize_query(q)
    found: list[str] = []
    # longest first
    for tok in sorted(FAMILY_TOKENS, key=len, reverse=True):
        if tok == "allison 1000" or tok == "allison1000":
            if re.search(r"\ballison\s*1000\b", ql):
                found.append("Allison 1000")
            continue
        pat = re.escape(tok).replace(r"\ ", r"\s*")
        if re.search(rf"\b{pat}\b", ql, flags=re.I):
            # canonical display form
            canon = tok.upper() if tok != "8hp70" else "8HP70"
            if tok.startswith("4l") or tok.startswith("6l") or tok.startswith("6r") or tok.startswith("10"):
                canon = tok.upper()
            if tok == "68rfe":
                canon = "68RFE"
            if tok in ("5r55s", "4r70w"):
                canon = tok.upper()
            if canon not in found:
                found.append(canon)
    return found


def part_category_in_query(q: str) -> str | None:
    ql = normalize_query(q)
    # pad for boundary checks on short tokens like "vb"
    padded = f" {ql} "
    hits: list[str] = []
    for cat, syns in PART_CATEGORY_SYNONYMS.items():
        for syn in sorted(syns, key=len, reverse=True):
            s = syn.strip().lower()
            if not s:
                continue
            if " " in s or "/" in s:
                if s in ql:
                    hits.append(cat)
                    break
            else:
                if re.search(rf"\b{re.escape(s)}\b", ql):
                    hits.append(cat)
                    break
                # trailing/leading space patterns in synonyms like " vb"
                if s in padded:
                    hits.append(cat)
                    break
    if not hits:
        return None
    for pref in _CATEGORY_PRIORITY:
        if pref in hits:
            return pref
    return hits[0]


def _category_match_sql_patterns(category: str) -> list[str]:
    """LIKE patterns against name+description (lowercase)."""
    syns = PART_CATEGORY_SYNONYMS.get(category, (category,))
    pats: list[str] = []
    for s in syns:
        s = s.strip().lower()
        if not s or s in ("core", "shell", "drum", "case", "shaft", "converter", "converters", "cores"):
            # short tokens handled carefully
            if s in ("core", "cores"):
                pats.extend(["%complete core%", "%core assembly%", "%transmission core%", "% rebuildable core%"])
            elif s in ("converter", "converters"):
                pats.extend(["%torque converter%", "% converter%"])
            elif s == "shell":
                pats.extend(["%sun shell%", "%reaction shell%", "%sun/reaction%"])
            elif s == "drum":
                pats.extend(["%input drum%", "%reverse input drum%", "%clutch drum%", "% drum%"])
            elif s == "case":
                pats.extend(["%case / housing%", "%bellhousing%", "%extension housing%", "% housing%"])
            elif s == "shaft":
                pats.extend(["%input shaft%", "%output shaft%"])
            continue
        pats.append(f"%{s}%")
    # de-dupe preserve order
    out: list[str] = []
    for p in pats:
        if p not in out:
            out.append(p)
    return out or [f"%{category}%"]


def _family_values(family: str) -> tuple[str, ...]:
    return FAMILY_GROUPS.get(family, (family,))


def _fetch_identifiers_for_skus(dms: DmsService, skus: Iterable[str]) -> dict[str, str]:
    sku_list = list(skus)
    if not sku_list:
        return {}
    # Prefer casting, then oem
    out: dict[str, str] = {}
    placeholders = ",".join("?" * len(sku_list))
    rows = dms.store.fetchall(
        f"""
        SELECT sku, identifier_type, identifier_value
        FROM part_identifiers
        WHERE sku IN ({placeholders})
        ORDER BY CASE identifier_type WHEN 'casting' THEN 0 WHEN 'oem' THEN 1 ELSE 2 END, id
        """,
        tuple(sku_list),
    )
    for r in rows:
        sku = str(r["sku"])
        if sku not in out:
            out[sku] = str(r["identifier_value"] or "")
    return out


def _rank_key(
    *,
    family: str | None,
    category: str | None,
    cand_family: str,
    cand_variant: str,
    name: str,
    description: str,
    available: int,
    verification: str,
    condition: str,
    location_code: str,
    sku: str,
) -> tuple:
    fams = _family_values(family) if family else ()
    exact_fam = 0 if cand_family in fams else 1
    exact_var = 0 if family and cand_variant.upper() == family.upper() else 1
    text = f"{name} {description}".lower()
    cat_hit = 0
    if category:
        syns = PART_CATEGORY_SYNONYMS.get(category, (category,))
        cat_hit = 0 if any(s.strip() in text for s in syns if len(s.strip()) >= 4) else 1
    avail_rank = 0 if available > 0 else 1
    ver_rank = 0 if (verification or "").lower() == "verified" else 1
    cond = (condition or "").lower()
    cond_rank = {
        "used": 0,
        "rebuilt": 1,
        "new": 2,
        "core": 3,
    }.get(cond, 4)
    loc_rank = 0 if location_code == "CHI-N" else 1
    return (exact_fam, exact_var, cat_hit, avail_rank, ver_rank, cond_rank, loc_rank, sku)


def discover_inventory(
    dms: DmsService,
    *,
    family: str | None,
    part_category: str | None,
    sku_filter: list[str] | None = None,
    limit: int = 100,
) -> DiscoveryResult:
    """Return ranked sellable inventory lots for a product class or SKU set."""
    notes: list[str] = []
    if not family and not sku_filter:
        return DiscoveryResult(None, part_category, 0, 0, 0, 0, notes=["no family or sku filter"])

    clauses: list[str] = []
    params: list[Any] = []

    if sku_filter:
        placeholders = ",".join("?" * len(sku_filter))
        clauses.append(f"c.sku IN ({placeholders})")
        params.extend(sku_filter)
    elif family:
        fams = _family_values(family)
        fam_ph = ",".join("?" * len(fams))
        clauses.append(
            f"(UPPER(c.transmission_family) IN ({fam_ph}) OR UPPER(COALESCE(c.transmission_variant,'')) IN ({fam_ph}))"
        )
        params.extend([f.upper() for f in fams])
        params.extend([f.upper() for f in fams])

    if part_category and not sku_filter:
        pats = _category_match_sql_patterns(part_category)
        like_bits = []
        for p in pats:
            like_bits.append("(LOWER(c.name) LIKE ? OR LOWER(COALESCE(c.description,'')) LIKE ?)")
            params.extend([p, p])
        clauses.append("(" + " OR ".join(like_bits) + ")")

    where = " AND ".join(clauses) if clauses else "1=1"
    sql = f"""
        SELECT c.sku, c.name, c.transmission_family, c.transmission_variant,
               c.description, c.list_price, c.verification_status, c.category,
               l.code AS location_code, l.name AS location_name,
               i.qty AS on_hand, COALESCE(i.reserved_qty, 0) AS reserved,
               COALESCE(i.condition, '') AS condition, COALESCE(i.bin, '') AS bin
        FROM catalog_parts c
        JOIN inventory_levels i ON i.sku = c.sku
        JOIN locations l ON l.id = i.location_id
        WHERE {where}
        ORDER BY c.sku, l.code
    """
    rows = dms.store.fetchall(sql, tuple(params))
    id_map = _fetch_identifiers_for_skus(dms, {str(r["sku"]) for r in rows})

    candidates: list[InventoryCandidate] = []
    for r in rows:
        on_hand = int(r["on_hand"] or 0)
        reserved = int(r["reserved"] or 0)
        available = max(0, on_hand - reserved)
        sku = str(r["sku"])
        name = str(r["name"] or "")
        desc = str(r["description"] or "")
        fam = str(r["transmission_family"] or "")
        var = str(r["transmission_variant"] or "")
        price_raw = r["list_price"]
        try:
            price = float(price_raw) if price_raw is not None and str(price_raw) != "" else None
        except (TypeError, ValueError):
            price = None
        rk = _rank_key(
            family=family,
            category=part_category,
            cand_family=fam,
            cand_variant=var,
            name=name,
            description=desc,
            available=available,
            verification=str(r["verification_status"] or ""),
            condition=str(r["condition"] or ""),
            location_code=str(r["location_code"] or ""),
            sku=sku,
        )
        candidates.append(
            InventoryCandidate(
                sku=sku,
                name=name,
                transmission_family=fam,
                transmission_variant=var,
                part_type_label=part_category or "",
                condition=str(r["condition"] or ""),
                location_code=str(r["location_code"] or ""),
                location_name=str(r["location_name"] or ""),
                bin=str(r["bin"] or ""),
                on_hand=on_hand,
                reserved=reserved,
                available=available,
                list_price=price,
                verification_status=str(r["verification_status"] or "unverified"),
                casting_or_id=id_map.get(sku, ""),
                description=desc,
                rank_key=rk,
            )
        )

    candidates.sort(key=lambda c: c.rank_key)
    if limit and len(candidates) > limit:
        notes.append(f"truncated to {limit} of {len(candidates)} lots")
        candidates = candidates[:limit]

    total_on = sum(c.on_hand for c in candidates)
    total_res = sum(c.reserved for c in candidates)
    total_av = sum(c.available for c in candidates)
    return DiscoveryResult(
        family=family,
        part_category=part_category,
        candidate_count=len(candidates),
        total_on_hand=total_on,
        total_reserved=total_res,
        total_available=total_av,
        candidates=candidates,
        notes=notes,
    )


def discover_by_identifier(dms: DmsService, identifier: str, *, limit: int = 100) -> DiscoveryResult:
    ident = (identifier or "").strip()
    if not ident:
        return DiscoveryResult(None, None, 0, 0, 0, 0)
    rows = dms.store.fetchall(
        """
        SELECT DISTINCT sku FROM part_identifiers
        WHERE UPPER(identifier_value) = UPPER(?)
        """,
        (ident,),
    )
    skus = [str(r["sku"]) for r in rows]
    if not skus:
        return DiscoveryResult(None, None, 0, 0, 0, 0, notes=["identifier not found"])
    return discover_inventory(dms, family=None, part_category=None, sku_filter=skus, limit=limit)
