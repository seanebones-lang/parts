"""
Parts catalog endpoints with semantic search.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import require_user_if_production
from app.models.user import User
from app.services.parts_service import PartsService
from app.services.vector_service import VectorService
from app.agents.parts_lookup import PartsLookupAgent

router = APIRouter()


@router.get("/")
async def get_parts(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    manufacturer: Optional[str] = None,
    make: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get parts with optional filters."""
    service = PartsService(db)
    
    filters = {}
    if category:
        filters["category"] = category
    if manufacturer:
        filters["manufacturer"] = manufacturer
    if make:
        filters["make"] = make
    
    parts = await service.get_parts(skip=skip, limit=limit, filters=filters)
    
    return {
        "success": True,
        "parts": parts,
        "count": len(parts)
    }


@router.get("/{part_id}")
async def get_part(
    part_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get part by ID."""
    service = PartsService(db)
    part = await service.get_part(part_id)
    
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    
    return {
        "success": True,
        "part": part
    }


@router.get("/search/{query}")
async def search_parts(
    query: str,
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Search parts using AI semantic search."""
    try:
        # Prepare search input
        search_input = {
            "query": query,
            "vehicle_info": {
                "make": make,
                "model": model,
                "year": year
            }
        }
        
        # Use Parts Lookup Agent for intelligent search
        agent = PartsLookupAgent(db)
        result = await agent.process(search_input)
        
        if result.success:
            return {
                "success": True,
                "search_results": result.data,
                "confidence": result.confidence,
                "processing_time": result.processing_time
            }
        else:
            raise HTTPException(status_code=500, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/semantic-search/{query}")
async def semantic_search_parts(
    query: str,
    limit: int = Query(10, le=50),
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db)
):
    """Direct semantic search on parts catalog."""
    try:
        vector_service = VectorService()
        results = await vector_service.semantic_search(
            query=query,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@router.get("/by-vehicle/{make}/{model}")
async def get_parts_by_vehicle(
    make: str,
    model: str,
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get parts compatible with a specific vehicle."""
    service = PartsService(db)
    parts = await service.get_parts_by_vehicle(make=make, model=model, year=year)
    
    return {
        "success": True,
        "vehicle": {"make": make, "model": model, "year": year},
        "parts": parts,
        "count": len(parts)
    }


@router.get("/catalog/filters")
async def get_catalog_filters(db: AsyncSession = Depends(get_db)):
    """Get available filters for parts catalog."""
    service = PartsService(db)
    
    categories = await service.get_categories()
    manufacturers = await service.get_manufacturers()
    makes = await service.get_makes()
    
    return {
        "success": True,
        "filters": {
            "categories": categories,
            "manufacturers": manufacturers,
            "makes": makes
        }
    }


@router.get("/catalog/models/{make}")
async def get_models_by_make(
    make: str,
    db: AsyncSession = Depends(get_db)
):
    """Get models for a specific make."""
    service = PartsService(db)
    models = await service.get_models(make=make)
    
    return {
        "success": True,
        "make": make,
        "models": models
    }


@router.post("/bulk-import")
async def bulk_import_parts(
    parts_data: List[dict],
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Bulk import parts from external data.

    Auth: open when AUTH_MODE=demo; JWT required when AUTH_MODE=production.
    """
    _ = current_user  # identity available for audit when authenticated
    try:
        service = PartsService(db)
        result = await service.bulk_import_parts(parts_data)
        
        return {
            "success": True,
            "import_result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk import failed: {str(e)}")


@router.post("/index-part/{part_id}")
async def index_part_for_search(
    part_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(require_user_if_production),
):
    """Index a part for semantic search.

    Auth: open when AUTH_MODE=demo; JWT required when AUTH_MODE=production.
    """
    _ = current_user
    try:
        service = PartsService(db)
        part = await service.get_part(part_id)
        
        if not part:
            raise HTTPException(status_code=404, detail="Part not found")
        
        vector_service = VectorService()
        success = await vector_service.index_part(part)
        
        if success:
            return {
                "success": True,
                "message": f"Part {part_id} indexed successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to index part")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.get("/similar/{part_id}")
async def get_similar_parts(
    part_id: int,
    limit: int = Query(5, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Get similar parts to a given part."""
    try:
        vector_service = VectorService()
        similar_parts = await vector_service.find_similar_parts(part_id, limit)
        
        return {
            "success": True,
            "part_id": part_id,
            "similar_parts": similar_parts,
            "count": len(similar_parts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similar parts search failed: {str(e)}")