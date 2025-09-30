"""
파서 규칙 엔진 (Parser Rules Engine)
탭/분전반 규칙 적용 및 증거 수집
"""

import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class RuleApplied:
    """적용된 규칙 증거"""
    rule_id: str
    span: Tuple[int, int]  # (start_row, end_row)
    reason: str


class ParserRules:
    """파서 규칙 엔진"""

    # 규칙 ID
    RULE_TAB_2 = "TAB_RULE_2"
    RULE_TAB_3PLUS = "TAB_RULE_3PLUS"
    RULE_PANEL_SPLIT = "PANEL_SPLIT_SUBTOTAL"
    RULE_FUZZY_MATCH = "FUZZY_KEYWORD_MATCH"
    RULE_SPACING_TOLERANCE = "SPACING_TOLERANCE_PM2"

    # 키워드 (Fuzzy 매칭용)
    SUBTOTAL_KEYWORDS = ["소계", "소게", "소젤"]  # 편집거리 1 허용
    TOTAL_KEYWORDS = ["합계", "합게", "할계"]

    def __init__(self):
        self.rules_applied: List[RuleApplied] = []

    def detect_tab_count_and_strategy(self, tab_count: int) -> Tuple[List[int], str]:
        """
        탭 개수에 따른 분석 전략 결정

        Returns:
            (분석할 탭 인덱스 리스트, 규칙 ID)
        """
        if tab_count == 2:
            # 규칙 1: 탭 2개 → 모두 분석 (고압반 없음)
            self.rules_applied.append(
                RuleApplied(
                    rule_id=self.RULE_TAB_2,
                    span=(0, 1),
                    reason=f"2 tabs detected: analyze both (no high-voltage panel)"
                )
            )
            return [0, 1], self.RULE_TAB_2

        elif tab_count >= 3:
            # 규칙 2: 탭 3개 이상 → 2번 제외 (고압반), 1+3+... 분석
            tabs_to_analyze = [0] + list(range(2, tab_count))
            self.rules_applied.append(
                RuleApplied(
                    rule_id=self.RULE_TAB_3PLUS,
                    span=(0, tab_count - 1),
                    reason=f"{tab_count} tabs: skip tab#2 (high-voltage), analyze tabs {tabs_to_analyze}"
                )
            )
            return tabs_to_analyze, self.RULE_TAB_3PLUS

        else:
            # 탭 1개: 기본 처리
            return [0], "TAB_RULE_SINGLE"

    def find_panel_boundaries(
        self,
        rows: List[List[str]],
        start_row: int = 0
    ) -> List[Tuple[int, int]]:
        """
        '소계/합계' 키워드로 분전반 경계 탐지

        규칙 3: '소계/합계' 종료행 다음 1행(±2) 공백 후 새 분전반 시작

        Returns:
            [(start, end), ...] 분전반 범위 리스트
        """
        boundaries = []
        current_start = start_row
        i = start_row

        while i < len(rows):
            row = rows[i]
            row_text = " ".join([str(cell) for cell in row]).lower()

            # 소계/합계 키워드 탐지 (Fuzzy)
            if self._is_subtotal_or_total(row_text):
                current_end = i

                # 다음 분전반 시작점 찾기 (공백행 ±1~2)
                next_start = self._find_next_panel_start(rows, i + 1)

                if next_start is not None:
                    boundaries.append((current_start, current_end))

                    self.rules_applied.append(
                        RuleApplied(
                            rule_id=self.RULE_PANEL_SPLIT,
                            span=(current_start, current_end),
                            reason=f"Panel boundary: rows {current_start}-{current_end}, next starts at {next_start}"
                        )
                    )

                    current_start = next_start
                    i = next_start
                else:
                    # 마지막 분전반
                    boundaries.append((current_start, current_end))
                    break

            i += 1

        # 남은 행 처리
        if current_start < len(rows) and (not boundaries or boundaries[-1][1] < len(rows) - 1):
            boundaries.append((current_start, len(rows) - 1))

        return boundaries

    def _is_subtotal_or_total(self, text: str) -> bool:
        """소계/합계 키워드 탐지 (Fuzzy 매칭)"""
        text_lower = text.lower()

        # Fuzzy 매칭 (편집거리 1 허용)
        for keyword in self.SUBTOTAL_KEYWORDS + self.TOTAL_KEYWORDS:
            # 정확한 매칭
            if keyword in text_lower:
                # 오탈자 여부 체크
                if keyword in ["소게", "합게", "소젤", "할계"]:
                    self.rules_applied.append(
                        RuleApplied(
                            rule_id=self.RULE_FUZZY_MATCH,
                            span=(-1, -1),
                            reason=f"Fuzzy matched typo '{keyword}' in text"
                        )
                    )
                return True

            # 편집거리 1 근사 매칭
            if self._edit_distance_1(text_lower, keyword):
                self.rules_applied.append(
                    RuleApplied(
                        rule_id=self.RULE_FUZZY_MATCH,
                        span=(-1, -1),
                        reason=f"Fuzzy matched '{keyword}' (edit distance 1) in '{text[:30]}'"
                    )
                )
                return True

        return False

    def _edit_distance_1(self, text: str, keyword: str) -> bool:
        """편집거리 1 이내 매칭 (간단한 근사)"""
        # 부분 문자열에서 1글자 차이 허용
        for i in range(len(text) - len(keyword) + 1):
            substr = text[i:i + len(keyword)]
            diff = sum(c1 != c2 for c1, c2 in zip(substr, keyword))
            if diff <= 1:
                return True
        return False

    def _find_next_panel_start(
        self,
        rows: List[List[str]],
        start_from: int
    ) -> int | None:
        """
        다음 분전반 시작점 찾기
        규칙: 공백행 1~2개 후 헤더 패턴 또는 비공백 행
        """
        blank_count = 0
        max_blank_tolerance = 2  # ±2행 허용

        for i in range(start_from, min(start_from + 5, len(rows))):
            row = rows[i]

            # 공백행 판정
            if self._is_blank_row(row):
                blank_count += 1
                continue

            # 공백 후 비공백행 발견
            if blank_count > 0 and blank_count <= max_blank_tolerance:
                self.rules_applied.append(
                    RuleApplied(
                        rule_id=self.RULE_SPACING_TOLERANCE,
                        span=(start_from, i),
                        reason=f"Found {blank_count} blank rows (±2 tolerance), panel starts at row {i}"
                    )
                )
                return i

            # 공백 없이 바로 비공백행 → 분전반 구분 없음
            if blank_count == 0 and i > start_from:
                return None

        return None

    def _is_blank_row(self, row: List[str]) -> bool:
        """공백행 판정"""
        return all(not str(cell).strip() for cell in row)

    def get_rules_applied(self) -> List[Dict[str, Any]]:
        """적용된 규칙 증거 반환"""
        return [
            {
                "rule_id": rule.rule_id,
                "span": list(rule.span),
                "reason": rule.reason
            }
            for rule in self.rules_applied
        ]

    def clear_rules(self):
        """규칙 증거 초기화"""
        self.rules_applied.clear()