# Environment Variables Contract

## Supabase Configuration

### Database Connection
**SUPABASE_DB_URL**
- **Purpose**: PostgreSQL connection string with connection pooling
- **Format**: `postgres://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
- **Scope**: Server-side only, never expose to client
- **Required**: Yes
- **Usage**: Database queries, migrations, admin operations

### API Configuration
**SUPABASE_URL**
- **Purpose**: Supabase project API endpoint
- **Format**: `https://[PROJECT_REF].supabase.co`
- **Scope**: Server-side and client-side safe
- **Required**: Yes
- **Usage**: REST API calls, Storage access, Auth operations

**SUPABASE_ANON_KEY**
- **Purpose**: Anonymous public API key for client-side operations
- **Format**: JWT token (long alphanumeric string)
- **Scope**: Client-side safe (public)
- **Required**: Yes
- **Usage**: Client-side API calls, RLS enforced operations
- **Security**: RLS policies protect data, no direct table access

**SUPABASE_SERVICE_ROLE_KEY**
- **Purpose**: Service role key for server-side admin operations
- **Format**: JWT token (long alphanumeric string)
- **Scope**: Server-side only, NEVER expose to client
- **Required**: Yes
- **Usage**: Bypass RLS, admin operations, migrations, server-side writes
- **Security**: Full database access, must be kept secret

## Environment Setup

### Development (.env.local)
```env
SUPABASE_DB_URL=postgres://postgres.xxx:password@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
```

### Production (GitHub Secrets)
Store as repository secrets:
- `SUPABASE_DB_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

### CI/CD (GitHub Actions)
```yaml
env:
  SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
  SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
  SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
  SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

## Security Requirements

### Client-Side
- ✅ SUPABASE_URL: Safe to expose
- ✅ SUPABASE_ANON_KEY: Safe to expose (RLS protected)
- ❌ SUPABASE_DB_URL: NEVER expose
- ❌ SUPABASE_SERVICE_ROLE_KEY: NEVER expose

### Server-Side
- All variables available
- Use SERVICE_ROLE_KEY for admin operations
- Use ANON_KEY for user-context operations

## Validation

All variables must be set before application start:
```python
import os
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    "SUPABASE_DB_URL",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
]

for var in required_vars:
    if not os.getenv(var):
        raise EnvironmentError(f"Missing required environment variable: {var}")
```

## Usage Patterns

### Database Operations (Pooled Connection)
```python
from supabase import create_client

db_url = os.getenv("SUPABASE_DB_URL")
# Use for direct SQL queries with connection pooling
```

### API Operations (Client)
```python
from supabase import create_client

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")  # For client-side
)
```

### Admin Operations (Service Role)
```python
from supabase import create_client

supabase_admin = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Bypass RLS
)
```

## Connection Pooling

Use pooler URL for better performance:
- **Transaction Mode**: Port 6543 (recommended for serverless)
- **Session Mode**: Port 5432 (for persistent connections)

## References
- [Supabase Environment Variables](https://supabase.com/docs/guides/getting-started/environment-variables)
- [Connection Pooling](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)