"""MCP tools for information-security workbench case queries (LIMS IsProjectWorkbenchAction)."""
import os
import sys

import httpx

JAVA_API_BASE = os.environ.get("JAVA_API_BASE", "http://localhost:8080")


async def query_is_workbench_case_list(
    token: str,
    page_no: int = 1,
    page_size: int = 20,
    keyword: str = None,
    project_id: str = None,
    scope: str = "all",
) -> dict:
    """查询信息安全工作台案件列表（分页）。

    对应后端接口:
    GET /IsProjectWorkbenchAction/caseSearch

    keyword 为通用搜索词，后端会按以下字段模糊匹配:
    - 案件号 project_no
    - 客户名称 customer_name_cn
    - 样品/产品名称 product_name
    - 样品/产品型号 product_model
    - 服务项目 service_pro_name
    - 案件负责人/工程师 person_name
    """
    if page_no is None or page_no < 1:
        page_no = 1
    if page_size is None or page_size < 1:
        page_size = 20

    params = {
        "pageNo": str(page_no),
        "pageSize": str(page_size),
        "scope": scope or "all",
    }
    if keyword:
        params["keyword"] = keyword
    if project_id:
        params["projectId"] = project_id

    api_url = f"{JAVA_API_BASE}/IsProjectWorkbenchAction/caseSearch"
    sys.stderr.write(f"\n[API REQUEST] GET {api_url}\n")
    for k, v in params.items():
        sys.stderr.write(f"  {k} = {v}\n")
    sys.stderr.write("\n")
    sys.stderr.flush()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            api_url,
            headers={"x-access-token": token},
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        data["_api_call"] = {
            "method": "GET",
            "url": api_url,
            "params": {k: v for k, v in params.items()},
            "token_masked": token[:8] + "***" if token and len(token) > 8 else "***",
        }
        return data


TOOL_HANDLERS = {
    "query_is_workbench_case_list": query_is_workbench_case_list,
}

TOOL_SCHEMAS = [
    {
        "name": "query_is_workbench_case_list",
        "description": (
            "查询信息安全工作台案件列表（分页）。"
            "支持按通用关键词搜索案件号、客户名称、样品名称、样品型号、服务项目、案件负责人。"
            "返回原始接口响应，业务数据通常位于 response.data.data.resultData。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_no": {
                    "type": "integer",
                    "description": "页码，从 1 开始，默认 1。",
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页条数，默认 20；后端最大通常为 100。",
                },
                "keyword": {
                    "type": "string",
                    "description": (
                        "通用搜索关键词。后端会模糊匹配：案件号、客户名称、样品/产品名称、"
                        "样品/产品型号、服务项目、案件负责人。"
                    ),
                },
                "project_id": {
                    "type": "string",
                    "description": "项目ID/案件ID，可选。",
                },
                "scope": {
                    "type": "string",
                    "description": "查询范围，默认 all；当前前端页面固定传 all。",
                },
            },
        },
    },
]
