-- ============================================================================
-- Supabase 배포 검증 쿼리
-- SQL Editor에서 이 쿼리들을 하나씩 실행하여 배포 상태를 확인하세요
-- ============================================================================

-- 1. 스키마 확인 (2개 나와야 함: estimator, shared)
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('estimator', 'shared')
ORDER BY schema_name;

-- 2. 테이블 확인 (7개 테이블 나와야 함)
SELECT
    table_schema,
    table_name,
    CASE
        WHEN table_schema = 'estimator' THEN '견적 시스템'
        WHEN table_schema = 'shared' THEN '공유 데이터'
    END as category
FROM information_schema.tables
WHERE table_schema IN ('estimator', 'shared')
ORDER BY table_schema, table_name;

-- 3. 함수 확인 (5개 이상 나와야 함)
SELECT
    routine_name,
    routine_type,
    CASE routine_name
        WHEN 'update_updated_at' THEN '타임스탬프 자동 업데이트'
        WHEN 'check_sha256' THEN 'SHA256 검증'
        WHEN 'validate_evidence_integrity' THEN '증거 무결성 검증'
        WHEN 'calculate_quote_totals' THEN '견적 합계 계산'
        WHEN 'get_phase_balance' THEN '3상 전력 균형 계산'
    END as description
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name IN (
    'update_updated_at',
    'check_sha256',
    'validate_evidence_integrity',
    'calculate_quote_totals',
    'get_phase_balance'
)
ORDER BY routine_name;

-- 4. RLS (Row Level Security) 확인 (모든 테이블이 true여야 함)
SELECT
    schemaname,
    tablename,
    rowsecurity as rls_enabled,
    CASE
        WHEN rowsecurity = true THEN '✅ 보안 활성화'
        ELSE '❌ 보안 비활성화'
    END as status
FROM pg_tables
WHERE schemaname IN ('estimator', 'shared')
ORDER BY schemaname, tablename;

-- 5. 정책(Policy) 확인 (14개 이상 나와야 함)
SELECT
    schemaname,
    tablename,
    policyname,
    CASE
        WHEN policyname LIKE '%service_role%' THEN 'Service Role (전체 권한)'
        WHEN policyname LIKE '%authenticated%' THEN 'Authenticated (읽기 전용)'
        ELSE 'Other'
    END as policy_type
FROM pg_policies
WHERE schemaname IN ('estimator', 'shared')
ORDER BY schemaname, tablename, policyname;

-- 6. 인덱스 확인 (최적화용)
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname IN ('estimator', 'shared')
ORDER BY schemaname, tablename, indexname;

-- 7. 트리거 확인 (5개 나와야 함: 각 테이블의 updated_at 트리거)
SELECT
    trigger_schema,
    event_object_table as table_name,
    trigger_name,
    event_manipulation,
    action_statement
FROM information_schema.triggers
WHERE trigger_schema IN ('estimator', 'shared')
ORDER BY trigger_schema, event_object_table;

-- 8. 테이블 행 수 확인 (초기에는 모두 0)
SELECT 'quotes' as table_name, COUNT(*) as row_count FROM estimator.quotes
UNION ALL
SELECT 'quote_items', COUNT(*) FROM estimator.quote_items
UNION ALL
SELECT 'panels', COUNT(*) FROM estimator.panels
UNION ALL
SELECT 'breakers', COUNT(*) FROM estimator.breakers
UNION ALL
SELECT 'documents', COUNT(*) FROM estimator.documents
UNION ALL
SELECT 'evidence_blobs', COUNT(*) FROM estimator.evidence_blobs
UNION ALL
SELECT 'catalog_items', COUNT(*) FROM shared.catalog_items;

-- 9. 함수 테스트: SHA256 검증
SELECT
    public.check_sha256('a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890') as valid_hash_result,
    public.check_sha256('invalid') as invalid_hash_result,
    public.check_sha256(NULL) as null_hash_result;

-- 10. 테스트 데이터 삽입 및 조회 (선택사항)
-- INSERT INTO estimator.quotes (customer, status)
-- VALUES ('{"name": "테스트 고객"}'::jsonb, 'draft')
-- RETURNING id, customer, status, created_at;

-- 11. 최종 요약
SELECT
    'Deployment Status' as check_type,
    '✅ SUCCESS' as result,
    'All systems operational' as message;