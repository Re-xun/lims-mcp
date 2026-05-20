"""Domain Router - Intent-based routing to MCP servers.

LLM classification picks the 1-2 most relevant domains.
Falls back to scored keyword matching, then to safe defaults.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


@dataclass
class DomainConfig:
    name: str
    description: str
    keywords: list[str]
    mcp_command: str = "python"
    mcp_args: list[str] = field(default_factory=list)


DOMAIN_REGISTRY: dict[str, DomainConfig] = {
    "customer_mcp": DomainConfig(
        name="customer_mcp",
        description="客户列表查询、客户信息、客户搜索",
        keywords=["客户", "客户列表", "customer", "顾客", "甲方"],
        mcp_args=["-m", "mcp_servers.customer_mcp.server"],
    ),
    "project_mcp": DomainConfig(
        name="project_mcp",
        description="项目查询、委托单查询、安全项目、EMC项目、产值统计、工程师提成",
        keywords=["项目", "委托", "委托单", "project", "安全项目", "EMC", "产值", "提成", "结案", "交付"],
        mcp_args=["-m", "mcp_servers.project_mcp.server"],
    ),
    "sales_order_mcp": DomainConfig(
        name="sales_order_mcp",
        description="销售订单查询、销售合同查询、销售订单列表、合同列表",
        keywords=["销售合同", "合同", "销售订单", "sales", "contract", "订单", "收款", "开票"],
        mcp_args=["-m", "mcp_servers.sales_order_mcp.server"],
    ),
}

# When all routing fails, load the 2 most commonly used domains
_DEFAULT_NAMES = ["project_mcp", "customer_mcp", "sales_order_mcp"]

# LLM config (shared with agent.py)
_LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
_LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-5bb52c099cc3406593c27f8394de74f0")
_LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")

_ROUTER_SYSTEM = """你是路由分类器。根据用户消息选择最相关的业务域（最多2个）。
只返回JSON数组，例如: ["project_mcp", "customer_mcp"]
不要输出其他任何内容。"""


def _build_classifier() -> ChatOpenAI:
    return ChatOpenAI(
        model=_LLM_MODEL,
        api_key=_LLM_API_KEY,
        base_url=_LLM_BASE_URL,
        temperature=0,
        streaming=False,
    )


async def _classify(user_message: str) -> list[str]:
    """LLM intent classification → list of domain names (max 2)."""
    domain_desc = "\n".join(
        f"- {name}: {cfg.description}" for name, cfg in DOMAIN_REGISTRY.items()
    )
    llm = _build_classifier()
    response = await llm.ainvoke([
        SystemMessage(content=_ROUTER_SYSTEM),
        HumanMessage(content=f"可用域:\n{domain_desc}\n\n用户消息: {user_message}"),
    ])
    text = response.content.strip()
    # Extract JSON array from optional markdown fences
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and start < end:
        text = text[start:end + 1]
    names = json.loads(text)
    return [n for n in names if n in DOMAIN_REGISTRY][:2]


def _keyword_match(user_message: str) -> list[str]:
    """Scored keyword matching. Longer keyword = stronger signal. Returns top 2."""
    msg = user_message.lower()
    scored = []
    for name, cfg in DOMAIN_REGISTRY.items():
        score = 0
        for kw in cfg.keywords:
            if kw.lower() in msg:
                score += len(kw)
        if score > 0:
            scored.append((name, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in scored[:2]]


async def route(user_message: str) -> list[DomainConfig]:
    """Route user message to the most relevant MCP domains (max 2).

    Tier 1 — LLM classification (most accurate)
    Tier 2 — Keyword matching with scoring (fast fallback)
    Tier 3 — Safe defaults: project_mcp + customer_mcp (last resort)
    """
    # Tier 1: LLM classification
    try:
        names = await _classify(user_message)
        if names:
            return [DOMAIN_REGISTRY[n] for n in names]
    except Exception:
        pass

    # Tier 2: Keyword matching
    names = _keyword_match(user_message)
    if names:
        return [DOMAIN_REGISTRY[n] for n in names]

    # Tier 3: Safe defaults
    return [DOMAIN_REGISTRY[n] for n in _DEFAULT_NAMES]


def get_all_domains() -> list[DomainConfig]:
    return list(DOMAIN_REGISTRY.values())
