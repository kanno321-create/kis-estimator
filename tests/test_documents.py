"""Document Generation Tests - PDF/XLSX/Lint validation"""
import pytest
from api.services import document_service

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_format_estimate_formula_preservation():
    """Test formula preservation (must be 100%)"""
    quote_data = {"items": [], "totals": {}}
    result = await document_service.format_estimate(quote_data)
    
    assert result["formatted"] is True
    assert result["formula_loss"] == 0, "Formula loss must be 0"
    assert result["named_ranges_ok"] is True


@pytest.mark.asyncio
async def test_generate_cover_branding():
    """Test cover generation follows branding policy"""
    customer = {"name": "Test Corp"}
    result = await document_service.generate_cover(customer, "quote-123")
    
    assert result["cover_generated"] is True
    assert result["policy_violations"] == 0, "Branding violations must be 0"
    assert result["logo_ok"] is True


@pytest.mark.asyncio
async def test_lint_document_no_errors():
    """Test document lint returns zero errors"""
    result = await document_service.lint_document({})
    
    assert result["errors"] == 0, "Lint errors must be 0"
    assert isinstance(result["warnings"], int)
    assert isinstance(result["recommendations"], list)


@pytest.mark.asyncio
async def test_export_pdf_xlsx_generates_files():
    """Test PDF/XLSX export generates files with SHA256"""
    quote_id = "test-quote-123"
    quote_data = {"customer": {"name": "Test"}, "items": []}
    
    result = await document_service.export_pdf_xlsx(quote_id, quote_data)
    
    assert "pdf" in result
    assert "xlsx" in result
    assert "sha256" in result["pdf"]
    assert "sha256" in result["xlsx"]
    assert len(result["pdf"]["sha256"]) == 64
    assert len(result["xlsx"]["sha256"]) == 64
