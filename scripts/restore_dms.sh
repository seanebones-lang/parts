#!/usr/bin/env bash
# Restore from a backup_dms.sh directory into .parrts/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-}"
if [[ -z "$SRC" || ! -d "$SRC" ]]; then
  echo "Usage: $0 /path/to/backup_dir" >&2
  exit 2
fi
mkdir -p "$ROOT/.parrts"
for f in dms.db emails.db inventory.json inventory_from_dms.json; do
  if [[ -f "$SRC/$f" ]]; then
    cp -a "$SRC/$f" "$ROOT/.parrts/$f"
    echo "restored $f"
  fi
done
if [[ -d "$SRC/index" ]]; then
  rm -rf "$ROOT/.parrts/index"
  cp -a "$SRC/index" "$ROOT/.parrts/index"
  echo "restored index/"
fi
if [[ -d "$SRC/invoices" ]]; then
  rm -rf "$ROOT/.parrts/invoices"
  cp -a "$SRC/invoices" "$ROOT/.parrts/invoices"
  echo "restored invoices/"
fi
if [[ -f "$SRC/dms_postgres.sql" ]]; then
  echo "Postgres dump present: restore manually with psql \$DMS_DATABASE_URL < $SRC/dms_postgres.sql"
fi
echo "RESTORE_OK $SRC -> $ROOT/.parrts"
