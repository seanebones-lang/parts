"""CLI: ingest, query, status, dms.*, email.*"""

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

    backend = getattr(args, "dms_backend", None)
    database_url = getattr(args, "dms_database_url", None)
    return DmsService(
        root=_root_from_args(args),
        backend=backend,
        database_url=database_url,
    )


def cmd_dms_status(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    print(json.dumps(svc.status(), indent=2))
    return 0


def cmd_dms_oem_runs(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    runs = svc.list_oem_sync_runs(limit=int(getattr(args, "limit", 20) or 20))
    print(json.dumps({"ok": True, "action": "dms.oem-runs", "count": len(runs), "runs": runs}, indent=2, default=str))
    return 0


def cmd_dms_migrate(args: argparse.Namespace) -> int:
    """Run Alembic upgrade head for Postgres DMS schema."""
    from parrts.dms.migrate import current, upgrade_head

    url = getattr(args, "dms_database_url", None)
    action = getattr(args, "migrate_action", "upgrade") or "upgrade"
    if action == "current":
        result = current(database_url=url)
    else:
        result = upgrade_head(database_url=url)
    print(json.dumps({"action": f"dms.migrate.{action}", **result}, indent=2))
    return 0 if result.get("ok") else 1


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


def cmd_dms_import_csv(args: argparse.Namespace) -> int:
    path = Path(args.path)
    text = path.read_text(encoding="utf-8")
    svc = _dms_service(args)
    result = svc.import_catalog_csv(text, source=getattr(args, "source", "csv") or "csv")
    if getattr(args, "reindex", False):
        result["reindex"] = svc.reindex_rag()
    print(json.dumps({"ok": bool(result.get("ok")), "action": "dms.import-csv", **result}, indent=2))
    return 0 if result.get("ok") else 1


def cmd_dms_set_status(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    try:
        result = svc.set_order_status(int(args.order_id), args.status)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"ok": True, "action": "dms.set-status", **result}, indent=2, default=str))
    return 0


def cmd_dms_invoice(args: argparse.Namespace) -> int:
    svc = _dms_service(args)
    try:
        result = svc.write_invoice_pdf(int(args.order_id), path=getattr(args, "out", None))
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"ok": True, "action": "dms.invoice", **result}, indent=2))
    return 0


def _email_service(args: argparse.Namespace):
    from parrts.email import EmailService

    return EmailService(root=_root_from_args(args))


