# Contributing to KIS Estimator Core

## Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please read and follow our Code of Conduct.

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use issue templates when available
3. Provide clear reproduction steps
4. Include system information and error messages

### Development Process

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the coding standards below
   - Write tests for new functionality
   - Update documentation as needed

4. **Run quality checks**
   ```bash
   # Format code
   black src/ tests/

   # Lint
   ruff check src/ tests/

   # Type check
   mypy src/

   # Run tests
   pytest
   ```

5. **Commit your changes**
   ```bash
   git commit -m "feat: add new feature description"
   ```

   Follow conventional commit format:
   - `feat:` New features
   - `fix:` Bug fixes
   - `docs:` Documentation changes
   - `style:` Code style changes
   - `refactor:` Code refactoring
   - `test:` Test additions or changes
   - `chore:` Maintenance tasks

6. **Push and create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Coding Standards

#### Python

- Follow PEP 8
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use descriptive variable names
- Document all public functions and classes

```python
def calculate_placement(
    enclosure: EnclosureSpec,
    breakers: List[BreakerSpec],
    constraints: Optional[PlacementConstraints] = None
) -> PlacementResult:
    """
    Calculate optimal breaker placement within an enclosure.

    Args:
        enclosure: Enclosure specifications
        breakers: List of breakers to place
        constraints: Optional placement constraints

    Returns:
        PlacementResult with positions and validation status
    """
    pass
```

#### Testing

- Write tests for all new features
- Maintain minimum 80% code coverage
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

```python
def test_breaker_placement_with_constraints():
    """Test breaker placement respects thermal constraints"""
    # Arrange
    enclosure = create_test_enclosure()
    breakers = create_test_breakers()
    constraints = ThermalConstraints(max_temp=45)

    # Act
    result = calculate_placement(enclosure, breakers, constraints)

    # Assert
    assert result.is_valid
    assert result.max_temperature <= 45
```

### Pull Request Guidelines

1. **PR Title**: Use conventional commit format
2. **Description**: Clearly describe what and why
3. **Tests**: All tests must pass
4. **Coverage**: Don't decrease code coverage
5. **Documentation**: Update relevant docs
6. **Reviewers**: Request review from maintainers

### Review Process

1. Automated checks must pass
2. At least one maintainer approval required
3. Address all review comments
4. Squash commits before merge

## Project Structure Guidelines

### File Organization

```
src/kis_estimator_core/
├── engine/          # Core business logic
├── infra/           # Infrastructure code
├── api/             # API endpoints
├── models/          # Data models
└── utils/           # Utility functions
```

### Import Order

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
import os
from typing import List, Optional

import numpy as np
from sqlalchemy import create_engine

from kis_estimator_core.engine import BreakerPlacer
from kis_estimator_core.models import EstimateModel
```

## Release Process

1. Version updates follow semantic versioning
2. Update CHANGELOG.md
3. Create release tag
4. Generate release notes
5. Deploy to staging first
6. Production deployment after validation

## Getting Help

- Check documentation first
- Search existing issues
- Ask in discussions
- Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the project's proprietary license.