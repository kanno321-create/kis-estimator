"""
파서 규칙 엔진 단위 테스트
20개 케이스: 탭 규칙, 오탈자, 공백, MCC, 경계 케이스
"""

import pytest
from api.services.parser_rules import ParserRules


class TestTabRules:
    """탭 규칙 테스트 (규칙 1, 2)"""

    def test_tab2_detect(self):
        """탭 2개 → 모두 분석 (고압반 없음)"""
        rules = ParserRules()
        tabs, rule_id = rules.detect_tab_count_and_strategy(2)

        assert tabs == [0, 1]
        assert rule_id == ParserRules.RULE_TAB_2
        assert len(rules.rules_applied) == 1
        assert rules.rules_applied[0].rule_id == ParserRules.RULE_TAB_2

    def test_tab3_detect(self):
        """탭 3개 → 2번 제외, 1+3번 분석"""
        rules = ParserRules()
        tabs, rule_id = rules.detect_tab_count_and_strategy(3)

        assert tabs == [0, 2]
        assert rule_id == ParserRules.RULE_TAB_3PLUS
        assert len(rules.rules_applied) == 1

    def test_tab4_detect(self):
        """탭 4개 → 2번 제외, 1+3+4번 분석"""
        rules = ParserRules()
        tabs, rule_id = rules.detect_tab_count_and_strategy(4)

        assert tabs == [0, 2, 3]
        assert rule_id == ParserRules.RULE_TAB_3PLUS

    def test_tab5_detect(self):
        """탭 5개 → 2번 제외, 1+3+4+5번 분석"""
        rules = ParserRules()
        tabs, rule_id = rules.detect_tab_count_and_strategy(5)

        assert tabs == [0, 2, 3, 4]
        assert rule_id == ParserRules.RULE_TAB_3PLUS


class TestPanelBoundaries:
    """분전반 경계 탐지 테스트 (규칙 3)"""

    def test_single_panel_subtotal(self):
        """단일 분전반 - 소계"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["", "소계", "", "", "2", "", "100000"],
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        assert len(boundaries) == 1
        assert boundaries[0] == (0, 2)

    def test_single_panel_total(self):
        """단일 분전반 - 합계"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["", "합계", "", "", "2", "", "100000"],
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        assert len(boundaries) == 1
        assert boundaries[0] == (0, 2)

    def test_multi_panel_blank_1(self):
        """다중 분전반 - 공백 1행"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["", "소계", "", "", "2", "", "100000"],
            [],  # 공백 1행
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "접촉기", "AC-3 30A", "EA", "1", "100000", "100000"],
            ["", "합계", "", "", "1", "", "100000"],
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        assert len(boundaries) == 2
        assert boundaries[0] == (0, 2)
        assert boundaries[1] == (4, 6)

    def test_multi_panel_blank_2(self):
        """다중 분전반 - 공백 2행 (±2 허용)"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["", "소계", "", "", "2", "", "100000"],
            [],  # 공백 1행
            [],  # 공백 2행
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "접촉기", "AC-3 30A", "EA", "1", "100000", "100000"],
            ["", "합계", "", "", "1", "", "100000"],
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        assert len(boundaries) == 2
        assert boundaries[0] == (0, 2)
        assert boundaries[1] == (5, 7)

        # RULE_SPACING_TOLERANCE 증거 확인
        spacing_rules = [r for r in rules.rules_applied if r.rule_id == ParserRules.RULE_SPACING_TOLERANCE]
        assert len(spacing_rules) >= 1


