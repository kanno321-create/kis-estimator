# KIS Estimator Constitution
## Contract-First + Evidence-Gated + SPEC KIT 기반 시스템

### 1. 핵심 원칙 (Core Principles)

#### 1.1 Contract-First Development
- 모든 API는 OpenAPI 3.1 스펙 우선 작성
- 스펙 검증 통과 후 구현 시작
- 계약 일치율 ≥99% 유지

#### 1.2 Evidence-Gated Validation
- 모든 쓰기 작업은 Evidence Pack 필수
- SHA256 해시로 무결성 보장
- Evidence 커버리지 100% 달성

#### 1.3 Quality Gates
- 회귀 테스트 20/20 통과 필수
- 각 단계별 품질 기준 충족
- Hard-fail on violations

### 2. FIX-4 파이프라인 규범

#### Stage 1: Enclosure
- **Quality Gate**: fit_score ≥ 0.90
- **IP Rating**: ≥ IP44
- **Door Clearance**: ≥ 30mm

#### Stage 2: Breaker
- **Quality Gate**: 상평형 ≤ 3%
- **Clearance**: 위반 = 0
- **Thermal**: Row ≤ 650W, Panel ≤ 2500W

#### Stage 3: Format
- **Quality Gate**: 수식 보존 = 100%
- **Named Ranges**: 손상 = 0

#### Stage 4: Cover
- **Quality Gate**: 정책 위반 = 0
- **Branding**: 100% 적용

#### Stage 5: Doc Lint
- **Quality Gate**: 오류 = 0
- **Citation**: 커버리지 = 100%

### 3. 기술 표준

#### 3.1 Database
- 모든 timestamp는 TIMESTAMPTZ with UTC
- Schemas: estimator, shared
- 트리거로 updated_at 자동 갱신

#### 3.2 API Standards
```json
{
  "error_schema": {
    "code": "string",
    "message": "string",
    "hint": "string?",
    "traceId": "uuid",
    "meta": {"dedupKey": "string"}
  }
}
```

#### 3.3 Performance
- API p95 < 200ms
- Health check < 50ms
- SSE heartbeat 필수

### 4. MCP 도구 규약

#### 4.1 필수 도구
1. enclosure.solve / validate
2. layout.place_breakers / check_clearance / balance_phases
3. estimate.format / export
4. doc.cover_generate / apply_branding / lint / policy_check
5. rag.ingest / normalize / index / verify
6. regression.run (20/20 PASS)

#### 4.2 도구 호출 규칙
- 모든 호출은 idempotency key 포함
- 실패 시 3회 재시도
- Evidence 생성 필수

### 5. 배포 차단 조건 (Hard Gates)

1. **회귀 테스트**: 20/20 미달 시 차단
2. **Evidence**: 누락 시 차단
3. **보안**: secrets 노출 시 차단
4. **계약**: OpenAPI 위반 시 차단

### 6. 바이브코딩 통합

#### 6.1 PRD 규칙
- 쉬운 언어 사용
- 질문 우선 방식
- 체크포인트 시스템

#### 6.2 Task 규칙
- 1시간 단위 분할
- 마크다운 체크박스
- 독립 테스트 가능

#### 6.3 실행 규칙
- 단일 Task 원칙
- 승인 체크포인트
- 진행 상황 추적

### 7. 팀 규범

#### 7.1 코드 리뷰
- 모든 PR은 2명 이상 승인
- 품질 게이트 통과 필수
- Evidence 검토 포함

#### 7.2 문서화
- 코드와 문서 동기화
- SSOT 원칙 준수
- 변경사항 즉시 반영

#### 7.3 인시던트 대응
- 5분 내 초기 대응
- 30분 내 근본 원인 파악
- 24시간 내 포스트모템

### 8. 개정 절차

이 헌법의 개정은 다음 절차를 따른다:
1. 개정안 PR 생성
2. 팀 전체 리뷰 (최소 7일)
3. 2/3 이상 승인
4. 회귀 테스트 통과
5. 즉시 발효

---

*제정일: 2024-12-30*
*버전: 1.0.0*
*다음 리뷰: 2025-03-30*