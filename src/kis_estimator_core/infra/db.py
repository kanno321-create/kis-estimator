"""
Database connection and session management
Supports both PostgreSQL and SQLite
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig:
    """Database configuration handler"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", "sqlite:///./data/kis_estimator.db"
        )
        self._parse_url()

    def _parse_url(self):
        """Parse database URL to determine type and settings"""
        parsed = urlparse(self.database_url)
        self.db_type = parsed.scheme.split("+")[0]  # Remove driver suffix

        # Determine if PostgreSQL or SQLite
        self.is_postgres = self.db_type in ["postgresql", "postgres"]
        self.is_sqlite = self.db_type == "sqlite"

    def get_engine_kwargs(self) -> dict:
        """Get engine configuration based on database type"""
        if self.is_sqlite:
            return {
                "connect_args": {"check_same_thread": False},
                "poolclass": NullPool,  # No connection pooling for SQLite
            }
        elif self.is_postgres:
            return {
                "poolclass": QueuePool,
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,  # Check connection health
                "pool_recycle": 3600,   # Recycle connections after 1 hour
            }
        else:
            return {}


class Database:
    """Database connection manager"""

    def __init__(self, database_url: Optional[str] = None):
        self.config = DatabaseConfig(database_url)
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._initialize()

    def _initialize(self):
        """Initialize database engine and session factory"""
        engine_kwargs = self.config.get_engine_kwargs()

        # Create engine
        self.engine = create_engine(
            self.config.database_url,
            echo=os.getenv("APP_DEBUG", "false").lower() == "true",
            **engine_kwargs
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def get_session(self) -> Session:
        """Get a new database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.

        Usage:
            with db.session_scope() as session:
                session.add(entity)
                session.commit()
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                # Test with simple query
                if self.config.is_postgres:
                    conn.execute(text("SELECT 1"))
                else:
                    conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False

    def create_tables(self, ddl_path: str = "sql/ddl.sql"):
        """
        Create database tables from DDL script

        Args:
            ddl_path: Path to DDL SQL file
        """
        if not os.path.exists(ddl_path):
            raise FileNotFoundError(f"DDL file not found: {ddl_path}")

        with open(ddl_path, "r") as f:
            ddl_script = f.read()

        # Split into individual statements (simple approach)
        # For production, use a proper SQL parser
        statements = [s.strip() for s in ddl_script.split(";") if s.strip()]

        with self.engine.begin() as conn:
            for statement in statements:
                if statement:
                    # Skip PostgreSQL-specific statements for SQLite
                    if self.config.is_sqlite:
                        # Skip SERIAL (use INTEGER PRIMARY KEY AUTOINCREMENT)
                        statement = statement.replace("SERIAL", "INTEGER")
                        # Skip CASCADE
                        statement = statement.replace("CASCADE", "")
                        # Skip function and trigger creation for SQLite
                        if any(x in statement.upper() for x in ["CREATE FUNCTION", "CREATE TRIGGER", "RETURNS TRIGGER"]):
                            continue

                    try:
                        conn.execute(text(statement))
                    except Exception as e:
                        print(f"Error executing statement: {e}")
                        print(f"Statement: {statement[:100]}...")

    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        tables = ["audit_logs", "estimate_items", "estimates", "products", "customers", "users"]

        with self.engine.begin() as conn:
            for table in tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                except Exception as e:
                    print(f"Error dropping table {table}: {e}")

    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()


# Global database instance (singleton pattern)
_db_instance: Optional[Database] = None


def get_db() -> Database:
    """Get global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def get_session() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session

    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_session)):
            return db.query(Item).all()
    """
    db = get_db()
    with db.session_scope() as session:
        yield session


# Utility functions for common queries
def execute_query(query: str, params: Optional[dict] = None) -> list:
    """Execute a raw SQL query and return results"""
    db = get_db()
    with db.session_scope() as session:
        result = session.execute(text(query), params or {})
        return result.fetchall()


def execute_scalar(query: str, params: Optional[dict] = None):
    """Execute a raw SQL query and return scalar result"""
    db = get_db()
    with db.session_scope() as session:
        result = session.execute(text(query), params or {})
        return result.scalar()


# Health check function
def check_database_health() -> dict:
    """Check database health and return status"""
    db = get_db()

    health = {
        "status": "unknown",
        "database_type": db.config.db_type,
        "database_url": db.config.database_url.split("@")[-1] if "@" in db.config.database_url else "local",
        "connected": False,
        "tables": []
    }

    try:
        # Test connection
        health["connected"] = db.test_connection()

        if health["connected"]:
            # Get table count
            if db.config.is_postgres:
                query = """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """
            else:
                query = """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                """

            tables = execute_query(query)
            health["tables"] = [t[0] for t in tables]
            health["table_count"] = len(health["tables"])
            health["status"] = "healthy" if health["table_count"] > 0 else "empty"
        else:
            health["status"] = "disconnected"

    except Exception as e:
        health["status"] = "error"
        health["error"] = str(e)

    return health