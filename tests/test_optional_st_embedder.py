"""Optional sentence-transformers / BGE embedder smoke.

Skipped unless PARRTS_TEST_ST=1 and sentence_transformers is installed.
Never runs model download in default CI.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    os.environ.get("PARRTS_TEST_ST", "").strip() not in {"1", "true", "yes"},
    reason="Set PARRTS_TEST_ST=1 to run optional ST/BGE smoke (downloads model)",
)
def test_bge_embedder_roundtrip():
    pytest.importorskip("sentence_transformers")
    from parrts.embeddings import SentenceTransformerEmbedder, resolve_embedder
    from parrts.engine import PartsRAGEngine

    emb = resolve_embedder("bge")
    assert isinstance(emb, SentenceTransformerEmbedder)
    vecs = emb.embed(["brake pads honda civic", "oil filter toyota"])
    assert vecs.shape[0] == 2
    assert vecs.shape[1] >= 32

    engine = PartsRAGEngine(root=ROOT, embedder=emb)
    # Force rebuild can be heavy; just ensure construct works
    assert engine.embedder is emb
