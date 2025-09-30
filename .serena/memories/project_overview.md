# NABERAL KIS Estimator - Project Overview

## Purpose
NABERAL KIS Estimator is an AI-powered electrical panel estimation system designed to:
- Automate enclosure sizing and breaker placement optimization
- Generate professional estimate documents (Excel/PDF)
- Validate configurations against electrical standards
- Optimize phase balancing and thermal management

## Operating Mode
**Contract-First + Evidence-Gated + SPEC KIT Based**
- All APIs start with OpenAPI 3.1 specification
- Every calculation produces evidence artifacts
- Quality gates enforce strict validation criteria
- Regression test suite (20/20) must pass before merge

## Scope

### In Scope (Estimator Only)
- `/v1/estimate`: Quote generation API
- `/v1/validate`: Validation API
- `/v1/documents`: Document generation API
- `/v1/catalog`: Material catalog API
- FIX-4 Pipeline (5-stage process)
- Evidence pack generation (PDF/XLSX/SVG/JSON)

### Out of Scope
- ERP functions (ordering, inventory, accounting, HR)
- Separate AI system handles ERP operations

## Key Quality Standards
- Contract compliance: ≥99%
- Regression tests: 20/20 PASS (mandatory)
- Evidence coverage: 100%
- API response P95: <200ms
- Health check: <50ms
- Code coverage: ≥80%

## Technology Stack
- **API**: FastAPI (Python) + OpenAPI 3.1
- **Database**: PostgreSQL (schemas: estimator, shared)
- **Cache**: Redis (idempotency, dedup, rate-limit)
- **Queue**: Celery + RabbitMQ
- **Gateway**: FastMCP (MCP tool orchestration)
- **Optimization**: OR-Tools CP-SAT solver
- **Observability**: OpenTelemetry + TraceId
- **Delivery**: Docker + GitHub Actions CI