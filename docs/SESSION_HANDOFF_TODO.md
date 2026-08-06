# Parts — Session Handoff

**Package:** parrts **v0.22.0**  
**SoT:** ~/Desktop/Parrts-Dist-RAG · ship seanebones-lang/parts  
**Tip track:** `git log -1` (W33 notify + load baseline landed on main)  
**Brand:** NextEleven Parts white-label only  
**Contact:** hello@mothership-ai.com · mothership-ai.com

## Done through Wave 33

- **W31** offline mutation queue (orders/customers) + PWA install shell (manifest + SW; never caches API JSON)
- **W32** automation MIN:
  - `src/parrts/automation/**` · `.parrts/automation.db` · rulesets
  - Email process → run ledger · HIL alerts · email→order bridge
  - API `/api/v1/automation/*` · FE `/results` · CLI `parrts automation *`
- **W33** customer notifications + load baseline:
  - `notification_events` ledger (sqlite + postgres)
  - `NotifyService` order/pay/ship/invoice templates; dry-run default; SMTP fail-closed
  - Status hook dry-run notify when customer email present (`PARRTS_NOTIFY_ON_STATUS`, default on)
  - Live send only with SMTP + confirm / `PARRTS_AUTO_NOTIFY`
  - API `POST /dms/orders/{id}/notify` · `GET /dms/notifications`
  - CLI `parrts dms notify|notifications` · Orders UI **Notify**
  - `scripts/load_baseline.py` → `docs/LOAD_BASELINE.md` (offline timings, not prod SLA)

## Next (Wave 34+)

- Partner OEM only with real contract — **leave unchecked** until then
- CRM/accounting only with dealer credentials
- HA / RO-GL later

## Cont

> Partner OEM only with credentials — else multi-tenant residuals.

## Docs SoT after ship

README · SYSTEM · ROADMAP · ROADMAP_TO_COMPLETION · CTO_BACKLOG · AUTOMATION · DMS_OEM · this handoff
