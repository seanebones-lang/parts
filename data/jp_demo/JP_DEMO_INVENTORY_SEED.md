# JP-tailored synthetic demo inventory seed

**Status:** SYNTHETIC DEMO / PILOT DATASET — **not** verified live JP stock.

## Source workbook

| Field | Value |
|-------|--------|
| Original path used | `/Users/nexteleven/Downloads/JP_Transmission_Synthetic_Inventory.xlsx` |
| Repo copy | `data/jp_demo/JP_Transmission_Synthetic_Inventory.xlsx` |
| SHA-256 | see `jp_demo_inventory_seed.meta.json` → `source_sha256` |
| Sheets used | `Inventory` (primary); `Families`, `Part Types`, `Buy Categories`, `README` for context only |
| Inventory rows in workbook | 500 unique SKUs |

Other copies searched under Desktop / Downloads / repo: **only the Downloads path was found** (then copied into the repo).

## Generation

```bash
PYTHONPATH=src /tmp/phase4-integrated-venv/bin/python scripts/build_jp_demo_inventory.py
PYTHONPATH=src /tmp/phase4-integrated-venv/bin/python scripts/build_jp_demo_inventory.py --check
```

Outputs:

- `data/jp_demo/jp_demo_inventory_seed.csv` — importer-ready CSV
- `data/jp_demo/jp_demo_inventory_seed.meta.json` — counts, skips, hashes

Deterministic: `--check` asserts byte-identical CSV rebuild.

**No LLM** invents SKUs, identifiers, fitment, interchange, prices, or quantities.

## Field mapping

| Workbook | Import CSV | Notes |
|----------|------------|-------|
| `sku` | `sku` | JP-* pilot SKUs (new) |
| `part_name` | `name` | preserved |
| `family` | `transmission_family` | as-is from workbook |
| `unit_code` | `transmission_variant` | e.g. 4L70E under 4L60E family |
| `warehouse` | `location` | see locations |
| `qty_on_hand` | `qty` | integer ≥ 0 |
| `qty_reserved` | **omitted** | reserved stays 0 after import |
| `condition` | `condition` | mapped to `used` / `core` |
| `bin` | `bin` | as-is |
| `unit_price` | `list_price` | **synthetic** demo pricing from workbook |
| `casting_or_id` | `identifier_type=casting` + `identifier_value` | workbook column only — no invented OEM |
| `part_type` | `part_type` when pump/valve body/drum; else description | resolver-known types only in `part_type` |
| `notes` + apps | `description` | apps are **not** fitment rows |
| `make` | `oem_brand` | GM / Ford / etc. |
| — | `verification_status` | always `unverified` |
| — | `category` | `transmission_hard_parts` |

### Locations

| Workbook warehouse | DMS code | UI label |
|--------------------|----------|----------|
| Main warehouse | `CHI-N` | Main Warehouse |
| Converter cage | `CHI-N` | Main Warehouse |
| Core yard | `CHI-N` | Main Warehouse |
| Dismantling floor hold | `OHARE` | Front Counter |

No arbitrary new locations. Import uses `allow_new_locations=false`.

### Conditions

| Workbook | Import |
|----------|--------|
| Used / inspected, Used / as-removed, Used / good, Hold for inspect, Parts-only | `used` |
| Rebuildable, As-removed, Teardown candidate | `core` |

Importer only allows `new|used|rebuilt|core`.

## Canonical SKU top-ups

Existing demo identity is **preserved** (not rewritten). Three inventory top-up rows reuse:

- `4L60E-VB-01` (flagship valve body)
- `6R80-PUMP-01` (flagship pump)
- `6L80-PUMP-01` (hero pump for Tahoe NL path)

Workbook JP-* SKUs are **not** collapsed onto these SKUs (names/unit codes differ). That avoids inventing identity merges.

## What is NOT generated

- **Fitment rows** — only existing `seed.py` / demo fitments
- **Interchange rows** — only existing demo interchanges
- **Buy-side categories** (engines, wheels, starters, …) — documented in workbook `Buy Categories` sheet; **not** imported into sellable inventory
- **Reserved qty** — import leaves `reserved_qty=0`
- Live JP stock claims

## Import path (safe)

```bash
# 1) Ensure DMS + baseline demo seed exist
PYTHONPATH=src:backend /tmp/phase4-integrated-venv/bin/python -c "
from pathlib import Path
from parrts.dms.service import DmsService
from parrts.transmission.seed_loader import load_demo_seed
root = Path('.')  # or pilot root
s = DmsService(root); s.ensure_schema(); load_demo_seed(s); s.store.close()
"

# 2) Preview then commit via importer CLI
PYTHONPATH=src:backend /tmp/phase4-integrated-venv/bin/python -m parrts transmission-import \
  data/jp_demo/jp_demo_inventory_seed.csv
PYTHONPATH=src:backend /tmp/phase4-integrated-venv/bin/python -m parrts transmission-import \
  data/jp_demo/jp_demo_inventory_seed.csv --commit --source jp_demo_inventory
```

Or UI: **Data Import** → select CSV → Preview → Confirm commit.

## Client-facing language

Say:

> JP-tailored **synthetic demo inventory** for pilot evaluation.

Do **not** say:

> JP’s actual inventory / live stock.

Eval v1/v2/v2b remain engineering suites. Eval v3 remains empty until real JP counter requests exist (`experiments/JP_PILOT_50_REQUESTS.md`).
