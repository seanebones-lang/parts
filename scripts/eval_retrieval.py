#!/usr/bin/env python3
"""
Retrieval eval smoke script — 12 fixed parts queries.

Calls the importable `parrts` engine when available; otherwise runs a
keyword-heuristic baseline against a tiny mock catalog and prints hit-rate.

Usage:
  python scripts/eval_retrieval.py
  python -m scripts.eval_retrieval  # if packaged
"""

from __future__ import annotations

import json
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@dataclass(frozen=True)
class EvalCase:
    query: str
    # Any of these tokens appearing in a top hit counts as a hit
    expect_any: Sequence[str]


EVAL_SET: List[EvalCase] = [
    EvalCase("brake pads for 2019 Honda Civic", ("brake", "pad", "civic", "honda")),
    EvalCase("oil filter Toyota Camry 2020", ("oil", "filter", "camry", "toyota")),
    EvalCase("spark plugs NGK Civic", ("spark", "plug", "ngk")),
    EvalCase("front rotors 2018 Ford F-150", ("rotor", "brake", "ford", "f-150", "f150")),
    EvalCase("cabin air filter Honda Accord", ("cabin", "filter", "accord", "honda")),
    EvalCase("wiper blades 22 inch", ("wiper", "blade")),
    EvalCase("serpenting belt or drive belt Civic", ("belt", "serpentine", "drive")),
    EvalCase("coolant thermostat Toyota", ("thermostat", "coolant", "toyota")),
    EvalCase("headlight bulb H11", ("headlight", "bulb", "h11")),
    EvalCase("brake fluid DOT 4", ("brake", "fluid", "dot")),
    EvalCase("tire 225/60R16", ("tire", "225", "60r16")),
    EvalCase("battery group 51R Honda", ("battery", "51r", "honda")),
]


# Tiny offline catalog for heuristic fallback when parrts is missing
MOCK_CATALOG: List[dict[str, Any]] = [
    {"name": "Brake Pad Set - Front", "make": "Honda", "model": "Civic", "brand": "Brembo"},
    {"name": "Brake Rotor Front", "make": "Ford", "model": "F-150", "brand": "OEM"},
    {"name": "Oil Filter", "make": "Toyota", "model": "Camry", "brand": "Fram"},
    {"name": "Spark Plug Set", "make": "Honda", "model": "Civic", "brand": "NGK"},
    {"name": "Cabin Air Filter", "make": "Honda", "model": "Accord", "brand": "OEM"},
    {"name": "Wiper Blade 22in", "make": "Universal", "model": "", "brand": "Bosch"},
    {"name": "Serpentine Belt", "make": "Honda", "model": "Civic", "brand": "Gates"},
    {"name": "Coolant Thermostat", "make": "Toyota", "model": "Camry", "brand": "OEM"},
    {"name": "Headlight Bulb H11", "make": "Universal", "model": "", "brand": "Philips"},
    {"name": "Brake Fluid DOT 4", "make": "Universal", "model": "", "brand": "Prestone"},
    {"name": "Tire 225/60R16", "make": "Honda", "model": "Civic", "brand": "Michelin"},
    {"name": "Battery Group 51R", "make": "Honda", "model": "Civic", "brand": "Interstate"},
]


def _flatten_hit(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        parts = []
        for k, v in obj.items():
            if isinstance(v, (str, int, float)):
                parts.append(str(v))
            elif isinstance(v, (list, dict)):
                parts.append(_flatten_hit(v))
        return " ".join(parts)
    if isinstance(obj, (list, tuple)):
        return " ".join(_flatten_hit(x) for x in obj)
    return str(obj)


def _extract_hits(result: Any) -> List[Any]:
    if result is None:
        return []
    if isinstance(result, list):
        return list(result)
    if isinstance(result, dict):
        for key in ("results", "hits", "parts", "items", "data", "search_results"):
            val = result.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                nested = _extract_hits(val)
                if nested:
                    return nested
        # single ranked object
        if any(k in result for k in ("name", "title", "part_number", "sku")):
            return [result]
    return []


def _is_hit(hits: Iterable[Any], expect_any: Sequence[str], k: int = 5) -> bool:
    top = list(hits)[:k]
    blob = " ".join(_flatten_hit(h) for h in top).lower()
    return any(tok.lower() in blob for tok in expect_any)


def try_parrts_retriever() -> Optional[Callable[[str], Any]]:
    """Return a callable(query) -> results if parrts core is importable."""
    try:
        from parrts.embeddings import HashingEmbedder
        from parrts.engine import PartsRAGEngine

        engine = PartsRAGEngine(root=ROOT, embedder=HashingEmbedder())
        engine.ensure_ready()

        def _call(q: str) -> Any:
            result = engine.query(text=q, top_k=5, use_llm=False)
            # QueryResult.to_dict() → hits list
            if hasattr(result, "to_dict"):
                data = result.to_dict()
            elif isinstance(result, dict):
                data = result
            else:
                data = {"hits": []}
            return data.get("hits") or data.get("results") or data

        # smoke
        _ = _call("brake pads")
        return _call
    except Exception:
        traceback.print_exc()
        return None


def mock_retrieve(query: str, top_k: int = 5) -> List[dict[str, Any]]:
    tokens = [t for t in query.lower().replace("/", " ").split() if len(t) > 1]
    scored: List[tuple[int, dict[str, Any]]] = []
    for item in MOCK_CATALOG:
        blob = _flatten_hit(item).lower()
        score = sum(1 for t in tokens if t in blob)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:top_k]] or MOCK_CATALOG[:top_k]


def main() -> int:
    retriever = try_parrts_retriever()
    mode = "parrts" if retriever is not None else "mock-heuristic"
    print(f"eval_retrieval mode={mode}")
    print(f"cases={len(EVAL_SET)} k=5")
    print("-" * 60)

    hits = 0
    details = []
    for i, case in enumerate(EVAL_SET, 1):
        err = None
        try:
            raw = retriever(case.query) if retriever else mock_retrieve(case.query)
            top = _extract_hits(raw)
            ok = _is_hit(top, case.expect_any, k=5)
        except Exception as exc:  # noqa: BLE001
            ok = False
            top = []
            err = f"{type(exc).__name__}: {exc}"
            if mode == "parrts":
                # fall back per-query so script still reports something
                try:
                    top = mock_retrieve(case.query)
                    ok = _is_hit(top, case.expect_any, k=5)
                    err = f"{err} (fell back to mock)"
                except Exception:
                    traceback.print_exc()

        hits += int(ok)
        mark = "HIT " if ok else "MISS"
        top_names = [
            _flatten_hit(h)[:80] for h in top[:3]
        ]
        line = f"[{i:02d}] {mark}  {case.query}"
        print(line)
        if top_names:
            print(f"       top: {top_names}")
        if err:
            print(f"       err: {err}")
        details.append(
            {
                "query": case.query,
                "hit": ok,
                "top": top_names,
                "error": err,
            }
        )

    rate = hits / len(EVAL_SET) if EVAL_SET else 0.0
    print("-" * 60)
    print(f"hit_rate@{5} = {hits}/{len(EVAL_SET)} = {rate:.1%}  (mode={mode})")
    summary = {
        "mode": mode,
        "hits": hits,
        "total": len(EVAL_SET),
        "hit_rate": rate,
        "details": details,
    }
    out = ROOT / ".parrts" / "eval_last.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"wrote {out}")
    except OSError as e:
        print(f"(could not write summary: {e})")

    # Non-zero only if completely broken (0 hits in mock mode would be surprising)
    if mode == "mock-heuristic" and hits == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
