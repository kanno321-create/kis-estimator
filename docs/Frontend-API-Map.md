# Frontend-API Mapping Guide

## Overview
1:1 mapping between frontend UI elements and API endpoints for KIS Estimator system.

## Quote Estimation Flow

### 1. Upload & Validate Input
**UI Element**: "엑셀 업로드" button / File input
**API Call**: `POST /v1/validate`
```bash
curl -X POST http://localhost:8000/v1/validate \
  -F "file=@quote_input.xlsx" \
  -F "ruleset=tab"
```
**Response**: Normalized input data
**Action**: Auto-fill form fields with detected panels/breakers

### 2. Create Estimate
**UI Element**: "견적 생성" button
**API Call**: `POST /v1/estimate`
```bash
curl -X POST http://localhost:8000/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {"name": "테스트 고객사"},
    "panels": [{"name": "Main", "breakers": [...]}],
    "currency": "KRW"
  }'
```
**Response**: `{ "quoteId": "uuid", "links": {...} }`
**Action**: 
- Store `quoteId` in state
- Subscribe to SSE stream
- Enable download buttons after DONE event

### 3. Monitor Progress (SSE)
**UI Element**: Progress bar / Status indicator
**API Call**: `GET /v1/estimate/stream?quoteId={id}`
```bash
curl -N http://localhost:8000/v1/estimate/stream?quoteId=abc-123
```
**Events**:
- `HEARTBEAT`: Update "시스템 연결 중..." indicator
- `PROGRESS`: Update progress bar (`stage: enclosure/breaker/...`)
- `GATE_RESULT`: Show gate pass/fail status
- `DONE`: Enable download buttons, show "완료" status

**Action**: 
- Parse `event` and `data` fields
- Update UI based on `meta.seq` (monotonic)
- Never show `meta: null` (validation enforced)

### 4. View Estimate Details
**UI Element**: "견적 상세보기" button
**API Call**: `GET /v1/estimate/{id}`
```bash
curl http://localhost:8000/v1/estimate/abc-123
```
**Response**: Full quote details with panels/breakers/evidence
**Action**: Navigate to detail view page

## Document Download Flow

### 5. List Available Documents
**UI Element**: Document download section
**API Call**: `GET /v1/documents?quoteId={id}&kind={pdf|xlsx}`
```bash
curl "http://localhost:8000/v1/documents?quoteId=abc-123&kind=pdf"
```
**Response**: `{ "items": [{"signedUrl": "...", "sha256": "..."}] }`
**Action**: Populate download button hrefs with `signedUrl`

### 6. Download PDF/Excel
**UI Element**: "PDF 다운로드" / "Excel 다운로드" buttons
**Action**: Use `signedUrl` from step 5 (10-min TTL)
```javascript
window.open(signedUrl, '_blank')
```

### 7. Export Documents (Async)
**UI Element**: "문서 재생성" button
**API Call**: `POST /v1/documents/export`
```bash
curl -X POST http://localhost:8000/v1/documents/export \
  -H "Content-Type: application/json" \
  -d '{"quoteId": "abc-123", "kinds": ["pdf", "xlsx"]}'
```
**Response**: `{ "taskId": "task-uuid" }` (202 Accepted)
**Action**: Poll or wait for SSE notification of completion

## Catalog Search Flow

### 8. Search Parts Catalog
**UI Element**: Parts search box / Autocomplete
**API Call**: `GET /v1/catalog?kind={enclosure|breaker}&q={query}`
```bash
curl "http://localhost:8000/v1/catalog?kind=breaker&q=LS+100A&page=1&size=20"
```
**Response**: `{ "items": [...], "pagination": {...} }`
**Action**: Display search results in dropdown/table

### 9. Add Catalog Items (Admin)
**UI Element**: Admin panel "카탈로그 추가" form
**API Call**: `POST /v1/catalog/items`
```bash
curl -X POST http://localhost:8000/v1/catalog/items \
  -H "Content-Type: application/json" \
  -d '[{"kind": "breaker", "sku": "BRK-123", ...}]'
```
**Response**: `{ "upserted": 5 }`
**Action**: Show success toast, refresh catalog list

## Error Handling

### Standard Error Response
All 4xx/5xx responses follow this schema:
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Enclosure fit score below threshold",
  "hint": "Minimum fit_score is 0.90, got 0.85",
  "traceId": "550e8400-e29b-41d4-a716-446655440000",
  "meta": {
    "dedupKey": "quote_xyz_enclosure_fit",
    "field": "fit_score",
    "constraint": "gte_0.90"
  }
}
```

**UI Action**:
- Display `message` to user
- Show `hint` if available
- Log `traceId` for support
- Use `meta.dedupKey` to deduplicate error toasts

## Quality Gates Display

### Gate Status Indicators
**Data Source**: From `/v1/estimate` response or SSE `GATE_RESULT` event

**Gates to Display**:
1. **Enclosure**: `fit_score >= 0.90` ✅/❌
2. **Phase Balance**: `phase_dev <= 0.03` ✅/❌
3. **Clearance**: `clearance_violations = 0` ✅/❌
4. **Formula Preservation**: `formula_loss = 0` ✅/❌
5. **Document Lint**: `lint_errors = 0` ✅/❌

**UI Example**:
```
품질 게이트 상태
✅ 외함 적합성: 0.92 (기준: ≥0.90)
✅ 상평형: 2.1% (기준: ≤3.0%)
✅ 간섭 검사: 위반 0건
✅ 수식 보존: 손실 0개
✅ 문서 검증: 오류 0개
```

## Common Headers

### Request Headers
- `X-Trace-Id`: UUID for request tracing (optional, generated if missing)
- `Idempotency-Key`: UUID for write operations (POST /v1/estimate, etc.)

### Response Headers
- `X-Trace-Id`: Echo back or generated trace ID
- `X-Process-Time`: Processing time in seconds

## SSE Event Structure

### Event Types
```
event: HEARTBEAT
data: {"meta": {"seq": 1, "timestamp": "2025-09-30T10:00:00Z"}}

event: PROGRESS
data: {"meta": {"seq": 2, "timestamp": "..."}, "stage": "enclosure", "progress": 0.2}

event: GATE_RESULT
data: {"meta": {"seq": 3, "timestamp": "..."}, "stage": "enclosure", "status": "pass", "metrics": {"fit_score": 0.92}}

event: DONE
data: {"meta": {"seq": 10, "timestamp": "..."}, "quoteId": "abc-123", "status": "success"}
```

### SSE Connection Management
- **Reconnect**: If connection drops, reconnect with same `quoteId`
- **Timeout**: Close connection after DONE event received
- **Error**: Display error event data to user, offer retry

## Pagination

### Query Parameters
- `page`: Page number (1-indexed)
- `size`: Items per page (default: 20, max: 100)

### Response Structure
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 156,
    "pages": 8
  }
}
```

## Complete User Journey

```
1. User clicks "엑셀 업로드"
   → POST /v1/validate
   → Form auto-filled

2. User clicks "견적 생성"
   → POST /v1/estimate
   → Get quoteId
   → Open SSE connection

3. SSE events update UI
   → PROGRESS: Update progress bar
   → GATE_RESULT: Show gate status
   → DONE: Enable downloads

4. User clicks "PDF 다운로드"
   → GET /v1/documents?kind=pdf
   → Get signedUrl
   → window.open(signedUrl)

5. User clicks "견적 상세보기"
   → GET /v1/estimate/{id}
   → Navigate to detail page
```

---

**Contract Version**: 1.0.0  
**Last Updated**: 2025-09-30  
**OpenAPI Spec**: `/openapi.yaml`
