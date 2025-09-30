#!/usr/bin/env python3
"""
데이터베이스 트랜잭션 테스트
psql 명령어와 동일한 작업을 Python으로 수행
"""
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import uuid

# 환경 변수 로드
load_dotenv('.env.local')

def test_transaction():
    """트랜잭션 테스트: CREATE TEMPORARY TABLE -> INSERT -> SELECT -> ROLLBACK"""

    db_url = os.getenv('SUPABASE_DB_URL')
    if not db_url:
        print("[ERROR] SUPABASE_DB_URL not found in environment")
        return False

    print(f"[INFO] Connecting to database...")
    print(f"[INFO] URL: {db_url[:50]}...")

    try:
        # 데이터베이스 연결
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        print("[INFO] Starting transaction...")

        # 트랜잭션 시작
        cur.execute("BEGIN;")
        print("[OK] Transaction started")

        # 임시 테이블 생성
        cur.execute("""
            CREATE TEMPORARY TABLE IF NOT EXISTS canary(
                id uuid DEFAULT gen_random_uuid()
            );
        """)
        print("[OK] Temporary table 'canary' created")

        # 데이터 삽입
        cur.execute("INSERT INTO canary DEFAULT VALUES;")
        print("[OK] Inserted default values into canary")

        # 카운트 확인
        cur.execute("SELECT COUNT(*) FROM canary;")
        count = cur.fetchone()[0]
        print(f"[OK] Count from canary table: {count}")

        # 롤백
        cur.execute("ROLLBACK;")
        print("[OK] Transaction rolled back")

        # 연결 종료
        cur.close()
        conn.close()

        print("\n[SUCCESS] Database transaction test completed!")
        print(f"  - Connected to Supabase")
        print(f"  - Created temporary table")
        print(f"  - Inserted {count} row(s)")
        print(f"  - Rolled back successfully")

        return True

    except Exception as e:
        print(f"\n[ERROR] Transaction test failed: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    success = test_transaction()
    sys.exit(0 if success else 1)