# Transmission Hard-Parts Vertical — Phase 1 Architecture

## Canonical Separation of Concerns

- **catalog_parts** — Canonical identity layer. Defines WHAT a part is (SKU, name, transmission family, OEM numbers, aliases, verification status).
- **inventory_levels** — Canonical physical inventory layer. Defines WHAT WE HAVE, WHERE it is, in what CONDITION, and in what quantity.
- **PartRecord / RAG models** — Derived projections for retrieval. Never the source of truth.
- **transmission package** — Domain intelligence layer (fitment, interchange, alias resolution, inquiry parsing). Consumes canonical data.
- **email pipeline** — Future consumer of transmission intelligence. Not modified in Phase 1.

## Key Design Decisions

- Condition (new/used/rebuilt/core) lives only in inventory records.
- Quantity and bin/location live only in inventory.
- `catalog_parts` may carry `transmission_family`, `transmission_variant`, and `verification_status`.
- Interchange relationships are directional and carry their own verification status.
- All 6L80/6L90 seed data is explicitly marked `verification_status = unverified` and `source = demo_seed`.

## Demo Data Philosophy

The 6L80/6L90 records seeded in Phase 1 are synthetic demonstration data only. They are not an authoritative interchange catalog. Any relationship or fitment claim that is not sourced from verified external data carries `verification_status = unverified`.

## Future Integration Points

- Transmission resolver will become a tool available to email specialists.
- Richer RAG documents will be generated from the canonical + transmission layers.
- Jev shadow mode can later be extended to also classify transmission intent.

Phase 1 deliberately stops before any production email or routing changes.