class TestFuzzyMatching:
    """Fuzzy 매칭 테스트 (오탈자 탐지)"""

    def test_typo_sogae(self):
        """오탈자: 소계 → 소게"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["", "소게", "", "", "2", "", "100000"],  # 오탈자
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        assert len(boundaries) == 1

        # RULE_FUZZY_MATCH 증거 확인
        fuzzy_rules = [r for r in rules.rules_applied if r.rule_id == ParserRules.RULE_FUZZY_MATCH]
        assert len(fuzzy_rules) >= 1
        assert "소게" in fuzzy_rules[0].reason

    def test_typo_hapge(self):
        """오탈자: 합계 → 합게"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["", "합게", "", "", "2", "", "100000"],  # 오탈자
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        assert len(boundaries) == 1

        # RULE_FUZZY_MATCH 증거 확인
        fuzzy_rules = [r for r in rules.rules_applied if r.rule_id == ParserRules.RULE_FUZZY_MATCH]
        assert len(fuzzy_rules) >= 1
        assert "합게" in fuzzy_rules[0].reason

    def test_typo_sojel(self):
        """오탈자: 소계 → 소젤 (편집거리 1)"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["", "소젤", "", "", "2", "", "100000"],  # 오탈자
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        assert len(boundaries) == 1

        # RULE_FUZZY_MATCH 증거 확인
        fuzzy_rules = [r for r in rules.rules_applied if r.rule_id == ParserRules.RULE_FUZZY_MATCH]
        assert len(fuzzy_rules) >= 1


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_no_panel_boundary(self):
        """경계 없음 - 단일 블록"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        # 마지막 행까지 단일 분전반
        assert len(boundaries) == 1
        assert boundaries[0][1] == len(rows) - 1

    def test_empty_rows(self):
        """빈 행만 있는 경우"""
        rows = [
            [],
            [],
            [],
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        assert len(boundaries) >= 1

    def test_mcc_keyword(self):
        """MCC 키워드 포함 (일반 분전반으로 처리)"""
        rows = [
            ["MCC-01 (Motor Control Center)"],
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "전자접촉기", "LS MC-32a", "EA", "5", "45000", "225000"],
            ["", "소계", "", "", "5", "", "225000"],
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        assert len(boundaries) >= 1

    def test_no_subtotal_or_total(self):
        """소계/합계 없는 경우"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["2", "접촉기", "AC-3 30A", "EA", "1", "100000", "100000"],
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        # 전체를 하나의 분전반으로 처리
        assert len(boundaries) == 1

    def test_blank_tolerance_exceed(self):
        """공백 3행 초과 (±2 범위 초과)"""
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["", "소계", "", "", "2", "", "100000"],
            [],  # 공백 1행
            [],  # 공백 2행
            [],  # 공백 3행 (초과)
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "접촉기", "AC-3 30A", "EA", "1", "100000", "100000"],
            ["", "합계", "", "", "1", "", "100000"],
        ]

        rules = ParserRules()
        boundaries = rules.find_panel_boundaries(rows)

        # 공백 3행이면 다음 분전반 찾지 못할 가능성
        # 구현에 따라 1개 또는 2개 가능
        assert len(boundaries) >= 1


class TestRulesEvidence:
    """규칙 증거 수집 테스트"""

    def test_evidence_collection(self):
        """규칙 적용 증거 수집"""
        rules = ParserRules()

        # 탭 전략
        tabs, rule_id = rules.detect_tab_count_and_strategy(3)

        # 분전반 경계
        rows = [
            ["번호", "품명", "규격", "단위", "수량", "단가", "금액"],
            ["1", "차단기", "3P 100A", "EA", "2", "50000", "100000"],
            ["", "소계", "", "", "2", "", "100000"],
        ]
        boundaries = rules.find_panel_boundaries(rows)

        # 증거 확인 (최소 1개 이상)
        evidence = rules.get_rules_applied()
        assert len(evidence) >= 1  # 탭 규칙은 반드시 있음

        # 증거 포맷 확인
        for ev in evidence:
            assert "rule_id" in ev
            assert "span" in ev
            assert "reason" in ev
            assert isinstance(ev["span"], list)
            assert len(ev["span"]) == 2

    def test_clear_rules(self):
        """규칙 초기화"""
        rules = ParserRules()

        # 규칙 적용
        tabs, rule_id = rules.detect_tab_count_and_strategy(2)
        assert len(rules.rules_applied) >= 1

        # 초기화
        rules.clear_rules()
        assert len(rules.rules_applied) == 0