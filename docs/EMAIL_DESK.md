# Email Desk — selling point

Inbound customer parts email is classified, answered by **section specialists**, graded **green / yellow / red**, and stored in a **searchable** employee archive.

## Grades

| Color | Meaning |
|-------|---------|
| **Green** | Handled — auto-answer OK, no further action |
| **Yellow** | Human review before send / action |
| **Red** | Urgent human (complaint, failure, critical stock/match) |

## Specialists

| Agent | Owns |
|-------|------|
| `parts_quote` | Quotes / availability via hybrid RAG + parts traffic-light |
| `parts_order` | Order intent + confirm SKU/qty |
| `inventory` | Stock-focused desk replies |
| `shipping` | Tracking / ETA playbook |
| `payment` | Invoice / billing playbook |
| `complaint` | Always escalate (red) |
| `customer_service` | Hours, warranty, general CS |
| `general` | Fallback + light RAG attempt |

Pipeline: **classify → specialist → grade → persist** (SQLite `.parrts/emails.db` + FTS5).

## CLI

```bash
python -m parrts email seed --clear
python -m parrts email status
python -m parrts email list --color red
python -m parrts email search "brake pads"
python -m parrts email ingest --subject "..." --body "..." --from-email a@b.com
python -m parrts email process --id 1
```

## API (`/api/v1/emails`)

| Method | Path | Role |
|--------|------|------|
| GET | `/status` | Counts by color/status |
| GET | `/` | List + filters + `?q=` search |
| GET | `/search?q=` | FTS search |
| GET | `/{id}` | Detail |
| POST | `/ingest` | Inbound message |
| POST | `/process` | Run specialists on pending / one id |
| POST | `/seed` | Demo mailbox |

Offline — **no Postgres**. Demo auth open when `AUTH_MODE=demo`.

## UI

- `/emails` — queue, filters, suggested reply, seed/process
- Nav: **Email Desk** (core)

## IMAP / SMTP

Not required for desk value. Live mailbox connectors are a later wave; product SoT is the offline desk + API/UI.
