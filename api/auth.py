"""
JWT Authentication Module for KIS Estimator API
Provides Supabase JWT token verification
"""

import os
from typing import Dict, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.security_config import JWT_ALGORITHM, JWT_AUDIENCE

# HTTP Bearer security scheme
security = HTTPBearer()

# JWT Configuration from environment
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
JWT_AUD = os.getenv("JWT_AUD", JWT_AUDIENCE)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify JWT token from Supabase

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        Decoded JWT payload with user information

    Raises:
        HTTPException: 500 if JWT secret not configured
        HTTPException: 401 if token is invalid or expired
    """
    if not JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "JWT_NOT_CONFIGURED",
                "message": "JWT secret not configured",
                "hint": "Set SUPABASE_JWT_SECRET environment variable"
            }
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUD
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "Token has expired",
                "hint": "Please login again to get a new token"
            }
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Invalid authentication token",
                "hint": str(e)
            }
        )


def get_current_user(token_payload: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """
    Extract current user information from verified token

    Args:
        token_payload: Decoded JWT payload

    Returns:
        User information dictionary
    """
    return {
        "user_id": token_payload.get("sub"),
        "email": token_payload.get("email"),
        "role": token_payload.get("role", "authenticated")
    }


# Optional: Role-based access control
def require_role(required_role: str):
    """
    Dependency for role-based access control

    Args:
        required_role: Required user role

    Returns:
        Dependency function that checks user role
    """
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{required_role}' required",
                    "hint": f"Your role is '{user.get('role')}'"
                }
            )
        return user

    return role_checker