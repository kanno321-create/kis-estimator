# Supabase Setup for KIS Estimator

## 🚀 Quick Start

### 1. Create Supabase Project

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Click "New project"
3. Enter project details:
   - **Name**: kis-estimator
   - **Database Password**: (save this securely)
   - **Region**: Choose closest to your users (Seoul/Tokyo for Korea)

### 2. Run Database Migration

1. Go to SQL Editor in Supabase Dashboard
2. Copy and paste the content from `migrations/001_initial_schema.sql`
3. Click "Run" to create all tables with proper structure

### 3. Load Seed Data

1. In SQL Editor, paste content from `seed.sql`
2. Click "Run" to insert catalog items and sample data

### 4. Get API Keys

Go to Settings → API and copy:
- **URL**: `https://your-project.supabase.co`
- **anon key**: Public client key
- **service_role key**: Server-side key (keep secret!)

### 5. Configure Environment

Copy `.env.supabase` to `.env` and update with your values:

```bash
cp .env.supabase .env
# Edit .env with your Supabase credentials
```

## 📊 Database Schema

### Main Tables
- **customers**: Customer information
- **quotes**: Main estimates with totals
- **quote_items**: Line items in quotes
- **panels**: Electrical panel configurations
- **breakers**: Circuit breaker details
- **documents**: Generated PDFs/Excel files
- **catalog_items**: Product catalog
- **evidence_blobs**: Audit trail with SHA256
- **audit_logs**: All operations log

### Key Features
- All timestamps use `TIMESTAMPTZ` with UTC
- Row Level Security (RLS) enabled
- Automatic `updated_at` triggers
- Views for summary and analysis

## 🔧 Python/FastAPI Integration

### Install Supabase Client
```bash
pip install supabase
```

### Connection Example
```python
from supabase import create_client, Client
import os

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# Example: Fetch catalog items
response = supabase.table('catalog_items').select("*").execute()
catalog = response.data

# Example: Create a quote
quote_data = {
    "customer_id": "550e8400-e29b-41d4-a716-446655440100",
    "status": "pending",
    "totals": {"subtotal": 0, "tax": 0, "total": 0},
    "currency": "KRW"
}
response = supabase.table('quotes').insert(quote_data).execute()
```

### Direct Database Connection
```python
import asyncpg
import os

DATABASE_URL = os.environ.get("SUPABASE_DB_URL")

async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)

# Use for complex queries or transactions
conn = await get_db_connection()
quotes = await conn.fetch("SELECT * FROM quotes WHERE status = $1", "completed")
```

## 🔐 Security

### Row Level Security (RLS)
- Enabled on all tables
- Policies configured for authenticated users
- Public read access for catalog items

### Authentication
Supabase provides built-in authentication:
```python
# Sign up
user = supabase.auth.sign_up({
    "email": "user@example.com",
    "password": "secure-password"
})

# Sign in
user = supabase.auth.sign_in_with_password({
    "email": "user@example.com",
    "password": "secure-password"
})
```

## 📈 Real-time Subscriptions

```python
# Subscribe to quote changes
def handle_changes(payload):
    print("Quote updated:", payload)

supabase.table('quotes').on('UPDATE', handle_changes).subscribe()
```

## 🛠️ Management Commands

### Backup Database
```bash
# From Supabase Dashboard
# Settings → Backups → Download
```

### Reset Database
```sql
-- Run in SQL Editor (CAUTION: Deletes all data)
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

-- Then re-run migration and seed files
```

## 📝 API Endpoints

Supabase automatically creates REST APIs:

- **Base URL**: `https://your-project.supabase.co/rest/v1`
- **Auth Header**: `apikey: your-anon-key`

### Examples
```bash
# Get all catalog items
curl https://your-project.supabase.co/rest/v1/catalog_items \
  -H "apikey: your-anon-key"

# Create a quote
curl -X POST https://your-project.supabase.co/rest/v1/quotes \
  -H "apikey: your-anon-key" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "...", "status": "pending"}'
```

## 🚨 Troubleshooting

### Connection Issues
- Check if project is not paused (free tier pauses after 1 week)
- Verify API keys are correct
- Ensure RLS policies allow your operation

### Performance
- Add indexes for frequently queried columns
- Use connection pooling for production
- Consider caching with Redis for hot data

## 📚 Resources

- [Supabase Docs](https://supabase.com/docs)
- [Supabase Python Client](https://github.com/supabase-community/supabase-py)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)

---

**Note**: Remember to never commit `.env` files with real credentials to version control!