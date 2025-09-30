"""Test Supabase DB Connection"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_db_connection():
    """Test database connection with canary query"""

    # Database URL from environment or hardcoded for test
    # Note: The password contains @ which needs special handling
    import urllib.parse
    password = urllib.parse.quote("@dnjsdl2572", safe="")
    db_url = f"postgresql://postgres:{password}@db.cgqukhmqnndwdbmkmjrn.supabase.co:5432/postgres"

    # Convert to async URL
    if db_url.startswith("postgresql://"):
        async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        async_db_url = db_url

    print(f"Testing connection to: {db_url.split('@')[1] if '@' in db_url else db_url}")

    try:
        # Create engine
        engine = create_async_engine(
            async_db_url,
            echo=False,
            pool_size=1,
            max_overflow=0
        )

        # Test connection
        async with engine.begin() as conn:
            # Create temporary table
            await conn.execute(text("""
                CREATE TEMPORARY TABLE IF NOT EXISTS canary (
                    id UUID DEFAULT gen_random_uuid(),
                    ts TIMESTAMPTZ DEFAULT now()
                )
            """))

            # Insert test data
            await conn.execute(text("INSERT INTO canary DEFAULT VALUES"))

            # Query count
            result = await conn.execute(text("SELECT COUNT(*) as count FROM canary"))
            row = result.fetchone()

            print(f"[OK] Database connection successful!")
            print(f"   Canary rows: {row.count}")

            # Transaction will rollback automatically

    except Exception as e:
        print(f"[ERROR] Database connection failed!")
        print(f"   Error: {str(e)}")
        return False

    finally:
        await engine.dispose()

    return True

if __name__ == "__main__":
    success = asyncio.run(test_db_connection())
    exit(0 if success else 1)