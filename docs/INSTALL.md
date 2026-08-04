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

## 4. Roles (RBAC)

`PARRTS_DEFAULT_ROLE=counter|manager|admin` (default **admin** in open demo).

| Source | When |
|--------|------|
| `X-Parts-Role` header | Demo tooling (no JWT required) |
| JWT claims `role` + `parts_role` | Minted on **login** / **refresh** from `User.role` / `is_superuser` |
| `User.role` row | Fallback when claims absent |

App roles → Parts RBAC via `parrts.rbac.map_app_role`:

| App / JWT `role` | Parts role |
|------------------|------------|
| `user`, `staff`, `counter` | counter |
| `manager`, `supervisor` | manager |
| `admin`, `superuser`, `owner` | admin |

```bash
# Demo as counter (cannot seed / import CSV)
curl -H 'X-Parts-Role: counter' -X POST http://127.0.0.1:8000/api/v1/dms/seed
# → 403 Forbidden: role 'counter' cannot dms.seed

# Demo default (no header) → admin open desk
curl -X POST http://127.0.0.1:8000/api/v1/dms/seed -H 'Content-Type: application/json' \
  -d '{"seed":1,"n_skus":5,"locations":3}'
# → 200

# Production: login mints role + parts_role into access_token
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"counter1","password":"***"}' | jq '{role: .user.role, token: .access_token}'
# Decode JWT payload → {"sub":"…","role":"user","parts_role":"counter","is_superuser":false,…}

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"counter1","password":"***"}' | jq -r .access_token)

# Counter JWT cannot seed or catalog import
curl -H "Authorization: Bearer $TOKEN" -X POST http://127.0.0.1:8000/api/v1/dms/seed
# → 403

curl -H "Authorization: Bearer $TOKEN" -X POST http://127.0.0.1:8000/api/v1/dms/catalog/import \
  -F 'file=@parts.csv'
# → 403

# Inspect permission matrix
curl 'http://127.0.0.1:8000/api/v1/dms/rbac?role=manager'
```

| Role | Can |
|------|-----|
| counter | search, orders write/status/invoice, pay/ship |
| manager | + catalog write/import, cancel, reindex, OEM sync |
| admin | + seed, orgs, ACL |

Mutating DMS routes use `Depends(require_permission(...))`. Login/refresh use `AuthService.create_access_token_for_user`.

### Location ACL (multi-rooftop foundation)

```bash
PUT /api/v1/dms/orgs  {"code":"CHI","name":"Chicago"}
PUT /api/v1/dms/locations/CHI-N/org  {"org_code":"CHI"}
PUT /api/v1/dms/acl/counter1  {"location_codes":["CHI-N"]}
GET /api/v1/dms/inventory?user_key=counter1   # or header X-Parts-User
```

Empty ACL = unrestricted. Non-empty = filter inventory to those codes.

### OEM schedule

Celery task `oem.scheduled_sync` / `run_scheduled_oem_sync()` — **skips** unless `OEM_FEED_URL` set; optional `OEM_SYNC_REINDEX=true`.

| Env | Role |
|-----|------|
| `OEM_FEED_URL` | Partner HTTP catalog feed (required for live sync) |
| `OEM_FEED_TOKEN` | Optional Bearer / token header |
| `OEM_SYNC_REINDEX` | `true` → rebuild RAG after successful HTTP sync |
| `OEM_SYNC_CRON_HOUR` / `OEM_SYNC_CRON_MINUTE` | Beat cron in UTC (default **06:00**) |

Compose:
- Dev: `docker compose --profile full up -d` → `celery` + `celery-beat` with OEM env passthrough
- Prod: `docker-compose.prod.yml` includes `celery` + `celery-beat` services

```bash
# Inspect runs
parrts dms oem-runs --limit 10
curl http://127.0.0.1:8000/api/v1/dms/oem/runs
curl http://127.0.0.1:8000/api/v1/dms/status   # includes oem_sync_runs + last_oem_sync

# Manual schedule tick (skips without URL)
PYTHONPATH=backend:src python -c 'from app.tasks.oem_tasks import run_scheduled_oem_sync; print(run_scheduled_oem_sync())'
```

## 5. Backup / restore

```bash
./scripts/backup_dms.sh              # -> .parrts/backups/<stamp>/
./scripts/restore_dms.sh .parrts/backups/<stamp>
# Postgres dual-mode also attempts pg_dump when DMS_BACKEND=postgres
```

## 6. Staging commerce runbook (Wave 25)

**Never invent charges, labels, or mail.** Demo mode stays usable offline; staging live steps require real test credentials.

| Env | Surface |
|-----|---------|
| `STRIPE_SECRET_KEY` (`sk_test_…`) | `/payments` · `POST /api/v1/payments/order-intent` · Orders **Pay** |
| `EASYPOST_API_KEY` (test) | `/shipping` · `POST /api/v1/shipping/rates` · `/label` |
| IMAP/SMTP `EMAIL_*` | Email desk send; dry-run always OK |

```bash
# Fail-closed smoke (no keys required; live steps auto-skip)
./scripts/staging_commerce_smoke.sh

# With API up
./scripts/demo_up.sh
./scripts/staging_commerce_smoke.sh

# Live Stripe test intent + EasyPost rates (keys on shell AND API process)
export STRIPE_SECRET_KEY=sk_test_...
export EASYPOST_API_KEY=EZTK...
# restart API so it sees env, then:
./scripts/staging_commerce_smoke.sh
# optional label purchase after rates:
STAGING_LIVE_LABEL=1 ./scripts/staging_commerce_smoke.sh

# Real SMTP only in staging (still fail-closed if SMTP missing)
STAGING_LIVE_EMAIL=1 ./scripts/staging_commerce_smoke.sh
```

UI path: seed DMS → create order on `/orders` → **Pay** → `/payments?order_id=…` → intent. Shipping: `/shipping` rates then label when keyed. Without keys, APIs return **503** with clear detail — not fake success.

Keep backups off-box. After restore: `parrts dms status` and optional `parrts dms reindex`.

## 7. Order lifecycle

`open → picking → invoiced → completed` · `cancelled` restores stock.  
Invoice PDF: `parrts dms invoice ID` or Orders UI / `GET /api/v1/dms/orders/{id}/invoice.pdf`.

## 8. Catalog admin

- UI `/catalog` — upsert SKU + CSV paste  
- CLI `parrts dms import-csv --path file.csv --reindex`  
- API `POST /api/v1/dms/catalog` · `POST /api/v1/dms/catalog/import-csv`

## 9. SSL / reverse proxy notes

Terminate TLS at nginx/Caddy; proxy `:8000` API and `:3000` UI (or FE `npm start` behind same host). Set `NEXT_PUBLIC_API_URL` to public API origin. Restrict CORS to dealer hostnames in production settings.
