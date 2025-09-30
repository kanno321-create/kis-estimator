"""
KIS Estimator - E2E Supabase Connection Test
Tests real DB connection + Storage upload/download with SHA256 integrity
"""

import pytest
import os
import hashlib
import uuid
from datetime import datetime, timezone


@pytest.fixture
def supabase_config():
    """Supabase configuration from environment"""
    config = {
        "url": os.getenv("SUPABASE_URL"),
        "anon_key": os.getenv("SUPABASE_ANON_KEY"),
        "service_role_key": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "db_url": os.getenv("SUPABASE_DB_URL"),
    }

    # Check if all required variables are set
    missing = [k for k, v in config.items() if not v]
    if missing:
        pytest.skip(f"Missing Supabase credentials: {', '.join(missing)}")

    return config


@pytest.fixture
def supabase_client(supabase_config):
    """Supabase client with service role key"""
    try:
        from supabase import create_client
        return create_client(
            supabase_config["url"],
            supabase_config["service_role_key"]
        )
    except ImportError:
        pytest.skip("supabase-py not installed (pip install supabase)")


@pytest.fixture
def db_connection(supabase_config):
    """Direct database connection for testing"""
    try:
        import psycopg2
        conn = psycopg2.connect(supabase_config["db_url"])
        yield conn
        conn.close()
    except ImportError:
        pytest.skip("psycopg2 not installed (pip install psycopg2-binary)")
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")


def test_db_ping(db_connection):
    """Test database connection with simple SELECT 1"""
    cursor = db_connection.cursor()
    cursor.execute("SELECT 1 as ping")
    result = cursor.fetchone()
    cursor.close()

    assert result is not None
    assert result[0] == 1


def test_db_utc_timestamp(db_connection):
    """Test database UTC timestamp query"""
    cursor = db_connection.cursor()
    cursor.execute("SELECT now() AT TIME ZONE 'utc' as utc_time")
    result = cursor.fetchone()
    cursor.close()

    assert result is not None
    utc_time = result[0]
    assert utc_time is not None

    # Verify it's recent (within last minute)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    time_diff = abs((now - utc_time).total_seconds())
    assert time_diff < 60, f"Time difference too large: {time_diff}s"


def test_storage_upload_download_integrity(supabase_client):
    """Test Storage upload → signed URL → download → SHA256 match"""

    # Generate test data
    test_data = b"KIS Estimator E2E Test - Evidence Pack"
    expected_sha256 = hashlib.sha256(test_data).hexdigest()

    test_id = str(uuid.uuid4())
    test_path = f"evidence/readyz/{test_id}.txt"

    try:
        # Step 1: Upload test file
        upload_response = supabase_client.storage.from_("evidence").upload(
            test_path,
            test_data,
            {"content-type": "text/plain"}
        )

        assert upload_response is not None, "Upload failed"

        # Step 2: Generate signed URL (600s TTL)
        ttl = int(os.getenv("SIGNED_URL_TTL_SEC", "600"))
        signed_url_response = supabase_client.storage.from_("evidence").create_signed_url(
            test_path,
            ttl
        )

        assert "signedURL" in signed_url_response, "Signed URL generation failed"
        signed_url = signed_url_response["signedURL"]
        assert signed_url.startswith("http"), f"Invalid signed URL: {signed_url}"

        # Step 3: Download via signed URL
        import requests
        download_response = requests.get(signed_url, timeout=10)
        assert download_response.status_code == 200, f"Download failed: {download_response.status_code}"

        downloaded_data = download_response.content

        # Step 4: Verify SHA256 integrity
        actual_sha256 = hashlib.sha256(downloaded_data).hexdigest()
        assert actual_sha256 == expected_sha256, (
            f"SHA256 mismatch!\n"
            f"Expected: {expected_sha256}\n"
            f"Actual:   {actual_sha256}"
        )

        # Step 5: Verify content matches
        assert downloaded_data == test_data, "Downloaded content doesn't match original"

    finally:
        # Cleanup: Delete test file
        try:
            supabase_client.storage.from_("evidence").remove([test_path])
        except Exception as e:
            # Non-fatal cleanup error
            print(f"Warning: Failed to cleanup test file: {e}")


def test_evidence_blobs_table_exists(db_connection):
    """Test evidence_blobs table exists and has correct structure"""
    cursor = db_connection.cursor()

    # Check table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'evidence_blobs'
        )
    """)
    table_exists = cursor.fetchone()[0]
    assert table_exists, "evidence_blobs table does not exist"

    # Check required columns
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'evidence_blobs'
    """)
    columns = {row[0]: row[1] for row in cursor.fetchall()}
    cursor.close()

    required_columns = {
        "id": "uuid",
        "quote_id": "uuid",
        "stage": "character varying",
        "sha256": "character varying",
        "created_at": "timestamp with time zone",
    }

    for col, dtype in required_columns.items():
        assert col in columns, f"Missing required column: {col}"
        assert dtype in columns[col], f"Column {col} has wrong type: {columns[col]} (expected {dtype})"


def test_storage_bucket_exists(supabase_client):
    """Test evidence bucket exists and is accessible"""
    try:
        # List buckets
        buckets = supabase_client.storage.list_buckets()
        bucket_ids = [b["id"] for b in buckets]

        assert "evidence" in bucket_ids, "evidence bucket does not exist"

        # Get bucket details
        evidence_bucket = next(b for b in buckets if b["id"] == "evidence")
        assert evidence_bucket["public"] == False, "evidence bucket should be private"

    except Exception as e:
        pytest.fail(f"Failed to check bucket existence: {e}")


def test_db_health_check_function(db_connection):
    """Test health_check_detailed() function exists and works"""
    cursor = db_connection.cursor()

    try:
        cursor.execute("SELECT public.health_check_detailed()")
        result = cursor.fetchall()
        cursor.close()

        assert len(result) > 0, "health_check_detailed() returned no rows"

        # Check expected components
        components = [row[0] for row in result]
        assert "database" in components, "Missing 'database' component"
        assert "tables" in components, "Missing 'tables' component"

    except Exception as e:
        pytest.fail(f"health_check_detailed() function error: {e}")


@pytest.mark.asyncio
async def test_readyz_endpoint_integration():
    """Test /readyz endpoint with real Supabase connection (if API is running)"""
    import httpx

    app_port = int(os.getenv("APP_PORT", "8000"))
    readyz_url = f"http://localhost:{app_port}/readyz"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(readyz_url)

            assert response.status_code == 200, f"/readyz returned {response.status_code}"

            data = response.json()
            assert "status" in data, "Missing 'status' field"
            assert data["status"] == "ok", f"Status not ok: {data['status']}"

            assert "db" in data, "Missing 'db' field"
            assert data["db"] == "ok", f"DB status not ok: {data['db']}"

            assert "storage" in data, "Missing 'storage' field"
            assert data["storage"] == "ok", f"Storage status not ok: {data['storage']}"

            assert "ts" in data, "Missing 'ts' (timestamp) field"
            assert data["ts"].endswith("Z") or "+" in data["ts"], "Timestamp not in UTC format"

    except httpx.ConnectError:
        pytest.skip("API server not running (start with: uvicorn api.main:app)")
    except Exception as e:
        pytest.fail(f"/readyz endpoint test failed: {e}")