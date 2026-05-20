"""Auto-generated tools for user_mcp MCP.

DO NOT EDIT MANUALLY. Run `python -m mcp_servers.generator.generate` to regenerate.
"""
import os
import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

async def get_user_by_id(    user_id: str,    token: str,
) -> dict:
    """Get user details by ID。返回: 单个User对象"""
    url = f"{JAVA_API_BASE}/api/users/{user_id}"
    params = {        "userId": user_id,    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"x-access-token": token},
            params=params,
        )
        response.raise_for_status()
        return response.json()

async def search_users(    keyword: str,    department: str,    page: int,    token: str,
) -> dict:
    """Search users by keyword。返回: 分页结果，包含 total(总数) 和 items(User列表)"""
    url = f"{JAVA_API_BASE}/api/users"
    params = {        "keyword": keyword,        "department": department,        "page": page,    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"x-access-token": token},
            params=params,
        )
        response.raise_for_status()
        return response.json()

async def list_departments(    token: str,
) -> dict:
    """List all departments"""
    url = f"{JAVA_API_BASE}/api/departments"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"x-access-token": token},
        )
        response.raise_for_status()
        return response.json()


TOOL_HANDLERS = {    "get_user_by_id": get_user_by_id,    "search_users": search_users,    "list_departments": list_departments,}

TOOL_SCHEMAS = [    {
        "name": "get_user_by_id",
        "description": "Get user details by ID。返回: 单个User对象",
        "inputSchema": {
        "type": "object",
        "properties": {
                "userId": {
                        "type": "string",
                        "description": "The user ID"
                }
        },
        "required": [
                "userId"
        ]
},
    },    {
        "name": "search_users",
        "description": "Search users by keyword。返回: 分页结果，包含 total(总数) 和 items(User列表)",
        "inputSchema": {
        "type": "object",
        "properties": {
                "keyword": {
                        "type": "string",
                        "description": "Search keyword for name/department/role"
                },
                "department": {
                        "type": "string",
                        "description": "Filter by department name"
                },
                "page": {
                        "type": "integer",
                        "description": "Page number (1-based)"
                }
        }
},
    },    {
        "name": "list_departments",
        "description": "List all departments",
        "inputSchema": {
        "type": "object",
        "properties": {}
},
    },]