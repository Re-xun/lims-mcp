# MCP 调用流程

## 一、启动

```
Claude Code 启动
  → 读 ~/.claude.json → mcpServers
  → spawn: python -m mcp_servers.unified_server
  → 发 tools/list → 拿到 12 个 tool(name + description)
  → 注入到 system prompt
```

## 二、匹配

```
用户: "查深圳的客户"
  → AI 遍历 tool description 做语义匹配
  → "客户" 命中 query_customer_list
  → 提取参数 keyword="深圳"
  → 返回 function_call
```

## 三、执行

```
Claude Code → stdin 发 JSON-RPC → unified_server
  → _ensure_token() 没 token 自动登录
  → 路由到 query_customer_list handler
  → HTTP GET /AbdCustomerListAction/listQuery
  → Java API 查数据库 → 返回 JSON
  → stdout 返回给 Claude Code
```

## 四、回复

```
AI 收到查询结果 JSON
  → 整理成自然语言
  → 展示给用户
```
