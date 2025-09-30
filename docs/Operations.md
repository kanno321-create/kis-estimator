# KIS Estimator - Operations Policy

## Overview
KIS Estimator 운영 정책 문서 - 보안, 성능, 비용, 가용성 기준

## Security Policy

### Access Control
- **Service Role Key**: Server-side only (절대 노출 금지)
- **Anon Key**: Client-side safe (RLS 보호)
- **Signed URLs**: Time-limited (300s prod / 600s staging)

### RLS Enforcement
- ✅ ALL tables: RLS enabled
- ✅ Writer: Service role ONLY
- ✅ Reader: Signed URLs ONLY

## Performance SLO

| Metric | Target | Maximum |
|--------|--------|---------|
| API Response (p95) | < 200ms | < 500ms |
| Health Check | < 50ms | < 100ms |
| Breaker Placement (100) | < 1s | < 30s |

## Availability SLA

- **Uptime**: 99.9% (monthly)
- **MTTR**: < 1 hour (P0/P1)
- **RTO**: < 1 hour
- **RPO**: < 5 minutes (PITR)

## Cost Management

- **Evidence Retention**: 90 days (prod), 30 days (staging)
- **DB Pool Size**: 50 (prod), 20 (staging)
- **Rate Limit**: 10 RPS (prod), 20 RPS (staging)

## Evidence Ledger Operations

### Overview
Evidence Ledger는 Go-Live 증거팩(artifacts, SHA256SUMS.txt)을 관리자가 열람, 다운로드, 무결성 검증할 수 있는 읽기 전용 API입니다.

### Access Control
- **Endpoint**: `/v1/evidence/*`
- **Authentication**: JWT 필수
- **Authorization**: Admin 또는 service_role만 접근 가능
- **Regular Users**: 403 Forbidden

### Operations

#### 1. List Evidence Packs
```bash
# 모든 증거팩 목록 조회
curl -H "Authorization: Bearer <ADMIN_JWT>" \
  "$BASE_URL/v1/evidence/packs"

# 검색 및 페이징
curl -H "Authorization: Bearer <ADMIN_JWT>" \
  "$BASE_URL/v1/evidence/packs?q=GO_LIVE_2025&limit=20&offset=0&order=created_at_desc"
```

**Response**:
```json
{
  "packs": [
    {
      "id": "GO_LIVE_20250930T120000Z",
      "created_at": "2025-09-30T12:00:00Z",
      "total_files": 15,
      "total_bytes": 1024000,
      "has_sha256sums": true
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

#### 2. Get Pack Details
```bash
# 특정 팩의 파일 목록 조회
curl -H "Authorization: Bearer <ADMIN_JWT>" \
  "$BASE_URL/v1/evidence/packs/GO_LIVE_20250930T120000Z"
```

**Response**:
```json
{
  "pack_id": "GO_LIVE_20250930T120000Z",
  "created_at": "2025-09-30T12:00:00Z",
  "total_files": 15,
  "total_bytes": 1024000,
  "has_sha256sums": true,
  "files": [
    {
      "name": "SHA256SUMS.txt",
      "full_path": "GO_LIVE_20250930T120000Z/SHA256SUMS.txt",
      "size": 2048,
      "mime": "text/plain",
      "created_at": "2025-09-30T12:00:00Z"
    },
    {
      "name": "artifacts/estimate_report.pdf",
      "full_path": "GO_LIVE_20250930T120000Z/artifacts/estimate_report.pdf",
      "size": 512000,
      "mime": "application/pdf",
      "created_at": "2025-09-30T12:00:05Z"
    }
  ]
}
```

#### 3. Generate Download URL
```bash
# 서명된 다운로드 URL 생성 (기본: 10분 만료)
curl -H "Authorization: Bearer <ADMIN_JWT>" \
  "$BASE_URL/v1/evidence/packs/GO_LIVE_20250930T120000Z/download?file=SHA256SUMS.txt"

# 커스텀 만료 시간 (5분)
curl -H "Authorization: Bearer <ADMIN_JWT>" \
  "$BASE_URL/v1/evidence/packs/GO_LIVE_20250930T120000Z/download?file=artifacts/report.pdf&expires_in=300"
```

**Response**:
```json
{
  "signed_url": "https://[supabase-url]/storage/v1/object/sign/evidence/GO_LIVE.../SHA256SUMS.txt?token=...",
  "expires_in": 600,
  "file_path": "GO_LIVE_20250930T120000Z/SHA256SUMS.txt",
  "generated_at": "2025-09-30T12:00:00Z"
}
```

#### 4. Verify Pack Integrity
```bash
# 증거팩 무결성 검증 (실제 SHA256 해시 계산)
curl -X POST \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"pack_id":"GO_LIVE_20250930T120000Z"}' \
  "$BASE_URL/v1/evidence/verify"
