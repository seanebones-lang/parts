"""
Vector service for semantic search using pgvector.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.services.llm_service import LLMService

# Whitelist of filterable column names (never interpolate user keys into SQL)
_FILTER_EQ_COLUMNS = frozenset({"make", "model", "category", "subcategory", "manufacturer"})
_FILTER_YEAR_KEYS = frozenset({"year_from", "year_to"})


def _normalize_filter_value(value: Any) -> Any:
    """Unwrap accidental Mongo-style operators to a scalar bound value."""
    if isinstance(value, dict):
        for op in ("$eq", "$lte", "$gte", "$lt", "$gt"):
            if op in value:
                return value[op]
        # Unknown shape — refuse rather than inject
        return None
    return value


class VectorService:
    """Service for vector operations and semantic search (pgvector when enabled)."""

    def __init__(self) -> None:
        self.llm_service = LLMService()
        self.embedding_model = "text-embedding-3-small"
        try:
            from app.core.config import settings

            self.pgvector_enabled = bool(getattr(settings, "PGVECTOR_ENABLED", False))
            self.vector_backend_pref = str(
                getattr(settings, "VECTOR_BACKEND", "auto")
            ).lower()
            self.hnsw = bool(getattr(settings, "PGVECTOR_HNSW", True))
        except Exception:
            self.pgvector_enabled = False
            self.vector_backend_pref = "auto"
            self.hnsw = True

    def backend_status(self) -> dict[str, Any]:
        """Report configured vector backend (no billed network call)."""
        return {
            "pgvector_enabled": self.pgvector_enabled,
            "vector_backend": self.vector_backend_pref,
            "hnsw": self.hnsw,
            "embedding_model": self.embedding_model,
            "active_path": (
                "pgvector"
                if self.pgvector_enabled and self.vector_backend_pref in {"auto", "pgvector"}
                else "parrts_or_disabled"
            ),
        }

    async def pgvector_status(self) -> dict[str, Any]:
        """Probe whether pgvector extension is available (best-effort)."""
        status = self.backend_status()
        if not self.pgvector_enabled:
            status["probe"] = "skipped"
            status["available"] = False
            return status
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
                )
                row = result.fetchone()
                status["available"] = bool(row)
                status["probe"] = "ok" if row else "missing_extension"
        except Exception as exc:
            status["available"] = False
            status["probe"] = f"error:{type(exc).__name__}"
        return status

    async def create_embedding(self, text_value: str) -> List[float]:
        """Create embedding for text using OpenAI async client."""
        try:
            if not self.llm_service.openai:
                print("Error creating embedding: OpenAI client not configured")
                return []
            response = await self.llm_service.openai.embeddings.create(
                model=self.embedding_model,
                input=text_value,
            )
            return list(response.data[0].embedding)
        except Exception as e:
            print(f"Error creating embedding: {e}")
            return []

    def _build_filter_clause(
        self, filters: Optional[Dict[str, Any]]
    ) -> tuple[str, Dict[str, Any]]:
        """Build WHERE fragments with bound params only; columns from whitelist."""
        if not filters:
            return "", {}

        clauses: List[str] = []
        params: Dict[str, Any] = {}

        for key, raw in filters.items():
            if key in _FILTER_EQ_COLUMNS:
                value = _normalize_filter_value(raw)
                if value is None:
                    continue
                param_name = f"f_{key}"
                # Column name from whitelist only — never from user input
                clauses.append(f"pc.{key} = :{param_name}")
                params[param_name] = value
            elif key == "year_from":
                value = _normalize_filter_value(raw)
                if value is None:
                    continue
                # Vehicle year should be >= part.year_from when set
                # When used as "part year_from filter", keep original semantics:
                # part.year_from IS NULL OR part.year_from <= :year_from
                clauses.append("(pc.year_from IS NULL OR pc.year_from <= :f_year_from)")
                params["f_year_from"] = value
            elif key == "year_to":
                value = _normalize_filter_value(raw)
                if value is None:
                    continue
                clauses.append("(pc.year_to IS NULL OR pc.year_to >= :f_year_to)")
                params["f_year_to"] = value
            # Unknown keys ignored (no injection path)

        if not clauses:
            return "", {}
        return " AND " + " AND ".join(clauses), params

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Perform semantic search on parts catalog via pgvector (when enabled)."""
        if not self.pgvector_enabled and self.vector_backend_pref == "pgvector":
            # Explicit pgvector-only but disabled → empty rather than silent SQL
            print("pgvector path requested but PGVECTOR_ENABLED=false")
            return []
        if not self.pgvector_enabled and self.vector_backend_pref != "pgvector":
            # Prefer caller to use parrts core; keep SQL path opt-in
            return []
        try:
            query_embedding = await self.create_embedding(query)
            if not query_embedding:
                return []

            embedding_literal = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
            filter_sql, filter_params = self._build_filter_clause(filters)

            sql = f"""
            SELECT
                pc.id,
                pc.part_number,
                pc.manufacturer,
                pc.part_name,
                pc.description,
                pc.category,
                pc.subcategory,
                pc.make,
                pc.model,
                pc.year_from,
                pc.year_to,
                pc.msrp,
                pc.cost,
                pc.is_active,
                1 - (pc.embedding <=> CAST(:embedding AS vector)) AS similarity_score
            FROM parts_catalog pc
            WHERE pc.embedding IS NOT NULL
              AND 1 - (pc.embedding <=> CAST(:embedding AS vector)) > :similarity_threshold
              {filter_sql}
            ORDER BY similarity_score DESC
            LIMIT :result_limit
            """

            params: Dict[str, Any] = {
                "embedding": embedding_literal,
                "similarity_threshold": float(similarity_threshold),
                "result_limit": int(limit),
                **filter_params,
            }

            async with AsyncSessionLocal() as db:
                result = await db.execute(text(sql), params)
                rows = result.fetchall()

                results: List[Dict[str, Any]] = []
                for row in rows:
                    result_dict = dict(row._mapping)
                    result_dict["relevance_score"] = float(
                        result_dict.get("similarity_score") or 0
                    )
                    results.append(result_dict)
                return results

        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []

    async def index_part(self, part_data: Dict[str, Any]) -> bool:
        """Index a part for semantic search."""
        try:
            part_id = part_data.get("id")
            searchable_text = self._create_searchable_text(part_data)
            embedding = await self.create_embedding(searchable_text)
            if not embedding:
                return False

            embedding_literal = "[" + ",".join(str(float(x)) for x in embedding) + "]"

            sql = """
            UPDATE parts_catalog
            SET embedding = CAST(:embedding AS vector)
            WHERE id = :part_id
            """

            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(sql),
                    {"embedding": embedding_literal, "part_id": part_id},
                )
                await db.commit()

            return True

        except Exception as e:
            print(f"Error indexing part: {e}")
            return False

    async def bulk_index_parts(self, parts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk index parts for semantic search."""
        results: Dict[str, Any] = {
            "total": len(parts_data),
            "successful": 0,
            "failed": 0,
            "errors": [],
        }

        for part_data in parts_data:
            try:
                success = await self.index_part(part_data)
                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to index part {part_data.get('id')}")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(
                    f"Error indexing part {part_data.get('id')}: {str(e)}"
                )

        return results

    def _create_searchable_text(self, part_data: Dict[str, Any]) -> str:
        """Create searchable text from part data."""
        text_parts: List[str] = []

        if part_data.get("part_number"):
            text_parts.append(f"Part number: {part_data['part_number']}")
        if part_data.get("part_name"):
            text_parts.append(f"Name: {part_data['part_name']}")
        if part_data.get("description"):
            text_parts.append(f"Description: {part_data['description']}")
        if part_data.get("manufacturer"):
            text_parts.append(f"Manufacturer: {part_data['manufacturer']}")
        if part_data.get("category"):
            text_parts.append(f"Category: {part_data['category']}")
        if part_data.get("subcategory"):
            text_parts.append(f"Subcategory: {part_data['subcategory']}")

        vehicle_parts: List[str] = []
        if part_data.get("make"):
            vehicle_parts.append(str(part_data["make"]))
        if part_data.get("model"):
            vehicle_parts.append(str(part_data["model"]))
        if part_data.get("year_from") and part_data.get("year_to"):
            vehicle_parts.append(f"{part_data['year_from']}-{part_data['year_to']}")
        elif part_data.get("year_from"):
            vehicle_parts.append(f"{part_data['year_from']}+")
        if vehicle_parts:
            text_parts.append(f"Compatible with: {' '.join(vehicle_parts)}")

        if part_data.get("engine"):
            text_parts.append(f"Engine: {part_data['engine']}")
        if part_data.get("transmission"):
            text_parts.append(f"Transmission: {part_data['transmission']}")
        if part_data.get("body_style"):
            text_parts.append(f"Body style: {part_data['body_style']}")
        if part_data.get("compatible_parts"):
            compatible = ", ".join(part_data["compatible_parts"])
            text_parts.append(f"Compatible parts: {compatible}")

        return " ".join(text_parts)

    async def find_similar_parts(self, part_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar parts to a given part."""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("SELECT embedding::text FROM parts_catalog WHERE id = :part_id"),
                    {"part_id": part_id},
                )
                row = result.fetchone()
                if not row or not row[0]:
                    return []

                embedding_literal = row[0]

                sql = """
                SELECT
                    pc.id,
                    pc.part_number,
                    pc.manufacturer,
                    pc.part_name,
                    pc.description,
                    pc.category,
                    pc.subcategory,
                    pc.make,
                    pc.model,
                    pc.year_from,
                    pc.year_to,
                    pc.msrp,
                    pc.cost,
                    1 - (pc.embedding <=> CAST(:embedding AS vector)) AS similarity_score
                FROM parts_catalog pc
                WHERE pc.id != :part_id
                  AND pc.embedding IS NOT NULL
                ORDER BY similarity_score DESC
                LIMIT :result_limit
                """
                result = await db.execute(
                    text(sql),
                    {
                        "embedding": embedding_literal,
                        "part_id": part_id,
                        "result_limit": int(limit),
                    },
                )
                rows = result.fetchall()
                return [dict(r._mapping) for r in rows]

        except Exception as e:
            print(f"Error finding similar parts: {e}")
            return []

    async def search_by_vehicle(
        self, make: str, model: str, year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for parts by vehicle information."""
        try:
            query_parts = [make, model]
            if year:
                query_parts.append(str(year))
            query = " ".join(query_parts)

            filters: Dict[str, Any] = {"make": make, "model": model}
            if year:
                filters["year_from"] = year
                filters["year_to"] = year

            return await self.semantic_search(query=query, filters=filters, limit=20)
        except Exception as e:
            print(f"Error searching by vehicle: {e}")
            return []
