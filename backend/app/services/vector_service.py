"""
Vector service for semantic search using pgvector.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.core.database import get_db
from app.services.llm_service import LLMService
import json


class VectorService:
    """Service for vector operations and semantic search."""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.embedding_model = "text-embedding-3-small"  # OpenAI embedding model
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using OpenAI."""
        try:
            # Use OpenAI embeddings
            response = await self.llm_service.openai.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error creating embedding: {e}")
            return []
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Perform semantic search on parts catalog."""
        try:
            # Create embedding for query
            query_embedding = await self.create_embedding(query)
            if not query_embedding:
                return []
            
            # Convert to PostgreSQL array format
            embedding_array = f"[{','.join(map(str, query_embedding))}]"
            
            # Build SQL query
            sql = """
            SELECT 
                pc.*,
                1 - (pc.embedding <=> %s::vector) as similarity_score
            FROM parts_catalog pc
            WHERE 1 - (pc.embedding <=> %s::vector) > %s
            """
            
            params = [embedding_array, embedding_array, similarity_threshold]
            
            # Add filters if provided
            if filters:
                for key, value in filters.items():
                    if key in ["make", "model", "category", "subcategory"]:
                        sql += f" AND pc.{key} = %s"
                        params.append(value)
                    elif key == "year_from":
                        sql += " AND (pc.year_from IS NULL OR pc.year_from <= %s)"
                        params.append(value)
                    elif key == "year_to":
                        sql += " AND (pc.year_to IS NULL OR pc.year_to >= %s)"
                        params.append(value)
            
            sql += " ORDER BY similarity_score DESC LIMIT %s"
            params.append(limit)
            
            # Execute query
            async with get_db() as db:
                result = await db.execute(text(sql), params)
                rows = result.fetchall()
                
                # Convert to dictionaries
                results = []
                for row in rows:
                    result_dict = dict(row._mapping)
                    # Convert numpy arrays to lists for JSON serialization
                    if 'embedding' in result_dict:
                        del result_dict['embedding']  # Remove embedding from results
                    results.append(result_dict)
                
                return results
                
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []
    
    async def index_part(self, part_data: Dict[str, Any]) -> bool:
        """Index a part for semantic search."""
        try:
            part_id = part_data.get("id")
            
            # Create searchable text
            searchable_text = self._create_searchable_text(part_data)
            
            # Create embedding
            embedding = await self.create_embedding(searchable_text)
            if not embedding:
                return False
            
            # Update part with embedding
            embedding_array = f"[{','.join(map(str, embedding))}]"
            
            sql = """
            UPDATE parts_catalog 
            SET embedding = %s::vector
            WHERE id = %s
            """
            
            async with get_db() as db:
                await db.execute(text(sql), [embedding_array, part_id])
                await db.commit()
            
            return True
            
        except Exception as e:
            print(f"Error indexing part: {e}")
            return False
    
    async def bulk_index_parts(self, parts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk index parts for semantic search."""
        results = {
            "total": len(parts_data),
            "successful": 0,
            "failed": 0,
            "errors": []
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
                results["errors"].append(f"Error indexing part {part_data.get('id')}: {str(e)}")
        
        return results
    
    def _create_searchable_text(self, part_data: Dict[str, Any]) -> str:
        """Create searchable text from part data."""
        text_parts = []
        
        # Basic part information
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
        
        # Vehicle compatibility
        vehicle_parts = []
        if part_data.get("make"):
            vehicle_parts.append(part_data["make"])
        
        if part_data.get("model"):
            vehicle_parts.append(part_data["model"])
        
        if part_data.get("year_from") and part_data.get("year_to"):
            vehicle_parts.append(f"{part_data['year_from']}-{part_data['year_to']}")
        elif part_data.get("year_from"):
            vehicle_parts.append(f"{part_data['year_from']}+")
        
        if vehicle_parts:
            text_parts.append(f"Compatible with: {' '.join(vehicle_parts)}")
        
        # Engine and transmission info
        if part_data.get("engine"):
            text_parts.append(f"Engine: {part_data['engine']}")
        
        if part_data.get("transmission"):
            text_parts.append(f"Transmission: {part_data['transmission']}")
        
        if part_data.get("body_style"):
            text_parts.append(f"Body style: {part_data['body_style']}")
        
        # Compatible parts
        if part_data.get("compatible_parts"):
            compatible = ", ".join(part_data["compatible_parts"])
            text_parts.append(f"Compatible parts: {compatible}")
        
        return " ".join(text_parts)
    
    async def find_similar_parts(self, part_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar parts to a given part."""
        try:
            # Get the part's embedding
            async with get_db() as db:
                sql = "SELECT embedding FROM parts_catalog WHERE id = %s"
                result = await db.execute(text(sql), [part_id])
                row = result.fetchone()
                
                if not row or not row[0]:
                    return []
                
                embedding = row[0]
                embedding_array = f"[{','.join(map(str, embedding))}]"
                
                # Find similar parts
                sql = """
                SELECT 
                    pc.*,
                    1 - (pc.embedding <=> %s::vector) as similarity_score
                FROM parts_catalog pc
                WHERE pc.id != %s
                ORDER BY similarity_score DESC
                LIMIT %s
                """
                
                result = await db.execute(text(sql), [embedding_array, part_id, limit])
                rows = result.fetchall()
                
                results = []
                for row in rows:
                    result_dict = dict(row._mapping)
                    if 'embedding' in result_dict:
                        del result_dict['embedding']
                    results.append(result_dict)
                
                return results
                
        except Exception as e:
            print(f"Error finding similar parts: {e}")
            return []
    
    async def search_by_vehicle(self, make: str, model: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for parts by vehicle information."""
        try:
            # Create search query
            query_parts = [make, model]
            if year:
                query_parts.append(str(year))
            
            query = " ".join(query_parts)
            
            # Build filters
            filters = {
                "make": make,
                "model": model
            }
            
            if year:
                filters["year_from"] = year
                filters["year_to"] = year
            
            # Perform semantic search
            results = await self.semantic_search(
                query=query,
                filters=filters,
                limit=20
            )
            
            return results
            
        except Exception as e:
            print(f"Error searching by vehicle: {e}")
            return []
