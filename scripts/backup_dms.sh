#!/usr/bin/env bash
# Backup DMS + email desk + RAG index (embedded profile).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="${1:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${BACKUP_DIR:-$ROOT/.parrts/backups}/$STAMP"
mkdir -p "$OUT_DIR"

copy_if() {
  local src="$1"
  local name="$2"
  if [[ -e "$src" ]]; then
    cp -a "$src" "$OUT_DIR/$name"
    echo "copied $name"
  else
    echo "skip missing $src"
  fi
}

copy_if "$ROOT/.parrts/dms.db" "dms.db"
copy_if "$ROOT/.parrts/emails.db" "emails.db"
copy_if "$ROOT/.parrts/inventory.json" "inventory.json"
copy_if "$ROOT/.parrts/inventory_from_dms.json" "inventory_from_dms.json"
if [[ -d "$ROOT/.parrts/index" ]]; then
  cp -a "$ROOT/.parrts/index" "$OUT_DIR/index"
  echo "copied index/"
fi
if [[ -d "$ROOT/.parrts/invoices" ]]; then
  cp -a "$ROOT/.parrts/invoices" "$OUT_DIR/invoices"
fi

# Optional Postgres dump when dual-mode
if [[ "${DMS_BACKEND:-sqlite}" == "postgres" && -n "${DMS_DATABASE_URL:-${DATABASE_URL:-}}" ]]; then
  URL="${DMS_DATABASE_URL:-$DATABASE_URL}"
  if command -v pg_dump >/dev/null 2>&1; then
    pg_dump "$URL" >"$OUT_DIR/dms_postgres.sql"
    echo "pg_dump -> dms_postgres.sql"
  else
    echo "pg_dump not installed; skipped postgres dump"
  fi
fi

echo "BACKUP_OK $OUT_DIR"
