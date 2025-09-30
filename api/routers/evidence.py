"""
Evidence Ledger API Router
Admin-only read-only viewer for Go-Live evidence packs
Contract-First + Evidence-Gated + Zero-Mock
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from api.utils.admin_guard import ensure_admin
from api.services.evidence_service import evidence_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==========================================
# Request/Response Models (OpenAPI 3.1)
# ==========================================


class PackListResponse(BaseModel):
    """Response for GET /v1/evidence/packs"""
    packs: list[dict]
    total: int
    limit: int
    offset: int


class PackDetailsResponse(BaseModel):
    """Response for GET /v1/evidence/packs/{pack_id}"""
    pack_id: str
    created_at: Optional[str]
    total_files: int
    total_bytes: int
    has_sha256sums: bool
    files: list[dict]


class DownloadUrlResponse(BaseModel):
    """Response for GET /v1/evidence/packs/{pack_id}/download"""
    signed_url: str
    expires_in: int
    file_path: str
    generated_at: str


class VerifyRequest(BaseModel):
    """Request for POST /v1/evidence/verify"""
    pack_id: str = Field(..., description="Evidence pack ID to verify")


class VerifyResponse(BaseModel):
    """Response for POST /v1/evidence/verify"""
    status: str = Field(..., description="OK or FAIL")
    pack_id: str
    files_checked: int
    mismatched: list[dict] = Field(default_factory=list)
    duration_ms: int
    verified_at: str
    trace_id: str


class ErrorResponse(BaseModel):
    """Standard error response"""
    code: str
    message: str
    hint: Optional[str] = None
    traceId: str
    meta: dict


# ==========================================
# Endpoints
# ==========================================


@router.get(
    "/v1/evidence/packs",
    response_model=PackListResponse,
    summary="List evidence packs",
    description="List all Go-Live evidence packs from Supabase Storage (admin only)",
    tags=["Evidence"]
)
async def list_packs(
    request: Request,
    q: Optional[str] = Query(None, description="Search query (partial match on pack ID)"),
    limit: int = Query(50, ge=1, le=100, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
    order: str = Query("created_at_desc", description="Sort order (created_at_desc or created_at_asc)"),
    _admin: dict = Depends(ensure_admin)
):
    """
    List evidence packs with search, pagination, and sorting.

    Requires: Admin or service_role JWT
    Returns: Array of pack metadata (id, created_at, total_files, total_bytes, has_sha256sums)
    """
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    try:
        result = evidence_service.list_packs(
            q=q,
            limit=limit,
            offset=offset,
            order=order
        )

        logger.info(
            f"[{trace_id}] Listed evidence packs: "
            f"total={result['total']} limit={limit} offset={offset} query={q}"
        )

        return result

    except Exception as e:
        logger.error(f"[{trace_id}] Failed to list evidence packs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EVIDENCE_LIST_FAILED",
                "message": "Failed to list evidence packs",
                "hint": str(e),
                "traceId": trace_id,
                "meta": {"dedupKey": f"evidence_list_{trace_id}"}
            }
        )


@router.get(
    "/v1/evidence/packs/{pack_id}",
    response_model=PackDetailsResponse,
    summary="Get pack details",
    description="Get detailed file list for a specific evidence pack (admin only)",
    tags=["Evidence"]
)
async def get_pack_details(
    pack_id: str,
    request: Request,
    _admin: dict = Depends(ensure_admin)
):
    """
    Get pack details including file list with names, sizes, MIME types, and timestamps.

    Requires: Admin or service_role JWT
    Returns: Pack metadata + array of file details
    """
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    try:
        result = evidence_service.get_pack_details(pack_id)

        logger.info(
            f"[{trace_id}] Retrieved pack details: "
            f"pack_id={pack_id} files={result['total_files']}"
        )

        return result

    except Exception as e:
        error_code = "PACK_NOT_FOUND" if "PACK_NOT_FOUND" in str(e) else "EVIDENCE_DETAILS_FAILED"
        status_code = status.HTTP_404_NOT_FOUND if error_code == "PACK_NOT_FOUND" else status.HTTP_500_INTERNAL_SERVER_ERROR

        logger.error(f"[{trace_id}] Failed to get pack details for {pack_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": error_code,
                "message": f"Failed to retrieve pack details for '{pack_id}'",
                "hint": str(e),
                "traceId": trace_id,
                "meta": {"dedupKey": f"evidence_details_{pack_id}_{trace_id}"}
            }
        )


@router.get(
    "/v1/evidence/packs/{pack_id}/download",
    response_model=DownloadUrlResponse,
    summary="Generate download URL",
    description="Generate signed URL for file download (admin only, short expiration)",
    tags=["Evidence"]
)
async def get_download_url(
    pack_id: str,
    request: Request,
    file: str = Query(..., description="File name within pack (e.g., 'SHA256SUMS.txt' or 'artifacts/report.pdf')"),
    expires_in: int = Query(600, ge=60, le=3600, description="URL expiration in seconds (default: 600 = 10 min)"),
    _admin: dict = Depends(ensure_admin)
):
    """
    Generate short-lived signed URL for secure file download.

    Requires: Admin or service_role JWT
    Returns: Signed URL with expiration info
    Security: Server-side credentials only, no client exposure
    """
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    try:
        result = evidence_service.create_download_url(
            pack_id=pack_id,
            file_name=file,
            expires_in=expires_in
        )

        logger.info(
            f"[{trace_id}] Generated signed URL: "
            f"pack_id={pack_id} file={file} expires_in={expires_in}"
        )

        return result

    except Exception as e:
        error_code = "FILE_NOT_FOUND" if "FILE_NOT_FOUND" in str(e) else "DOWNLOAD_URL_FAILED"
        status_code = status.HTTP_404_NOT_FOUND if error_code == "FILE_NOT_FOUND" else status.HTTP_500_INTERNAL_SERVER_ERROR

        logger.error(
            f"[{trace_id}] Failed to generate download URL for {pack_id}/{file}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": error_code,
                "message": f"Failed to generate download URL",
                "hint": str(e),
                "traceId": trace_id,
                "meta": {"dedupKey": f"download_url_{pack_id}_{file}_{trace_id}"}
            }
        )


@router.post(
    "/v1/evidence/verify",
    response_model=VerifyResponse,
    summary="Verify pack integrity",
    description="Verify evidence pack integrity by comparing actual file hashes against SHA256SUMS.txt (admin only)",
    tags=["Evidence"]
)
async def verify_pack(
    request: Request,
    verify_req: VerifyRequest,
    _admin: dict = Depends(ensure_admin)
):
    """
    Verify pack integrity using streaming SHA256 hash calculation.

    Process:
    1. Download SHA256SUMS.txt from pack
    2. Stream-calculate hash for each file in pack
    3. Compare actual vs expected hashes
    4. Return verification status with mismatched files

    Requires: Admin or service_role JWT
    Returns: Verification status (OK/FAIL) with detailed results
    Zero-Mock: Real file download and hash calculation
    """
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    try:
        result = evidence_service.verify_pack_integrity(
            pack_id=verify_req.pack_id,
            trace_id=trace_id
        )

        # Log structured verification result
        logger.info(
            f"[{trace_id}] Pack verification complete: "
            f"action=evidence.verify pack_id={verify_req.pack_id} "
            f"status={result['status']} files_checked={result['files_checked']} "
            f"mismatched_count={len(result['mismatched'])} duration_ms={result['duration_ms']}"
        )

        return result

    except Exception as e:
        logger.error(
            f"[{trace_id}] Pack verification failed: "
            f"action=evidence.verify pack_id={verify_req.pack_id} error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EVIDENCE_VERIFY_FAIL",
                "message": f"Failed to verify pack integrity",
                "hint": str(e),
                "traceId": trace_id,
                "meta": {"dedupKey": f"verify_{verify_req.pack_id}_{trace_id}"}
            }
        )