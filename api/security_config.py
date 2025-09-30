"""
Security Configuration for KIS Estimator API
Centralizes security settings for CORS, Trusted Hosts, and authentication
"""

import os

# CORS Configuration
ALLOWED_ORIGINS = [
    "https://kis-estimator.com",
    "https://app.kis-estimator.com",
]

# Trusted Host Configuration
ALLOWED_HOSTS = [
    "kis-estimator.com",
    "*.kis-estimator.com",
    "localhost",
    "127.0.0.1",
]

# Response Headers to Expose
EXPOSE_HEADERS = ["X-Trace-Id", "X-Evidence-SHA"]

# Development overrides
def get_allowed_origins() -> list[str]:
    """Get allowed origins based on environment"""
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return ALLOWED_ORIGINS
    else:
        return ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000"]

def get_allowed_hosts() -> list[str]:
    """Get allowed hosts based on environment"""
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return ALLOWED_HOSTS
    else:
        return ["localhost", "127.0.0.1", "testserver"]

# Rate Limiting Configuration
RATE_LIMIT_DEFAULT = "100/minute"
RATE_LIMIT_STRICT = "20/minute"  # For sensitive endpoints

# JWT Configuration
JWT_ALGORITHM = "HS256"
JWT_AUDIENCE = "authenticated"