"""CLI: ingest, query, status."""

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
