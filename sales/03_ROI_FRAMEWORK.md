# ROI & Business Case Framework — Parts

**NextEleven LLC · For sales + finance discussions · v0.22.0**  
*Illustrative model — replace inputs with dealer actuals. Not a guarantee of results.*  
**Contact:** hello@mothership-ai.com · mothership-ai.com

---

## 1. Cost of the status quo (inputs)

| Input | Example | Your number |
|-------|---------|-------------|
| Rooftops | 7 | |
| Parts advisors / counter staff involved in availability | 12 | |
| Fully loaded cost per hour | $35 | |
| “Do you have” events per day (group) | 200 | |
| Average minutes per event today | 4 | |
| Error / comeback rate on availability | 3% | |
| Cost per comeback (goodwill + rework) | $75 | |
| Inbound parts emails / day | 40 | |
| Minutes to first meaningful reply today | 15 | |

### Daily labor minutes (example)
`200 events × 4 min = 800 min ≈ 13.3 hours/day`  
`13.3 × $35 ≈ $466/day labor on lookups alone`  
`× 250 working days ≈ $116,500/year`

### Comeback cost (example)
`200 × 3% × $75 × 250 ≈ $112,500/year`

**Directional annual drag (example only): ~$200k+** before CSI impact.

---

## 2. Value levers Parts targets

1. **Time-to-answer** on green-path queries (seconds vs minutes)  
2. **Multi-store first answer** (reduce phone trees)  
3. **Fewer wrong yeses** via yellow/red human gate  
4. **Email desk handle rate** with graded human workflow  
5. **Notify follow-through** (order/pay/ship drafts — delivery when SMTP keyed)  
6. **Advisor capacity** returned to selling / closing ROs  

---

## 3. Conservative pilot math (template)

Assume pilot improves only **30%** of events by **2 minutes** each:

```
200 × 30% × 2 min = 120 min/day saved
120/60 × $35 × 250 ≈ $17,500/year labor (single conservative lever)
```

If wrong-promise rate drops from 3% → 2%:

```
200 × 1% × $75 × 250 ≈ $37,500/year avoided rework
```

**Combined conservative illustration: ~$55k/year** on a 7-store example — before CSI or email effects.

Use this only as a **framework**. Run the pilot; put **their** numbers in the model.

---

## 4. What we measure in a pilot (not vibes)

| Metric | Why |
|--------|-----|
| hit@k on agreed golden queries | Answer quality |
| Latency p50/p95 | Counter experience (see offline `LOAD_BASELINE.md`) |
| % green vs yellow vs red (search + email) | Human load forecast |
| Override / HIL resolve rate | Trust calibration |
| Notify dry-run coverage on completed orders | Ops follow-through |
| Advisor time sample (before/after) | Labor case |

---

## 5. Investment framing

- Pilot: fixed, time-boxed, success criteria written down (rate card SoT)  
- Production: rooftop band + support + optional integration  
- Avoid “unlimited AI” pricing — price **locations + measured usage**  
- Contact: **hello@mothership-ai.com**

---

## 6. Risk to include in every proposal

- Catalog quality drives retrieval quality (garbage in → yellow/red out)  
- Live OEM / pay / ship / SMTP are credential-gated and fail closed  
- Not a full CDK parity project unless scoped and contracted  
- Offline load baseline ≠ multi-user production SLA  

---

## 7. One-slide summary for GM

> We spend six figures a year asking “do we have it?” slowly and sometimes wrong.  
> Parts answers in plain English across stores, grades weak answers, runs an email desk with human control, and we prove it on our top queries in 30 days — before we talk about ripping anything out of the DMS.

---

*NextEleven LLC · Proprietary · Not a financial guarantee*
