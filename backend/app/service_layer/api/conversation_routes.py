"""对话 API 路由"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agent_layer.contracts.query import AskRequest
from app.data_layer.storage.sqlite_runtime._types import ConversationSession, utc_now_iso
from app.data_layer.storage.sqlite_runtime.async_wrapper import run_sync
from app.service_layer.schemas.conversation import (
    ChatRequest,
    ConversationMessageOut,
    ConversationSessionOut,
    EditMessageRequest,
    RenameRequest,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSessionOut])
async def list_sessions(request: Request):
    container = request.app.state.container
    sessions = await run_sync(container.conversation_repo.list_sessions, limit=50, offset=0)
    return [ConversationSessionOut(**s.__dict__) for s in sessions]


@router.post("", response_model=ConversationSessionOut)
async def create_session(request: Request):
    container = request.app.state.container
    session_id = uuid.uuid4().hex[:12]
    now = utc_now_iso()
    session = ConversationSession(session_id=session_id, title="新对话", created_at=now, updated_at=now)
    await run_sync(container.conversation_repo.upsert_session, session)
    return ConversationSessionOut(**session.__dict__)


@router.get("/{session_id}", response_model=ConversationSessionOut)
async def get_session(session_id: str, request: Request):
    container = request.app.state.container
    session = await run_sync(container.conversation_repo.get_session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ConversationSessionOut(**session.__dict__)


@router.delete("/{session_id}")
async def delete_session(session_id: str, request: Request):
    container = request.app.state.container
    session = await run_sync(container.conversation_repo.get_session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    await run_sync(container.conversation_repo.delete_session, session_id)
    return {"status": "ok", "message": "会话已删除"}


@router.put("/{session_id}/title", response_model=ConversationSessionOut)
async def rename_session(session_id: str, body: RenameRequest, request: Request):
    """重命名会话"""
    container = request.app.state.container
    ok = await run_sync(container.conversation_repo.rename_session, session_id, body.title)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    session = await run_sync(container.conversation_repo.get_session, session_id)
    return ConversationSessionOut(**session.__dict__)


@router.get("/search")
async def search_conversations(request: Request, q: str = "", limit: int = 20):
    """搜索会话（标题）和消息（内容）"""
    if not q.strip():
        return {"sessions": [], "messages": []}

    container = request.app.state.container
    sessions = await run_sync(container.conversation_repo.search_sessions, q, limit=limit)
    messages = await run_sync(container.conversation_repo.search_messages, q, limit=limit)

    return {
        "sessions": [ConversationSessionOut(**s.__dict__) for s in sessions],
        "messages": [ConversationMessageOut(**m.__dict__) for m in messages],
    }


@router.get("/{session_id}/messages", response_model=list[ConversationMessageOut])
async def list_messages(session_id: str, request: Request, limit: int = 50):
    container = request.app.state.container
    messages = await run_sync(container.conversation_repo.get_messages, session_id, limit=limit)
    return [ConversationMessageOut(**m.__dict__) for m in messages]


@router.delete("/{session_id}/messages/{message_id}")
async def delete_message(session_id: str, message_id: int, request: Request):
    """删除单条消息"""
    container = request.app.state.container
    ok = await run_sync(container.conversation_repo.delete_message, message_id)
    if not ok:
        raise HTTPException(status_code=404, detail="消息不存在")
    return {"status": "ok", "message": "消息已删除"}


@router.patch("/{session_id}/messages/{message_id}", response_model=ConversationMessageOut)
async def edit_message(session_id: str, message_id: int, body: EditMessageRequest, request: Request):
    """编辑消息内容"""
    container = request.app.state.container
    ok = await run_sync(container.conversation_repo.update_message, message_id, body.content)
    if not ok:
        raise HTTPException(status_code=404, detail="消息不存在")
    return ConversationMessageOut(id=message_id, session_id=session_id, role="", content=body.content)


@router.post("/chat")
async def chat(body: ChatRequest, request: Request):
    """对话入口 — 转发到 TurnRunner（与 /api/v1/query 共享同一套 Agent 编排）"""
    from app.service_layer.api.query_routes import _build_runner

    session_id = body.session_id or uuid.uuid4().hex[:12]
    ask_req = AskRequest(
        session_id=session_id,
        prompt=body.message,
        paper_ids=body.paper_ids,
        enable_rag=True,
    )

    runner = _build_runner(request)

    async def event_stream():
        async for frame in runner.run(ask_req):
            yield frame

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
