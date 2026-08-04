# Parts — Production install & backup

**Product:** Parts (`parrts`) · Repo: https://github.com/seanebones-lang/parts

## 1. Single-site embedded (laptop / one rooftop)

```bash
git clone https://github.com/seanebones-lang/parts.git
cd parts
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api]"
cp .env.example .env   # set SECRET_KEY for any non-demo deploy

# Data + UI
./scripts/demo_up.sh
# http://127.0.0.1:3000/emails  (selling point)
# http://127.0.0.1:3000/catalog /orders /inventory
./scripts/demo_smoke.sh
```

Storage: `.parrts/dms.db`, `.parrts/emails.db`, `.parrts/index/`.

## 2. Server profile (Postgres DMS)

```bash
export DMS_BACKEND=postgres
export DMS_DATABASE_URL=postgresql://postgres:STRONG@db:5432/dealership_parts
export AUTH_MODE=production ENVIRONMENT=production DEBUG=false
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export POSTGRES_PASSWORD=STRONG

parrts dms migrate                 # Alembic 001_dms_core
parrts dms --backend postgres seed --reindex

docker compose -f docker-compose.prod.yml up -d --build
```

## 3. Integrations (optional keys)

| Env | Module |
|-----|--------|
| `STRIPE_SECRET_KEY` | Payments `/payments` |
| `EASYPOST_API_KEY` | Shipping `/shipping` |
| `IMAP_*` / `EMAIL_*` | Email desk live mailbox |
| `OEM_FEED_URL` (+ token) | Live OEM sync |

Fail closed without keys — no fake charges/labels/mail.

## 4. Roles (light RBAC)

`PARRTS_DEFAULT_ROLE=counter|manager|admin` (default admin in open demo).  
Permissions matrix: `parrts.rbac` · `GET /api/v1/dms/rbac?role=manager`.

| Role | Can |
|------|-----|
| counter | search, orders, invoice, pay/ship |
| manager | + catalog write/import, cancel, reindex |
| admin | + seed |

Wire JWT claim → role in production auth as next hardening step; matrix is live for policy checks.

## 5. Backup / restore

```bash
./scripts/backup_dms.sh              # -> .parrts/backups/<stamp>/
./scripts/restore_dms.sh .parrts/backups/<stamp>
# Postgres dual-mode also attempts pg_dump when DMS_BACKEND=postgres
```

Keep backups off-box. After restore: `parrts dms status` and optional `parrts dms reindex`.

## 6. Order lifecycle

`open → picking → invoiced → completed` · `cancelled` restores stock.  
Invoice PDF: `parrts dms invoice ID` or Orders UI / `GET /api/v1/dms/orders/{id}/invoice.pdf`.

## 7. Catalog admin

- UI `/catalog` — upsert SKU + CSV paste  
- CLI `parrts dms import-csv --path file.csv --reindex`  
- API `POST /api/v1/dms/catalog` · `POST /api/v1/dms/catalog/import-csv`

## 8. SSL / reverse proxy notes

Terminate TLS at nginx/Caddy; proxy `:8000` API and `:3000` UI (or FE `npm start` behind same host). Set `NEXT_PUBLIC_API_URL` to public API origin. Restrict CORS to dealer hostnames in production settings.
