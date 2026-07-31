"""PartsRAGEngine — build index + hybrid query with traffic-light policy."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from parrts.bm25 import BM25Index
from parrts.embeddings import Embedder, HashingEmbedder, resolve_embedder
from parrts.inventory import ensure_inventory, generate_catalog
from parrts.llm import offline_answer, status_info, synthesize_answer
from parrts.models import LocationInventory, QueryResult
from parrts.policy import policy_for_hits
from parrts.retrieve import HybridRetriever
from parrts.store import VectorStore


class PartsRAGEngine:
    """
    End-to-end offline-capable parts RAG.

    build() seeds inventory, embeds documents, builds FAISS/numpy + BM25.
    query() runs hybrid RRF retrieval + traffic-light policy + optional LLM.
    """

    def __init__(
        self,
        root: Path | str | None = None,
        embedder: Embedder | None = None,
        seed: int = 42,
    ) -> None:
        self.root = Path(root) if root is not None else Path.cwd()
        self.seed = seed
        # Force hash in tests / default offline path unless caller overrides
        if embedder is not None:
            self.embedder = embedder
        else:
            # Prefer env; default hash so unit tests never download models
            env = os.environ.get("PARRTS_EMBEDDER", "hash").lower()
            if env == "hash":
                self.embedder = HashingEmbedder()
            else:
                self.embedder = resolve_embedder(env)
        self.inventory: LocationInventory | None = None
        self.store = VectorStore(dim=getattr(self.embedder, "dim", 384))
        self.bm25 = BM25Index()
        self.retriever: HybridRetriever | None = None
        self._built = False

    @property
    def built(self) -> bool:
        return self._built

    def build(self, force_inventory: bool = False) -> dict[str, Any]:
        """Generate/load inventory, embed, index dense+sparse, persist under .parrts/."""
        self.inventory = ensure_inventory(
            root=self.root, seed=self.seed, force=force_inventory
        )
        parts = self.inventory.all_parts()
        texts = [p.document_text() for p in parts]
        vectors = self.embedder.embed(texts)
        self.store = VectorStore(dim=vectors.shape[1] if len(vectors) else 384)
        self.store.build(parts, vectors)
        self.bm25 = BM25Index()
        self.bm25.build(parts, texts)
        self.store.save(root=self.root)
        self.retriever = HybridRetriever(
            store=self.store,
            bm25=self.bm25,
            embedder=self.embedder,
        )
        self._built = True
        return {
            "parts": len(parts),
            "locations": len(self.inventory.locations),
            "dim": self.store.dim,
            "dense_backend": self.store.backend,
            "sparse_backend": self.bm25.backend,
            "embedder": type(self.embedder).__name__,
            "root": str(self.root),
        }

    def load(self) -> dict[str, Any]:
        """Load persisted vector store and rebuild BM25 from stored parts."""
        self.store = VectorStore.load(root=self.root)
        parts = self.store.parts
        # rebuild inventory view
        locs: dict[str, list] = {}
        for p in parts:
            locs.setdefault(p.location, []).append(p)
        self.inventory = LocationInventory(locations=locs)
        texts = [p.document_text() for p in parts]
        self.bm25 = BM25Index()
        self.bm25.build(parts, texts)
        # Ensure embedder dim matches
        if getattr(self.embedder, "dim", None) != self.store.dim:
            if isinstance(self.embedder, HashingEmbedder):
                self.embedder = HashingEmbedder(dim=self.store.dim)
        self.retriever = HybridRetriever(
            store=self.store,
            bm25=self.bm25,
            embedder=self.embedder,
        )
        self._built = True
        return {
            "parts": len(parts),
            "dim": self.store.dim,
            "dense_backend": self.store.backend,
            "sparse_backend": self.bm25.backend,
        }

    def ensure_ready(self) -> None:
        if self._built and self.retriever is not None:
            return
        index_meta = self.root / ".parrts" / "index" / "meta.json"
        if index_meta.exists():
            try:
                self.load()
                return
            except Exception:
                pass
        self.build()

    def query(
        self,
        text: str,
        location: str | None = None,
        top_k: int = 5,
        use_llm: bool = False,
        use_rerank: bool = False,
        expand_parent: bool = False,
    ) -> QueryResult:
        from parrts.logging_utils import get_correlation_id, get_logger, log_span
        from parrts.parent_expand import expand_parent_hits

        log = get_logger("parrts.engine")
        with log_span(log, "parrts.query", q=text[:80], top_k=top_k):
            self.ensure_ready()
            assert self.retriever is not None
            hits = self.retriever.retrieve(
                text, top_k=top_k, location=location, use_rerank=use_rerank
            )
            # Parent expansion: show sibling locations for top base SKUs (no location filter)
            if expand_parent and location is None and hits:
                hits = expand_parent_hits(
                    hits,
                    self.store.parts,
                    max_siblings=7,
                    top_parents=min(3, len(hits)),
                )
            tl = policy_for_hits(hits[:top_k], location_filter=location)
            result = QueryResult(
                query=text,
                hits=hits,
                traffic_light=tl,
                location_filter=location,
                meta={
                    "top_k": top_k,
                    "dense_backend": self.store.backend,
                    "sparse_backend": self.bm25.backend,
                    "embedder": type(self.embedder).__name__,
                    "rerank": bool(use_rerank and self.retriever.reranker_available),
                    "parent_expand": bool(expand_parent and location is None),
                    "llm": status_info(),
                    "correlation_id": get_correlation_id(),
                },
            )
            if use_llm:
                answer = synthesize_answer(text, result)
                if answer is None:
                    answer = offline_answer(text, result)
                result.answer = answer
            else:
                result.answer = offline_answer(text, result)
            return result

    def status(self) -> dict[str, Any]:
        inv = self.inventory
        if inv is None:
            try:
                from parrts.inventory import load_inventory

                inv = load_inventory(root=self.root)
            except Exception:
                inv = generate_catalog(seed=self.seed)
        summary = inv.summary() if inv else {}
        index_exists = (self.root / ".parrts" / "index" / "meta.json").exists()
        return {
            "version": "0.4.2",
            "root": str(self.root.resolve()),
            "built": self._built,
            "index_exists": index_exists,
            "inventory": summary,
            "dense_backend": self.store.backend if self._built else None,
            "sparse_backend": self.bm25.backend if self._built else None,
            "embedder": type(self.embedder).__name__,
            "llm": status_info(),
            "parts_indexed": len(self.store) if self._built else 0,
            "features": {
                "hybrid_rrf": True,
                "parent_expand": True,
                "lazy_rerank": True,
                "embedders": ["hash", "st", "bge", "openai", "auto"],
            },
        }
