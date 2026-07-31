"""Vector store: FAISS if available else numpy brute-force cosine. Persist under .parrts/index/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from parrts.embeddings import batch_cosine, l2_normalize
from parrts.models import PartRecord

INDEX_DIRNAME = "index"
META_FILENAME = "meta.json"
VECTORS_FILENAME = "vectors.npy"
FAISS_FILENAME = "index.faiss"
PARTS_FILENAME = "parts.json"


def _has_faiss() -> bool:
    try:
        import faiss  # noqa: F401

        return True
    except ImportError:
        return False


class VectorStore:
    """In-memory vector index with disk persistence."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.vectors: np.ndarray = np.zeros((0, dim), dtype=np.float32)
        self.parts: list[PartRecord] = []
        self._faiss_index: Any = None
        self.backend: str = "numpy"

    def __len__(self) -> int:
        return len(self.parts)

    def build(self, parts: list[PartRecord], vectors: np.ndarray) -> None:
        if len(parts) != vectors.shape[0]:
            raise ValueError("parts and vectors length mismatch")
        if vectors.ndim != 2:
            raise ValueError("vectors must be 2-d")
        self.parts = list(parts)
        self.dim = int(vectors.shape[1])
        self.vectors = l2_normalize(np.asarray(vectors, dtype=np.float32))
        self._rebuild_faiss()

    def _rebuild_faiss(self) -> None:
        self._faiss_index = None
        self.backend = "numpy"
        if self.vectors.shape[0] == 0:
            return
        if not _has_faiss():
            return
        import faiss

        index = faiss.IndexFlatIP(self.dim)
        index.add(self.vectors)
        self._faiss_index = index
        self.backend = "faiss"

    def search(
        self,
        query_vec: np.ndarray,
        top_k: int = 5,
        location: str | None = None,
    ) -> list[tuple[int, float]]:
        """Return list of (local_index, cosine_score) sorted desc."""
        if len(self.parts) == 0:
            return []

        mask = np.ones(len(self.parts), dtype=bool)
        if location:
            key = location.strip().lower()
            mask = np.array(
                [
                    p.location.lower() == key or key in p.location.lower()
                    for p in self.parts
                ],
                dtype=bool,
            )
            if not mask.any():
                return []

        q = np.asarray(query_vec, dtype=np.float32).reshape(-1)
        if q.shape[0] != self.dim:
            raise ValueError(f"query dim {q.shape[0]} != store dim {self.dim}")

        if self._faiss_index is not None and location is None:
            k = min(top_k, len(self.parts))
            qn = q / max(float(np.linalg.norm(q)), 1e-12)
            scores, idxs = self._faiss_index.search(qn.reshape(1, -1), k)
            out: list[tuple[int, float]] = []
            for i, s in zip(idxs[0], scores[0], strict=False):
                if i < 0:
                    continue
                out.append((int(i), float(s)))
            return out

        # numpy path (always used when location filter active)
        sims = batch_cosine(q, self.vectors)
        sims = np.where(mask, sims, -np.inf)
        k = min(top_k, int(mask.sum()))
        if k <= 0:
            return []
        # partial top-k
        if k >= len(sims):
            order = np.argsort(-sims)
        else:
            part = np.argpartition(-sims, kth=k - 1)[:k]
            order = part[np.argsort(-sims[part])]
        return [(int(i), float(sims[i])) for i in order if np.isfinite(sims[i])]

    def save(self, root: Path | str | None = None, index_dir: Path | str | None = None) -> Path:
        base = Path(index_dir) if index_dir is not None else Path(root or Path.cwd()) / ".parrts" / INDEX_DIRNAME
        base.mkdir(parents=True, exist_ok=True)
        np.save(base / VECTORS_FILENAME, self.vectors)
        with (base / PARTS_FILENAME).open("w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in self.parts], f, indent=2)
        meta = {
            "dim": self.dim,
            "count": len(self.parts),
            "backend": self.backend,
        }
        with (base / META_FILENAME).open("w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        if self._faiss_index is not None:
            import faiss

            faiss.write_index(self._faiss_index, str(base / FAISS_FILENAME))
        elif (base / FAISS_FILENAME).exists():
            (base / FAISS_FILENAME).unlink()
        return base

    @classmethod
    def load(cls, root: Path | str | None = None, index_dir: Path | str | None = None) -> VectorStore:
        base = Path(index_dir) if index_dir is not None else Path(root or Path.cwd()) / ".parrts" / INDEX_DIRNAME
        meta_path = base / META_FILENAME
        if not meta_path.exists():
            raise FileNotFoundError(f"No index meta at {meta_path}")
        with meta_path.open(encoding="utf-8") as f:
            meta = json.load(f)
        store = cls(dim=int(meta.get("dim", 384)))
        store.vectors = np.load(base / VECTORS_FILENAME).astype(np.float32)
        with (base / PARTS_FILENAME).open(encoding="utf-8") as f:
            parts_data = json.load(f)
        store.parts = [PartRecord.from_dict(d) for d in parts_data]
        faiss_path = base / FAISS_FILENAME
        if faiss_path.exists() and _has_faiss():
            import faiss

            store._faiss_index = faiss.read_index(str(faiss_path))
            store.backend = "faiss"
        else:
            store._rebuild_faiss()
        return store
