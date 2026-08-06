# Parts — Session Handoff

**Package:** parrts **v0.22.0**  
**SoT:** ~/Desktop/Parrts-Dist-RAG · ship seanebones-lang/parts

## Done through Wave 33
- W32 automation MIN (runs · HIL · email→order · `/results`)
- **W33 customer notifications + load baseline:**
  - `notification_events` ledger (sqlite+pg)
  - `NotifyService` order/pay/ship/invoice templates; dry-run default; SMTP fail-closed
  - Status hook dry-run notify when customer email present (`PARRTS_NOTIFY_ON_STATUS`)
  - API `POST /dms/orders/{id}/notify` · `GET /dms/notifications`
  - CLI `parrts dms notify|notifications` · Orders UI **Notify**
  - `scripts/load_baseline.py` → `docs/LOAD_BASELINE.md`

## Next (Wave 34+)
- Partner OEM only with real contract
- CRM/accounting only with dealer credentials
- HA / RO-GL later

## Cont
> Partner OEM only with credentials — else multi-tenant residuals.

Tip: Wave 33 notify + load baseline v0.22.0
