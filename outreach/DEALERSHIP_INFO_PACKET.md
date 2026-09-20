# Dealership Information Packet — Parts

**Prepared by:** NextEleven LLC  
**Product:** Parts — Multi-Location Dealership Parts AI  
**Document date:** 2026-07-31  
**Classification:** Buyer-facing information (proprietary product)

---

## 1. Executive overview

**Parts** helps multi-rooftop dealer groups answer parts availability questions in plain English—across locations—while signaling when a human should review the result.

It is designed to sit **alongside** your DMS and counter processes, not to rip them out on day one.

---

## 2. Business problems addressed

1. **Time cost** of repeated availability research  
2. **Cross-store opacity** (“call the other store”)  
3. **Incorrect availability promises** to customers and advisors  
4. **Inconsistent process** between rooftops  
5. **Distrust of chatbots** that fabricate inventory  

---

## 3. Solution summary

| Capability | Description |
|------------|-------------|
| Natural language lookup | e.g. “brake pads for 2019 Honda Civic” |
| Hybrid retrieval | Combines meaning-based and keyword-style ranking |
| Multi-location results | Ranked SKUs with location and stock posture |
| Traffic-light confidence | Green / yellow / red guidance for human-in-the-loop |
| Optional expansion | Show sibling locations for the same base part |
| API & UI paths | Counter tools and system integration options |
| Offline-capable core | Demo and retrieval without cloud LLM keys |

---

## 4. Typical users

- Parts managers and counter staff  
- Service advisors (availability checks)  
- Fixed operations directors  
- IT / innovation leads evaluating AI with guardrails  

---

## 5. Deployment shapes

### A. Pilot (recommended start)
- 1–3 rooftops  
- Seed catalog or agreed export  
- Golden query list (your top questions)  
- Read-only / shadow mode  
- 30 days, written success metrics  

### B. Group production (lookup)
- Broader rooftop rollout  
- SSO / network controls as required  
- Monitoring of latency and override rates  

### C. Enterprise integration (phase)
- DMS / inventory feed integration  
- Production auth (`AUTH_MODE=production` + JWT)  
- Optional payments/shipping processors when contracted  
- Optional pgvector/Postgres for large centralized catalogs  

---

## 6. Security & data posture (summary)

- **Proprietary software** owned by NextEleven LLC — not open source  
- Catalog and query data should be handled under your MSA/NDA  
- Production deployments should not expose admin APIs to the public internet without auth  
- Demo mode exists for controlled demonstrations; production mode expects stronger auth  
- Live third-party processors (payments, shipping, LLMs) only when you supply credentials and approve scope  

*Full legal terms are in the license / MSA — this packet is informational.*

---

## 7. What is included vs optional

| Included in core narrative | Optional / key-gated |
|----------------------------|----------------------|
| Hybrid parts retrieval | Cloud LLM answer wording |
| Traffic-light policy | Live Stripe payments |
| Multi-location model | Live EasyPost / carrier labels |
| CLI + API + web UI paths | Heavy supplier web scraping |
| Evaluation harness for query quality | Custom DMS connectors |

---

## 8. Implementation prerequisites (pilot)

- Named business owner (parts or fixed ops)  
- Named technical contact  
- List of locations and naming conventions  
- Top 20–50 real availability questions  
- Sample catalog extract **or** agreement to start on demonstration catalog then swap  
- Network path for install (laptop pilot vs server)  

---

## 9. Success metrics (suggested)

| Metric | Example target (negotiate) |
|--------|----------------------------|
| hit@5 on golden queries | ≥ 90% |
| Median answer latency | < 2 seconds on agreed hardware |
| Yellow/red rate | Understood and staffed |
| Advisor time sample | Directional reduction on green-path queries |
| User trust survey | “Would use daily” from counter cohort |

---

## 10. Commercial model (high level)

1. **Pilot fee** — time-boxed, fixed  
2. **Subscription** — per rooftop / tier  
3. **Integration SOW** — if DMS or custom SSO required  

Formal quotes follow discovery. No public unlimited free tier.

---

## 11. FAQ

**Q: Does this replace our DMS?**  
A: No. It accelerates availability intelligence and can integrate over time.

**Q: Will it make up stock levels?**  
A: The design is retrieval-first with confidence gating. Weak results surface as yellow/red for humans.

**Q: Do we need internet AI keys?**  
A: Not for core lookup demos. Keys unlock optional wording and live processors.

**Q: Can it run in our VPC?**  
A: Architecture supports controlled deployment; scope in enterprise SOW.

**Q: Is the GitHub repo public-open source?**  
A: The product is **proprietary**. Access and use require NextEleven authorization.

**Q: How fast to first value?**  
A: Same-day technical demo on sample catalog; pilot value in weeks, not years.

---

## 12. Sample interaction (illustrative)

**Input:** brake pads for 2019 Honda Civic  

**Output (conceptual):**  
- Ranked SKUs with location and quantity  
- Similarity / rank signals  
- Traffic-light: green when match and stock support a confident answer  
- Optional: expand to other stores carrying the same base SKU  

---

## 13. About NextEleven LLC

NextEleven builds practical AI systems for real operations—not slideware.  
Parts is our multi-location dealership parts platform.

**Engineering reference:** https://github.com/seanebones-lang/parts  

---

## 14. Next steps

1. Discovery call (pain, rooftops, DMS)  
2. NDA if required  
3. Live demo on agreed queries  
4. Pilot SOW with metrics  
5. Readout and production decision  

**Contact:** Your NextEleven representative  

---

## Appendix A — Glossary

| Term | Meaning |
|------|---------|
| Hybrid retrieval | Combining vector-style and keyword-style search |
| Traffic-light | green/yellow/red answer policy |
| Golden queries | Fixed evaluation questions for quality |
| Rooftop | Physical dealership location |
| HITL | Human-in-the-loop |

## Appendix B — Document control

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-07-31 | Initial packet with health-check-aligned claims |

---

© 2026 NextEleven LLC. All rights reserved.  
This document does not grant a license to the software.
