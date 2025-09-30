"""
파서 Pydantic 스키마
OpenAPI 3.1 계약 준수
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# === 요청 스키마 ===

class ParseRequest(BaseModel):
    """파싱 요청"""
    source: Literal["upload", "supabase"] = Field(..., description="파일 소스 (upload: 직접 업로드, supabase: 저장소)")
    pathOrFile: str = Field(..., description="파일 경로 또는 파일명")
    options: Optional[Dict[str, Any]] = Field(None, description="파싱 옵션 (향후 확장)")

    class Config:
        json_schema_extra = {
            "example": {
                "source": "upload",
                "pathOrFile": "/tmp/upload/sample.xlsx",
                "options": {}
            }
        }


class ValidateRequest(BaseModel):
    """검증 요청"""
    panels: List[Dict[str, Any]] = Field(..., description="파싱된 분전반 배열")
    evidence: Dict[str, Any] = Field(..., description="파싱 증거")

    class Config:
        json_schema_extra = {
            "example": {
                "panels": [
                    {
                        "tab": "저압반1",
                        "panel_id": "TAB1_PANEL1",
                        "items": []
                    }
                ],
                "evidence": {
                    "traceId": "abc-123",
                    "rules_applied": []
                }
            }
        }


# === 응답 스키마 ===

class PanelItem(BaseModel):
    """분전반 아이템"""
    no: str = Field("", description="번호")
    name: str = Field("", description="품명")
    spec: str = Field("", description="규격")
    unit: str = Field("", description="단위")
    qty: str = Field("", description="수량")
    price: str = Field("", description="단가")
    amount: str = Field("", description="금액")


class Panel(BaseModel):
    """분전반"""
    tab: str = Field(..., description="탭 이름")
    tab_index: int = Field(..., description="탭 인덱스")
    panel_id: str = Field(..., description="분전반 ID (예: TAB1_PANEL1)")
    rows_span: List[int] = Field(..., description="행 범위 [start, end]")
    items: List[Dict[str, Any]] = Field(..., description="아이템 배열")


class RuleApplied(BaseModel):
    """적용된 규칙"""
    rule_id: str = Field(..., description="규칙 ID")
    span: List[int] = Field(..., description="적용 범위 [start, end]")
    reason: str = Field(..., description="적용 이유")


class Evidence(BaseModel):
    """파싱 증거"""
    traceId: str = Field(..., description="추적 ID")
    rules_applied: List[RuleApplied] = Field(..., description="적용된 규칙 배열")
    warnings: List[str] = Field(..., description="경고 메시지")
    tabs_detected: int = Field(..., description="탐지된 탭 개수")
    tabs_analyzed: List[int] = Field(..., description="분석된 탭 인덱스")
    panels_count: int = Field(..., description="분전반 개수")
    duration_ms: int = Field(..., description="처리 시간 (ms)")


class ParseResponse(BaseModel):
    """파싱 응답"""
    panels: List[Panel] = Field(..., description="파싱된 분전반 배열")
    evidence: Evidence = Field(..., description="파싱 증거")

    class Config:
        json_schema_extra = {
            "example": {
                "panels": [
                    {
                        "tab": "저압반1",
                        "tab_index": 0,
                        "panel_id": "TAB1_PANEL1",
                        "rows_span": [0, 10],
                        "items": [
                            {
                                "no": "1",
                                "name": "배선용차단기",
                                "spec": "3P 100A",
                                "unit": "EA",
                                "qty": "2",
                                "price": "50000",
                                "amount": "100000"
                            }
                        ]
                    }
                ],
                "evidence": {
                    "traceId": "abc-123",
                    "rules_applied": [
                        {
                            "rule_id": "TAB_RULE_2",
                            "span": [0, 1],
                            "reason": "2 tabs detected: analyze both"
                        }
                    ],
                    "warnings": [],
                    "tabs_detected": 2,
                    "tabs_analyzed": [0, 1],
                    "panels_count": 1,
                    "duration_ms": 150
                }
            }
        }


class ValidateResponse(BaseModel):
    """검증 응답"""
    status: Literal["OK", "FAIL"] = Field(..., description="검증 상태")
    reasons: List[str] = Field(..., description="실패 이유 (FAIL 시)")
    edges_hit: List[str] = Field(..., description="탐지된 엣지 케이스")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "OK",
                "reasons": [],
                "edges_hit": ["FUZZY_KEYWORD_MATCH"]
            }
        }