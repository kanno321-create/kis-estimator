"""Documents Router - Document generation and retrieval"""
import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/documents", tags=["documents"])

@router.get("")
async def list_documents(quoteId: str, kind: str = None):
    """List documents with signed URLs (10-min TTL)"""
    # Stub: Will query documents table
    return {
        "items": [{
            "id": "doc-uuid",
            "quote_id": quoteId,
            "kind": kind or "pdf",
            "sha256": "a" * 64,
            "signedUrl": "https://storage.example.com/signed",
            "created_at": "2025-09-30T10:00:00Z"
        }]
    }

@router.post("/export")
async def export_documents(quoteId: str, kinds: list[str]):
    """Export documents in specified formats"""
    # Stub: Will generate and upload documents
    return {"taskId": "task-uuid", "documents": []}, 202
