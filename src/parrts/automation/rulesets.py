"""Operator-editable automation rulesets (JSON under .parrts/rulesets.json)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_RULESETS: dict[str, Any] = {
    "version": 1,
    "email_to_order": {
        "enabled": True,
        "require_human_confirm": True,
        "auto_create_on_green": False,
        "default_qty": 1,
        "required_fields": ["sku_or_parts", "sender_email"],
        "preferred_fields": ["vehicle_info", "quantity", "phone"],
    },
    "missing_fields": {
        "order_types": ["parts_order", "quote_request"],
        "block_auto_send_if_missing": ["sku_or_parts"],
    },
    "alerts": {
        "on_pipeline_error": True,
        "on_missing_fields": True,
        "on_red_grade": True,
    },
    "integrations": {
        "dms": True,
        "crm": False,
        "accounting": False,
        "note": "CRM/accounting connectors require dealer credentials — fail closed until configured",
    },
}


def rulesets_path(root: Path | str) -> Path:
    return Path(root).resolve() / ".parrts" / "rulesets.json"


def load_rulesets(root: Path | str) -> dict[str, Any]:
    path = rulesets_path(root)
    if not path.is_file():
        return deepcopy(DEFAULT_RULESETS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return deepcopy(DEFAULT_RULESETS)
        # merge defaults so new keys appear
        out = deepcopy(DEFAULT_RULESETS)
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                merged = dict(out[k])
                merged.update(v)
                out[k] = merged
            else:
                out[k] = v
        return out
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULT_RULESETS)


def save_rulesets(root: Path | str, data: dict[str, Any]) -> dict[str, Any]:
    path = rulesets_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = deepcopy(DEFAULT_RULESETS)
    for k, v in (data or {}).items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            m = dict(merged[k])
            m.update(v)
            merged[k] = m
        else:
            merged[k] = v
    path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return merged
