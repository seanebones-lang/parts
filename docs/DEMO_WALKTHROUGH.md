# Demo walkthrough

## Dealership room (preferred)

```bash
./scripts/demo_up.sh
# UI:  http://127.0.0.1:3000/parts
# API: http://127.0.0.1:8000/demo/scenarios
./scripts/demo_smoke.sh
```

Talk track: [`DEALERSHIP_PITCH.md`](DEALERSHIP_PITCH.md)

## CLI-only

```bash
pip install -e ".[dev]"
python -m parrts ingest --force
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm
python scripts/eval_retrieval.py -k 5
```

## Backend boot

```bash
pip install -e ".[dev,api]"
pip install -r backend/requirements.txt
PYTHONPATH=backend:src python scripts/verify_boot.py
```

## Tests

```bash
pytest -q
cd frontend && npm run build
```
