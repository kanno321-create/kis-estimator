"""Validate Router - Input validation and parsing"""
import logging
from fastapi import APIRouter, UploadFile, File, Form

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/validate", tags=["validate"])

@router.post("")
async def validate_input(
    file: UploadFile = File(None),
    text: str = Form(None),
    ruleset: str = Form("tab")
):
    """
    Tab parsing rules:
    - 2 tabs: Analyze tabs 1 and 2
    - 3+ tabs: Tab 2 is high-voltage (ignore), analyze tabs 1 and 3
    - New panel block: "소계/합계" + 1-2 blank rows
    """
    # Stub: Will implement tab/panel parsing
    return {
        "normalized_input": {},
        "panels_detected": 1,
        "blocks": [{"tab": 1, "start_row": 1, "end_row": 50}]
    }
