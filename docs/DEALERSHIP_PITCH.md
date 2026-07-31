# Dealership pitch — 10 minutes

**Product:** Parts (NextEleven LLC) — multi-location dealership parts AI  
**Repo:** https://github.com/seanebones-lang/parts  
**Status:** Design-partner **pilot** (not full DMS replacement)

---

## One-sentence pitch

> “Counter staff type what the customer says — *brake pads for a 2019 Civic* — and see ranked parts across your locations with a green / yellow / red confidence light so a human stays in the loop.”

---

## Demo script (live)

```bash
# Terminal 1 — from monorepo root
./scripts/demo_up.sh

# Optional check
./scripts/demo_smoke.sh
```

Open **http://localhost:3000/parts**

| Say | Type / click |
|-----|----------------|
| “Everyday counter ask” | `brake pads for 2019 Honda Civic` |
| “Oil service” | `oil filter Toyota Camry 2020` |
| “Multi-location siblings” | same query → expand / show multiple locations |
| “Low confidence / red” | nonsense query or zero-stock SKU if available |

Show JSON CLI if technical buyer:

```bash
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm | head
```

---

## What is real today

- Hybrid retrieval (dense + keyword/BM25 + RRF) over a **demo multi-location catalog** (7 locations)
- Traffic-light stock/confidence policy (green / yellow / red)
- FastAPI boot with honest health; offline-capable core
- Next.js Parts Search UI (live API or mock fallback)
- Automated tests + CI on GitHub

## What is *not* live today (say this first)

- Not connected to your live DMS / CDK / Reynolds yet
- Payments, shipping, email automation = **demo / roadmap** screens
- Not a guaranteed ROI calculator — any ROI discussion is directional only
- Production deploy needs your secrets, network, catalog feed, and auth mode

---

## Objection handling

| Objection | Answer |
|-----------|--------|
| “Is this production?” | Pilot-grade core + API shell. We harden for your stack as design partner. |
| “Our catalog is different” | Ingest path is the product work — demo catalog proves the UX and ranking. |
| “Hallucinations?” | Traffic-light + ranked SKUs + human confirm; optional LLM answer is off by default (`--no-llm`). |
| “Security?” | Demo mode open for room demo; production requires JWT + strong `SECRET_KEY`. |

---

## Close

Next step: **2-week design-partner pilot** — load a slice of their catalog, map locations, counter workflow workshop, success = counter lookup time + confidence accuracy on their phrases.
