# Parts — Load baseline (offline)

**Package:** `parrts` **v0.22.0** · Wave 33  
**Measured:** `2026-08-06T19:13:39+00:00`  
**Note:** local offline baseline — **not** production multi-user SLA  

Re-run:
```bash
python scripts/load_baseline.py
```

## Summary (ms)

| Metric | ms |
|--------|---:|
| `order_create_mean` | 1.96 |
| `query_mean` | 3.52 |
| `query_p50` | 2.47 |
| `query_p95` | 2.57 |

## Samples

```json
{
  "dms_seed_ms": 17.93,
  "dms_list_inventory_ms": 1.3,
  "inventory_rows": 200,
  "rag_build_ms": 19.79,
  "query_ms": [
    8.01,
    2.47,
    2.37,
    2.57,
    2.18
  ],
  "order_create_ms": [
    2.11,
    1.99,
    1.91,
    1.91,
    1.9
  ],
  "email_seed_process_ms": 47.52,
  "automation_results_ms": 0.39,
  "automation_total_runs": 8,
  "notify_dry_run_ms": 1.52
}
```

Not a multi-user load test. Partner OEM / HA still gated.  
Contact: hello@mothership-ai.com · mothership-ai.com
