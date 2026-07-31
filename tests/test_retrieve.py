"""Unit tests for hybrid retrieval + RRF (offline, HashingEmbedder)."""

from __future__ import annotations

import numpy as np

from parrts.bm25 import BM25Index, tokenize
from parrts.embeddings import HashingEmbedder
from parrts.inventory import generate_catalog
from parrts.retrieve import HybridRetriever, reciprocal_rank_fusion
from parrts.store import VectorStore


def test_tokenize():
    toks = tokenize("Brake Pads 2019 Honda Civic!")
    assert "brake" in toks
    assert "pads" in toks
    assert "2019" in toks


def test_rrf_prefers_consensus():
    # doc 1 ranks high in both lists → should win
    dense = [(1, 0.9), (2, 0.8), (3, 0.1)]
    sparse = [(1, 5.0), (3, 4.0), (2, 1.0)]
    fused = reciprocal_rank_fusion([dense, sparse], k=60)
    assert fused[0][0] == 1
    assert fused[0][1] > fused[1][1]


def test_rrf_k_constant():
    a = [(0, 1.0)]
    b = [(0, 1.0)]
    fused = reciprocal_rank_fusion([a, b], k=60)
    # 1/(60+1) + 1/(60+1)
    assert abs(fused[0][1] - 2.0 / 61.0) < 1e-9


def test_hashing_embedder_deterministic():
    emb = HashingEmbedder(dim=384, seed=42)
    a = emb.embed(["brake pads honda civic"])[0]
    b = emb.embed(["brake pads honda civic"])[0]
    assert a.shape == (384,)
    assert np.allclose(a, b)
    # similar texts closer than unrelated
    c = emb.embed(["quantum astrophysics nebula"])[0]
    sim_ab = float(np.dot(a, b))
    sim_ac = float(np.dot(a, c))
    assert sim_ab > sim_ac


def test_bm25_ranks_relevant(sample_parts):
    # use subset
    parts = [p for p in sample_parts if "Brake Pads" in p.name and "Civic" in p.name][:10]
    if len(parts) < 3:
        parts = sample_parts[:20]
    idx = BM25Index()
    idx.build(parts)
    hits = idx.search("brake pads 2019 honda civic", top_k=5)
    assert hits
    top_part = parts[hits[0][0]]
    assert "brake" in top_part.name.lower() or "civic" in top_part.name.lower()


def test_hybrid_retrieve_brake_pads():
    inv = generate_catalog(seed=42)
    parts = inv.all_parts()
    emb = HashingEmbedder(dim=384)
    texts = [p.document_text() for p in parts]
    vectors = emb.embed(texts)
    store = VectorStore(dim=384)
    store.build(parts, vectors)
    bm25 = BM25Index()
    bm25.build(parts, texts)
    ret = HybridRetriever(store=store, bm25=bm25, embedder=emb)
    hits = ret.retrieve("brake pads for 2019 Honda Civic", top_k=5)
    assert len(hits) <= 5
    assert len(hits) >= 1
    top = hits[0]
    blob = (top.part.name + " " + top.part.description).lower()
    assert "brake" in blob or "civic" in blob or "honda" in blob
    assert top.rrf_score > 0


def test_location_filter_restricts():
    inv = generate_catalog(seed=42)
    parts = inv.all_parts()
    emb = HashingEmbedder(dim=64)
    vectors = emb.embed([p.document_text() for p in parts])
    store = VectorStore(dim=64)
    store.build(parts, vectors)
    bm25 = BM25Index()
    bm25.build(parts)
    ret = HybridRetriever(store=store, bm25=bm25, embedder=emb)
    hits = ret.retrieve("oil filter", top_k=10, location="Logan Square Motors")
    assert hits
    assert all("logan" in h.part.location.lower() for h in hits)
