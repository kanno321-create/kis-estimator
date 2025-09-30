"""Test Supabase Connection with Proper URL Parsing"""
import os

# Parse the problematic DB URL
# Original: postgresql://postgres:@dnjsdl2572@db.cgqukhmqnndwdbmkmjrn.supabase.co:5432/postgres
# The password is: @dnjsdl2572 (starts with @)
# This needs URL encoding because @ is a special character

def parse_db_url(raw_url):
    """Parse database URL with special character handling"""

    # The URL format is: postgresql://username:password@host:port/database
    # Our password starts with @ which causes parsing issues

    if raw_url.count('@') > 2:
        # Multiple @ signs indicate password contains @
        # Split carefully
        parts = raw_url.split('://')
        protocol = parts[0]  # postgresql

        # Rest: postgres:@dnjsdl2572@db.cgqukhmqnndwdbmkmjrn.supabase.co:5432/postgres
        rest = parts[1]

        # Find the last @ which separates credentials from host
        last_at_index = rest.rfind('@')
        credentials = rest[:last_at_index]  # postgres:@dnjsdl2572
        host_and_db = rest[last_at_index+1:]  # db.cgqukhmqnndwdbmkmjrn.supabase.co:5432/postgres

        # Split credentials
        if ':' in credentials:
            username, password = credentials.split(':', 1)
        else:
            username = credentials
            password = ''

        print(f"Protocol: {protocol}")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Host/DB: {host_and_db}")

        # URL encode the password (@ needs to be encoded as %40)
        import urllib.parse
        encoded_password = urllib.parse.quote(password, safe='')

        # Reconstruct URL with encoded password
        clean_url = f"{protocol}://{username}:{encoded_password}@{host_and_db}"
        return clean_url

    return raw_url

def test_connection():
    """Test the parsed connection"""
    raw_url = "postgresql://postgres:@dnjsdl2572@db.cgqukhmqnndwdbmkmjrn.supabase.co:5432/postgres"

    print("Original URL (with password issue):")
    print(f"  {raw_url}")
    print()

    clean_url = parse_db_url(raw_url)

    print("\nCleaned URL (password encoded):")
    print(f"  {clean_url}")
    print()

    # Test with psycopg2 (synchronous) for simpler testing
    try:
        import psycopg2
        print("Testing connection with psycopg2...")

        # Use the cleaned URL
        conn = psycopg2.connect(clean_url)
        cursor = conn.cursor()

        # Simple query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"[OK] Connected to PostgreSQL!")
        print(f"     Version: {version[0]}")

        # Test canary
        cursor.execute("""
            BEGIN;
            CREATE TEMPORARY TABLE IF NOT EXISTS canary (
                id UUID DEFAULT gen_random_uuid(),
                ts TIMESTAMPTZ DEFAULT now()
            );
            INSERT INTO canary DEFAULT VALUES;
            SELECT COUNT(*) FROM canary;
        """)

        count = cursor.fetchone()
        print(f"     Canary test: {count[0]} rows")

        cursor.execute("ROLLBACK")
        cursor.close()
        conn.close()

        return True

    except ImportError:
        print("[ERROR] psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False

    except Exception as e:
        print(f"[ERROR] Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)