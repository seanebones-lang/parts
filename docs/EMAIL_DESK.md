# Email Desk — selling point (production)

Inbound customer parts email is classified, answered by **section specialists**, graded **green / yellow / red**, stored in a **searchable** employee archive, and optionally synced via **IMAP/SMTP** when credentials are set.

## Grades

| Color | Meaning |
|-------|---------|
| **Green** | Handled — auto-answer OK |
| **Yellow** | Human review before send |
| **Red** | Urgent human (complaint / failure / critical stock) |

## Specialists

parts_quote · parts_order · inventory · shipping · payment · complaint · customer_service · general

Pipeline: **classify → specialist → (optional LLM polish) → grade → persist → (optional SMTP auto-send)**

## Production mailbox

| Env | Role |
|-----|------|
| `IMAP_USER` / `IMAP_PASSWORD` (+ host) | Live ingest |
| `EMAIL_USER` / `EMAIL_PASSWORD` (+ host) | SMTP send |
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

Red sends require `force=true`.

## CLI

```bash
python -m parrts email seed --clear
python -m parrts email status
python -m parrts email mailbox
python -m parrts email list --color red
python -m parrts email send 1 --dry-run
python -m parrts email fetch-imap   # needs IMAP_* 
```

## API (`/api/v1/emails`)

status · mailbox · list/search · get · ingest · process · seed · fetch-imap · `/{id}/send|override|draft|polish`

## UI

`/emails` — queue, G/Y/R, suggested reply, approve/send, override, mailbox badge

## Celery

`process_new_emails` → IMAP fetch (if configured) + process pending desk queue.
