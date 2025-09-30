"""
Pytest configuration and fixtures
"""

import os
import sys
from pathlib import Path
from typing import Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kis_estimator_core.infra.db import Database


@pytest.fixture(scope="session")
def test_db_url():
    """Test database URL"""
    return os.getenv("TEST_DATABASE_URL", "sqlite:///./test_data/test.db")


@pytest.fixture(scope="session")
def test_database(test_db_url):
    """Create test database instance for entire test session"""
    # Create test data directory
    test_data_dir = Path("./test_data")
    test_data_dir.mkdir(exist_ok=True)

    # Initialize database
    db = Database(test_db_url)

    # Create tables
    try:
        db.create_tables()
    except Exception as e:
        print(f"Error creating test tables: {e}")

    yield db

    # Cleanup
    db.close()


@pytest.fixture
def db_session(test_database) -> Generator[Session, None, None]:
    """Create a test database session for each test"""
    with test_database.session_scope() as session:
        yield session
        # Rollback after each test to ensure isolation
        session.rollback()


@pytest.fixture
def sample_enclosure_data():
    """Sample enclosure data for testing"""
    return {
        "width": 800,
        "height": 2000,
        "depth": 600,
        "ip_rating": "IP44",
        "material": "steel",
        "door_type": "single",
        "mounting": "floor"
    }


@pytest.fixture
def sample_breaker_data():
    """Sample breaker data for testing"""
    return [
        {
            "id": "MCCB-001",
            "type": "MCCB",
            "rating": 100,
            "width": 150,
            "height": 200,
            "depth": 100,
            "phase": 3
        },
        {
            "id": "MCB-001",
            "type": "MCB",
            "rating": 20,
            "width": 18,
            "height": 90,
            "depth": 75,
            "phase": 1
        }
    ]


@pytest.fixture
def sample_estimate_data():
    """Sample estimate data for testing"""
    return {
        "estimate_no": "EST-2024-001",
        "customer_id": 1,
        "project_name": "Test Factory Panel",
        "description": "Main distribution panel for factory",
        "items": [
            {
                "description": "Enclosure 800x2000x600",
                "quantity": 1,
                "unit_price": 500000
            },
            {
                "description": "MCCB 100A",
                "quantity": 3,
                "unit_price": 150000
            },
            {
                "description": "MCB 20A",
                "quantity": 12,
                "unit_price": 25000
            }
        ]
    }


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset database singleton before each test"""
    import kis_estimator_core.infra.db as db_module
    db_module._db_instance = None
    yield
    db_module._db_instance = None


# Test markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (database, file I/O)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full workflow)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )
    config.addinivalue_line(
        "markers", "regression: Regression tests"
    )
    config.addinivalue_line(
        "markers", "critical: Critical path tests that must pass"
    )