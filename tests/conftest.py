"""Shared fixtures — always HashingEmbedder, isolated tmp .parrts root."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Force offline hash embedder for all tests (no network / torch)
os.environ["PARRTS_EMBEDDER"] = "hash"
# Ensure no accidental LLM calls
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)


@pytest.fixture
def tmp_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def engine(tmp_root: Path):
    from parrts.embeddings import HashingEmbedder
    from parrts.engine import PartsRAGEngine

    eng = PartsRAGEngine(root=tmp_root, embedder=HashingEmbedder(dim=384), seed=42)
    eng.build(force_inventory=True)
    return eng


@pytest.fixture
def sample_parts():
    from parrts.inventory import generate_catalog

    return generate_catalog(seed=42).all_parts()
