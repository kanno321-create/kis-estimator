#!/usr/bin/env python3
"""
Supabase Database Deployment Script
Connects directly to PostgreSQL and deploys schema, policies, and functions
"""
import os
import sys
import psycopg2
from psycopg2 import sql, errors
from datetime import datetime, timezone

# Database connection - direct connection, not pooler
DB_HOST = "aws-0-ap-northeast-2.pooler.supabase.com"
DB_PORT = "5432"  # Direct connection port
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "@dnjsdl2572"
DB_PROJECT_ID = "cgqukhmqnndwdbmkmjrn"

# Build connection string
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db.{DB_PROJECT_ID}.supabase.co:5432/{DB_NAME}"

def log(msg: str):
    """Log with timestamp"""
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{timestamp}] {msg}")

def execute_sql_file(conn, filepath: str):
    """Execute SQL file and return success status"""
    log(f"Executing {filepath}...")

    try:
        with open(filepath, 'r') as f:
            sql_content = f.read()

        with conn.cursor() as cur:
            cur.execute(sql_content)

        conn.commit()
        log(f"✅ {filepath} executed successfully")
        return True

    except errors.UniqueViolation as e:
        log(f"⚠️  Some objects already exist in {filepath} (safe to ignore): {e}")
        conn.rollback()
        return True

    except Exception as e:
        log(f"❌ Error executing {filepath}: {e}")
        conn.rollback()
        return False

def verify_deployment(conn):
    """Verify database deployment"""
    log("Verifying deployment...")

    checks = []

    with conn.cursor() as cur:
        # Check schemas exist
        cur.execute("""
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name IN ('estimator', 'shared')
            ORDER BY schema_name
        """)
        schemas = [row[0] for row in cur.fetchall()]
        checks.append(("Schemas", len(schemas) == 2, f"Found: {schemas}"))

        # Check tables exist
        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('estimator', 'shared')
            ORDER BY table_schema, table_name
        """)
        tables = cur.fetchall()
        checks.append(("Tables", len(tables) >= 6, f"Found {len(tables)} tables"))

        # Check functions exist
        cur.execute("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
            AND routine_name IN (
                'update_updated_at',
                'check_sha256',
                'validate_evidence_integrity',
                'calculate_quote_totals',
                'get_phase_balance',
                'health_check_detailed'
            )
        """)
        functions = [row[0] for row in cur.fetchall()]
        checks.append(("Functions", len(functions) >= 5, f"Found {len(functions)} functions"))

        # Check RLS enabled
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'estimator'
            AND rowsecurity = true
        """)
        rls_tables = [row[0] for row in cur.fetchall()]
        checks.append(("RLS Enabled", len(rls_tables) >= 5, f"Found {len(rls_tables)} tables with RLS"))

    # Print results
    log("\n" + "="*60)
    log("DEPLOYMENT VERIFICATION RESULTS")
    log("="*60)

    all_passed = True
    for check_name, passed, details in checks:
        status = "✅" if passed else "❌"
        log(f"{status} {check_name}: {details}")
        if not passed:
            all_passed = False

    log("="*60)

    if all_passed:
        log("✅ All verification checks PASSED")
        return True
    else:
        log("❌ Some verification checks FAILED")
        return False

def main():
    """Main deployment function"""
    log("="*60)
    log("KIS Estimator Database Deployment")
    log("="*60)
    log(f"Target: db.{DB_PROJECT_ID}.supabase.co:5432")

    # Connect to database
    try:
        log("Connecting to database...")
        conn = psycopg2.connect(DB_URL)
        log("✅ Connected successfully")
    except Exception as e:
        log(f"❌ Connection failed: {e}")
        return 1

    try:
        # Deploy schema
        if not execute_sql_file(conn, "/workspace/db/schema.sql"):
            log("❌ Schema deployment failed")
            return 1

        # Deploy functions
        if not execute_sql_file(conn, "/workspace/db/functions.sql"):
            log("❌ Functions deployment failed")
            return 1

        # Deploy policies
        if not execute_sql_file(conn, "/workspace/db/policies.sql"):
            log("⚠️  Policies deployment had warnings (check if already exist)")

        # Verify deployment
        if not verify_deployment(conn):
            log("❌ Deployment verification failed")
            return 1

        log("\n" + "="*60)
        log("✅ DATABASE DEPLOYMENT COMPLETED SUCCESSFULLY")
        log("="*60)
        return 0

    except Exception as e:
        log(f"❌ Deployment failed: {e}")
        return 1

    finally:
        conn.close()
        log("Database connection closed")

if __name__ == "__main__":
    sys.exit(main())
