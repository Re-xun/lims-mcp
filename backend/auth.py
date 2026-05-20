"""Authentication module - Login, Token management, Session.

Responsibilities: forward login to Java API, store token, inject into MCP calls.
Does NOT: validate permissions (that's Java's job).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")


@dataclass
class AuthResult:
    success: bool
    token: str | None = None
    username: str | None = None
    error: str | None = None


async def login(username: str, password: str) -> AuthResult:
    """Forward login request to LIMS API (form-urlencoded)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{JAVA_API_BASE}/LoginAction2/login",
                data={"userNo": username, "password": password, "loginType": "1"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 1:
                    token = data.get("token")
                    if not token:
                        return AuthResult(success=False, error="Login response missing token")
                    user_info = data.get("userInfo", {})
                    display_name = user_info.get("userName", username)
                    return AuthResult(success=True, token=token, username=display_name)
                else:
                    return AuthResult(success=False, error=data.get("msg", "登录失败"))
            else:
                return AuthResult(success=False, error=f"Login failed ({resp.status_code})")
    except httpx.RequestError as e:
        return AuthResult(success=False, error=f"Cannot reach Java API: {e}")


async def verify_token(token: str) -> bool:
    """Optional: verify token is still valid via Java API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{JAVA_API_BASE}/api/verify",
                headers={"x-access-token": token},
            )
            return resp.status_code == 200
    except Exception:
        return False
