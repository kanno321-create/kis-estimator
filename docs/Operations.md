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

