# Live Demo Script — Parts (12–15 minutes)

**Goal:** Buyer believes (1) natural language works, (2) multi-store is real, (3) traffic-light + email grades protect them, (4) automation/notify paths are auditable, (5) path to production is sane.  
**Package:** `parrts` **v0.22.0** · Contact: hello@mothership-ai.com  
**Brand:** NextEleven Parts white-label only

---

## Setup (before the call)

```bash
cd ~/Desktop/Parrts-Dist-RAG   # or cloned parts repo
source .venv/bin/activate
./scripts/demo_up.sh          # preferred — API :8000 + UI :3000
# or offline-only:
# pip install -e ".[dev]" -q && python -m parrts dms seed --reindex
```

Have a second screen or shared terminal + browser.

---

## Minute 0–2 — Frame

> “Most AI demos write a nice paragraph. We show ranked parts, a green/yellow/red, an email desk with human control, and an automation results page you can audit. No cloud keys required for the core path.”

Ask: “What’s your most common availability question?” (park it for later)

---

## Minute 2–5 — Core query

```bash
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm --expand-parent
```

**Callouts:** hits include SKU, location, stock, scores; `traffic_light`; multi-store siblings.

---

## Minute 5–8 — Email desk (selling point)

Browser: `http://127.0.0.1:3000/emails`  
- Seeded G/Y/R queue, draft reply, approve/send dry-run  
- Optional CLI: `parrts email status`

---

## Minute 8–11 — Ops + notify + automation

Browser:
- `/orders` — lifecycle + **Notify** (dry-run customer notice; needs email on customer)  
- `/results` — automation runs + HIL alerts  
- `/analytics` — real DMS tables only  

CLI:

```bash
parrts automation results
parrts dms analytics
# parrts dms notify ORDER_ID --kind order_status --dry-run
```

---

## Minute 11–13 — Trust & humans

Explain yellow/red (search + email).  
Automation email→order is preview-first; confirm reserves stock.  
Notify dry-run ≠ delivered mail — SMTP when they connect credentials.

```bash
python scripts/eval_retrieval.py | tail -5
```

---

## Minute 13–15 — Close

- 30-day pilot, 1–3 rooftops  
- Success = hit-rate + latency + override rate you accept  
- Not claiming full CDK parity  
- Proprietary NextEleven IP · **hello@mothership-ai.com**  

**Ask:** “Who owns the golden query list on your side — parts manager or fixed ops?”

---

## Failure modes (and recovery)

| Glitch | Recovery |
|--------|----------|
| `No module named parrts` | `pip install -e ".[dev]"` or `PYTHONPATH=src` |
| Empty index | `parrts dms seed --reindex` / `parrts ingest --force` |
| Notify errors “no customer email” | Create/update customer with email first |
| Docker questions | “Production path optional today; core demo is offline.” |
| “Where’s Stripe?” | “Fail closed until keys — lookup + desk are the wedge.” |

---

## Do not do on demo

- Promise live supplier scraping  
- Invent ROI dollars  
- Show another customer’s data  
- Claim open source  
- Claim CDK parity  
- Co-brand any third-party dealership  
- Fake SMTP success without credentials  
