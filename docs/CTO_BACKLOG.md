# Parts — CTO Backlog

**v0.22.0** · tip track `git log -1` · https://github.com/seanebones-lang/parts

| Layer | Status |
|-------|--------|
| Email desk | Production-ready |
| DMS + transfers + ship/pay ledgers | In system |
| Live analytics / supersession / compliance | In system |
| Offline queue + PWA | **W31 shipped** |
| AI workflow automation MIN | **W32 shipped** (`src/parrts/automation`, `/results`) |
| Customer notify + load baseline | **W33 shipped** (`notification_events`, `NotifyService`, `docs/LOAD_BASELINE.md`) |
| Partner OEM / HA / RO-GL | Later — **unchecked** until contract |

## Next
Wave 34+ — partner OEM **only with real contract**. Optional: CRM/accounting when credentials; multi-site HA; SSO.

## Never
Fake Stripe/EasyPost/IMAP · OEM scraping · CDK parity · fake analytics KPIs · invent offline stock · dealer co-brand · invent CRM/GL · silent SMTP send without keys

## Cont one-liner
> Partner OEM only with credentials — else multi-tenant residuals.
