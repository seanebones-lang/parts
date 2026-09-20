# Parts — Multi-Location Dealership System

**Repository:** https://github.com/seanebones-lang/parts  
**Owner:** NextEleven LLC  
**Package:** `parrts` **v0.22.0**  
**License:** Proprietary — NextEleven LLC (see `LICENSE`)  
**Contact:** hello@mothership-ai.com · mothership-ai.com  
**Brand:** NextEleven Parts white-label only

> Engineering SoT is the monorepo root `README.md`. This packet copy tracks **v0.22.0** truth (W31–W33).

---

## What this is

**Parts** is NextEleven’s dealership parts operating system:

1. **Email desk** — specialists + G/Y/R + human approve; IMAP/SMTP when keyed  
2. **AI parts lookup** — hybrid dense + BM25 + RRF + traffic light  
3. **DMS core** — multi-location catalog, inventory, customers, orders, transfers, adjust, supersessions  
4. **AI workflow automation** — runs, HIL alerts, email→order, `/results`  
5. **Customer notify** — order/pay/ship drafts + ledger; SMTP when keyed  
6. **OEM feeds** — file / http / synthetic; beat when URL set  
7. **Commerce ledgers** — Stripe + EasyPost when keyed (fail closed)  
8. **Operator UI** — Next.js including offline queue + light PWA  

```bash
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm
python -m parrts automation results
python -m parrts dms notify 1 --kind order_status --dry-run
```

---

## Honesty table

| Layer | What works today |
|-------|------------------|
| Retrieval | Hybrid RAG, traffic-light, offline tests, eval harness |
| Email desk | Production-ready offline; live mailbox when IMAP/SMTP set |
| DMS | SQLite default / Postgres dual-mode ops surfaces |
| Automation | W32 MIN bar — `/results`, CLI `parrts automation *` |
| Notify | W33 ledger + dry-run; live send only with SMTP |
| Pay / ship | Key-gated; ledgers ≠ bank/carrier settlement |
| Offline / PWA | Order/customer queue; shell SW never caches API JSON |
| Partner OEM | Contract + feed credentials only |
| CDK parity | **No** |

---

## Quick start

```bash
git clone https://github.com/seanebones-lang/parts.git
cd parts
./scripts/demo_up.sh
# http://127.0.0.1:3000/emails | /parts | /orders | /results
./scripts/demo_smoke.sh
```

See root README and `docs/SYSTEM.md` for full architecture, env, and testing.
