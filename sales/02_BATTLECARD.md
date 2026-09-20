# Battlecard — Parts vs Common Alternatives

**Internal use only · NextEleven LLC · v0.22.0**  
**Contact:** hello@mothership-ai.com

---

## Elevator (15 seconds)

“Parts is multi-location dealership parts intelligence: plain-English lookup, ranked stock across rooftops, an email desk with green/yellow/red, and automation you can audit — without inventing inventory.”

---

## Vs. Public ChatGPT / generic copilots

| Them | Us |
|------|-----|
| Invents inventory | Retrieves from **your** catalog index |
| No stock policy | Green/yellow/red built in |
| Data leaves to consumer tools | Deployable in your environment |
| No dealership workflow | Email desk + DMS + notify + automation |

**Landmine question:** “If the model is wrong about stock, who gets sued — and how does your tool prevent the wrong promise?”

---

## Vs. DMS native search only

| Them | Us |
|------|-----|
| Exact part # / rigid filters | Natural language + vehicle context |
| Often single-store mental model | Multi-location ranking & expand |
| Great system of record | Parts can **be** the parts system or sit beside |
| Email is a separate mess | Built-in graded email desk |

**Landmine:** “How many steps from customer question to multi-store yes/no today?”

---

## Vs. “AI email bot” vendors

| Them | Us |
|------|-----|
| Email automation theater | Retrieval math + policy + FTS archive |
| Hard to audit answers | Structured hits + G/Y/R + automation runs |
| All-or-nothing autonomy | Human-in-loop by design |

**Landmine:** “Show me the ranked parts list, the grade, and the automation run — not just a friendly paragraph.”

---

## Vs. Building in-house RAG

| Them | Us |
|------|-----|
| 6–18 months of glue | Productized catalog + policy + DMS + desk |
| No parts-specific eval | Dealership query eval harness |
| Staffing risk | Pilot in 30 days |

**Landmine:** “Who maintains embedder drift, eval sets, and traffic-light thresholds after the first demo?”

---

## Proof points (use only measured)

- Package **v0.22.0** — W31 offline/PWA · W32 automation · W33 notify + load baseline  
- Offline hybrid RAG + automated tests + eval harness (`mode=parrts`)  
- Email desk production-ready path since v0.9.0  
- Live DMS analytics from real tables (not mock charts)  
- Fail-closed Stripe/EasyPost/OEM/SMTP  

*(Re-check `gh run list -R seanebones-lang/parts -L 1` and `docs/LOAD_BASELINE.md` before big pitches.)*

---

## When to walk away

- Buyer wants fully autonomous PO placement with no oversight  
- No willingness to measure pilot queries  
- Expectation of free unlimited IP / unauthorized OEM scraping  
- Demand for CDK parity certificate without the product work  

---

*Never co-brand third-party dealerships in decks.*
