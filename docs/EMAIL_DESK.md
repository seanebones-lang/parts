# Email Desk — selling point (production)

**Package:** `parrts` **v0.22.0** · Still the primary selling surface.  
**Product:** NextEleven Parts (white-label) · Contact: hello@mothership-ai.com · mothership-ai.com

Inbound customer parts email is classified, answered by **section specialists**, graded **green / yellow / red**, stored in a **searchable** employee archive, and optionally synced via **IMAP/SMTP** when credentials are set.

Automation hook (W32): each process writes a run to `.parrts/automation.db` and may open HIL alerts / email→order draft — see `docs/AUTOMATION.md` and `/results`.

## Grades

| Color | Meaning |
|-------|---------|
| **Green** | Handled — auto-answer OK |
| **Yellow** | Human review before send |
| **Red** | Urgent human (complaint / failure / critical stock) |

## Specialists

parts_quote · parts_order · inventory · shipping · payment · complaint · customer_service · general

Pipeline: **classify → specialist → (optional LLM polish) → grade → persist → automation run → (optional SMTP auto-send)**

## Production mailbox

| Env | Role |
|-----|------|
| `IMAP_USER` / `IMAP_PASSWORD` (+ host) | Live ingest |
| `EMAIL_USER` / `EMAIL_PASSWORD` (+ host) | SMTP send (desk + customer notify) |
| `EMAIL_AUTO_SEND=true` | Auto-SMTP **green** only when SMTP configured |
| `EMAIL_FROM` | From address |

Without credentials the desk is fully usable offline (seed/API/UI). Fetch/send fail closed with clear errors — never fake delivery.

## Human desk actions

| Action | CLI / API |
|--------|-----------|
| Override grade | `parrts email override ID --color green` · `POST /{id}/override` |
| Approve mark-sent | `parrts email send ID --dry-run` · `POST /{id}/send` `{"dry_run":true}` |
| SMTP send | `parrts email send ID` · `POST /{id}/send` |
| Edit draft | `PATCH /{id}/draft` |
| Polish (LLM keys) | `POST /{id}/polish` |
| IMAP pull | `parrts email fetch-imap` · `POST /fetch-imap` |
| Draft DMS order (HIL) | `parrts automation email-to-order ID` · `POST /api/v1/automation/email/{id}/to-order` |

Red sends require `force=true`.

## CLI

```bash
python -m parrts email seed --clear
python -m parrts email status
python -m parrts email mailbox
python -m parrts email list --color red
python -m parrts email send 1 --dry-run
python -m parrts email fetch-imap   # needs IMAP_*
python -m parrts automation results
```

## API (`/api/v1/emails`)

status · mailbox · list/search · get · ingest · process · seed · fetch-imap · `/{id}/send|override|draft|polish`

Related automation: `/api/v1/automation/*`

## UI

`/emails` — queue, G/Y/R, suggested reply, approve/send, override, mailbox badge, email→order bridge  
`/results` — automation runs + HIL alerts

## Celery

`process_new_emails` → IMAP fetch (if configured) + process pending desk queue.

## Honesty

- Not a full CRM mailbox replacement  
- Not unsupervised auto-order without HIL when rulesets require confirm  
- Customer order/pay/ship notices are a separate surface (`parrts dms notify`) — see `docs/DMS_OEM.md`
