# Code Style and Conventions

## Python Code Style

### General Guidelines
- **PEP 8 Compliance**: Follow PEP 8 style guide
- **Line Length**: Maximum 100 characters
- **Type Hints**: Required for all function signatures
- **Docstrings**: Required for all public functions and classes
- **Import Order**: stdlib → third-party → local

### Type Hints
```python
from typing import List, Optional, Dict

def calculate_placement(
    enclosure: EnclosureSpec,
    breakers: List[BreakerSpec],
    constraints: Optional[PlacementConstraints] = None
) -> PlacementResult:
    """Calculate optimal breaker placement within an enclosure."""
    pass
```

### Docstring Format (Google Style)
```python
def solve_enclosure(breakers: List[BreakerSpec], ip_rating: int = 44) -> EnclosureResult:
    """
    Calculate optimal enclosure dimensions for given breakers.

    Args:
        breakers: List of breaker specifications to accommodate
        ip_rating: Minimum IP protection rating (default: 44)

    Returns:
        EnclosureResult containing dimensions and fit score

    Raises:
        ValidationError: If breaker specifications are invalid
        SolverError: If no valid solution found
    """
    pass
```

### Naming Conventions
- **Functions/Methods**: `snake_case` (e.g., `calculate_phase_balance`)
- **Classes**: `PascalCase` (e.g., `BreakerPlacer`, `EnclosureSolver`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_BREAKERS`, `DEFAULT_IP_RATING`)
- **Private Members**: `_leading_underscore` (e.g., `_internal_method`)

### Import Organization
```python
# Standard library
import os
from typing import List, Optional

# Third-party
import numpy as np
from sqlalchemy import create_engine
from ortools.sat.python import cp_model

# Local application
from kis_estimator_core.engine import BreakerPlacer
from kis_estimator_core.models import EstimateModel
```

## Testing Conventions

### Test Structure (AAA Pattern)
```python
def test_breaker_placement_with_thermal_constraints():
    """Test breaker placement respects thermal constraints."""
    # Arrange
    enclosure = create_test_enclosure()
    breakers = create_test_breakers(count=10)
    constraints = ThermalConstraints(max_temp=45)

    # Act
    result = calculate_placement(enclosure, breakers, constraints)

    # Assert
    assert result.is_valid
    assert result.max_temperature <= 45
    assert len(result.violations) == 0
```

### Test Naming
- Format: `test_<function_name>_<scenario>`
- Examples:
  - `test_phase_balance_with_three_phases`
  - `test_enclosure_solving_with_invalid_breakers`
  - `test_placement_fails_with_insufficient_space`

### Test Markers
Use pytest markers for categorization:
```python
@pytest.mark.unit
def test_unit_calculation():
    pass

@pytest.mark.integration
def test_database_integration():
    pass

@pytest.mark.regression
def test_golden_case_1():
    pass
```

## File Organization

### Directory Structure
```
src/kis_estimator_core/
├── engine/          # Core business logic
├── infra/           # Infrastructure (DB, cache)
├── api/             # API endpoints
├── models/          # Data models
└── utils/           # Utility functions
```

### Module Structure
```python
"""Module docstring describing purpose."""

# Imports (organized as shown above)

# Constants
MAX_BREAKERS = 100
DEFAULT_TIMEOUT = 30

# Type aliases
BreakerList = List[BreakerSpec]

# Classes
class MyClass:
    pass

# Functions
def my_function():
    pass

# Main guard
if __name__ == "__main__":
    main()
```

## Commit Message Format

### Conventional Commits
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

### Examples
```
feat: add phase balancing optimization
fix: correct thermal calculation in breaker placement
docs: update API documentation for estimate endpoint
test: add regression tests for golden cases
```

## Error Handling

### Error Schema
All errors must follow this structure:
```python
{
    "code": "VALIDATION_ERROR",
    "message": "Phase imbalance exceeds threshold",
    "hint": "Consider redistributing breakers across phases",
    "traceId": "uuid-trace-id",
    "meta": {
        "dedupKey": "hash-of-error"
    }
}
```

## Database Conventions

### Timestamp Requirements
- **ALWAYS use TIMESTAMPTZ**: Never use TIMESTAMP without time zone
- **Default to UTC**: All timestamps stored in UTC
- **Required fields**: created_at, updated_at on all tables

```sql
CREATE TABLE quotes (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now() AT TIME ZONE 'utc',
    updated_at TIMESTAMPTZ DEFAULT now() AT TIME ZONE 'utc'
);
```