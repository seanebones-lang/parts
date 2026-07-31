"""BM25 sparse retrieval with rank_bm25 if installed, else token TF fallback."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

from parrts.models import PartRecord

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    """Corpus BM25 (or TF fallback) over part documents."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.parts: list[PartRecord] = []
        self.docs: list[list[str]] = []
        self._backend: str = "tf"
        self._bm25 = None
        self._df: dict[str, int] = {}
        self._avgdl: float = 0.0
        self._N: int = 0

    def build(self, parts: list[PartRecord], texts: list[str] | None = None) -> None:
        self.parts = list(parts)
        if texts is None:
            texts = [p.document_text() for p in parts]
        if len(texts) != len(parts):
            raise ValueError("texts/parts length mismatch")
        self.docs = [tokenize(t) for t in texts]
        self._N = len(self.docs)
        self._try_rank_bm25()
        if self._bm25 is None:
            self._build_tf_fallback()

    def _try_rank_bm25(self) -> None:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            self._bm25 = None
            self._backend = "tf"
            return
        if not self.docs:
            self._bm25 = None
            self._backend = "tf"
            return
        self._bm25 = BM25Okapi(self.docs)
        self._backend = "rank_bm25"

    def _build_tf_fallback(self) -> None:
        self._backend = "tf"
        self._df = {}
        total_len = 0
        for doc in self.docs:
            total_len += len(doc)
            for tok in set(doc):
                self._df[tok] = self._df.get(tok, 0) + 1
        self._avgdl = (total_len / self._N) if self._N else 0.0

    def _idf(self, term: str) -> float:
        df = self._df.get(term, 0)
        # BM25+ style smooth idf
        return math.log(1.0 + (self._N - df + 0.5) / (df + 0.5))

    def _score_tf(self, query_tokens: list[str]) -> list[float]:
        scores = [0.0] * self._N
        if not query_tokens or self._N == 0:
            return scores
        q_counts = Counter(query_tokens)
        for i, doc in enumerate(self.docs):
            if not doc:
                continue
            tf = Counter(doc)
            dl = len(doc)
            s = 0.0
            for term, qtf in q_counts.items():
                if term not in tf:
                    continue
                freq = tf[term]
                idf = self._idf(term)
                denom = freq + self.k1 * (1 - self.b + self.b * dl / max(self._avgdl, 1e-9))
                s += idf * (freq * (self.k1 + 1) / denom) * qtf
            scores[i] = s
        return scores

    def scores(self, query: str) -> list[float]:
        q_tokens = tokenize(query)
        if self._bm25 is not None:
            raw = self._bm25.get_scores(q_tokens)
            return [float(x) for x in raw]
        return self._score_tf(q_tokens)

    def search(
        self,
        query: str,
        top_k: int = 5,
        location: str | None = None,
    ) -> list[tuple[int, float]]:
        if self._N == 0:
            return []
        sc = self.scores(query)
        candidates: Iterable[int] = range(self._N)
        if location:
            key = location.strip().lower()
            candidates = [
                i
                for i in candidates
                if self.parts[i].location.lower() == key
                or key in self.parts[i].location.lower()
            ]
        ranked = sorted(candidates, key=lambda i: sc[i], reverse=True)
        out: list[tuple[int, float]] = []
        for i in ranked[:top_k]:
            out.append((i, float(sc[i])))
        return out

    @property
    def backend(self) -> str:
        return self._backend
