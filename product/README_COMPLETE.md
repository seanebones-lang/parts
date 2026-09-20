# Parts Platform — Complete README (sales/engineering copy)

> Canonical engineering README lives in the git repo root.  
> Repo: https://github.com/seanebones-lang/parts · Package `parrts` **v0.22.0** · NextEleven LLC  
> Contact: **hello@mothership-ai.com** · mothership-ai.com  
> Brand: **NextEleven Parts** white-label only

---

## One-sentence pitch

**Parts** finds the right part across every rooftop in your group — in plain English — with green/yellow/red confidence, a production email desk, offline DMS ops, automation results, and customer notify when you connect mail.

## Product promise

| Buyer pain | Parts response |
|------------|----------------|
| “Do we have brake pads for a 2019 Civic at any store?” | Hybrid search + multi-location expand |
| Techs and advisors buried in email/DMS lookups | Email desk specialists + G/Y/R + human approve |
| Wrong promise to customer on stock | Red/yellow forces human review |
| Multi-store inventory is invisible | Shared catalog + location filter + transfers |
| Fear of “black box AI” | Retrieval-first; automation HIL; no invented stock |

## What’s real vs roadmap (v0.22.0)

**Real today (measured):**

- Hybrid RAG core + traffic-light + eval harness  
- Email desk (IMAP/SMTP when keyed)  
- DMS SQLite/Postgres: catalog, inventory, orders, transfers, stock adjust, supersessions  
- Live analytics from real DMS tables  
- Pay/ship ledgers + Stripe/EasyPost when keyed (fail closed)  
- Offline order/customer queue + light PWA shell (W31)  
- AI workflow automation MIN + `/results` (W32)  
- Customer notify ledger + Orders **Notify** dry-run (W33)  
- Offline load baseline (`docs/LOAD_BASELINE.md`)  

**Needs your environment:** feed URL/token for live OEM; SMTP for live mail; Stripe/EasyPost keys for live commerce.

**Not claimed:** CDK/Reynolds parity, unattended full-agent SLA, automatic OEM portal scraping, guaranteed ROI dollars, dealer co-brand.

## Stack (short)

- Python 3.11+ · `parrts` hybrid RAG · FastAPI · LangGraph · Postgres dual-mode DMS · Redis/Celery · Next.js 15  
- Ship: https://github.com/seanebones-lang/parts  

## 5-minute demo script

1. `./scripts/demo_up.sh` → open `/emails`, `/parts`, `/orders`, `/results`  
2. `parrts query "brake pads for 2019 Honda Civic" --no-llm`  
3. `parrts automation results`  
4. Orders **Notify** dry-run (order needs customer email)  
5. Optional: `python scripts/load_baseline.py`

## Contact

**hello@mothership-ai.com** · mothership-ai.com  
Technical SoT: repo root `README.md` · `docs/SYSTEM.md`
