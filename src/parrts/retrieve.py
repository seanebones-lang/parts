"""Hybrid dense + sparse retrieval with RRF fusion."""

from __future__ import annotations

from typing import Any

import numpy as np

from parrts.bm25 import BM25Index
from parrts.embeddings import Embedder
from parrts.models import PartRecord, RankedHit
from parrts.store import VectorStore

RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[int, float]]],
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    """
    Fuse multiple ranked lists of (doc_id, score) via RRF.
    Returns list of (doc_id, rrf_score) sorted descending.
    """
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, (doc_id, _raw) in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _normalize_scores(pairs: list[tuple[int, float]]) -> dict[int, float]:
    if not pairs:
        return {}
    vals = [s for _, s in pairs]
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return {i: 1.0 for i, _ in pairs}
    return {i: (s - lo) / (hi - lo) for i, s in pairs}


class HybridRetriever:
    """Dense (vector) + sparse (BM25) with RRF; optional cross-encoder rerank stub."""

    def __init__(
        self,
        store: VectorStore,
        bm25: BM25Index,
        embedder: Embedder,
        rrf_k: int = RRF_K,
        candidate_k: int = 40,
    ) -> None:
        self.store = store
        self.bm25 = bm25
        self.embedder = embedder
        self.rrf_k = rrf_k
        self.candidate_k = candidate_k
        self._cross_encoder: Any = None
        self._try_load_reranker()

    def _try_load_reranker(self) -> None:
        try:
            from sentence_transformers import CrossEncoder

            self._cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception:
            self._cross_encoder = None

    @property
    def reranker_available(self) -> bool:
        return self._cross_encoder is not None

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        location: str | None = None,
        use_rerank: bool = False,
    ) -> list[RankedHit]:
        if len(self.store) == 0:
            return []

        q_vec = self.embedder.embed([query])[0]
        cand = max(self.candidate_k, top_k * 4)

        dense = self.store.search(q_vec, top_k=cand, location=location)
        sparse = self.bm25.search(query, top_k=cand, location=location)

        fused = reciprocal_rank_fusion([dense, sparse], k=self.rrf_k)
        dense_norm = _normalize_scores(dense)
        sparse_norm = _normalize_scores(sparse)
        dense_raw = dict(dense)
        sparse_raw = dict(sparse)

        # Map fused ids — note: dense/sparse both use indices into store.parts
        # BM25 is built on same part order as store
        hits: list[RankedHit] = []
        for doc_id, rrf in fused[: max(cand, top_k)]:
            if doc_id < 0 or doc_id >= len(self.store.parts):
                continue
            part = self.store.parts[doc_id]
            d = dense_norm.get(doc_id, 0.0)
            s = sparse_norm.get(doc_id, 0.0)
            # Combined display score: blend RRF with dense cosine if available
            cosine = dense_raw.get(doc_id, 0.0)
            score = 0.6 * max(cosine, 0.0) + 0.4 * rrf * 10  # scale rrf ~ into [0,1]
            # Prefer actual cosine when strong
            if cosine > 0:
                score = float(0.7 * max(min(cosine, 1.0), 0.0) + 0.3 * min(rrf * (self.rrf_k), 1.0))
            hits.append(
                RankedHit(
                    part=part,
                    score=float(max(0.0, min(score, 1.0))),
                    dense_score=float(dense_raw.get(doc_id, 0.0)),
                    sparse_score=float(sparse_raw.get(doc_id, 0.0)),
                    rrf_score=float(rrf),
                )
            )

        if use_rerank and self._cross_encoder is not None and hits:
            hits = self._rerank(query, hits, top_k=top_k)
        else:
            hits = hits[:top_k]

        return hits

    def _rerank(self, query: str, hits: list[RankedHit], top_k: int) -> list[RankedHit]:
        pairs = [[query, h.part.document_text()] for h in hits]
        try:
            scores = self._cross_encoder.predict(pairs)
        except Exception:
            return hits[:top_k]
        order = list(np.argsort(-np.asarray(scores)))
        reranked: list[RankedHit] = []
        for i in order[:top_k]:
            h = hits[int(i)]
            # map CE score roughly to 0-1 via sigmoid-ish clamp
            ce = float(scores[int(i)])
            norm = 1.0 / (1.0 + float(np.exp(-ce)))
            reranked.append(
                RankedHit(
                    part=h.part,
                    score=norm,
                    dense_score=h.dense_score,
                    sparse_score=h.sparse_score,
                    rrf_score=h.rrf_score,
                )
            )
        return reranked


def parts_in_order(parts: list[PartRecord]) -> list[PartRecord]:
    return list(parts)
