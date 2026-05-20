# AI 对话系统 — 设计文档

**日期**：2026-05-15
**阶段**：POC 原型（先只做查询）

---

## 1. 需求概要

- AI 对话系统，Web Chat 界面，支持登录
- 50+ Java REST API 跨多业务系统，不动 Java 项目
- 将 Java API 封装为 MCP Server，供 AI 根据对话意图调用
- 认证：Token 认证（AES 加密，存 Redis），Header `x-access-token`
- 登录/Token 签发也在 Java 项目中
- API 文档：OpenAPI 3.0 规范
- LLM：云端大模型 API
- Python 项目，使用 LangChain

## 2. 整体架构

```
┌──────────────────────────────────────────────────────┐
│                 前端 Chat UI (Streamlit)              │
└──────────────────────┬───────────────────────────────┘
                       │ WebSocket / SSE
┌──────────────────────▼───────────────────────────────┐
│              Python 后端 (FastAPI + LangChain)         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │  登录/鉴权   │  │  LangChain   │  │  会话管理    │  │
│  │  模块       │  │  Agent       │  │  (Token存储) │  │
│  └─────────────┘  └──────┬───────┘  └─────────────┘  │
│  ┌───────────────────────▼──────────────────────────┐ │
│  │            领域路由器 (Domain Router)              │ │
│  │    关键词 + 意图 → 命中 1~N 个 MCP                │ │
│  └────┬──────────┬──────────┬───────────────────────┘ │
└───────┼──────────┼──────────┼─────────────────────────┘
        │          │          │    MCP Protocol
   ┌────▼──┐  ┌───▼───┐  ┌──▼──────┐
   │ 用户   │  │ 订单  │  │  报表   │   ← 每个 MCP 独立进程
   │ MCP   │  │ MCP   │  │  MCP    │      OpenAPI → Tool 自动生成
   └───┬───┘  └───┬───┘  └───┬─────┘
       └──────────┴──────────┘
                  │  HTTP + x-access-token Header
       ┌──────────▼──────────┐
       │    Java 业务系统     │  ← 不改动
       │  (50+ REST API)     │
       └─────────────────────┘
```

分层职责：

| 层 | 职责 | 不负责 |
|----|------|--------|
| Streamlit | Chat UI，登录表单，消息展示 | 不做权限判断 |
| FastAPI 后端 | 会话管理，Token 存取，Agent 编排 | 不校验业务权限 |
| 领域路由器 | 根据用户意图选择目标 MCP | 不做语义推理（POC 阶段） |
| MCP Server | 将 Java API 暴露为 MCP Tool，转发请求 | 不修改请求/响应内容 |
| Java 系统 | 业务逻辑，权限校验 | 不动 |

## 3. MCP 生成策略

### 3.1 核心思路

不手写 MCP 代码，写一个生成器：读取 OpenAPI 3.0 JSON → 按业务域 tag 分组 → 生成对应的 MCP Server Python 包。

```
OpenAPI 3.0 JSON
      │
      ▼
┌─────────────────┐
│  MCP 生成器      │  读取 paths/parameters/schemas
│  (Python 脚本)   │  → 自动生成 tool 定义
└───────┬─────────┘
        │ 按业务域 tag 分组
        ▼
┌───────────────┐
│  生成产物      │
│  user_mcp/    │  server.py    MCP Server 入口
│               │  tools.py     自动生成的 tool 函数
│               │  schemas.py   Pydantic 请求/响应模型
│  order_mcp/   │
│  ...          │
└───────────────┘
```

### 3.2 映射规则

一个 Java API 端点 = 一个 MCP Tool。不合并、不拆分。

| OpenAPI 字段 | MCP Tool 字段 | 说明 |
|-------------|--------------|------|
| `operationId` | tool `name` | `getUserById` → `get_user_by_id` |
| `summary` / `description` | tool `description` | 直接映射，帮助 LLM 理解工具用途 |
| `parameters`（query/path） | `inputSchema` | 自动生成 JSON Schema |
| `responses.200.schema` | 返回描述 | 嵌入 tool description，告诉 LLM 返回值结构 |
| `tags[0]` | 分组依据 | `用户管理` → user_mcp |

### 3.3 生成器实现要点

- 解析 OpenAPI JSON 使用 `openapi-spec-validator` 或 `prance`
- 用 Jinja2 模板生成 `tools.py`、`schemas.py`、`server.py`
- 生成的 tool 函数内部：构造 HTTP 请求 → 注入 `x-access-token` → 调 Java API → 返回 JSON
- Token 不在 tool 参数中暴露，通过环境变量或上下文注入

## 4. LangChain Agent + 领域路由器

### 4.1 Agent 流程

