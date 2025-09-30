# 바이브코딩 규칙 (Vibe Coding Rules)

## 📋 3가지 파일 규칙 시스템

### 1️⃣ PRD 생성 규칙

**AI는 PRD를 작성할 때 다음 규칙을 준수해야 합니다:**

1. **쉬운 언어 사용**
   - 주니어 개발자도 이해할 수 있는 단어 선택
   - 복잡한 전문 용어 최소화
   - 명확하고 구체적인 설명

2. **질문 우선 방식**
   - PRD 작성 전 필요한 정보 파악
   - 체계적인 번호로 질문 (1.1, 1.2, 2.1 형식)
   - 사용자 응답 후 PRD 작성

3. **체크포인트 시스템**
   - 각 섹션 작성 후 사용자 확인
   - 수정사항 즉시 반영

### 2️⃣ Task 생성 규칙

**PRD를 기반으로 Task를 생성할 때:**

1. **분할 정복 (Divide & Conquer)**
   ```markdown
   - [ ] Task 1: 데이터베이스 스키마 설계
   - [ ] Task 2: API 엔드포인트 구현
   - [ ] Task 3: 입력 검증 로직 추가
   ```

2. **마크다운 체크박스 필수**
   - 모든 Task는 `- [ ]` 형식
   - 완료 시 `- [x]`로 변경
   - 하위 Task는 들여쓰기로 표현

3. **작업 단위 기준**
   - 1시간 이내 완료 가능한 크기
   - 독립적으로 테스트 가능
   - 명확한 완료 기준 포함

### 3️⃣ Task 실행 규칙

**실제 코딩 시 준수사항:**

1. **단일 Task 원칙**
   ```
   현재 Task: [Task 1 실행 중...]
   상태: 진행 중
   다음 Task: 승인 대기
   ```

2. **승인 체크포인트**
   - Task 완료 → 정지
   - 사용자 검토 대기
   - "continue" 또는 "다음" 명령 시 진행

3. **진행 상황 추적**
   ```markdown
   ## 진행 상황
   - [x] Task 1: 완료 ✅
   - [x] Task 2: 완료 ✅
   - [ ] Task 3: 진행 중 🔄
   - [ ] Task 4: 대기 ⏳
   ```

## 🔄 SPEC KIT 통합

### PRD → SPEC 문서 변환
```
PRD 섹션          → SPEC KIT 위치
-----------------------------------------
제품 개요         → /spec_kit/spec/overview.md
기능 요구사항     → /spec_kit/spec/requirements.md
기술 사양        → /spec_kit/spec/technical.md
```

### Task → FIX-4 파이프라인 매핑
```
Task 유형         → FIX-4 단계
-----------------------------------------
외함 관련        → Stage 1: Enclosure
브레이커 관련    → Stage 2: Breaker
문서 생성        → Stage 3: Format
표지/메타        → Stage 4: Cover
검증/테스트      → Stage 5: Doc Lint
```

## 🎯 실행 프로토콜

1. **시작 시**
   ```
   "PRD를 생성하겠습니다. 먼저 몇 가지 질문이 필요합니다:"
   ```

2. **Task 실행 중**
   ```
   "Task 1을 실행합니다..."
   [코드 생성]
   "Task 1 완료. 검토 후 'continue'로 다음 진행하세요."
   ```

3. **완료 시**
   ```
   "모든 Task 완료 ✅
   Evidence: /spec_kit/evidence/[timestamp]/
   품질 게이트: 모두 통과"
   ```

## ⚙️ 자동화 설정

### MCP 알림 (선택사항)
```yaml
trigger:
  - task_duration > 60s
  - task_completed: true
action:
  - send_notification: "Task 완료"
  - update_checklist: true
```

## 📊 품질 지표

- PRD 명확도: 주니어 이해도 ≥ 90%
- Task 분할: 평균 크기 ≤ 1시간
- 승인률: 첫 시도 승인 ≥ 80%
- 완료율: 계획 대비 ≥ 95%

---
*이 규칙은 바이브코딩 원칙과 SPEC KIT 표준을 통합합니다.*