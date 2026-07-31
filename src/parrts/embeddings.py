"""Embedding backends: deterministic hash (default for tests), optional ST/OpenAI."""

from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Protocol, runtime_checkable

import numpy as np

DEFAULT_DIM = 384
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@runtime_checkable
class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return float32 array shape (n, dim), L2-normalized rows preferred."""
        ...


class HashingEmbedder:
    """Deterministic bag-of-words hashed into fixed dim — no torch/network."""

    def __init__(self, dim: int = DEFAULT_DIM, seed: int = 42) -> None:
        self.dim = dim
        self.seed = seed

    def _token_index(self, token: str) -> int:
        h = hashlib.sha256(f"{self.seed}:{token}".encode()).hexdigest()
        return int(h[:16], 16) % self.dim

    def _token_sign(self, token: str) -> float:
        h = hashlib.md5(f"{self.seed}:sign:{token}".encode()).hexdigest()
        return 1.0 if int(h[:8], 16) % 2 == 0 else -1.0

    def embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = tokenize(text)
        if not tokens:
            return vec
        for tok in tokens:
            idx = self._token_index(tok)
            vec[idx] += self._token_sign(tok)
        # TF scaling
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.vstack([self.embed_one(t) for t in texts])


class SentenceTransformerEmbedder:
    """Optional sentence-transformers backend (downloads model on first use)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "sentence-transformers is required for SentenceTransformerEmbedder. "
                "Install with: pip install parrts[embeddings]"
            ) from exc
        self._model = SentenceTransformer(model_name)
        dim = self._model.get_sentence_embedding_dimension()
        self.dim = int(dim if dim is not None else DEFAULT_DIM)
        self.model_name = model_name

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        arr = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return np.asarray(arr, dtype=np.float32)


class OpenAIEmbedder:
    """Optional OpenAI embeddings when OPENAI_API_KEY is set."""

    def __init__(self, model: str = "text-embedding-3-small", dim: int = DEFAULT_DIM) -> None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not set")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "openai package required. Install with: pip install parrts[openai]"
            ) from exc
        self._client = OpenAI()
        self.model = model
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        resp = self._client.embeddings.create(model=self.model, input=texts)
        vectors = [np.asarray(item.embedding, dtype=np.float32) for item in resp.data]
        mat = np.vstack(vectors)
        # L2 normalize
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        mat = mat / norms
        self.dim = mat.shape[1]
        return mat


def resolve_embedder(name: str | None = None) -> Embedder:
    """
    Choose embedder via argument or PARRTS_EMBEDDER env (st|hash|openai).
    Default: hash (offline-safe). Prefer st when explicitly requested and installed.
    """
    choice = (name or os.environ.get("PARRTS_EMBEDDER") or "hash").strip().lower()
    if choice in {"hash", "hashing", "bow"}:
        return HashingEmbedder()
    if choice in {"st", "sentence", "sentence-transformers", "bge"}:
        try:
            return SentenceTransformerEmbedder()
        except Exception:
            return HashingEmbedder()
    if choice in {"openai", "oai"}:
        try:
            return OpenAIEmbedder()
        except Exception:
            return HashingEmbedder()
    # auto: prefer ST if installed and env not forcing hash
    if choice == "auto":
        try:
            import sentence_transformers  # noqa: F401

            return SentenceTransformerEmbedder()
        except Exception:
            return HashingEmbedder()
    return HashingEmbedder()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-d vectors."""
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return (mat / norms).astype(np.float32)


def batch_cosine(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine sims of query (d,) against matrix (n, d). Assumes optional L2 norms."""
    if matrix.size == 0:
        return np.zeros(0, dtype=np.float32)
    q = query.astype(np.float32).reshape(-1)
    qn = float(np.linalg.norm(q))
    if qn == 0.0:
        return np.zeros(matrix.shape[0], dtype=np.float32)
    q = q / qn
    m_norms = np.linalg.norm(matrix, axis=1)
    m_norms = np.maximum(m_norms, 1e-12)
    m = matrix / m_norms[:, None]
    return (m @ q).astype(np.float32)


# silence unused import warning helpers
_ = math
