"""
파서 API 라우트
/v1/estimate/parse, /v1/estimate/parse/validate
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException, Request, Depends, status
from typing import Dict, Any

from api.models.parser_schemas import (
    ParseRequest,
    ParseResponse,
    ValidateRequest,
    ValidateResponse
)
from api.services.parser_service import parser_service
from api.utils.admin_guard import ensure_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/estimate", tags=["Parser"])


@router.post(
    "/parse",
    response_model=ParseResponse,
    summary="파일 파싱",
    description="Excel/CSV 파일을 파싱하여 분전반 정보 추출"
)
async def parse_file(
    request: Request,
    parse_req: ParseRequest,
    _admin: dict = Depends(ensure_admin)
):
    """
    파일 파싱 엔드포인트
    Zero-Mock: 실제 파일 I/O만 수행
    """
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    try:
        logger.info(
            f"[{trace_id}] Parse request: "
            f"source={parse_req.source}, path={parse_req.pathOrFile}"
        )

        # 실제 파일 파싱 (Zero-Mock)
        result = parser_service.parse_file(
            file_path=parse_req.pathOrFile,
            trace_id=trace_id
        )

        logger.info(
            f"[{trace_id}] Parse success: "
            f"panels={len(result['panels'])}, "
            f"duration={result['evidence']['duration_ms']}ms"
        )

        return result

    except Exception as e:
        logger.error(
            f"[{trace_id}] Parse failed: {str(e)}",
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "PARSE_FAILED",
                "message": "Failed to parse file",
                "hint": str(e),
                "traceId": trace_id
            }
        )


@router.post(
    "/parse/validate",
    response_model=ValidateResponse,
    summary="파싱 결과 검증",
    description="파싱된 결과의 유효성 검증"
)
async def validate_parse_result(
    request: Request,
    validate_req: ValidateRequest,
    _admin: dict = Depends(ensure_admin)
):
    """
    파싱 결과 검증 엔드포인트
    """
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    try:
        logger.info(
            f"[{trace_id}] Validate request: "
            f"panels={len(validate_req.panels)}"
        )

        # 검증 로직
        reasons = []
        edges_hit = []

        # 1. 분전반 개수 확인
        if len(validate_req.panels) == 0:
            reasons.append("No panels found")

        # 2. 엣지 케이스 탐지
        rules_applied = validate_req.evidence.get("rules_applied", [])
        for rule in rules_applied:
            rule_id = rule.get("rule_id", "")

            if "FUZZY" in rule_id:
                edges_hit.append(rule_id)
            if "SPACING" in rule_id:
                edges_hit.append(rule_id)

        # 3. 경고 확인
        warnings = validate_req.evidence.get("warnings", [])
        if warnings:
            reasons.extend([f"Warning: {w}" for w in warnings])

        # 상태 결정
        status_result = "OK" if len(reasons) == 0 else "FAIL"

        logger.info(
            f"[{trace_id}] Validate result: "
            f"status={status_result}, edges={len(edges_hit)}"
        )

        return {
            "status": status_result,
            "reasons": reasons,
            "edges_hit": edges_hit
        }

    except Exception as e:
        logger.error(
            f"[{trace_id}] Validate failed: {str(e)}",
            exc_info=True
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "VALIDATE_FAILED",
                "message": "Failed to validate parse result",
                "hint": str(e),
                "traceId": trace_id
            }
        )