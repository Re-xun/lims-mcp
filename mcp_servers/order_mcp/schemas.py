"""Pydantic schemas for order_mcp MCP - Auto-generated.

DO NOT EDIT MANUALLY. Run `python -m mcp_servers.generator.generate` to regenerate.
"""
from pydantic import BaseModel, Field
from typing import Optional

class User(BaseModel):
    """User profile information"""
    id: str = Field(
        description="Unique user ID"
    )
    name: str = Field(
        description="User's full name"
    )
    email: Optional[str] = Field(
        default=None,
        description="User's email address"
    )
    department: Optional[str] = Field(
        default=None,
        description="Department name"
    )
    role: Optional[str] = Field(
        default=None,
        description="User role/permission group"
    )

