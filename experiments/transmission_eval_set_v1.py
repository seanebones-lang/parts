"""Frozen evaluation set: 20 realistic counter transmission hard-parts requests.

System under test: commit 39797b6 (transmission UoW + human feedback).
Do not use this set to tune the resolver during evaluation runs.
"""
from __future__ import annotations

# Each case:
#   id, query
#   expected_sku: ground-truth final SKU if a correct identification exists in seed, else None
#   human_verdict:
#     accept_if_match — if system RESOLVED with expected_sku → accept; else correct/resolve to expected or leave NEEDS_HUMAN
#   notes: evaluator rationale

EVAL_CASES: list[dict] = [
    {
        "id": "E01",
        "query": "Do you have a pump for a 2011 Tahoe 6L80?",
        "expected_sku": "6L80-PUMP-01",
        "notes": "Clean vehicle + family + part type",
    },
    {
        "id": "E02",
        "query": "6L80 VB in stock?",
        "expected_sku": "6L80-VB-01",
        "notes": "Abbreviation VB = valve body",
    },
    {
        "id": "E03",
        "query": "need a 6l80 valv body rebuilt",
        "expected_sku": "6L80-VB-01",
        "notes": "Misspelling valv/body",
    },
    {
        "id": "E04",
        "query": "Do you have 24264418?",
        "expected_sku": "6L80-PUMP-01",
        "notes": "Casting/OEM identifier hit",
    },
    {
        "id": "E05",
        "query": "looking for oem 24264419",
        "expected_sku": "6L80-VB-01",
        "notes": "OEM number for valve body",
    },
    {
        "id": "E06",
        "query": "you got a pump?",
        "expected_sku": None,
        "notes": "Incomplete — no family",
    },
    {
        "id": "E07",
        "query": "transmission pump",
        "expected_sku": None,
        "notes": "Ambiguous part terminology across families",
    },
    {
        "id": "E08",
        "query": "6L80 pump for an F-150",
        "expected_sku": "6R80-PUMP-01",
        "notes": "Wrong family claim (F-150 typically 6R80). Truth prefers 6R80 if system picks 6L80 that is a false resolution.",
    },
    {
        "id": "E09",
        "query": "4L60E pump for a 2011 Tahoe 6L80",
        "expected_sku": "6L80-PUMP-01",
        "notes": "Conflicting family tokens; human wants Tahoe 6L80 pump",
    },
    {
        "id": "E10",
        "query": "Do you have a 4L60E valve body?",
        "expected_sku": "4L60E-VB-01",
        "notes": "Known zero-stock part — still correct identity",
    },
    {
        "id": "E11",
        "query": "what interchanges with a 6L80 pump?",
        "expected_sku": "6L80-PUMP-01",
        "notes": "Interchange-oriented; seed has 6L80↔6L90 pump interchange",
    },
    {
        "id": "E12",
        "query": "pump assembly",
        "expected_sku": None,
        "notes": "Multiple possible matches / insufficient",
    },
    {
        "id": "E13",
        "query": "Do you have ZZ-NO-SUCH-999?",
        "expected_sku": None,
        "notes": "Unknown identifier",
    },
    {
        "id": "E14",
        "query": "asdf qwer zxcv transmission blah",
        "expected_sku": None,
        "notes": "Nonsense / insufficient",
    },
    {
        "id": "E15",
        "query": "Do you have an 8HP70 pump?",
        "expected_sku": "8HP70-PUMP-01",
        "notes": "Zero stock (core) — identity still valid",
    },
    {
        "id": "E16",
        "query": "Do you have a 6R80 pump?",
        "expected_sku": "6R80-PUMP-01",
        "notes": "Clean family+type with stock",
    },
    {
        "id": "E17",
        "query": "Do you have 6L80-PUMP-01?",
        "expected_sku": "6L80-PUMP-01",
        "notes": "Exact SKU",
    },
    {
        "id": "E18",
        "query": "need 6l80 pmp asap",
        "expected_sku": "6L80-PUMP-01",
        "notes": "Misspelled pump abbreviation",
    },
    {
        "id": "E19",
        "query": "do you have a drum for 10R80?",
        "expected_sku": "10R80-DRUM-01",
        "notes": "Drum part type",
    },
    {
        "id": "E20",
        "query": "4L80E input drum on the shelf?",
        "expected_sku": "4L80E-DRUM-01",
        "notes": "Family+part; may lack inventory row in seed",
    },
]
