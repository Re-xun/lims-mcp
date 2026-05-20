"""Auto-generated tools for order_mcp MCP.

DO NOT EDIT MANUALLY. Run `python -m mcp_servers.generator.generate` to regenerate.
"""
import os
import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")

async def get_order_by_id(    order_id: str,    token: str,
) -> dict:
    """Get order details by ID"""
    url = f"{JAVA_API_BASE}/api/orders/{order_id}"
    params = {        "orderId": order_id,    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"x-access-token": token},
            params=params,
        )
        response.raise_for_status()
        return response.json()

async def search_orders(    status: str,    start_date: str,    end_date: str,    page: int,    token: str,
) -> dict:
    """Search orders with filters"""
    url = f"{JAVA_API_BASE}/api/orders"
    params = {        "status": status,        "startDate": start_date,        "endDate": end_date,        "page": page,    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"x-access-token": token},
            params=params,
        )
        response.raise_for_status()
        return response.json()

async def get_order_statistics(    period: str,    token: str,
) -> dict:
    """Get order statistics overview"""
    url = f"{JAVA_API_BASE}/api/orders/statistics"
    params = {        "period": period,    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"x-access-token": token},
            params=params,
        )
        response.raise_for_status()
        return response.json()


TOOL_HANDLERS = {    "get_order_by_id": get_order_by_id,    "search_orders": search_orders,    "get_order_statistics": get_order_statistics,}

TOOL_SCHEMAS = [    {
        "name": "get_order_by_id",
        "description": "Get order details by ID",
        "inputSchema": {
        "type": "object",
        "properties": {
                "orderId": {
                        "type": "string",
                        "description": "The order ID"
                }
        },
        "required": [
                "orderId"
        ]
},
    },    {
        "name": "search_orders",
        "description": "Search orders with filters",
        "inputSchema": {
        "type": "object",
        "properties": {
                "status": {
                        "type": "string",
                        "description": "Order status filter"
                },
                "startDate": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                },
                "endDate": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                },
                "page": {
                        "type": "integer",
                        "description": "Page number"
                }
        }
},
    },    {
        "name": "get_order_statistics",
        "description": "Get order statistics overview",
        "inputSchema": {
        "type": "object",
        "properties": {
                "period": {
                        "type": "string",
                        "description": "Statistics period"
                }
        }
},
    },]