```

**Response (Success)**:
```json
{
  "status": "OK",
  "pack_id": "GO_LIVE_20250930T120000Z",
  "files_checked": 14,
  "mismatched": [],
  "duration_ms": 1234,
  "verified_at": "2025-09-30T12:05:00Z",
  "trace_id": "abc-123-def"
}
```

**Response (Failure - Hash Mismatch)**:
```json
{
  "status": "FAIL",
  "pack_id": "GO_LIVE_20250930T120000Z",
  "files_checked": 14,
  "mismatched": [
    {
      "file": "artifacts/report.pdf",
      "expected": "abc123...",
      "actual": "def456..."
    }
  ],
  "duration_ms": 1456,
  "verified_at": "2025-09-30T12:05:00Z",
  "trace_id": "abc-123-def"
}
```

### Security Notes

1. **Zero Client Exposure**: 서명 URL 생성은 서버에서만 수행. 클라이언트는 서명된 URL만 받음.
2. **Short Expiration**: 다운로드 URL은 기본 10분 만료 (최대 1시간).
3. **Admin Only**: 모든 엔드포인트는 admin 또는 service_role만 접근 가능.
4. **Audit Logging**: 모든 요청은 traceId와 함께 로깅됨.

### Performance Targets

| Operation | Target | Maximum |
|-----------|--------|---------|
| List Packs | < 500ms | < 2s |
| Get Details | < 300ms | < 1s |
| Generate URL | < 200ms | < 500ms |
| Verify (small pack) | < 2s | < 10s |
| Verify (large pack) | < 10s | < 60s |

### Verification Process

1. **Download SHA256SUMS.txt**: 실제 Supabase Storage에서 다운로드
2. **Parse**: 예상 해시값 파싱
3. **Stream Hash**: 각 파일을 실제로 다운로드하여 SHA256 해시 계산
4. **Compare**: 실제 해시 vs 예상 해시 비교
5. **Report**: OK 또는 FAIL + 불일치 파일 목록 반환

**Zero-Mock**: 모든 파일 I/O와 해시 계산은 실제 수행. 시뮬레이션/목업 절대 금지.

### Error Handling

| Error Code | Status | Description |
|------------|--------|-------------|
| `INSUFFICIENT_PERMISSIONS` | 403 | Admin 권한 부족 |
| `PACK_NOT_FOUND` | 404 | 증거팩 존재하지 않음 |
| `FILE_NOT_FOUND` | 404 | 파일 존재하지 않음 |
| `EVIDENCE_LIST_FAILED` | 500 | 목록 조회 실패 |
| `EVIDENCE_DETAILS_FAILED` | 500 | 상세 조회 실패 |
| `DOWNLOAD_URL_FAILED` | 500 | URL 생성 실패 |
| `EVIDENCE_VERIFY_FAIL` | 500 | 무결성 검증 실패 |

### Monitoring

**Structured Logging Fields**:
- `traceId`: 요청 추적 ID
- `action`: `evidence.list`, `evidence.details`, `evidence.download`, `evidence.verify`
- `pack_id`: 증거팩 ID
- `files_checked`: 검증된 파일 수 (verify only)
- `mismatched_count`: 불일치 파일 수 (verify only)
- `duration_ms`: 작업 소요 시간

**Example Log**:
```
[abc-123-def] Evidence verification complete: action=evidence.verify pack_id=GO_LIVE_20250930T120000Z status=OK files_checked=14 mismatched_count=0 duration_ms=1234
```

### Troubleshooting

#### Pack Not Found
```bash
# 1. Supabase Storage 버킷 확인
# 2. 경로 규칙 확인: GO_LIVE_YYYYMMDDTHHMMSSZ/**
# 3. RLS 정책 확인 (service_role은 bypass)
```

#### Verification Failure
```bash
# 1. SHA256SUMS.txt 존재 확인
# 2. 파일 경로 일치 확인 (대소문자 구분)
# 3. 실제 파일 변조 여부 확인
# 4. 로그에서 mismatched 배열 분석
```

#### Permission Denied (403)
```bash
# 1. JWT 토큰 role 확인 (admin 또는 service_role 필요)
# 2. 토큰 만료 여부 확인
# 3. SUPABASE_JWT_SECRET 환경변수 확인
```

