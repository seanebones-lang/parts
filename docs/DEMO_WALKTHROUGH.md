# Demo walkthrough (5 minutes)

Safe path for technical presentations. All commands from monorepo root with venv active.

## 1. Retrieval core (no keys)

```bash
pip install -e ".[dev]"
python -m parrts ingest --force
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm
python scripts/eval_retrieval.py -k 5
# expect: hit_rate@5 = 12/12, mode=parrts
```

## 2. Backend boot

```bash
pip install -e ".[dev,api]"
pip install -r backend/requirements.txt
PYTHONPATH=backend:src python scripts/verify_boot.py
# expect: api_v1 loaded_count=15, parrts traffic_light green
```

## 3. Tests

```bash
pytest -q
# expect: 67+ passed, skips only optional live deps
```

## 4. Frontend (optional live UI)

```bash
cd frontend && npm ci && npm run build && npm run dev
# Parts search: http://localhost:3000/parts
```

## Talking points

- **SoT:** `src/parrts` hybrid dense + BM25 + RRF + traffic-light  
- **Enterprise shell:** FastAPI 15 route groups, honest health, demo vs production auth  
- **Not claimed live:** Stripe/EasyPost, supplier scrape SLA, multi-tenant GA  
- **Legacy pitch:** `archive/legacy-pitch/` only  

Ship: https://github.com/seanebones-lang/parts
