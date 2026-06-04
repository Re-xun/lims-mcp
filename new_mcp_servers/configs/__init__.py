"""
ALL_MODULES — 唯一需要手动维护的注册列表。

新增模块只需在此添加一行 import + 加入列表即可。

已排除的特殊模块（不通过 QueryEngine 执行）：
- dm_project_mcp    — 5 个工具，raw 透传，无 FIELD_LABELS
- emc_mcp           — 3 个工具，无 FIELD_LABELS，非标准 filter 配置
- is_workbench_mcp  — 不同 API 模式
- user_mcp          — REST API 客户端
"""

from __future__ import annotations

from new_mcp_servers.core.config import ModuleConfig

from .customer import customer
from .sales_order import sales_order
from .quotation import quotation
from .supplier import supplier
from .customer_contact import customer_contact
from .dc_project import dc_project
from .fin_ar_invoice import fin_ar_invoice
from .fin_cas_reversing import fin_cas_reversing
from .fin_expense_apply import fin_expense_apply
from .fin_receiving_notice import fin_receiving_notice
from .fin_cas_payment_apply import fin_cas_payment_apply
from .my_fin_cas_receiving import my_fin_cas_receiving
from .ps_activity import ps_activity
from .ps_plan import ps_plan
from .ps_opportunity import ps_opportunity
from .pur_outgoing import pur_outgoing
from .pur_purchase import pur_purchase
from .pur_request import pur_request
from .sd_invoice_request import sd_invoice_request
from .sd_service_item import sd_service_item
from .sd_temp_test_service_item import sd_temp_test_service_item
from .dm_test_charge import dm_test_charge
from .dmtestcharge_temporary import dmtestcharge_temporary
from .dm_test_charge_item_free import dm_test_charge_item_free
from .emc_temporary_test import emc_temporary_test

ALL_MODULES: list[ModuleConfig] = [
    # 销售/客户
    customer,
    customer_contact,
    quotation,
    sales_order,
    supplier,
    # 项目
    dc_project,
    dm_test_charge,
    dmtestcharge_temporary,
    dm_test_charge_item_free,
    emc_temporary_test,
    # 市场
    ps_activity,
    ps_plan,
    ps_opportunity,
    # 财务
    fin_ar_invoice,
    fin_cas_payment_apply,
    fin_cas_reversing,
    fin_expense_apply,
    fin_receiving_notice,
    my_fin_cas_receiving,
    # 采购
    pur_outgoing,
    pur_purchase,
    pur_request,
    # 服务项目
    sd_invoice_request,
    sd_service_item,
    sd_temp_test_service_item,
]
