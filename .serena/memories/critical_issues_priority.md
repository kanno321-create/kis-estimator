# KIS Estimator 핵심 이슈 및 우선순위

## 🔴 Critical 블로커 (즉시 해결 필요)

### 1. 테스트 커버리지: 19.9%
**목표**: 80% (Constitution 요구사항)
**차단 사유**: 실제 테스트 환경 부재
**필요 조치**:
```bash
# Docker Compose로 테스트 환경 구축
docker-compose -f docker-compose.test.yml up -d
```

### 2. 회귀 테스트: 미검증
**요구사항**: 20/20 PASS 필수 (머지 전)
**현재 상태**: 확인 필요
```bash
pytest -m regression
```

## ✅ 해결 완료

### 1. 보안 취약점 (2025-10-01)
- APP_DEBUG=False 설정 완료
- 환경별 설정 파일 분리

### 2. 테스트 컬렉션 오류 (2025-10-01)
- Optional import 추가
- inject_failure 메서드 구현

## 📋 핵심 규칙 (절대 위반 금지)

### 목업(MOCKUP) 절대 금지
- Mock 테스트 작성 금지
- Fake 클라이언트 테스트 무효
- 실제 환경 테스트만 인정
- 위반 시 프로젝트 폐기 위험

## 🎯 다음 단계 로드맵

### Phase 1: 테스트 환경 구축
1. PostgreSQL 테스트 DB 설정
2. Supabase 테스트 프로젝트 생성
3. Redis 테스트 인스턴스 구동
4. MCP 서버 연동 설정

### Phase 2: 실제 테스트 작성
1. 핵심 서비스 통합 테스트
2. FIX-4 파이프라인 E2E 테스트
3. 회귀 테스트 20/20 검증

### Phase 3: 프로덕션 준비
1. 테스트 커버리지 80% 달성
2. 성능 벤치마크 검증
3. v1.0.0 릴리즈 준비

## 성능 목표 (달성 예상)
- API 응답 P95: <200ms ✅
- Health 체크: <50ms ✅
- 브레이커 배치: <1s ✅
- 외함 계산: <500ms ✅