def cmd_email_status(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    print(json.dumps(svc.status(), indent=2))
    return 0


def cmd_email_seed(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    result = svc.seed_demo(process=not bool(args.no_process), clear=bool(args.clear))
    print(json.dumps({"ok": True, "action": "email.seed", **result}, indent=2))
    return 0


def cmd_email_process(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    eid = getattr(args, "id", None)
    result = svc.process(email_id=int(eid) if eid is not None else None, limit=int(args.limit))
    print(json.dumps({"ok": True, "action": "email.process", **result}, indent=2))
    return 0


def cmd_email_list(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    rh = None
    if getattr(args, "requires_human", False):
        rh = True
    rows = svc.list(
        status=args.status,
        traffic_light=args.color,
        email_type=args.type,
        requires_human=rh,
        limit=int(args.limit),
    )
    print(json.dumps({"ok": True, "count": len(rows), "emails": rows}, indent=2))
    return 0


def cmd_email_search(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    rows = svc.search(args.query, limit=int(args.limit))
    print(json.dumps({"ok": True, "count": len(rows), "emails": rows}, indent=2))
    return 0


def cmd_email_get(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    row = svc.get(int(args.id))
    if not row:
        print(json.dumps({"ok": False, "error": "not_found", "id": args.id}, indent=2))
        return 1
    print(json.dumps({"ok": True, "email": row}, indent=2))
    return 0


def cmd_email_ingest(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    row = svc.ingest(
        subject=args.subject,
        body_text=args.body,
        sender_email=args.from_email,
        sender_name=args.from_name or "",
        process=not bool(args.no_process),
    )
    print(json.dumps({"ok": True, "action": "email.ingest", "email": row}, indent=2))
    return 0


def cmd_email_mailbox(args: argparse.Namespace) -> int:
    from parrts.email.mail_io import mailbox_status

    print(json.dumps(mailbox_status(), indent=2))
    return 0


def cmd_email_fetch(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    try:
        result = svc.fetch_imap(limit=int(args.limit), process=not bool(args.no_process))
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"ok": True, "action": "email.fetch-imap", **result}, indent=2))
    return 0


def cmd_email_send(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    try:
        row = svc.approve_and_send(
            int(args.id),
            force=bool(args.force),
            dry_run=bool(args.dry_run),
        )
    except (KeyError, ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"ok": True, "action": "email.send", "email": row}, indent=2))
    return 0


def cmd_email_override(args: argparse.Namespace) -> int:
    svc = _email_service(args)
    try:
        row = svc.override(int(args.id), color=args.color, notes=args.notes)
    except (KeyError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"ok": True, "action": "email.override", "email": row}, indent=2))
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

    # --- DMS subcommands ---
    p_dms = sub.add_parser("dms", help="DMS + OEM feed operations (sqlite|postgres)")
    p_dms.add_argument(
        "--backend",
        dest="dms_backend",
        choices=["sqlite", "postgres"],
        default=None,
        help="Override DMS_BACKEND (default: env or sqlite)",
    )
    p_dms.add_argument(
        "--database-url",
        dest="dms_database_url",
        default=None,
        help="Postgres URL (or set DMS_DATABASE_URL / DATABASE_URL)",
    )
    dms_sub = p_dms.add_subparsers(dest="dms_command", required=True)

    p_dms_status = dms_sub.add_parser("status", help="DMS status counts (backend + db)")
    p_dms_status.set_defaults(func=cmd_dms_status)

    p_dms_oem_runs = dms_sub.add_parser(
        "oem-runs", help="List recent oem_sync_runs (newest first)"
    )
    p_dms_oem_runs.add_argument("--limit", type=int, default=20)
    p_dms_oem_runs.set_defaults(func=cmd_dms_oem_runs)

    p_dms_migrate = dms_sub.add_parser(
        "migrate",
        help="Alembic upgrade head for Postgres DMS (requires DMS_DATABASE_URL)",
    )
    p_dms_migrate.add_argument(
        "migrate_action",
        nargs="?",
        default="upgrade",
        choices=["upgrade", "current"],
        help="upgrade (default) or current",
    )
    p_dms_migrate.set_defaults(func=cmd_dms_migrate)

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

    p_dms_csv = dms_sub.add_parser("import-csv", help="Import catalog CSV (sku,name required)")
    p_dms_csv.add_argument("--path", required=True, help="CSV file path")
    p_dms_csv.add_argument("--source", default="csv")
    p_dms_csv.add_argument("--reindex", action="store_true")
    p_dms_csv.set_defaults(func=cmd_dms_import_csv)

    p_dms_st = dms_sub.add_parser("set-status", help="Set order lifecycle status")
    p_dms_st.add_argument("order_id", type=int)
    p_dms_st.add_argument(
        "status",
        choices=["open", "picking", "invoiced", "completed", "cancelled"],
    )
    p_dms_st.set_defaults(func=cmd_dms_set_status)

    p_dms_inv = dms_sub.add_parser("invoice", help="Write invoice PDF for order")
    p_dms_inv.add_argument("order_id", type=int)
    p_dms_inv.add_argument("--out", default=None, help="Output PDF path")
    p_dms_inv.set_defaults(func=cmd_dms_invoice)

    # --- Email desk (selling point) ---
    p_email = sub.add_parser("email", help="Inbound email auto-answer desk (G/Y/R)")
    email_sub = p_email.add_subparsers(dest="email_command", required=True)

    p_email_status = email_sub.add_parser("status", help="Email desk SQLite stats")
    p_email_status.set_defaults(func=cmd_email_status)

    p_email_seed = email_sub.add_parser("seed", help="Seed demo inbound emails + process")
    p_email_seed.add_argument("--clear", action="store_true", help="Wipe desk DB first")
    p_email_seed.add_argument("--no-process", action="store_true", help="Ingest only")
    p_email_seed.set_defaults(func=cmd_email_seed)

    p_email_process = email_sub.add_parser("process", help="Run specialist pipeline")
    p_email_process.add_argument("--id", type=int, default=None, help="Single email id")
    p_email_process.add_argument("--limit", type=int, default=50)
    p_email_process.set_defaults(func=cmd_email_process)

    p_email_list = email_sub.add_parser("list", help="List desk emails (priority sort)")
    p_email_list.add_argument("--status", default=None)
    p_email_list.add_argument("--color", default=None, help="green|yellow|red")
    p_email_list.add_argument("--type", default=None, help="email_type filter")
    p_email_list.add_argument("--requires-human", action="store_true")
    p_email_list.add_argument("--limit", type=int, default=100)
    p_email_list.set_defaults(func=cmd_email_list)

    p_email_search = email_sub.add_parser("search", help="Full-text search email desk")
    p_email_search.add_argument("query", help="Search query")
    p_email_search.add_argument("--limit", type=int, default=50)
    p_email_search.set_defaults(func=cmd_email_search)

    p_email_get = email_sub.add_parser("get", help="Get email by id")
    p_email_get.add_argument("id", type=int)
    p_email_get.set_defaults(func=cmd_email_get)

    p_email_ingest = email_sub.add_parser("ingest", help="Ingest one inbound email")
    p_email_ingest.add_argument("--subject", required=True)
    p_email_ingest.add_argument("--body", required=True)
    p_email_ingest.add_argument("--from-email", required=True)
    p_email_ingest.add_argument("--from-name", default="")
    p_email_ingest.add_argument("--no-process", action="store_true")
    p_email_ingest.set_defaults(func=cmd_email_ingest)

    p_email_mb = email_sub.add_parser("mailbox", help="IMAP/SMTP config status (no secrets)")
    p_email_mb.set_defaults(func=cmd_email_mailbox)

    p_email_fetch = email_sub.add_parser("fetch-imap", help="Fetch IMAP when credentials set")
    p_email_fetch.add_argument("--limit", type=int, default=20)
    p_email_fetch.add_argument("--no-process", action="store_true")
    p_email_fetch.set_defaults(func=cmd_email_fetch)

    p_email_send = email_sub.add_parser("send", help="Approve/send reply (SMTP or dry-run)")
    p_email_send.add_argument("id", type=int)
    p_email_send.add_argument("--force", action="store_true", help="Allow send on red")
    p_email_send.add_argument(
        "--dry-run",
        action="store_true",
        help="Mark responded without SMTP",
    )
    p_email_send.set_defaults(func=cmd_email_send)

    p_email_ov = email_sub.add_parser("override", help="Human override traffic-light color")
    p_email_ov.add_argument("id", type=int)
    p_email_ov.add_argument("--color", required=True, choices=["green", "yellow", "red"])
    p_email_ov.add_argument("--notes", default=None)
    p_email_ov.set_defaults(func=cmd_email_override)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
