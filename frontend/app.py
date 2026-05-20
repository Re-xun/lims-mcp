"""Streamlit Chat UI - AI 对话系统前端."""
from __future__ import annotations

import json
import os

import httpx
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _render_result(result):
    """智能展示工具调用结果：列表数据用表格，其他用 JSON."""
    data = _parse_result(result)
    if isinstance(data, dict) and "resultList" in data:
        count = data.get("count", 0)
        rows = data["resultList"]
        st.metric("总数", count)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.caption("无数据")
    elif isinstance(data, list):
        st.dataframe(data, use_container_width=True, hide_index=True)
    else:
        st.json(data)


def _parse_result(result):
    """解析结果：已是 dict/list 直接返回，字符串尝试 JSON 解析."""
    if isinstance(result, (dict, list)):
        return result
    if isinstance(result, str):
        try:
            return json.loads(result)
        except (json.JSONDecodeError, ValueError):
            return result
    return result

st.set_page_config(page_title="AI 对话系统", page_icon="", layout="centered")
st.title("AI 对话系统")

# --- Session State ---
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "messages" not in st.session_state:
    st.session_state.messages = []


# --- Login Form ---
if not st.session_state.session_id:
    st.subheader("登录")
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")

        if submitted:
            with st.spinner("登录中..."):
                try:
                    resp = httpx.post(
                        f"{BACKEND_URL}/api/login",
                        json={"username": username, "password": password},
                        timeout=10,
                    )
                    data = resp.json()
                    if data.get("success"):
                        st.session_state.session_id = data["session_id"]
                        st.session_state.username = data["username"]
                        st.rerun()
                    else:
                        st.error(data.get("error", "登录失败"))
                except httpx.RequestError as e:
                    st.error(f"无法连接到后端: {e}")
    st.stop()


# --- Logged In: Chat Interface ---
st.sidebar.write(f"已登录: **{st.session_state.username}**")
if st.sidebar.button("退出登录"):
    try:
        httpx.post(
            f"{BACKEND_URL}/api/logout",
            json={"session_id": st.session_state.session_id},
            timeout=5,
        )
    except Exception:
        pass
    st.session_state.session_id = None
    st.session_state.username = None
    st.session_state.messages = []
    st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                with st.expander(f"调用: {tc['tool']}", expanded=False):
                    # 实际发出的 API 请求
                    if tc.get("api_call"):
                        st.caption("实际请求")
                        api = tc["api_call"]
                        st.code(
                            f"{api['method']} {api['url']}\n"
                            f"Token: {api.get('token_masked', '***')}\n"
                            f"Params:\n" + "\n".join(f"  {k}={v}" for k, v in api.get("params", {}).items()),
                            language="text",
                        )
                    st.caption("参数")
                    st.json(tc["args"])
                    if tc.get("result"):
                        st.caption("结果")
                        _render_result(tc["result"])

# Chat input
if prompt := st.chat_input("输入你的问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        tool_calls = []

        try:
            with httpx.stream(
                "POST",
                f"{BACKEND_URL}/api/chat",
                json={"session_id": st.session_state.session_id, "message": prompt},
                timeout=60,
            ) as response:
                if response.status_code == 401:
                    st.session_state.session_id = None
                    st.session_state.username = None
                    st.session_state.messages = []
                    st.error("登录已过期，请重新登录")
                    st.rerun()
                elif response.status_code != 200:
                    st.error(f"后端错误: {response.status_code}")
                else:
                    for line in response.iter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            event = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue

                        ev_type = event.get("event")
                        if ev_type == "tool_call":
                            tool_calls.append({
                                "tool": event["tool"],
                                "args": event["args"],
                                "result": None,
                            })
                            placeholder.write(f"正在查询 **{event['tool']}** ...")
                        elif ev_type == "tool_result":
                            if tool_calls:
                                tool_calls[-1]["result"] = event.get("result", "")
                                tool_calls[-1]["api_call"] = event.get("api_call")
                            placeholder.write(f"已获取 **{event['tool']}** 数据，分析中...")
                        elif ev_type == "text":
                            full_response = event.get("content", "")
                            placeholder.markdown(full_response)
                        elif ev_type == "error":
                            placeholder.error(f"出错了: {event.get('error', '')}")
                        elif ev_type == "done":
                            pass  # streaming complete

        except httpx.RequestError as e:
            placeholder.error(f"请求失败: {e}")

        if full_response:
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "tool_calls": tool_calls if tool_calls else None,
            })