```
用户消息
    │
    ▼
┌─────────────────────┐
│  领域路由器           │  POC: 关键词 + 意图匹配
│  (Domain Router)     │  后期: 升级为 RAG 语义路由
└────────┬────────────┘
         │ 返回目标 MCP 列表
         ▼
┌─────────────────────┐
│  MCP Client         │  连接目标 MCP → 拉取 tool list
│  自动发现工具         │
└────────┬────────────┘
         │ 注入 tool schema 到 LLM
         ▼
┌─────────────────────┐
│  LangChain Agent     │  Agent 类型: tool_calling
│  + Memory            │  LLM 决定调用哪个 tool
│  + System Prompt     │  组装结果 → 自然语言回复
└────────┬────────────┘
         │ SSE 流式返回
         ▼
      前端 Chat UI
```

### 4.2 Agent 选型

Tool Calling Agent — 查询场景最合适。LLM 拿到 tool 列表 → 决定调哪个 → 拿到 JSON 结果 → 转为自然语言回复。

### 4.3 领域路由器（POC 版）

关键词匹配，不引入 RAG：

```python
DOMAIN_REGISTRY = {
    "user_mcp": {
        "description": "用户信息查询、部门查询、权限查询",
        "keywords": ["用户", "员工", "部门", "权限", "角色", "账号"]
    },
    "order_mcp": {
        "description": "订单查询、交易记录、支付状态",
        "keywords": ["订单", "交易", "支付", "退款"]
    },
}
```

- 命中关键词 → 只激活对应 MCP 的 tool
- 未命中 → 激活所有 MCP（fallback）
- 升级路径：`description` 向量化 → embedding 语义检索 → RAG 路由

## 5. 认证与 Token 流转

### 5.1 流程

```
前端 ──① 登录──► Python 后端 ──② 转发──► Java 系统
                                           │
前端 ◄──④ Token── Python 后端 ◄──③ Token──┘
         存入会话
           │
前端 ──⑥ 对话──► Python 后端 ──⑦ MCP Tool 调用
                                    │
                          ⑧ HTTP 请求 Java API
                          Header: x-access-token: <token>
                                    │
用户 ◄──⑩ 回复── Python ◄──⑨ 数据──┘
```

### 5.2 关键设计

- Python 后端只做：转发登录请求 + 存 Token + 注入 Token Header
- **不做权限校验** — 全部交给 Java
- Token 不在 MCP Tool 参数中暴露给 LLM（安全考虑）
- MCP Server 从请求上下文获取 Token，直接注入 HTTP Header
- POC 阶段：FastAPI SessionMiddleware 内存存 Token
- 后期：Redis 存储，支持 Token 过期刷新

## 6. 目录结构 & 技术栈

```
mcp-ai-chat/
├── frontend/
│   └── app.py              # Streamlit Chat UI
│
├── backend/
│   ├── main.py             # FastAPI 入口，Session 管理
│   ├── auth.py             # 登录/登出，Token 存取
│   ├── agent.py            # LangChain Agent 初始化
│   ├── router.py           # 领域路由器
│   ├── mcp_client.py       # MCP Client 连接管理（多 MCP）
│   └── prompts/
│       └── system.md       # System Prompt 模板
│
├── mcp_servers/            # 由生成器自动生成
│   ├── user_mcp/
│   │   ├── server.py       # MCP Server 入口
│   │   ├── tools.py        # 自动生成的 tool（= Java API 端点）
│   │   └── schemas.py      # Pydantic 模型
│   ├── order_mcp/
│   │   └── ...
│   └── generator/
│       ├── generate.py     # OpenAPI → MCP 生成器
│       └── templates/      # Jinja2 模板
│
├── openapi_specs/          # Java 项目的 OpenAPI JSON
│   ├── user-api.json
│   └── order-api.json
│
├── requirements.txt
└── docker-compose.yml
```

### 技术栈

| 层 | 技术 | 原因 |
|----|------|------|
| 前端 | Streamlit | POC 快速，自带聊天组件 |
| 后端框架 | FastAPI + SSE | 异步，原生流式支持 |
| Agent | LangChain + langchain-mcp-adapters | MCP 协议原生集成 |
| MCP SDK | Python `mcp` | 官方库 |
| 生成器 | Jinja2 + openapi-spec-validator | 读 JSON 生成 Python 代码 |
| 会话 | FastAPI Session（POC）→ Redis（后期） | 先简单后扩展 |

## 7. 运行流程

**开发期**：
```
OpenAPI JSON ──► generate.py ──► 自动生成各 MCP Server
```

**运行期**：
```
用户登录 → 拿到 Token → 发消息 "查上个月订单"
→ 路由器命中 order_mcp
→ Agent 拿到 order_mcp 的所有 tool（listOrders, getOrderDetail...）
→ LLM 决定调用 listOrders(start="2026-04-01", end="2026-04-30")
→ MCP Tool 执行：HTTP GET Java API + x-access-token: <token>
→ 返回订单列表 → LLM 生成自然语言回复 → 流式输出给用户
```

## 8. 演进路线

| 阶段 | 路由方式 | Tool 选择 | 会话存储 |
|------|---------|----------|---------|
| POC | 关键词匹配 | 域内全量 tool | 内存 Session |
| V2 | 关键词 + 简单语义 | 域内全量 tool | Redis |
| V3 | RAG 语义路由 | RAG 预筛选 top-K tool | Redis + Token 刷新 |
