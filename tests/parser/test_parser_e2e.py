"""
E2E 파서 회귀 테스트 (10/10)
Zero-Mock: 실제 합성 샘플 파일 I/O
"""

import pytest
from pathlib import Path
from api.services.parser_service import parser_service


@pytest.fixture
def fixtures_dir():
    """픽스처 디렉토리 경로"""
    return Path("tests/parser/fixtures")


def test_01_2tab_simple(fixtures_dir):
    """케이스1: 탭 2개 - 단순"""
    result = parser_service.parse_file(str(fixtures_dir / "01_2tab_simple.xlsx"))

    assert len(result["panels"]) >= 1
    assert result["evidence"]["tabs_detected"] == 2
    assert 0 in result["evidence"]["tabs_analyzed"]
    assert 1 in result["evidence"]["tabs_analyzed"]
    assert result["evidence"]["duration_ms"] < 200  # p95 < 200ms


def test_02_2tab_mcc(fixtures_dir):
    """케이스2: 탭 2개 - MCC 포함"""
    result = parser_service.parse_file(str(fixtures_dir / "02_2tab_mcc.xlsx"))

    assert len(result["panels"]) >= 1
    assert result["evidence"]["tabs_analyzed"] == [0, 1]


def test_03_2tab_multi_panel(fixtures_dir):
    """케이스3: 탭 2개 - 다중 분전반"""
    result = parser_service.parse_file(str(fixtures_dir / "03_2tab_multi_panel.xlsx"))

    assert len(result["panels"]) >= 2  # 최소 2개 분전반
    assert any("PANEL_SPLIT" in r["rule_id"] for r in result["evidence"]["rules_applied"])


def test_04_2tab_typo_sogae(fixtures_dir):
    """케이스4: 탭 2개 - OCR 오탈자 '소게'"""
    result = parser_service.parse_file(str(fixtures_dir / "04_2tab_typo_sogae.xlsx"))

    assert len(result["panels"]) >= 1
    # Fuzzy 매칭 규칙 적용 확인
    fuzzy_rules = [r for r in result["evidence"]["rules_applied"] if "FUZZY" in r["rule_id"]]
    assert len(fuzzy_rules) > 0


def test_05_2tab_spacing(fixtures_dir):
    """케이스5: 탭 2개 - 공백 변이 (±2)"""
    result = parser_service.parse_file(str(fixtures_dir / "05_2tab_spacing.xlsx"))

    assert len(result["panels"]) >= 2
    # 공백 허용 규칙 확인
    spacing_rules = [r for r in result["evidence"]["rules_applied"] if "SPACING" in r["rule_id"]]
    assert len(spacing_rules) > 0


def test_06_2tab_csv(fixtures_dir):
    """케이스6: CSV (탭 2개 상당)"""
    result = parser_service.parse_file(str(fixtures_dir / "06_2tab_equiv.csv"))

    assert len(result["panels"]) >= 1
    assert result["evidence"]["tabs_detected"] >= 2


def test_07_3tab_highvolt_skip(fixtures_dir):
    """케이스7: 탭 3개 - 2번 고압반 제외"""
    result = parser_service.parse_file(str(fixtures_dir / "07_3tab_highvolt_skip.xlsx"))

    assert result["evidence"]["tabs_detected"] == 3
    # 2번 탭 제외 확인
    assert 1 not in result["evidence"]["tabs_analyzed"]
    assert 0 in result["evidence"]["tabs_analyzed"]
    assert 2 in result["evidence"]["tabs_analyzed"]


def test_08_4tab_complex(fixtures_dir):
    """케이스8: 탭 4개 - 2번 제외"""
    result = parser_service.parse_file(str(fixtures_dir / "08_4tab_complex.xlsx"))

    assert result["evidence"]["tabs_detected"] == 4
    assert 1 not in result["evidence"]["tabs_analyzed"]


def test_09_3tab_typo_hapge(fixtures_dir):
    """케이스9: 탭 3개 - OCR 오탈자 '합게'"""
    result = parser_service.parse_file(str(fixtures_dir / "09_3tab_typo_hapge.xlsx"))

    assert result["evidence"]["tabs_detected"] == 3
    fuzzy_rules = [r for r in result["evidence"]["rules_applied"] if "FUZZY" in r["rule_id"]]
    assert len(fuzzy_rules) > 0


def test_10_3tab_csv(fixtures_dir):
    """케이스10: CSV (탭 3개 상당)"""
    result = parser_service.parse_file(str(fixtures_dir / "10_3tab_equiv.csv"))

    assert result["evidence"]["tabs_detected"] >= 3
    assert result["evidence"]["duration_ms"] < 200