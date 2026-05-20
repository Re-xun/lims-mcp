"""FastAPI Backend - Main entry point for the AI chat system."""
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import json
import sys
import uuid
from contextvars import ContextVar
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import auth
from .agent import chat_stream
from .mcp_client import current_token, load_tools_for_domains
from .router import route

app = FastAPI(title="MCP AI Chat System", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store: session_id -> {token, username, history}
_sessions: dict[str, dict] = {}


# --- Request/Response models ---

class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class LoginResponse(BaseModel):
    success: bool
    session_id: str | None = None
    username: str | None = None
    error: str | None = None


# --- Endpoints ---

@app.post("/api/login", response_model=LoginResponse)
async def login_endpoint(req: LoginRequest):
    """Forward login to Java API, create a local session."""
    result = await auth.login(req.username, req.password)
    if not result.success:
        return LoginResponse(success=False, error=result.error)

    session_id = uuid.uuid4().hex
    _sessions[session_id] = {
        "token": result.token,
        "username": result.username,
        "history": [],
    }
    return LoginResponse(success=True, session_id=session_id, username=result.username)


@app.post("/api/logout")
async def logout_endpoint(req: Request):
    """Clear session."""
    body = await req.json()
    session_id = body.get("session_id", "")
    _sessions.pop(session_id, None)
    return {"success": True}


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Stream the AI chat response via SSE."""
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session not found. Please login first.")

    # Inject token into ContextVar for this request
    current_token.set(session["token"])

    # Route to relevant MCP domains
    sys.stderr.write(f"\n[STEP 1] 收到消息: {req.message}\n")
    sys.stderr.flush()
    domains = await route(req.message)
    sys.stderr.write(f"[STEP 2] 路由结果: {[d.name for d in domains]}\n")
    sys.stderr.flush()
    tools = await load_tools_for_domains(domains)
    sys.stderr.write(f"[STEP 3] 加载工具: {[t.name for t in tools]}\n")
    sys.stderr.flush()

    if not tools:
        raise HTTPException(status_code=503, detail="No MCP tools available.")

    async def event_generator() -> AsyncIterator[str]:
        async for event in chat_stream(
            user_message=req.message,
            tools=tools,
            history=session["history"],
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "sessions": len(_sessions)}
