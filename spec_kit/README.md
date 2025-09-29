# SPEC KIT Framework for NABERAL Project

## 📋 Overview
SPEC KIT은 KIS 프로젝트의 표준 문서화 및 사양 관리 프레임워크입니다.

## 📁 Structure

```
spec_kit/
├── docs/       # 프로젝트 문서 (헌법, 가이드라인)
├── spec/       # 기술 사양 및 요구사항
├── plan/       # 개발 계획 및 로드맵
├── tasks/      # 작업 목록 및 진행 상황
├── templates/  # 문서 템플릿
├── rules/      # 비즈니스 규칙 및 제약사항
└── evidence/   # 증거 및 검증 자료
```

## 🎯 Purpose
- **표준화**: 일관된 문서 구조 유지
- **추적성**: 모든 결정과 변경사항 추적
- **품질**: 체계적인 품질 관리 체계
- **증거 기반**: 모든 구현에 대한 증거 수집

## 📐 FIX-4 Pipeline Integration
1. **Enclosure** → 외함 계산
2. **Breaker** → 브레이커 배치 (+Critic)
3. **Format** → 문서 포맷팅
4. **Cover** → 표지 생성
5. **Doc Lint** → 문서 검증

## ✅ Quality Gates
- Enclosure: fit_score ≥ 0.90, IP ≥ 44
- Breaker: 상평형 ≤ 3-5%, 위반 = 0
- Format: 문서 린트 = 0, 표지 = 100%
- Design: Polisher ≥ 95, WCAG AA = 100%
- Regression: 20/20 PASS