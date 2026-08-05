# Parts — Session Handoff

**Package:** parrts **v0.18.0**  
**SoT:** ~/Desktop/Parrts-Dist-RAG · ship seanebones-lang/parts

## Done through Wave 29
- Email desk, DMS, commerce key-gated, JWT mint, org FE, OEM beat, staging smoke
- Transfers + stock receive/adjust audit
- Live analytics (W28)
- **Supersession chains** — `part_supersessions` · resolve chain · API/CLI/FE `/supersessions` · query meta redirects
- **Payment ledger** — `payment_events` on orders · order-intent records DMS when order_id int · fail-closed
- **Compliance export** — `GET /dms/compliance/export` · `parrts dms export-audit`
- Analytics: dead_stock + fill_rate + supersession/payment counts

## Next (Wave 30+)
- Partner OEM only with real contract
- Full multi-rooftop HA / RO-GL later
- Optional: ship-from-order EasyPost UX, PWA

## Cont
> Partner OEM / M3 only with credentials — else polish GA residuals (ship UX, PWA).

Tip: Wave 29 supersession + ledger v0.18.0
