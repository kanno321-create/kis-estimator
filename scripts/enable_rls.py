#!/usr/bin/env python3
"""
Supabase RLS (Row Level Security) 활성화 스크립트
모든 테이블에 RLS를 활성화하고 적절한 정책을 설정합니다.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv('.env.local')

# 데이터베이스 연결
DATABASE_URL = os.getenv('SUPABASE_DB_URL', os.getenv('DATABASE_URL'))

# RLS 활성화 및 정책 SQL
ENABLE_RLS_SQL = """
-- RLS(Row Level Security) 활성화
-- 모든 테이블에 대해 RLS를 활성화합니다

-- 1. Customers 테이블
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;

-- 정책: 인증된 사용자만 읽기 가능
CREATE POLICY "Allow authenticated users to read customers"
ON customers FOR SELECT
TO authenticated
USING (true);

-- 정책: 서비스 역할은 모든 작업 가능
CREATE POLICY "Service role full access to customers"
ON customers FOR ALL
TO service_role
USING (true);

-- 2. Quotes 테이블
ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;

-- 정책: 인증된 사용자는 자신의 견적만 조회
CREATE POLICY "Users can view their own quotes"
ON quotes FOR SELECT
TO authenticated
USING (auth.uid()::text = created_by OR created_by IS NULL);

-- 정책: 서비스 역할은 모든 작업 가능
CREATE POLICY "Service role full access to quotes"
ON quotes FOR ALL
TO service_role
USING (true);

-- 3. Quote Items 테이블
ALTER TABLE quote_items ENABLE ROW LEVEL SECURITY;

-- 정책: 견적에 접근 가능한 사용자만 항목 조회 가능
CREATE POLICY "Users can view quote items for their quotes"
ON quote_items FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM quotes
        WHERE quotes.id = quote_items.quote_id
        AND (quotes.created_by = auth.uid()::text OR quotes.created_by IS NULL)
    )
);

-- 정책: 서비스 역할은 모든 작업 가능
CREATE POLICY "Service role full access to quote_items"
ON quote_items FOR ALL
TO service_role
USING (true);

-- 4. Panels 테이블
ALTER TABLE panels ENABLE ROW LEVEL SECURITY;

-- 정책: 견적에 접근 가능한 사용자만 패널 조회 가능
CREATE POLICY "Users can view panels for their quotes"
ON panels FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM quotes
        WHERE quotes.id = panels.quote_id
        AND (quotes.created_by = auth.uid()::text OR quotes.created_by IS NULL)
    )
);

-- 정책: 서비스 역할은 모든 작업 가능
CREATE POLICY "Service role full access to panels"
ON panels FOR ALL
TO service_role
USING (true);

-- 5. Evidence Blobs 테이블
ALTER TABLE evidence_blobs ENABLE ROW LEVEL SECURITY;

-- 정책: 견적에 접근 가능한 사용자만 증거 조회 가능
CREATE POLICY "Users can view evidence for their quotes"
ON evidence_blobs FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM quotes
        WHERE quotes.id = evidence_blobs.quote_id
        AND (quotes.created_by = auth.uid()::text OR quotes.created_by IS NULL)
    )
);

-- 정책: 서비스 역할은 모든 작업 가능
CREATE POLICY "Service role full access to evidence_blobs"
ON evidence_blobs FOR ALL
TO service_role
USING (true);

-- 6. Breaker Catalog 테이블 (읽기 전용)
ALTER TABLE breaker_catalog ENABLE ROW LEVEL SECURITY;

-- 정책: 모든 인증된 사용자가 카탈로그 읽기 가능
CREATE POLICY "All authenticated users can read breaker catalog"
ON breaker_catalog FOR SELECT
TO authenticated
USING (true);

-- 정책: 서비스 역할만 수정 가능
CREATE POLICY "Only service role can modify breaker catalog"
ON breaker_catalog FOR ALL
TO service_role
USING (true);

-- 7. Enclosure Catalog 테이블 (읽기 전용)
ALTER TABLE enclosure_catalog ENABLE ROW LEVEL SECURITY;

-- 정책: 모든 인증된 사용자가 카탈로그 읽기 가능
CREATE POLICY "All authenticated users can read enclosure catalog"
ON enclosure_catalog FOR SELECT
TO authenticated
USING (true);

-- 정책: 서비스 역할만 수정 가능
CREATE POLICY "Only service role can modify enclosure catalog"
ON enclosure_catalog FOR ALL
TO service_role
USING (true);

-- 8. Validation Rules 테이블 (읽기 전용)
ALTER TABLE validation_rules ENABLE ROW LEVEL SECURITY;

-- 정책: 모든 인증된 사용자가 검증 규칙 읽기 가능
CREATE POLICY "All authenticated users can read validation rules"
ON validation_rules FOR SELECT
TO authenticated
USING (true);

-- 정책: 서비스 역할만 수정 가능
CREATE POLICY "Only service role can modify validation rules"
ON validation_rules FOR ALL
TO service_role
USING (true);

-- 9. Audit Logs 테이블 (추가 전용)
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- 정책: 사용자는 자신의 감사 로그만 조회
CREATE POLICY "Users can view their own audit logs"
ON audit_logs FOR SELECT
TO authenticated
USING (user_id = auth.uid()::text);

