# Swarm-45 plan (45 micro-slices)

## Batch A — Schema + CORE (1–12)
1. SCHEMA_SQL part_supersessions
2. SCHEMA_SQL payment_events + orders.payment_status soft cols
3. pg_store mirror tables
4. schema.sql doc mirror
5. DmsService.set_supersession / list / resolve_chain
6. Cycle detection on supersession
7. resolve_current_sku + seed sample supersessions
8. Engine query: supersession meta + optional hit boost note
9. DmsService.record_payment_event / list_payment_events
10. analytics: dead_stock + fill_rate + supersession_count
11. compliance_export(days=90)
12. tests/test_supersession.py RED→GREEN

## Batch B — BE/CLI (13–22)
13. RBAC catalog.supersession + compliance.export
14. DMS API supersession endpoints
15. DMS API payment events + order pay-intent bridge
16. DMS API compliance export
17. CLI dms supersede / resolve / supersessions
18. CLI dms export-audit
19. payments order-intent records DMS event when order_id int
20. test_dms_api supersession + payments
21. test_analytics dead stock
22. verify_boot still green

## Batch C — FE (23–34)
23. dms-api.ts supersession clients
24. dms-api.ts payment events + compliance
25. /supersessions page list/create/resolve
26. nav core link Supersessions
27. payments: fetch order total when order_id set
28. orders: pay link already; show payment_status badge
29. shipping: order_id query prefill notes
30. analytics FE dead stock cards
31. catalog: show superseded_by when present
32. tsc + build
33. home honesty blurb if needed
34. FE empty states fail-closed

## Batch D — Polish + ship (35–45)
35. sample OEM JSON supersession fields optional
36. docs/DMS_OEM.md supersession section
37. CTO_BACKLOG Wave 29
38. SESSION_HANDOFF
39. ROADMAP checkboxes honesty
40. version 0.18.0
41. pytest full core+smoke subset
42. eval_retrieval
43. commit
44. push origin + legacy
45. HQ activity log + swarm complete
