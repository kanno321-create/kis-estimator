# Project Structure Overview

## Directory Layout

```
kis-estimator-main/
├── .github/              # GitHub Actions CI/CD workflows
├── .serena/             # Serena MCP configuration (auto-generated)
├── .specify/            # Project specifications
├── api/                 # API services and integrations
│   ├── services/       # Business logic services
│   │   ├── document_service.py
│   │   ├── enclosure_service.py
│   │   ├── estimate_service.py
│   │   ├── layout_service.py
│   │   └── rag_service.py
│   ├── integrations/   # External integrations
│   │   ├── mcp_client.py
│   │   └── supabase_client.py
│   └── main.py         # FastAPI application entry
├── db/                  # Database scripts and migrations
├── docs/                # Project documentation
├── mcp/                 # MCP tool definitions
├── out/                 # Build outputs
├── readme/              # Additional readme files
├── seed/                # Database seed data
├── spec_kit/           # Specification and evidence
│   ├── docs/           # Constitutional documents
│   ├── rules/          # Business rules
│   ├── spec/           # Technical specifications
│   └── evidence/       # Generated evidence artifacts
├── sql/                 # SQL schemas and queries
├── src/                 # Source code
│   └── kis_estimator_core/
│       ├── engine/      # Core algorithms (FIX-4 pipeline)
│       │   ├── breaker_placer.py
│       │   ├── breaker_critic.py
│       │   ├── enclosure_solver.py
│       │   ├── estimate_formatter.py
│       │   ├── cover_tab_writer.py
│       │   ├── doc_lint_guard.py
│       │   ├── spatial_assistant.py
│       │   ├── _util_io.py
│       │   └── stubs/       # Fallback implementations
│       └── infra/           # Infrastructure layer
│           └── db.py        # Database management
├── supabase/           # Supabase configuration
├── tests/              # Test suite
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── conftest.py    # Pytest fixtures
├── .env.example        # Environment template
├── .gitignore
├── ARCHITECTURE_ANALYSIS.md
├── CLAUDE.md          # Development guide (this file)
├── CONTRIBUTING.md    # Contribution guidelines
├── package.json       # NPM scripts
├── pytest.ini         # Pytest configuration
├── README.md          # Project overview
└── requirements.txt   # Python dependencies
```

## Key Modules

### Core Engine (`src/kis_estimator_core/engine/`)
The heart of the estimation system implementing the FIX-4 pipeline:

1. **breaker_placer.py**: OR-Tools based optimization for breaker placement
2. **enclosure_solver.py**: Calculates optimal enclosure dimensions
3. **breaker_critic.py**: Validates and critiques placement decisions
4. **estimate_formatter.py**: Generates formatted Excel/PDF documents
5. **cover_tab_writer.py**: Creates document cover pages
6. **doc_lint_guard.py**: Final document quality validation
7. **spatial_assistant.py**: Spatial layout assistance
8. **_util_io.py**: Common I/O utilities

### Stubs (`src/kis_estimator_core/engine/stubs/`)
Fallback implementations for environments without OR-Tools or other dependencies.

### Infrastructure (`src/kis_estimator_core/infra/`)
- **db.py**: Database connection management (PostgreSQL/SQLite)

### API Layer (`api/`)
- **services/**: Business logic services
- **integrations/**: External system integrations (MCP, Supabase)
- **main.py**: FastAPI application

### Tests (`tests/`)
- **unit/**: Fast, isolated unit tests
- **integration/**: Database and API integration tests
- **conftest.py**: Shared test fixtures and configuration

### Specifications (`spec_kit/`)
- **docs/**: Constitutional and architectural documents
- **rules/**: Business rules and constraints
- **spec/**: Technical specifications
- **evidence/**: Generated evidence artifacts

## Important Files

### Configuration
- **.env.example**: Environment variable template
- **pytest.ini**: Test framework configuration
- **package.json**: NPM scripts for development workflow
- **requirements.txt**: Python package dependencies

### Documentation
- **CLAUDE.md**: Primary development guide (you are here)
- **README.md**: Project overview and quick start
- **CONTRIBUTING.md**: Contribution guidelines and code standards
- **ARCHITECTURE_ANALYSIS.md**: Detailed architecture analysis

### Database
- **sql/ddl.sql**: Database schema definitions
- **supabase/config.toml**: Supabase configuration

## Module Dependencies

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Services Layer                 │
│  (document, enclosure, estimate,    │
│   layout, rag services)             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Engine Layer (FIX-4)           │
│  (breaker_placer, enclosure_solver, │
│   critic, formatter, etc.)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    Infrastructure Layer              │
│    (database, cache, file I/O)      │
└─────────────────────────────────────┘
```

## File Naming Conventions

- **Python modules**: `snake_case.py`
- **Test files**: `test_*.py` or `*_test.py`
- **Configuration**: lowercase with `.` separator (e.g., `config.toml`)
- **Documentation**: `UPPERCASE.md` for important docs, `lowercase.md` for others
- **SQL**: `lowercase.sql`

## Import Resolution

The package uses absolute imports from `kis_estimator_core`:

```python
# Correct
from kis_estimator_core.engine import BreakerPlacer
from kis_estimator_core.infra.db import get_database_connection

# Avoid
from ..engine import BreakerPlacer  # Relative imports
```