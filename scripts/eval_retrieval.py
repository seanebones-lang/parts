#!/usr/bin/env python3
"""
Retrieval eval harness — hit@k, recall@k, MRR, latency.

Uses importable `parrts` engine when available; otherwise keyword mock baseline.

Usage:
  python scripts/eval_retrieval.py
  python scripts/eval_retrieval.py --k 10
  python scripts/eval_retrieval.py --dataset default --json-out .parrts/eval_results.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
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
    # Optional: all of these must appear somewhere in top-k blob for "strict"
    expect_all: Sequence[str] = ()


DEFAULT_SET: List[EvalCase] = [
    EvalCase("brake pads for 2019 Honda Civic", ("brake", "pad", "civic", "honda")),
    EvalCase("oil filter Toyota Camry 2020", ("oil", "filter", "camry", "toyota")),
    EvalCase("spark plugs NGK Civic", ("spark", "plug", "ngk")),
    EvalCase("front rotors 2018 Ford F-150", ("rotor", "brake", "ford", "f-150", "f150")),
    EvalCase("cabin air filter Honda Accord", ("cabin", "filter", "accord", "honda")),
    EvalCase("wiper blades 22 inch", ("wiper", "blade")),
    EvalCase("serpentine belt or drive belt Civic", ("belt", "serpentine", "drive")),
    EvalCase("coolant thermostat Toyota", ("thermostat", "coolant", "toyota")),
    EvalCase("headlight bulb H11", ("headlight", "bulb", "h11")),
    EvalCase("brake fluid DOT 4", ("brake", "fluid", "dot")),
    EvalCase("tire 225/60R16", ("tire", "225", "60r16")),
    EvalCase("battery group 51R Honda", ("battery", "51r", "honda")),
]

EXTENDED_SET: List[EvalCase] = DEFAULT_SET + [
    EvalCase("air filter Honda Civic", ("air", "filter", "civic", "honda")),
    EvalCase("transmission fluid ATF", ("transmission", "fluid", "atf")),
    EvalCase("shock absorber Ford F-150", ("shock", "ford", "f-150", "f150", "strut")),
    EvalCase("alternator Toyota Camry", ("alternator", "toyota", "camry")),
    EvalCase("radiator hose Honda", ("radiator", "hose", "honda")),
    EvalCase("oxygen sensor O2", ("oxygen", "sensor", "o2")),
    EvalCase("wheel bearing hub assembly", ("wheel", "bearing", "hub")),
    EvalCase("fuel pump assembly", ("fuel", "pump")),
]

DATASETS = {
    "default": DEFAULT_SET,
    "extended": EXTENDED_SET,
}


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
        if any(k in result for k in ("name", "title", "part_number", "sku")):
            return [result]
    return []


def _is_hit(hits: Iterable[Any], expect_any: Sequence[str], k: int = 5) -> bool:
    top = list(hits)[:k]
    blob = " ".join(_flatten_hit(h) for h in top).lower()
    return any(tok.lower() in blob for tok in expect_any)


def _first_relevant_rank(
    hits: Sequence[Any], expect_any: Sequence[str], k: int
) -> Optional[int]:
    """1-based rank of first relevant hit, or None."""
    for i, h in enumerate(list(hits)[:k], start=1):
        blob = _flatten_hit(h).lower()
        if any(tok.lower() in blob for tok in expect_any):
            return i
    return None


def _recall_at_k(hits: Sequence[Any], expect_any: Sequence[str], k: int) -> float:
    """Binary recall: 1.0 if any expected token found in top-k, else 0.0."""
    return 1.0 if _is_hit(hits, expect_any, k=k) else 0.0


def try_parrts_retriever(top_k: int = 5) -> Optional[Callable[[str], Any]]:
    try:
        from parrts.embeddings import HashingEmbedder
        from parrts.engine import PartsRAGEngine

        engine = PartsRAGEngine(root=ROOT, embedder=HashingEmbedder())
        engine.ensure_ready()

        def _call(q: str) -> Any:
            result = engine.query(text=q, top_k=top_k, use_llm=False)
            if hasattr(result, "to_dict"):
                data = result.to_dict()
            elif isinstance(result, dict):
                data = result
            else:
                data = {"hits": []}
            return data.get("hits") or data.get("results") or data

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


def run_eval(
    cases: Sequence[EvalCase],
    *,
    k: int = 5,
    retriever: Optional[Callable[[str], Any]] = None,
) -> dict[str, Any]:
    mode = "parrts" if retriever is not None else "mock-heuristic"
    hits_n = 0
    mrr_scores: list[float] = []
    recalls: list[float] = []
    latencies_ms: list[float] = []
    details = []

    for i, case in enumerate(cases, 1):
        err = None
        t0 = time.perf_counter()
        try:
            raw = retriever(case.query) if retriever else mock_retrieve(case.query, top_k=k)
            top = _extract_hits(raw)
            ok = _is_hit(top, case.expect_any, k=k)
            rank = _first_relevant_rank(top, case.expect_any, k=k)
            rec = _recall_at_k(top, case.expect_any, k=k)
        except Exception as exc:  # noqa: BLE001
            ok = False
            top = []
            rank = None
            rec = 0.0
            err = f"{type(exc).__name__}: {exc}"
            if mode == "parrts":
                try:
                    top = mock_retrieve(case.query, top_k=k)
                    ok = _is_hit(top, case.expect_any, k=k)
                    rank = _first_relevant_rank(top, case.expect_any, k=k)
                    rec = _recall_at_k(top, case.expect_any, k=k)
                    err = f"{err} (fell back to mock)"
                except Exception:
                    traceback.print_exc()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)
        hits_n += int(ok)
        mrr = (1.0 / rank) if rank else 0.0
        mrr_scores.append(mrr)
        recalls.append(rec)
        top_names = [_flatten_hit(h)[:80] for h in top[:3]]
        mark = "HIT " if ok else "MISS"
        print(f"[{i:02d}] {mark}  mrr={mrr:.3f}  {elapsed_ms:6.1f}ms  {case.query}")
        if top_names:
            print(f"       top: {top_names}")
        if err:
            print(f"       err: {err}")
        details.append(
            {
                "query": case.query,
                "hit": ok,
                "mrr": mrr,
                "recall": rec,
                "rank": rank,
                "latency_ms": round(elapsed_ms, 2),
                "top": top_names,
                "error": err,
            }
        )

    n = len(cases) or 1
    rate = hits_n / n
    mean_mrr = statistics.fmean(mrr_scores) if mrr_scores else 0.0
    mean_recall = statistics.fmean(recalls) if recalls else 0.0
    mean_lat = statistics.fmean(latencies_ms) if latencies_ms else 0.0
    p50 = statistics.median(latencies_ms) if latencies_ms else 0.0
    p95 = (
        statistics.quantiles(latencies_ms, n=20)[18]
        if len(latencies_ms) >= 20
        else max(latencies_ms) if latencies_ms else 0.0
    )

    return {
        "mode": mode,
        "k": k,
        "hits": hits_n,
        "total": len(cases),
        "hit_rate": rate,
        "mrr": mean_mrr,
        "recall_at_k": mean_recall,
        "latency_ms": {
            "mean": round(mean_lat, 2),
            "p50": round(p50, 2),
            "p95": round(p95, 2),
        },
        "details": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parrts retrieval eval harness")
    parser.add_argument("-k", type=int, default=5, help="Top-k for hit/recall/MRR (default 5)")
    parser.add_argument(
        "--dataset",
        choices=sorted(DATASETS.keys()),
        default="default",
        help="Eval case set (default|extended)",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Write full JSON results (default: .parrts/eval_results.json + eval_last.json)",
    )
    args = parser.parse_args(argv)

    cases = DATASETS[args.dataset]
    retriever = try_parrts_retriever(top_k=args.k)
    mode_preview = "parrts" if retriever is not None else "mock-heuristic"
    print(f"eval_retrieval mode={mode_preview} dataset={args.dataset} cases={len(cases)} k={args.k}")
    print("-" * 60)

    summary = run_eval(cases, k=args.k, retriever=retriever)

    print("-" * 60)
    print(
        f"hit_rate@{args.k} = {summary['hits']}/{summary['total']} = {summary['hit_rate']:.1%}  "
        f"mrr={summary['mrr']:.3f}  recall@{args.k}={summary['recall_at_k']:.3f}  "
        f"lat_mean={summary['latency_ms']['mean']}ms  (mode={summary['mode']})"
    )

    out_paths = [
        ROOT / ".parrts" / "eval_last.json",
        ROOT / ".parrts" / "eval_results.json",
    ]
    if args.json_out:
        out_paths.append(Path(args.json_out))
    for out in out_paths:
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(f"wrote {out}")
        except OSError as e:
            print(f"(could not write {out}: {e})")

    if summary["mode"] == "mock-heuristic" and summary["hits"] == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