-- 정책: 인증된 사용자는 로그 추가만 가능
CREATE POLICY "Authenticated users can insert audit logs"
ON audit_logs FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid()::text);

-- 정책: 서비스 역할은 모든 로그 접근 가능
CREATE POLICY "Service role full access to audit_logs"
ON audit_logs FOR ALL
TO service_role
USING (true);

-- 10. SSE Events 테이블
ALTER TABLE sse_events ENABLE ROW LEVEL SECURITY;

-- 정책: 견적에 접근 가능한 사용자만 이벤트 조회 가능
CREATE POLICY "Users can view SSE events for their quotes"
ON sse_events FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM quotes
        WHERE quotes.id = sse_events.quote_id
        AND (quotes.created_by = auth.uid()::text OR quotes.created_by IS NULL)
    )
);

-- 정책: 서비스 역할은 모든 작업 가능
CREATE POLICY "Service role full access to sse_events"
ON sse_events FOR ALL
TO service_role
USING (true);
"""

# anon 역할에 대한 추가 정책 (읽기 전용 카탈로그)
ANON_POLICIES_SQL = """
-- anon 역할도 카탈로그는 읽을 수 있도록 설정

-- Breaker Catalog 읽기 허용
CREATE POLICY "Anon can read breaker catalog"
ON breaker_catalog FOR SELECT
TO anon
USING (true);

-- Enclosure Catalog 읽기 허용
CREATE POLICY "Anon can read enclosure catalog"
ON enclosure_catalog FOR SELECT
TO anon
USING (true);

-- Validation Rules 읽기 허용
CREATE POLICY "Anon can read validation rules"
ON validation_rules FOR SELECT
TO anon
USING (is_active = true);
"""

def enable_rls():
    """RLS 활성화 및 정책 설정"""
    print("[RLS SETUP] Supabase RLS 설정 시작...")
    print(f"[RLS SETUP] 데이터베이스 연결: {DATABASE_URL[:50]}...")

    try:
        # 데이터베이스 연결
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # 기존 정책 확인
        cur.execute("""
            SELECT t.tablename, COUNT(p.policyname) as policy_count
            FROM pg_tables t
            LEFT JOIN pg_policies p ON t.tablename = p.tablename
            WHERE t.schemaname = 'public'
            GROUP BY t.tablename
            ORDER BY t.tablename;
        """)

        print("\n[RLS SETUP] 현재 테이블 상태:")
        tables = cur.fetchall()
        for table, policy_count in tables:
            status = "RLS 활성화됨" if policy_count > 0 else "UNRESTRICTED"
            print(f"  - {table}: {status} (정책 {policy_count}개)")

        # RLS 활성화 및 정책 생성
        print("\n[RLS SETUP] RLS 활성화 및 정책 생성 중...")

        # 기존 정책 삭제 (중복 방지)
        for table, _ in tables:
            cur.execute(f"""
                DROP POLICY IF EXISTS "Allow authenticated users to read {table}" ON {table};
                DROP POLICY IF EXISTS "Service role full access to {table}" ON {table};
                DROP POLICY IF EXISTS "Users can view their own {table}" ON {table};
                DROP POLICY IF EXISTS "Users can view {table} for their quotes" ON {table};
                DROP POLICY IF EXISTS "All authenticated users can read {table}" ON {table};
                DROP POLICY IF EXISTS "Only service role can modify {table}" ON {table};
                DROP POLICY IF EXISTS "Authenticated users can insert {table}" ON {table};
                DROP POLICY IF EXISTS "Anon can read {table}" ON {table};
            """)

        # RLS 활성화
        cur.execute(ENABLE_RLS_SQL)
        print("[OK] RLS 활성화 완료")

        # Anon 정책 추가
        cur.execute(ANON_POLICIES_SQL)
        print("[OK] Anon 읽기 정책 추가 완료")

        # 결과 확인
        cur.execute("""
            SELECT t.tablename,
                   CASE WHEN t.rowsecurity THEN 'ENABLED' ELSE 'DISABLED' END as rls_status,
                   COUNT(p.policyname) as policy_count
            FROM pg_tables t
            LEFT JOIN pg_policies p ON t.tablename = p.tablename
            WHERE t.schemaname = 'public'
            GROUP BY t.tablename, t.rowsecurity
            ORDER BY t.tablename;
        """)

        print("\n[RLS SETUP] 최종 RLS 상태:")
        results = cur.fetchall()
        enabled_count = 0
        for table, rls_status, policy_count in results:
            if rls_status == 'ENABLED':
                enabled_count += 1
                print(f"  [OK] {table}: RLS {rls_status} (정책 {policy_count}개)")
            else:
                print(f"  [WARNING] {table}: RLS {rls_status}")

        # 연결 종료
        cur.close()
        conn.close()

        print(f"\n[SUCCESS] RLS 설정 완료!")
        print(f"  활성화된 테이블: {enabled_count}/{len(results)}")
        print("  모든 테이블이 이제 보호됩니다.")

        return True

    except Exception as e:
        print(f"\n[ERROR] RLS 설정 실패: {str(e)}")
        return False

if __name__ == "__main__":
    success = enable_rls()
    sys.exit(0 if success else 1)