"""Parent-document expansion for multi-location SKUs.

Parts are stored per-location (e.g. BP-HC19-L1 … L7). After hybrid retrieval,
expand hits to include sibling locations for the same base SKU so the UI can
show multi-store availability without a second search.
"""

from __future__ import annotations

import re
from typing import Iterable

from parrts.models import PartRecord, RankedHit

_LOC_SUFFIX = re.compile(r"-L\d+$", re.IGNORECASE)


def base_sku(sku: str) -> str:
    """Strip location suffix (-L1 … -Ln) to get the parent SKU key."""
    return _LOC_SUFFIX.sub("", sku.strip())


def expand_parent_hits(
    hits: list[RankedHit],
    all_parts: Iterable[PartRecord],
    *,
    max_siblings: int = 7,
    top_parents: int | None = None,
) -> list[RankedHit]:
    """
    For each unique base SKU in `hits`, attach sibling location rows.

    Sibling hits keep the parent's rank score (slightly decayed) so ordering
    stays driven by the original retrieval rank. Already-present SKUs are not
    duplicated.
    """
    if not hits:
        return []

    parts_list = list(all_parts)
    by_base: dict[str, list[PartRecord]] = {}
    for p in parts_list:
        by_base.setdefault(base_sku(p.sku), []).append(p)

    seen_skus = {h.part.sku for h in hits}
    parents = hits if top_parents is None else hits[:top_parents]
    expanded = list(hits)

    for h in parents:
        key = base_sku(h.part.sku)
        siblings = by_base.get(key, [])
        added = 0
        for sib in siblings:
            if sib.sku in seen_skus:
                continue
            if sib.location == h.part.location and sib.sku == h.part.sku:
                continue
            seen_skus.add(sib.sku)
            decay = 0.97
            expanded.append(
                RankedHit(
                    part=sib,
                    score=float(h.score) * decay,
                    dense_score=h.dense_score,
                    sparse_score=h.sparse_score,
                    rrf_score=h.rrf_score,
                )
            )
            added += 1
            if added >= max_siblings:
                break

    # Stable: primary hits first (already ordered), then siblings by score
    primary_n = len(hits)
    primary = expanded[:primary_n]
    extras = sorted(expanded[primary_n:], key=lambda x: x.score, reverse=True)
    return primary + extras
