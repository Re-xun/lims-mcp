# MCP Servers 解耦重构设计

## 问题陈述

当前 `mcp_servers/` 下 27 个 MCP 模块存在严重的代码重复和紧耦合：

| 问题 | 现状 |
|---|---|
| 辅助函数重复 | `_mask_token`、`_extract_result_list`、`_extract_count`、`build_filter`、`_normalize_row`、`_build_columns` 等在 27 个文件中逐字重复 |
| 硬编码注册 | `unified_server.py` 顶部 27 行显式 import，新增模块必须手动注册 |
| 同一数据写三遍 | 每个 filter 字段需要：FILTER_CONFIG 定义 + 函数签名参数 + `_PROPS` schema 属性 |
| 零共享基础设施 | 没有 `common.py` / `utils.py`，模块间完全孤立 |
| 两种范式混杂 | "规范化"（FIELD_LABELS）和"原始透传"两种模式逻辑交织 |

## 目标架构

```
new_mcp_servers/
├── core/
│   ├── __init__.py
│   ├── config.py           # ModuleConfig, FilterDef, FieldLabel, EnumField
│   ├── engine.py           # QueryEngine 统一执行引擎
│   ├── filter_builder.py   # build_filter() 过滤器构建
│   ├── security.py         # 三防线安全校验
│   └── registry.py         # 显式注册 + MCP Tool Schema 自动生成
├── configs/
│   ├── __init__.py          # ALL_MODULES 显式列表（唯一需手写的注册点）
│   ├── customer.py
│   ├── quotation.py
│   ├── sales_order.py
│   └── ... (27 个配置)
├── unified_server.py        # 薄编排层 (~100 行)
└── __init__.py
```

## 核心类型

```python
@dataclass
class FilterDef:
    key: str                    # Python 参数名
    backend_field: str          # 后端 SQL 字段
    label: str                  # 中文显示名
    operator: str               # "=" | "like" | ">=" | "<=" | "in"
    is_date_range: bool = False
    enums: dict[int, str] | None = None


@dataclass
class FieldLabel:
    key: str                    # 后端字段名
    title: str                  # 中文列名


@dataclass
class EnumField:
    mapping: dict[int, str]     # 值 → 文本


@dataclass
class ModuleConfig:
    name: str                   # 工具名
    display_name: str           # 显示名
    endpoint: str               # 默认 API 端点
    method: str = "POST"        # HTTP 方法
    description: str = ""
    scope_endpoints: dict[str, str] | None = None  # mine/dept/all → endpoint
    scope_svars: dict[str, dict] = field(default_factory=dict)
    scope_datatype_defaults: dict[str, str] = field(default_factory=dict)
    filters: list[FilterDef] = field(default_factory=list)
    field_labels: dict[str, FieldLabel] = field(default_factory=dict)
    enum_fields: dict[str, EnumField] = field(default_factory=dict)
    default_limit: int = 10
    max_limit: int = 200
    route_fn: Callable[[dict], str] | None = None  # 特殊模块自定义路由
```

**设计决策：Python dataclass 而非 YAML。** 类型安全、IDE 自动补全、无新依赖、与现有项目风格一致。

## 统一执行引擎

```python
class QueryEngine:
    async def execute(self, config: ModuleConfig, params: dict, token: str) -> dict:
        # 1. 安全校验 —— 三防线
        security.validate(config, params)

        # 2. 解析端点（自定义路由 > scope 映射 > 固定端点）
        endpoint = self._resolve_endpoint(config, params)

        # 3. 构建过滤条件
        filter_str = filter_builder.build(config.filters, params)

        # 4. 构建请求体
        body = self._build_body(config, params, filter_str)

        # 5. API 调用
        resp = await self._client.request(
            method=config.method,
            url=f"{JAVA_API_BASE}{endpoint}",
            json=body,
            headers={"x-access-token": token},
        )

        # 6. 提取 & 规范化
        rows = _extract_result_list(resp.json())
        count = _extract_count(resp.json(), rows)
        data = [_normalize_row(row, config) for row in rows]

        return {"count": count, "columns": _build_columns(config), "data": data}
```

## 三防线安全模型

操作符不来自用户输入，硬编码在配置中。用户只传值。

| 防线 | 机制 | 防护目标 |
|---|---|---|
| 防线1 — 角色门控 | `params["scope"]` 必须在 `config.scope_endpoints` 的 keys 中 | 防止越权查询 |
| 防线2 — 字段白名单 | `params` 中的 filter key 必须在 `config.filters` 中声明 | 防止注入未声明字段 |
| 防线3 — 操作符绑定 | 操作符从 `config.filters[N].operator` 取值，不由用户传入 | 防止 `like` 拖库、`=` 爆破 |

## 注册中心

