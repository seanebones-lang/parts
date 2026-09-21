#!/usr/bin/env python3
"""Generate frozen Transmission Eval v2b synthetic pressure corpus.

Ground truth from canonical seed DMS only — no LLM expected SKUs.
Fixed RNG seed. Writes cases JSON; does not run the SUT.

  PYTHONPATH=src:backend:experiments \\
    python experiments/generate_transmission_eval_v2b.py
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
OUT_CASES = Path(__file__).resolve().parent / "transmission_eval_set_v2b.json"
OUT_META = Path(__file__).resolve().parent / "transmission_eval_v2b_meta.json"

# Fixed seed — must match meta after freeze
RNG_SEED = 20260921
TARGET_N = 1000


def _part_type_from_name(name: str, sku: str) -> str:
    n = (name or "").lower()
    s = (sku or "").lower()
    if "valve" in n or "-vb-" in f"-{s}-" or s.endswith("-vb-01"):
        return "valve body"
    if "drum" in n:
        return "drum"
    if "pump" in n:
        return "pump"
    # fallback from sku tokens
    if "vb" in s:
        return "valve body"
    if "drum" in s:
        return "drum"
    return "pump"


def load_canonical() -> dict:
    from parrts.dms.service import DmsService
    from parrts.transmission.seed_loader import load_demo_seed

    with TemporaryDirectory() as tmp:
        dms = DmsService(Path(tmp))
        dms.ensure_schema()
        load_demo_seed(dms)
        parts = [
            dict(r)
            for r in dms.store.fetchall(
                """
                SELECT sku, name, description, transmission_family, category,
                       verification_status, oem_brand
                FROM catalog_parts
                WHERE category = 'transmission_hard_parts'
                   OR transmission_family IS NOT NULL
                """
            )
        ]
        idents = [
            dict(r)
            for r in dms.store.fetchall(
                "SELECT sku, identifier_type, identifier_value FROM part_identifiers"
            )
        ]
        fitments = [
            dict(r)
            for r in dms.store.fetchall(
                """
                SELECT sku, year_from, year_to, make, model, transmission_family
                FROM part_fitments
                """
            )
        ]
        inv = [
            dict(r)
            for r in dms.store.fetchall(
                "SELECT sku, location_id, qty, condition, bin FROM inventory_levels"
            )
        ]
    for p in parts:
        p["part_type"] = _part_type_from_name(p.get("name") or "", p.get("sku") or "")
    return {"parts": parts, "idents": idents, "fitments": fitments, "inventory": inv}


def _years(yf, yt) -> list[int]:
    try:
        a, b = int(yf), int(yt)
    except (TypeError, ValueError):
        return []
    if b < a:
        a, b = b, a
    # sample-friendly discrete years
    return list(range(a, b + 1))


def generate(canonical: dict, rng: random.Random, target_n: int = TARGET_N) -> list[dict]:
    parts = canonical["parts"]
    idents = canonical["idents"]
    fitments = canonical["fitments"]
    inv_by_sku: dict[str, list] = {}
    for row in canonical["inventory"]:
        inv_by_sku.setdefault(row["sku"], []).append(row)

    families = sorted({p["transmission_family"] for p in parts if p.get("transmission_family")})
    part_types = sorted({p["part_type"] for p in parts})
    idents_by_sku: dict[str, list] = {}
    for i in idents:
        idents_by_sku.setdefault(i["sku"], []).append(i)

    cases: list[dict] = []
    seq = 0

    def add(
        *,
        cohort: str,
        category: str,
        query: str,
        expected_outcome: str,
        expected_sku: str | None,
        expected_reason: str | None,
        source: dict,
        mutation: str | None = None,
        adversarial: str | None = None,
    ) -> None:
        nonlocal seq
        seq += 1
        cases.append(
            {
                "id": f"V2B-{seq:04d}",
                "cohort": cohort,
                "category": category,
                "mutation_type": mutation,
                "adversarial_category": adversarial,
                "query": query,
                "expected_outcome": expected_outcome,
                "expected_sku": expected_sku,
                "expected_reason": expected_reason,
                "source_kind": "synthetic_from_canonical",
                "canonical_source": source,
            }
        )

    # ---------- Cohort A: resolvable from canonical ----------
    a_templates_family_part = [
        "Do you have a {family} {part}?",
        "looking for {family} {part}",
        "{family} {part} please",
        "need a {family} {part}",
        "got a {family} {part}?",
        "{family} {part} in stock?",
        "check stock {family} {part}",
        "do you stock {family} {part}",
        "quote {family} {part}",
        "any {family} {part} available",
    ]
    a_templates_sku = [
        "Do you have {sku}?",
        "looking for {sku}",
        "sku {sku}",
        "pull {sku}",
        "{sku} on the shelf?",
        "inventory for {sku}",
        "need {sku} now",
        "have {sku}?",
    ]
    a_templates_oem = [
        "Do you have {ident}?",
        "looking for oem {ident}",
        "oem {ident}",
        "part number {ident}",
        "need {ident}",
        "casting {ident}",
        "got {ident}?",
        "identifier {ident}",
    ]
    a_templates_vehicle = [
        "Do you have a pump for a {year} {model} {family}?",
        "{year} {model} {family} {part}",
        "need {part} for {year} {make} {model} {family}",
        "{model} {year} {family} {part} in stock?",
        "fitment {year} {model} {family} {part}",
        "customer has {year} {model} needs {family} {part}",
    ]
    a_templates_inv = [
        "how many {family} {part_plural} on hand",
        "do we have any {family} {part_plural} left",
        "{family} {part} qty?",
        "stock check {family} {part}",
        "available inventory {family} {part}",
        "{family} {part} availability",
    ]

    def plural(pt: str) -> str:
        if pt == "valve body":
            return "valve bodies"
        if pt.endswith("s"):
            return pt
        return pt + "s"

    # A1 family+part for every catalog part × templates
    for p in parts:
        fam = p["transmission_family"]
        pt = p["part_type"]
        sku = p["sku"]
        src = {
            "sku": sku,
            "transmission_family": fam,
            "part_type": pt,
            "name": p.get("name"),
            "via": "catalog_family_part",
        }
        for tmpl in a_templates_family_part:
            add(
                cohort="A",
                category="clean_family_part",
                query=tmpl.format(family=fam, part=pt),
                expected_outcome="RESOLVED",
                expected_sku=sku,
                expected_reason=None,
                source=src,
            )
        for tmpl in a_templates_sku:
            add(
                cohort="A",
                category="exact_sku",
                query=tmpl.format(sku=sku),
                expected_outcome="RESOLVED",
                expected_sku=sku,
                expected_reason=None,
                source={**src, "via": "catalog_sku"},
            )
        for tmpl in a_templates_inv:
            add(
                cohort="A",
                category="inventory_phrasing",
                query=tmpl.format(
                    family=fam, part=pt, part_plural=plural(pt)
                ),
                expected_outcome="RESOLVED",
                expected_sku=sku,
                expected_reason=None,
                source={**src, "via": "catalog_inventory_phrasing"},
            )

    # A2 identifiers
    for i in idents:
        sku = i["sku"]
        p = next((x for x in parts if x["sku"] == sku), None)
        if not p:
            continue
        src = {
            "sku": sku,
            "identifier_type": i["identifier_type"],
            "identifier_value": i["identifier_value"],
            "via": "part_identifiers",
        }
        for tmpl in a_templates_oem:
            # casting template only for casting type (still ok either way)
            q = tmpl.format(ident=i["identifier_value"])
            if "casting" in tmpl.lower() and i["identifier_type"] != "casting":
                q = f"looking for {i['identifier_value']}"
            add(
                cohort="A",
                category=f"identifier_{i['identifier_type']}",
                query=q,
                expected_outcome="RESOLVED",
                expected_sku=sku,
                expected_reason=None,
                source=src,
            )

    # A3 vehicle+family+part from fitments (only pump rows in seed fitments mostly)
    for f in fitments:
        sku = f["sku"]
        p = next((x for x in parts if x["sku"] == sku), None)
        if not p:
            continue
        fam = f.get("transmission_family") or p["transmission_family"]
        pt = p["part_type"]
        years = _years(f.get("year_from"), f.get("year_to"))
        if not years:
            continue
        # pick several years deterministically via rng sample later — add fixed set
        year_picks = sorted(set([years[0], years[len(years) // 2], years[-1]]))
        for year in year_picks:
            src = {
                "sku": sku,
                "make": f.get("make"),
                "model": f.get("model"),
                "year": year,
                "transmission_family": fam,
                "part_type": pt,
                "via": "part_fitments",
            }
            for tmpl in a_templates_vehicle:
                add(
                    cohort="A",
                    category="vehicle_family_part",
                    query=tmpl.format(
                        year=year,
                        make=f.get("make"),
                        model=f.get("model"),
                        family=fam,
                        part=pt,
                    ),
                    expected_outcome="RESOLVED",
                    expected_sku=sku,
                    expected_reason=None,
                    source=src,
                )

    # ---------- Cohort B: counter-language mutations of resolvable bases ----------
    # Build base resolvable queries (family+part and a few vehicle) then mutate
    bases: list[tuple[str, str, dict]] = []
    for p in parts:
        fam, pt, sku = p["transmission_family"], p["part_type"], p["sku"]
        src = {
            "sku": sku,
            "transmission_family": fam,
            "part_type": pt,
            "via": "mutation_base_catalog",
        }
        bases.append((f"Do you have a {fam} {pt}?", sku, src))
        bases.append((f"{fam} {pt} in stock?", sku, src))
        bases.append((f"need a {fam} {pt}", sku, src))

    for f in fitments:
        p = next((x for x in parts if x["sku"] == f["sku"]), None)
        if not p:
            continue
        years = _years(f.get("year_from"), f.get("year_to"))
        if not years:
            continue
        y = years[len(years) // 2]
        fam = f.get("transmission_family") or p["transmission_family"]
        src = {
            "sku": p["sku"],
            "model": f.get("model"),
            "year": y,
            "transmission_family": fam,
            "part_type": p["part_type"],
            "via": "mutation_base_fitment",
        }
        bases.append(
            (
                f"Do you have a {p['part_type']} for a {y} {f.get('model')} {fam}?",
                p["sku"],
                src,
            )
        )

    def mutations(q: str, pt: str) -> list[tuple[str, str]]:
        """Return (mutated_query, mutation_type) — semantics preserved."""
        out: list[tuple[str, str]] = []
        out.append((q.lower(), "lowercase"))
        out.append((q.upper(), "uppercase"))
        out.append((re.sub(r"[^\w\s]", " ", q), "punctuation_stripped"))
        out.append((re.sub(r"\s+", " ", q).strip() + " asap", "urgency_asap"))
        out.append(("customer waiting " + q, "urgency_waiting"))
        out.append(("hey " + q, "filler_hey"))
        out.append((q + " please thanks", "filler_please"))
        # terse: drop leading politeness
        terse = re.sub(
            r"^(do you have a|do you have|looking for|need a|need|got a|got)\s+",
            "",
            q,
            flags=re.I,
        ).strip(" ?")
        if terse and terse != q:
            out.append((terse + "?", "terse"))
        # plurals on part word
        if pt == "pump" and re.search(r"\bpump\b", q, re.I):
            out.append((re.sub(r"\bpump\b", "pumps", q, flags=re.I), "plural_pumps"))
        if pt == "drum" and re.search(r"\bdrum\b", q, re.I):
            out.append((re.sub(r"\bdrum\b", "drums", q, flags=re.I), "plural_drums"))
        # observed abbreviations only (eval-proven tokens)
        if pt == "valve body" and re.search(r"valve body", q, re.I):
            out.append((re.sub(r"valve body", "VB", q, flags=re.I), "abbrev_vb"))
            out.append((re.sub(r"valve body", "valv body", q, flags=re.I), "misspell_valv"))
        if pt == "pump" and re.search(r"\bpump\b", q, re.I):
            out.append((re.sub(r"\bpump\b", "pmp", q, flags=re.I), "abbrev_pmp"))
        # word order: family after part
        m = re.search(
            r"\b(4L60E|4L80E|6L80|6L90|6R80|10R80|8HP70)\b\s+(pump|valve body|drum|pumps|drums)\b",
            q,
            re.I,
        )
        if m:
            fam_t, pt_t = m.group(1), m.group(2)
            out.append(
                (
                    re.sub(
                        re.escape(m.group(0)),
                        f"{pt_t} for {fam_t}",
                        q,
                        count=1,
                        flags=re.I,
                    ),
                    "word_order_part_for_family",
                )
            )
        return out

    for base_q, sku, src in bases:
        pt = src.get("part_type") or "pump"
        for mq, mtype in mutations(base_q, pt):
            add(
                cohort="B",
                category="counter_language_mutation",
                query=mq,
                expected_outcome="RESOLVED",
                expected_sku=sku,
                expected_reason=None,
                source=src,
                mutation=mtype,
            )

    # ---------- Cohort C: safety / adversarial by construction ----------
    # Multi part type
    multi_part_tmpls = [
        "pump or valve body for {fam} — not sure which",
        "{fam} pump and valve body both now",
        "need {fam} pump AND {fam} valve body",
        "{fam} pump that is also a valve body",
        "pump / valve body {fam}?",
    ]
    for fam in families:
        for tmpl in multi_part_tmpls:
            add(
                cohort="C",
                category="adversarial_multi_part",
                query=tmpl.format(fam=fam),
                expected_outcome="NEEDS_HUMAN",
                expected_sku=None,
                expected_reason="multiple part types / multi-item",
                source={"via": "constructed_multi_part", "families": [fam]},
                adversarial="multi_part_type",
            )

    # Multi family comparison / substitution
    if len(families) >= 2:
        pairs = []
        for i, a in enumerate(families):
            for b in families[i + 1 :]:
                pairs.append((a, b))
        # limit pair explosion later via sample; add core patterns for many pairs
        for a, b in pairs:
            specs = [
                (
                    f"is {a} pump same as {b} pump?",
                    "same_as_symmetric",
                ),
                (
                    f"can I use {a} pump instead of {b}?",
                    "instead_of",
                ),
                (
                    f"can I use {b} pump instead of {a}?",
                    "instead_of",
                ),
                (
                    f"cross over from {a} pump to {b}",
                    "crossover",
                ),
                (
                    f"{a} {b} pump which one",
                    "which_one",
                ),
                (
                    f"{a} or {b} pump?",
                    "or_family",
                ),
                (
                    f"{a} {b} {families[0] if families[0] not in (a, b) else families[-1]} pump which one",
                    "which_one_multi",
                ),
            ]
            for q, adv in specs:
                add(
                    cohort="C",
                    category="adversarial_multi_family",
                    query=q,
                    expected_outcome="NEEDS_HUMAN",
                    expected_sku=None,
                    expected_reason="comparative/substitution/multi-family choice",
                    source={"via": "constructed_multi_family", "families": [a, b]},
                    adversarial=adv,
                )

    # Vehicle / family conflicts: known fitment vehicle + wrong family
    # Tahoe implies 6L80; F-150 implies 6R80; Silverado implies 4L60E
    conflict_specs = [
        ("F-150", "Ford", "6L80", "pump", "vehicle_family_conflict"),
        ("F-150", "Ford", "4L60E", "pump", "vehicle_family_conflict"),
        ("Tahoe", "Chevrolet", "6R80", "pump", "vehicle_family_conflict"),
        ("Tahoe", "Chevrolet", "4L80E", "drum", "vehicle_family_conflict"),
        ("Yukon", "GMC", "6R80", "pump", "vehicle_family_conflict"),
        ("Silverado", "Chevrolet", "6L80", "pump", "vehicle_family_conflict"),
        ("Silverado", "Chevrolet", "6R80", "valve body", "vehicle_family_conflict"),
    ]
    for model, make, fam, pt, adv in conflict_specs:
        for year in (2009, 2011, 2012):
            add(
                cohort="C",
                category="adversarial_vehicle_conflict",
                query=f"{fam} {pt} for a {year} {model}",
                expected_outcome="NEEDS_HUMAN",
                expected_sku=None,
                expected_reason="vehicle fitment conflicts with stated family",
                source={
                    "via": "constructed_conflict",
                    "model": model,
                    "make": make,
                    "stated_family": fam,
                },
                adversarial=adv,
            )
            add(
                cohort="C",
                category="adversarial_vehicle_conflict",
                query=f"need a {pt} for {make} {model} {year} {fam}",
                expected_outcome="NEEDS_HUMAN",
                expected_sku=None,
                expected_reason="vehicle fitment conflicts with stated family",
                source={
                    "via": "constructed_conflict",
                    "model": model,
                    "make": make,
                    "stated_family": fam,
                },
                adversarial=adv,
            )

    # Recognizable vehicle with unsupported family (Prius + any catalog family)
    for fam in families:
        for pt in ("pump", "valve body"):
            add(
                cohort="C",
                category="adversarial_no_fitment",
                query=f"CVT {pt} for Prius {fam}",
                expected_outcome="NEEDS_HUMAN",
                expected_sku=None,
                expected_reason="vehicle has no canonical fitment for family",
                source={"via": "constructed_no_fitment", "model": "Prius", "family": fam},
                adversarial="no_fitment_vehicle",
            )
            add(
                cohort="C",
                category="adversarial_no_fitment",
                query=f"{fam} {pt} for a Prius",
                expected_outcome="NEEDS_HUMAN",
                expected_sku=None,
                expected_reason="vehicle has no canonical fitment for family",
                source={"via": "constructed_no_fitment", "model": "Prius", "family": fam},
                adversarial="no_fitment_vehicle",
            )

    # Malformed / unknown identifiers
    bad_idents = [
        "ZZ-NO-SUCH-999",
        "00000000",
        "NOTAREALID",
        "OEM-FAKE-777",
        "????",
        "12",
        "ABCDEFGHIJKLMNOP",
        "6L80-FAKE-99",
        "24264418X",
        "DROP TABLE parts",
    ]
    for bi in bad_idents:
        add(
            cohort="C",
            category="adversarial_unknown_identifier",
            query=f"Do you have {bi}?",
            expected_outcome="NEEDS_HUMAN",
            expected_sku=None,
            expected_reason="unknown/malformed identifier",
            source={"via": "constructed_bad_ident", "identifier": bi},
            adversarial="unknown_identifier",
        )
        add(
            cohort="C",
            category="adversarial_unknown_identifier",
            query=f"looking for oem {bi}",
            expected_outcome="NEEDS_HUMAN",
            expected_sku=None,
            expected_reason="unknown/malformed identifier",
            source={"via": "constructed_bad_ident", "identifier": bi},
            adversarial="unknown_identifier",
        )

    # Nonsense mixed with valid family tokens
    nonsense = [
        "asdf qwer {fam} blah pump zxcv",
        "{fam} purple elephant torque banana",
        "send pizza and a {fam} maybe",
        "lorem ipsum {fam} dolor pump sit",
        "### {fam} ###",
    ]
    for fam in families:
        for tmpl in nonsense:
            add(
                cohort="C",
                category="adversarial_nonsense",
                query=tmpl.format(fam=fam),
                expected_outcome="NEEDS_HUMAN",
                expected_sku=None,
                expected_reason="insufficient/nonsensical request",
                source={"via": "constructed_nonsense", "family": fam},
                adversarial="nonsense",
            )

    # Insufficient: family only / part only / vehicle only
    for fam in families:
        add(
            cohort="C",
            category="adversarial_insufficient",
            query=f"got {fam}?",
            expected_outcome="NEEDS_HUMAN",
            expected_sku=None,
            expected_reason="family only — no part type",
            source={"via": "constructed_insufficient", "family": fam},
            adversarial="family_only",
        )
    for pt in part_types:
        add(
            cohort="C",
            category="adversarial_insufficient",
            query=f"you got a {pt}?",
            expected_outcome="NEEDS_HUMAN",
            expected_sku=None,
            expected_reason="part type only",
            source={"via": "constructed_insufficient", "part_type": pt},
            adversarial="part_only",
        )
    for model in ("Tahoe", "F-150", "Yukon", "Silverado"):
        add(
            cohort="C",
            category="adversarial_insufficient",
            query=f"parts for a {model}",
            expected_outcome="NEEDS_HUMAN",
            expected_sku=None,
            expected_reason="vehicle only",
            source={"via": "constructed_insufficient", "model": model},
            adversarial="vehicle_only",
        )

    # Conflicting part claims
    for fam in families[:5]:
        add(
            cohort="C",
            category="adversarial_contradiction",
            query=f"{fam} pump that is also a {fam} drum right now",
            expected_outcome="NEEDS_HUMAN",
            expected_sku=None,
            expected_reason="contradictory part types",
            source={"via": "constructed_contradiction", "family": fam},
            adversarial="contradictory_parts",
        )

    # ---------- Downsample / upsample to target_n with fixed rng ----------
    # Prefer keeping all unique queries; if over target, stratified sample.
    # If under target, duplicate A templates with light deterministic fillers.
    # Dedup by query string keeping first
    seen_q: set[str] = set()
    unique: list[dict] = []
    for c in cases:
        key = c["query"].strip().lower()
        if key in seen_q:
            continue
        seen_q.add(key)
        unique.append(c)
    cases = unique

    def restamp(cs: list[dict]) -> list[dict]:
        out = []
        for i, c in enumerate(cs, start=1):
            nc = dict(c)
            nc["id"] = f"V2B-{i:04d}"
            out.append(nc)
        return out

    if len(cases) > target_n:
        # Stratified: keep proportions of A/B/C
        by_c: dict[str, list] = {"A": [], "B": [], "C": []}
        for c in cases:
            by_c.setdefault(c["cohort"], []).append(c)
        # target mix ~ 45% A, 30% B, 25% C
        n_a = int(target_n * 0.45)
        n_b = int(target_n * 0.30)
        n_c = target_n - n_a - n_b
        picked: list[dict] = []
        for bucket, n in (("A", n_a), ("B", n_b), ("C", n_c)):
            pool = by_c.get(bucket) or []
            rng.shuffle(pool)
            if len(pool) >= n:
                picked.extend(pool[:n])
            else:
                picked.extend(pool)
                # fill shortfall from other pools later
        if len(picked) < target_n:
            rest = [c for c in cases if c not in picked]
            rng.shuffle(rest)
            picked.extend(rest[: target_n - len(picked)])
        rng.shuffle(picked)
        cases = restamp(picked[:target_n])
    elif len(cases) < target_n:
        # Expand A with extra year/vehicle and filler variants
        extra: list[dict] = []
        fillers = ["", " please", " thx", " — counter", " today", " if possible"]
        while len(cases) + len(extra) < target_n:
            p = rng.choice(parts)
            fam, pt, sku = p["transmission_family"], p["part_type"], p["sku"]
            fill = rng.choice(fillers)
            style = rng.randint(0, 5)
            if style == 0:
                q = f"Do you have a {fam} {pt}?{fill}".strip()
            elif style == 1:
                q = f"{fam} {pt}{fill}".strip()
            elif style == 2:
                q = f"need {fam} {pt}{fill}".strip()
            elif style == 3:
                q = f"stock {sku}{fill}".strip()
            elif style == 4:
                q = f"{pt} {fam} available{fill}".strip()
            else:
                q = f"check {fam} {pt} inventory{fill}".strip()
            key = q.strip().lower()
            if key in seen_q:
                continue
            seen_q.add(key)
            extra.append(
                {
                    "id": "TMP",
                    "cohort": "A",
                    "category": "clean_family_part_expanded",
                    "mutation_type": None,
                    "adversarial_category": None,
                    "query": q,
                    "expected_outcome": "RESOLVED",
                    "expected_sku": sku,
                    "expected_reason": None,
                    "source_kind": "synthetic_from_canonical",
                    "canonical_source": {
                        "sku": sku,
                        "transmission_family": fam,
                        "part_type": pt,
                        "via": "catalog_expand",
                    },
                }
            )
        cases = restamp(cases + extra)
        cases = cases[:target_n]
    else:
        cases = restamp(cases)

    return cases


def distribution(cases: list[dict]) -> dict:
    return {
        "total": len(cases),
        "cohort": dict(Counter(c["cohort"] for c in cases)),
        "category": dict(Counter(c["category"] for c in cases)),
        "expected_outcome": dict(Counter(c["expected_outcome"] for c in cases)),
        "mutation_type": dict(
            Counter(c.get("mutation_type") or "none" for c in cases)
        ),
        "adversarial_category": dict(
            Counter(c.get("adversarial_category") or "none" for c in cases)
        ),
        "expected_sku": dict(
            Counter(c.get("expected_sku") or "NEEDS_HUMAN" for c in cases)
        ),
        "family_from_source": dict(
            Counter(
                (c.get("canonical_source") or {}).get("transmission_family")
                or (c.get("canonical_source") or {}).get("family")
                or (
                    (c.get("canonical_source") or {}).get("families") or [None]
                )[0]
                or "n/a"
                for c in cases
            )
        ),
        "part_type_from_source": dict(
            Counter(
                (c.get("canonical_source") or {}).get("part_type") or "n/a"
                for c in cases
            )
        ),
    }


def main() -> int:
    rng = random.Random(RNG_SEED)
    canonical = load_canonical()
    cases = generate(canonical, rng, TARGET_N)
    dist = distribution(cases)
    meta = {
        "eval": "v2b",
        "title": "Transmission Eval v2b — Synthetic Pressure Test",
        "rng_seed": RNG_SEED,
        "target_n": TARGET_N,
        "actual_n": len(cases),
        "sut_intended": "932af65d58201a3e2be50fa4ed9262f136ce3598",
        "ground_truth_rule": "canonical seed catalog/identifiers/fitments only; no LLM SKUs",
        "synthetic": True,
        "not_live_jp_traffic": True,
        "distribution": dist,
        "canonical_part_count": len(canonical["parts"]),
        "canonical_identifier_count": len(canonical["idents"]),
        "canonical_fitment_count": len(canonical["fitments"]),
        "parts": [
            {
                "sku": p["sku"],
                "family": p["transmission_family"],
                "part_type": p["part_type"],
                "name": p["name"],
            }
            for p in canonical["parts"]
        ],
    }
    OUT_CASES.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    OUT_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(dist, indent=2))
    print(f"Wrote {OUT_CASES} n={len(cases)}")
    print(f"Wrote {OUT_META}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
