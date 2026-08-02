# Parts — CTO Backlog

**Product identity:** Parts is the **dealership parts system** (not a pilot demo shell).  
**Ship:** https://github.com/seanebones-lang/parts · **parrts v0.8.0**

## Completeness (honest)

| Layer | Status |
|-------|--------|
| **Inbound email auto-answer + G/Y/R desk** | **In system** (selling point) |
| AI counter search | **In system** |
| DMS inventory/customers/orders | **In system** (embedded SQLite; server PG path next) |
| OEM file + HTTP feeds | **In system** (live when URL/token set) |
| Operator UI (core modules) | **In system** |
| Payments / shipping | **In system as integrations** (activate with keys) |
| Live IMAP/SMTP connectors | **Next** |
| Postgres multi-node HA | **Next** |
| Named OEM partner connectors | **Next** (contracts) |
| Full RO/GL accounting suite | **Next** |

## Wave 15 — Email desk revival (this ship)

- [x] Offline `parrts.email` core: store + FTS, classify, specialists, grade, pipeline, service
- [x] CLI `parrts email status|seed|list|search|get|ingest|process`
- [x] API `/api/v1/emails/*` real (not stubs)
- [x] FE `/emails` queue + search + G/Y/R + suggested reply
- [x] Nav + home CTA as selling point
- [x] `demo_up` seeds email desk
- [x] Offline tests `test_email_desk` + `test_email_api`
- [x] Docs `EMAIL_DESK.md` + SYSTEM/AGENTS update
- [ ] Live IMAP ingest + SMTP send when credentials set
- [ ] Optional LLM polish on suggested_response when keys present

## Wave 14 — Product identity + system hardening

- [x] Kill pilot/design-partner framing in README, UI, docs
- [x] `docs/SYSTEM.md` as product definition
- [x] `scripts/system_up|down|smoke` aliases
- [x] Nav/home as production product language
- [ ] Postgres dual-mode for DMS (same API)
- [ ] Payments/shipping UI bound to services when keys present
- [ ] Alembic migrations for server profile

## Never
Unauthorized OEM scraping · calling integrations “fake” when they are key-gated production modules · claiming live mailbox without IMAP/SMTP credentials

**Full roadmap:** [`ROADMAP_TO_COMPLETION.md`](ROADMAP_TO_COMPLETION.md) · **Email desk:** [`EMAIL_DESK.md`](EMAIL_DESK.md)
