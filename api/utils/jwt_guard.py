"""
JWT/JWKS Verification Utility for Supabase Authentication
Implements RS256 token verification with JWKS caching.
"""
import os
import time
import json
import httpx
import base64
from typing import Dict, Any
from jose import jwt

_JWKS_CACHE: Dict[str, Any] = {"ts": 0, "keys": None}

def _jwks_url() -> str:
    """Get JWKS URL from environment"""
    url = os.environ.get("SUPABASE_JWKS_URL") or (
        os.environ.get("SUPABASE_URL", "").rstrip("/") + "/auth/v1/jwks"
    )
    if not url.startswith("http"):
        raise RuntimeError("SUPABASE_JWKS_URL not set")
    return url

async def get_jwks(refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch JWKS from Supabase with 1-hour caching.

    Args:
        refresh: Force refresh cache

    Returns:
        JWKS data with public keys
    """
    now = time.time()
    if (not refresh) and _JWKS_CACHE["keys"] and now - _JWKS_CACHE["ts"] < 3600:
        return _JWKS_CACHE["keys"]

    async with httpx.AsyncClient(timeout=5.0) as cx:
        r = await cx.get(_jwks_url())
        r.raise_for_status()
        data = r.json()
        _JWKS_CACHE.update({"ts": now, "keys": data})
        return data

async def verify_jwt(token: str) -> Dict[str, Any]:
    """
    Verify Supabase JWT token using JWKS.

    Args:
        token: JWT token string

    Returns:
        Decoded token claims

    Raises:
        ValueError: Invalid token format or verification failed
    """
    if not token or token.count(".") != 2:
        raise ValueError("invalid token")

    # Extract kid from header
    header = json.loads(base64.urlsafe_b64decode(token.split(".")[0] + "=="))
    kid = header.get("kid")

    # Get JWKS
    keys = await get_jwks()

    # Find matching key by kid, or try all keys
    candidates = [k for k in keys.get("keys", []) if k.get("kid") == kid] or keys.get("keys", [])

    last_exc = None
    for k in candidates:
        try:
            return jwt.decode(
                token,
                k,
                algorithms=[k.get("alg", "RS256")],
                options={"verify_aud": False}
            )
        except Exception as e:
            last_exc = e

    raise last_exc or ValueError("jwt verify failed")