"""Catalog Router - Parts catalog management"""
import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/catalog", tags=["catalog"])

@router.get("")
async def list_catalog(kind: str = None, q: str = None, page: int = 1, size: int = 20):
    """Search catalog items"""
    # Stub: Will query catalog_items table
    return {
        "items": [],
        "pagination": {"page": page, "size": size, "total": 0, "pages": 0}
    }

@router.post("/items")
async def upsert_catalog_items(items: list[dict]):
    """Upsert catalog items (seed/admin)"""
    # Stub: Will upsert to catalog_items table
    return {"upserted": len(items)}