```python
# configs/__init__.py —— 唯一需要手动维护的模块列表

from new_mcp_servers.configs.customer import customer
from new_mcp_servers.configs.sales_order import sales_order

ALL_MODULES: list[ModuleConfig] = [customer, sales_order, ...]
```

```python
class ModuleRegistry:
    def build(self, engine: QueryEngine):
        for m in self._modules:
            handler = self._create_handler(m, engine)
            schema = self._build_schema(m)
            self._handlers[m.name] = handler
            self._schemas[m.name] = schema
```

- `_build_schema()` 从 `FilterDef` 列表自动生成 JSON Schema properties，包含枚举值描述
- `_create_handler()` 返回闭包，将 `params` + `token` 绑定到 `engine.execute(config, params, token)`
- 显式注册：在 `configs/__init__.py` 的 `ALL_MODULES` 列表中加一行。不放文件就自动不会被注册，简单可控

## 配置示例

```python
sales_order = ModuleConfig(
    name="query_sales_order_list",
    display_name="销售合同/订单",
    description="查询销售订单列表，支持按订单编号、客户、状态等过滤",
    endpoint="/SdSalesOrderListAction/listQuery",
    scope_endpoints={
        "default": "/SdSalesOrderListAction/listQuery",
        "my": "/SdSalesOrderListAction/listQueryMy",
        "dept": "/SdSalesOrderListAction/listQueryDept",
        "fin": "/SdSalesOrderListAction/listQueryFin",
        "cancel": "/SdSalesOrderListAction/listQueryCancel",
        # ... 14 个 scope
    },
    scope_svars={
        "default": {"customerType": 1, "operation": "operation"},
        "my": {"customerType": 3},
    },
    scope_datatype_defaults={
        "default": "Last30days",
        "my": "Last30days",
    },
    filters=[
        FilterDef("sales_order_no", "sso.sales_order_no", "销售合同号", "like"),
        FilterDef("customer_name", "ac.CUSTOMER_NAME_CN", "客户名称", "like"),
        FilterDef("bstatus", "sso.bstatus", "业务状态", "=",
                  enums={20: "未开案", 30: "案件进行中", 40: "结案收款中", 45: "结案已收款", 50: "结束", 60: "取消"}),
        FilterDef("create_on_start", "sso.create_on", "创建日期起", ">=", is_date_range=True),
        FilterDef("create_on_end", "sso.create_on", "创建日期止", "<=", is_date_range=True),
        # ... ~95 个其他 filter
    ],
    field_labels={
        "salesOrderNo": FieldLabel("sales_order_no", "销售合同号"),
        "customerNameCn": FieldLabel("customer_name_cn", "客户名称"),
        # ... ~33 个其他字段
    },
    enum_fields={
        "bstatus": EnumField({20: "未开案", 30: "案件进行中", 40: "结案收款中", 45: "结案已收款", 50: "结束", 60: "取消"}),
        "rstatus": EnumField({0: "已作废", 1: "已审核", 2: "暂存", 3: "等待重新审批", 4: "审批中"}),
    },
)
```

Filter 字段本身是领域数据，无论什么设计都必须存在。旧版同一 filter 需写三遍（FILTER_CONFIG + 函数签名参数 + _PROPS），新版只写一次 `FilterDef`。

## Scope/Endpoint 路由

三种路由方式，引擎按优先级处理：

1. **自定义路由函数**（`route_fn`）—— 复杂场景如 dm_project 按 `data_type` + `modular_type` 分发
2. **Scope 映射表**（`scope_endpoints`）—— 90% 模块使用 mine/dept/all → endpoint
3. **固定端点**（`endpoint`）—— 不需要路由的简单模块

优先级：自定义函数 > scope 映射 > 固定端点。

## 量化收益

| 指标 | 当前 | 重构后 | 减少 |
|---|---|---|---|
| 总代码行数 | ~6,500 | ~1,300 | ~80% |
| MCP tool schema tokens | ~68,200 | ~20,000 | ~70% |
| 新增模块工作量 | ~200 行 tools.py | ~50-150 行 config | ~60-75% |
| 修改通用逻辑 | 改 27 个文件 | 改 1 个 engine.py | — |

## 迁移策略

新旧两套并行运行，通过环境变量切换：

```python
USE_NEW_MCP = os.environ.get("USE_NEW_MCP", "0") == "1"
```

**Phase 1：搭建核心** — 创建 `new_mcp_servers/core/`（engine、security、filter_builder、registry、config），验证引擎逻辑正确。

**Phase 2：迁移首批模块** — 选 3-5 个模块写 config 并在 `configs/__init__.py` 注册，同时从旧 `unified_server.py` 移除对应 import。验证通过后继续。

**Phase 3：逐模块迁移** — 每迁移一个模块：写 config → 注册 → 移除旧 import → 验证。每次变更隔离可回滚。

**Phase 4：清理** — 全部迁移完成后，删除旧的 27 个模块目录和旧 `unified_server.py`。
