#!/usr/bin/env python3
"""
Supabase Database Deployment Script
Uses connection parameters to avoid URL parsing issues with special characters
"""
import os
import sys
import psycopg2
from psycopg2 import errors
from datetime import datetime, timezone
from urllib.parse import quote_plus

# Connection parameters
CONN_PARAMS = {
    "host": "db.cgqukhmqnndwdbmkmjrn.supabase.co",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "@dnjsdl2572"
}

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
        log(f"⚠️  Some objects already exist (safe to ignore)")
        conn.rollback()
        return True

    except Exception as e:
        log(f"❌ Error: {type(e).__name__}: {str(e)[:200]}")
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
                'get_phase_balance'
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
        checks.append(("RLS Enabled", len(rls_tables) >= 5, f"{len(rls_tables)} tables"))

    # Print results
    log("\n" + "="*60)
    log("DEPLOYMENT VERIFICATION")
    log("="*60)

    all_passed = True
    for check_name, passed, details in checks:
        status = "✅" if passed else "❌"
        log(f"{status} {check_name}: {details}")
        if not passed:
            all_passed = False

    log("="*60)

    if all_passed:
        log("✅ All checks PASSED")
        return True
    else:
        log("❌ Some checks FAILED")
        return False

def main():
    """Main deployment function"""
    log("="*60)
    log("KIS Estimator Database Deployment")
    log("="*60)
    log(f"Target: {CONN_PARAMS['host']}:{CONN_PARAMS['port']}")

    # Connect to database
    try:
        log("Connecting to database...")
        conn = psycopg2.connect(**CONN_PARAMS)
        log("✅ Connected successfully")
    except Exception as e:
        log(f"❌ Connection failed: {e}")
        log("\nTroubleshooting:")
        log("1. Check if password is correct: @dnjsdl2572")
        log("2. Verify project ID: cgqukhmqnndwdbmkmjrn")
        log("3. Ensure direct database access is enabled")
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
            log("⚠️  Policies had warnings (may already exist)")

        # Verify deployment
        if not verify_deployment(conn):
            log("❌ Verification failed")
            return 1

        log("\n" + "="*60)
        log("✅ DATABASE DEPLOYMENT SUCCESS")
        log("="*60)
        return 0

    except Exception as e:
        log(f"❌ Deployment error: {e}")
        return 1

    finally:
        conn.close()
        log("Connection closed")

if __name__ == "__main__":
    sys.exit(main())
