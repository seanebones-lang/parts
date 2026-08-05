# W29 ship notes · swarm-45

## Shipped
- `part_supersessions` + cycle-safe resolve
- `payment_events` + order payment stamps
- compliance 90d export
- analytics dead_stock / fill_rate
- FE `/supersessions`, nav, analytics cards, payments order prefill
- version **0.18.0**

## Verify
```
pytest core 86 passed
pytest dms_api + boot + commerce green
verify_boot loaded_count=18
eval hit_rate@5=100% mode=parrts
```
