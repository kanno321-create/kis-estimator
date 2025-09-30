"""
KIS Estimator API Configuration
Environment variable loading with validation and safe defaults
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ConfigError(Exception):
    """Configuration validation error"""
    pass


class Config:
    """Application configuration with environment variable validation"""

    # Supabase configuration
    SUPABASE_DB_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Application configuration
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True
    APP_LOG_LEVEL: str = "INFO"

    # Storage configuration
    STORAGE_BUCKET: str = "evidence"
    SIGNED_URL_TTL: int = 600  # 10 minutes

    # Database configuration
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    def __init__(self):
        """Initialize and validate configuration"""
        self._load_required_env_vars()
        self._load_optional_env_vars()
        self._validate_config()

    def _load_required_env_vars(self) -> None:
        """Load required environment variables"""
        required_vars = {
            "SUPABASE_DB_URL": "Database connection URL",
            "SUPABASE_URL": "Supabase project URL",
            "SUPABASE_ANON_KEY": "Supabase anonymous key",
            "SUPABASE_SERVICE_ROLE_KEY": "Supabase service role key",
        }

        missing_vars = []
        for var_name, description in required_vars.items():
            value = os.getenv(var_name)
            if not value:
                missing_vars.append(f"{var_name} ({description})")
            else:
                setattr(self, var_name, value)

        if missing_vars:
            raise ConfigError(
                "Missing required environment variables:\n"
                + "\n".join(f"  - {var}" for var in missing_vars)
            )

    def _load_optional_env_vars(self) -> None:
        """Load optional environment variables with defaults"""
        self.APP_ENV = os.getenv("APP_ENV", self.APP_ENV)
        self.APP_PORT = int(os.getenv("APP_PORT", str(self.APP_PORT)))
        self.APP_DEBUG = os.getenv("APP_DEBUG", str(self.APP_DEBUG)).lower() in (
            "true",
            "1",
            "yes",
        )
        self.APP_LOG_LEVEL = os.getenv("APP_LOG_LEVEL", self.APP_LOG_LEVEL)

        self.STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", self.STORAGE_BUCKET)
        self.SIGNED_URL_TTL = int(os.getenv("SIGNED_URL_TTL", str(self.SIGNED_URL_TTL)))

        self.DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", str(self.DB_POOL_SIZE)))
        self.DB_MAX_OVERFLOW = int(
            os.getenv("DB_MAX_OVERFLOW", str(self.DB_MAX_OVERFLOW))
        )
        self.DB_POOL_TIMEOUT = int(
            os.getenv("DB_POOL_TIMEOUT", str(self.DB_POOL_TIMEOUT))
        )
        self.DB_ECHO = os.getenv("DB_ECHO", str(self.DB_ECHO)).lower() in (
            "true",
            "1",
            "yes",
        )

    def _validate_config(self) -> None:
        """Validate configuration values"""
        # Validate URLs
        if not self.SUPABASE_URL.startswith(("http://", "https://")):
            raise ConfigError(
                "Invalid SUPABASE_URL: must start with http:// or https://"
            )

        if not self.SUPABASE_DB_URL.startswith("postgres"):
            raise ConfigError(
                "Invalid SUPABASE_DB_URL: must start with postgres:// or postgresql://"
            )

        # Validate pool sizes
        if self.DB_POOL_SIZE < 1:
            raise ConfigError("DB_POOL_SIZE must be at least 1")

        if self.DB_MAX_OVERFLOW < 0:
            raise ConfigError("DB_MAX_OVERFLOW must be non-negative")

        if self.SIGNED_URL_TTL < 60:
            raise ConfigError("SIGNED_URL_TTL must be at least 60 seconds")

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.APP_ENV.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.APP_ENV.lower() == "development"


# Global configuration instance
try:
    config = Config()
except ConfigError as e:
    print(f"Configuration Error: {e}")
    print("\nPlease ensure all required environment variables are set.")
    print("See .specify/contracts/env.md for details.")
    raise