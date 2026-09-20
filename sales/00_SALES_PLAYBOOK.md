# Sales Playbook — Parts (NextEleven Parts Inventory System)

**Company:** NextEleven LLC  
**Product name (buyer-facing):** Parts / NextEleven Parts Inventory System  
**Engineering repo:** https://github.com/seanebones-lang/parts  
**Package:** `parrts` **v0.22.0**  
**Packet date:** 2026-08-06  
**Contact:** hello@mothership-ai.com · mothership-ai.com  
**Brand:** NextEleven Parts white-label only — never dealer co-brand in collateral

---

## 1. Ideal customer profile (ICP)

### Primary
- Multi-rooftop dealer groups (3–15 stores) with shared or loosely shared parts inventory  
- Parts managers drowning in phone/email “do you have…” requests  
- Fixed ops leaders under pressure on CSI, time-to-quote, and advisor load  
- Groups that already run a DMS but still reconcile stock manually across locations  

### Secondary
- Large independent multi-location parts retailers  
- Collisions / body groups with heavy OEM + aftermarket mix  
- Dealer groups piloting AI but burned by chatbot demos that invent inventory  

### Disqualify (for now)
- Single-store shops that only need a basic e-comm catalog (overkill)  
- Buyers demanding “fully autonomous orders with no humans” on day one  
- Prospects who refuse any pilot measurement  
- Buyers requiring full CDK/Reynolds rip-and-replace on day one  

---

## 2. Pain → value map

| Pain | Discovery question | Value proof |
|------|-------------------|-------------|
| Cross-store blindness | “How long to know if *any* store has the SKU?” | Multi-location hybrid search + parent expand |
| Advisor hold time | “What’s average handle time on parts availability?” | Sub-second retrieval offline demo + load baseline |
| Wrong availability promises | “How often do we tell a customer we have it and don’t?” | Traffic-light red/yellow → human gate |
| Email chaos | “How many people touch inbound parts email?” | Email desk specialists + G/Y/R + approve/send |
| Ops follow-through | “Who tells the customer when the order ships?” | Customer notify ledger (dry-run; SMTP when keyed) |
| AI trust | “Have you tried chatbots that make up stock?” | Retrieval-first; automation HIL on `/results` |

---

## 3. Positioning

**Category:** Dealership parts operating system with AI counter + email desk (not “generic chatbot”)  

**Pillars:**
1. **Find** — plain-language multi-store lookup + traffic light  
2. **Desk** — inbound email auto-answer with human control  
3. **Operate** — DMS core (stock, orders, transfers, supersessions, analytics)  
4. **Automate** — workflow runs + HIL + email→order MIN bar  
5. **Notify** — order/pay/ship drafts with fail-closed delivery  

**Against pure chatbots:** We retrieve, rank, and score — we don’t free-associate inventory.  
**Against DMS-only search:** Natural language + multi-store + email desk in one product.  
**Against “AI email theater”:** Structured grades, FTS archive, automation ledger you can audit.

---

## 4. Objection handling

| Objection | Response |
|-----------|----------|
| “We already have a DMS.” | Parts can run as the parts system (embedded or server) or sit beside — API-first. Not claiming full CDK parity. |
| “AI will hallucinate stock.” | Retrieval + traffic-light. Yellow/red require humans. Offline demo needs no cloud model. |
| “Is this production?” | Email desk + DMS + automation MIN + notify ledger shipped through v0.22.0. Live OEM/pay/ship/mail are key-gated and fail closed. |
| “Open source?” | No. Proprietary NextEleven LLC IP. |
| “Price?” | Rate card: pilot + rooftop bands — eng SoT `NextEleven_Parts_Rate_Card.pdf`. Contact hello@mothership-ai.com. |
| “Security?” | Demo vs production JWT; boot guard on weak secrets; deploy in your environment. |

---

## 5. Discovery call agenda (30 min)

1. Rooftops, DMS, parts org chart (5)  
2. Top 10 “do you have” query types (5)  
3. Current tools + failure modes (5)  
4. Live demo: email desk + search + orders/notify + `/results` (8)  
5. Success metrics for a 30-day pilot (5)  
6. Next step: pilot SOW or technical deep-dive (2)  

---

## 6. Pilot blueprint (30 days)

**Goal:** Prove green-path lookup + email desk handle rate + honest stock posture on the group’s real top queries.

**In scope:** catalog import or feed file, counter search, email desk offline/live, orders, analytics, automation results, notify dry-run.  
**Out of scope unless contracted:** partner OEM connector, live Stripe/EasyPost, CRM/GL bridges.

---

## 7. Never say

- Full CDK/Reynolds replacement  
- Live OEM without feed credentials  
- Silent SMTP success without keys  
- Guaranteed ROI dollars without their data  
- Any third-party dealership co-brand  

---

*NextEleven LLC · Proprietary · hello@mothership-ai.com*
