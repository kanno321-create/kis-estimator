"""
Admin Guard Module
Role-based access control for administrative endpoints
Requires admin or service_role JWT claims
"""

from typing import Dict, Any
from fastapi import Depends, HTTPException, status

from api.auth import get_current_user


def ensure_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency to ensure user has admin or service_role privileges.

    Args:
        user: Decoded JWT user information

    Returns:
        User information if authorized

    Raises:
        HTTPException: 403 if user lacks admin/service_role
    """
    role = user.get("role", "")

    # Allow admin and service_role (Supabase service role key tokens)
    allowed_roles = ["admin", "service_role"]

    if role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INSUFFICIENT_PERMISSIONS",
                "message": "Administrative privileges required",
                "hint": f"Your role '{role}' does not have access to this resource"
            }
        )

    return user