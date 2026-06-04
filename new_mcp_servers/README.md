# LIMS MCP Server (new_mcp_servers)

解耦后的 LIMS 系统 MCP 查询服务，基于配置驱动的架构，提供 25 个业务查询工具 + 1 个登录工具。

## 目录

- [快速开始](#快速开始)
- [配置 MCP 客户端](#配置-mcp-客户端)
  - [Claude Desktop](#claude-desktop)
  - [Codex (OpenAI)](#codex-openai)
  - [VS Code / Cursor](#vs-code--cursor)
- [环境变量](#环境变量)
- [可用工具](#可用工具)
- [架构说明](#架构说明)

## 快速开始

### 1. 环境要求

- Python >= 3.10
- 可访问 LIMS Java API（默认 `https://dev.metalims.cn/server`）

### 2. 安装依赖

```bash
pip install mcp httpx python-dotenv
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填写：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
JAVA_API_BASE=https://dev.metalims.cn/server
LIMS_USERNAME=你的工号
LIMS_PASSWORD=你的密码
```

### 4. 运行

```bash
USE_NEW_MCP=1 python -m new_mcp_servers.unified_server
```

服务通过 stdio 与 MCP 客户端通信，不需要独立端口。

## 配置 MCP 客户端

### Claude Desktop

编辑 Claude Desktop 配置文件：

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "lims-unified": {
      "command": "python",
      "args": ["-m", "new_mcp_servers.unified_server"],
      "env": {
        "USE_NEW_MCP": "1",
        "JAVA_API_BASE": "https://dev.metalims.cn/server",
        "LIMS_USERNAME": "你的工号",
        "LIMS_PASSWORD": "你的密码"
      }
    }
  }
}
```

### Codex (OpenAI)

编辑 Codex CLI 配置文件（`~/.codex/config.toml` 或项目级 `.codex/config.toml`）：

```toml
[mcp_servers.lims-unified]
command = "python"
args = ["-m", "new_mcp_servers.unified_server"]
env = { USE_NEW_MCP = "1", JAVA_API_BASE = "https://dev.metalims.cn/server", LIMS_USERNAME = "你的工号", LIMS_PASSWORD = "你的密码" }
```

或者使用 JSON 格式（`~/.codex/config.json`）：

```json
{
  "mcpServers": {
    "lims-unified": {
      "command": "python",
      "args": ["-m", "new_mcp_servers.unified_server"],
      "env": {
        "USE_NEW_MCP": "1",
        "JAVA_API_BASE": "https://dev.metalims.cn/server",
        "LIMS_USERNAME": "你的工号",
        "LIMS_PASSWORD": "你的密码"
      }
    }
  }
}
```

### VS Code / Cursor

在 `.vscode/mcp.json` 中：

```json
{
  "servers": {
    "lims-unified": {
      "command": "python",
      "args": ["-m", "new_mcp_servers.unified_server"],
      "env": {
        "USE_NEW_MCP": "1",
        "JAVA_API_BASE": "https://dev.metalims.cn/server",
        "LIMS_USERNAME": "你的工号",
        "LIMS_PASSWORD": "你的密码"
      }
    }
  }
}
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `USE_NEW_MCP` | **是** | 必须设为 `1` 启用新架构 |
| `JAVA_API_BASE` | 否 | LIMS Java API 地址（默认 `http://localhost:3011`） |
| `LIMS_USERNAME` | 否 | 自动登录用户名（也可通过 `login` 工具手动登录） |
| `LIMS_PASSWORD` | 否 | 自动登录密码 |
| `LIMS_TOKEN` | 否 | 已缓存的 token，跳过登录步骤 |

## 可用工具

| 工具名 | 说明 |
|--------|------|
| `login` | 登录 LIMS 系统获取 token |
| `query_customer_list` | 查询客户列表 |
| `query_customer_contact_list` | 查询客户联系人列表 |
| `query_contact_plan_list` | 查询客户联系计划列表 |
| `query_sales_opportunity_list` | 查询销售机会列表 |
| `query_psactivitylistaction` | 查询客户联系记录列表 |
| `query_quotation_list` | 查询报价单列表 |
| `query_sales_order_list` | 查询销售合同列表 |
| `query_dc_project_list` | 查询 DC 项目列表 |
| `query_dmtestchargelistaction` | 查询收费单列表 |
| `query_dmtestchargetemporarylistaction` | 查询临时收费单列表 |
| `query_emctemporarytestlistaction` | 查询 EMC 临时测试列表 |
| `query_finarinvoicelistaction` | 查询开票记录列表 |
| `query_fincaspaymentapplylistaction` | 查询付款申请列表 |
| `query_fincasreversinglistaction` | 查询退款单列表 |
| `query_daily_expense_apply_list` | 查询日常申请列表 |
| `query_finreceivingnoticelistaction` | 查询收款通知单列表 |
| `query_myfincasreceivinglistaction` | 查询我的收款单列表 |
| `query_sdinvoicerequestlistaction` | 查询开票申请列表 |
| `query_sdserviceitemlistaction` | 查询服务项目列表 |
| `query_sdtemptestserviceitemlistaction` | 查询临时测试服务项目列表 |
| `query_supplier_list` | 查询供应商列表 |
| `query_puroutgoingrequestformlistaction` | 查询外发/分包申请单列表 |
| `query_purpurchaselistaction` | 查询采购单列表 |
| `query_purrequestlistaction` | 查询采购申请列表 |

## 架构说明

```
new_mcp_servers/
├── unified_server.py    # 入口：MCP stdio 服务 + token 管理
├── core/
│   ├── config.py        # 类型定义（ModuleConfig, FilterDef, FieldLabel）
│   ├── registry.py      # 根据 ModuleConfig 自动生成 MCP tool schema 和 handler
│   ├── engine.py        # 统一查询执行引擎（HTTP 调用 Java API）
│   ├── security.py      # 三层安全校验
│   └── filter_builder.py # SQL WHERE 子句构建
└── configs/             # 业务模块配置（纯数据，无逻辑）
    ├── customer.py
    ├── sales_order.py
    ├── dc_project.py
    └── ... (21 more)
```

**核心设计**：每个业务模块只需要一个 `ModuleConfig` 数据类来声明接口参数、字段映射、枚举值，`ModuleRegistry` 自动生成对应的 MCP tool schema 和 async handler。添加新模块只需新建一个 config 文件并注册到 `ALL_MODULES` 列表。

## 添加新模块

1. 在 `new_mcp_servers/configs/` 下新建 `your_module.py`
2. 定义一个 `ModuleConfig` 实例，包含 `name`, `endpoint`, `filters`, `field_labels` 等
3. 在 `configs/__init__.py` 的 `ALL_MODULES` 列表中导入并添加
4. 重启 MCP 服务即可
