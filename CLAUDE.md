# CLAUDE.md

## MCP 工具数据展示

- 展示 MCP 查询结果时，直接使用各 MCP 工具 `FIELD_LABELS` 中定义的中文列名，不要自行编造或修改列名
- `FIELD_LABELS` 是后端接口字段到中文展示名的权威映射

## MCP API 调用

- 实际 API 地址由 `.env` 中的 `JAVA_API_BASE` 环境变量决定：
  ```
  JAVA_API_BASE=https://dev.metalims.cn/server
  ```
- 调用时需带 `x-access-token` 请求头（MCP server 登录后自动注入）

## 分页

- 默认 `limit=10`，用户说"更多"，"分页"时再酌情增大

## 展示

- 展示 MCP 查询结果时，全部列给出，不需要筛选，对于多行数据用表格展示