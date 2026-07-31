"""CLI: ingest, query, status, dms.*"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from parrts import __version__
from parrts.embeddings import HashingEmbedder, resolve_embedder
from parrts.engine import PartsRAGEngine


def _root_from_args(args: argparse.Namespace) -> Path:
    return Path(args.root).resolve() if getattr(args, "root", None) else Path.cwd()


def _make_engine(args: argparse.Namespace) -> PartsRAGEngine:
    root = _root_from_args(args)
    embedder_name = getattr(args, "embedder", None)
    if embedder_name:
        embedder = resolve_embedder(embedder_name)
    else:
        # default offline-safe
        embedder = HashingEmbedder()
    return PartsRAGEngine(root=root, embedder=embedder)


def cmd_ingest(args: argparse.Namespace) -> int:
    engine = _make_engine(args)
    info = engine.build(force_inventory=bool(args.force))
    print(json.dumps({"ok": True, "action": "ingest", **info}, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    engine = _make_engine(args)
    # Prefer existing index
    engine.ensure_ready()
    use_llm = not bool(args.no_llm)
    result = engine.query(
        text=args.text,
        location=args.location,
        top_k=args.k,
        use_llm=use_llm,
        use_rerank=bool(getattr(args, "rerank", False)),
        expand_parent=bool(getattr(args, "expand_parent", False)),
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    engine = _make_engine(args)
    if (engine.root / ".parrts" / "index" / "meta.json").exists():
        try:
            engine.load()
        except Exception:
            pass
    print(json.dumps(engine.status(), indent=2))
    return 0


def _dms_service(args: argparse.Namespace):
    from parrts.dms.service import DmsService

    return DmsService(root=_root_from_args(args))


def cmd_dms_status(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    print(json.dumps(svc.status(), indent=2))
    return 0


def cmd_dms_seed(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    stats = svc.seed_demo(
        seed=int(getattr(args, "seed", 42)),
        n_skus=int(getattr(args, "n_skus", 40)),
        locations=int(getattr(args, "locations", 7)),
    )
    if getattr(args, "reindex", False):
        stats["reindex"] = svc.reindex_rag()
    print(json.dumps({"ok": True, "action": "dms.seed", **stats}, indent=2))
    return 0


def cmd_dms_sync_oem(args: argparse.Namespace) -> int:
    from parrts.dms.oem import FileOemFeed, HttpOemFeed, SyntheticOemFeed

    svc = _dms_service(args)
    source = str(args.source).lower()
    if source == "synthetic":
        feed = SyntheticOemFeed(
            seed=int(getattr(args, "seed", 42)),
            n_skus=int(getattr(args, "n_skus", 40)),
            locations=int(getattr(args, "locations", 7)),
        )
        label = "synthetic"
    elif source == "file":
        if not args.path:
            print(json.dumps({"ok": False, "error": "--path required for --source file"}), file=sys.stderr)
            return 2
        feed = FileOemFeed(args.path)
        label = f"file:{args.path}"
    elif source == "http":
        if not args.url:
            print(json.dumps({"ok": False, "error": "--url required for --source http"}), file=sys.stderr)
            return 2
        feed = HttpOemFeed(url=args.url, token=getattr(args, "token", None))
        label = f"http:{args.url}"
    else:
        print(json.dumps({"ok": False, "error": f"unknown source: {source}"}), file=sys.stderr)
        return 2

    try:
        stats = svc.sync_oem(feed, source=label)
    except Exception as exc:
        print(json.dumps({"ok": False, "action": "dms.sync-oem", "error": str(exc)}, indent=2))
        return 1

    if getattr(args, "reindex", False):
        stats["reindex"] = svc.reindex_rag()
    print(json.dumps({"ok": True, "action": "dms.sync-oem", **stats}, indent=2))
    return 0


def cmd_dms_inventory(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    rows = svc.list_inventory(location=getattr(args, "location", None))
    print(json.dumps({"ok": True, "count": len(rows), "inventory": rows}, indent=2))
    return 0


def cmd_dms_orders(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    rows = svc.list_orders()
    print(json.dumps({"ok": True, "count": len(rows), "orders": rows}, indent=2))
    return 0


def cmd_dms_customers(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    rows = svc.list_customers()
    print(json.dumps({"ok": True, "count": len(rows), "customers": rows}, indent=2))
    return 0


def cmd_dms_reindex(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    result = svc.reindex_rag()
    print(json.dumps({"ok": bool(result.get("ok", True)), "action": "dms.reindex", **result}, indent=2))
    return 0 if result.get("ok", True) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parrts",
        description="Parrts hybrid RAG CLI for multi-location auto parts",
    )
    parser.add_argument("--version", action="version", version=f"parrts {__version__}")
    parser.add_argument(
        "--root",
        default=None,
        help="Project root for .parrts/ data (default: cwd)",
    )
    parser.add_argument(
        "--embedder",
        choices=["hash", "st", "bge", "openai", "auto"],
        default=None,
        help="Embedding backend (default: hash / PARRTS_EMBEDDER). bge=st alias for BAAI/bge-small-en-v1.5",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Build inventory + vector/BM25 index")
    p_ingest.add_argument(
        "--force",
        action="store_true",
        help="Regenerate inventory even if JSON exists",
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_query = sub.add_parser("query", help="Query parts inventory")
    p_query.add_argument("text", help="Natural language parts query")
    p_query.add_argument("--location", default=None, help="Filter by location name")
    p_query.add_argument("--no-llm", action="store_true", help="Skip LLM synthesis")
    p_query.add_argument("-k", type=int, default=5, help="Top-k hits (default 5)")
    p_query.add_argument("--rerank", action="store_true", help="Use cross-encoder if available")
    p_query.add_argument(
        "--expand-parent",
        action="store_true",
        help="Expand top hits to sibling locations (same base SKU)",
    )
    p_query.set_defaults(func=cmd_query)

    p_status = sub.add_parser("status", help="Show index/inventory status")
    p_status.set_defaults(func=cmd_status)

    # --- DMS subcommands ---
    p_dms = sub.add_parser("dms", help="Offline DMS + OEM feed operations")
    dms_sub = p_dms.add_subparsers(dest="dms_command", required=True)

    p_dms_status = dms_sub.add_parser("status", help="DMS SQLite status counts")
    p_dms_status.set_defaults(func=cmd_dms_status)

    p_dms_seed = dms_sub.add_parser("seed", help="Seed demo catalog via SyntheticOemFeed")
    p_dms_seed.add_argument("--seed", type=int, default=42)
    p_dms_seed.add_argument("--n-skus", type=int, default=40)
    p_dms_seed.add_argument("--locations", type=int, default=7)
    p_dms_seed.add_argument(
        "--reindex",
        action="store_true",
        help="Export inventory JSON and rebuild RAG index",
    )
    p_dms_seed.set_defaults(func=cmd_dms_seed)

    p_dms_sync = dms_sub.add_parser("sync-oem", help="Sync OEM feed into DMS catalog/inventory")
    p_dms_sync.add_argument(
        "--source",
        choices=["synthetic", "file", "http"],
        default="synthetic",
        help="Feed adapter (default: synthetic)",
    )
    p_dms_sync.add_argument("--path", default=None, help="JSON/CSV path for --source file")
    p_dms_sync.add_argument("--url", default=None, help="URL for --source http")
    p_dms_sync.add_argument("--token", default=None, help="Optional Bearer token for http")
    p_dms_sync.add_argument("--seed", type=int, default=42)
    p_dms_sync.add_argument("--n-skus", type=int, default=40)
    p_dms_sync.add_argument("--locations", type=int, default=7)
    p_dms_sync.add_argument(
        "--reindex",
        action="store_true",
        help="Export inventory JSON and rebuild RAG index after sync",
    )
    p_dms_sync.set_defaults(func=cmd_dms_sync_oem)

    p_dms_inv = dms_sub.add_parser("inventory", help="List DMS inventory levels")
    p_dms_inv.add_argument("--location", default=None, help="Filter by location code/name/id")
    p_dms_inv.set_defaults(func=cmd_dms_inventory)

    p_dms_orders = dms_sub.add_parser("orders", help="List DMS orders")
    p_dms_orders.set_defaults(func=cmd_dms_orders)

    p_dms_cust = dms_sub.add_parser("customers", help="List DMS customers")
    p_dms_cust.set_defaults(func=cmd_dms_customers)

    p_dms_reindex = dms_sub.add_parser(
        "reindex", help="Export DMS inventory and rebuild RAG index"
    )
    p_dms_reindex.set_defaults(func=cmd_dms_reindex)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
