"""POST /api/v1/query — Agent 层对话入口"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.agent_layer.contracts.query import AskRequest
from app.agent_layer.orchestration.turn_runner import TurnRunner
from app.agent_layer.planning.retrieval_gate import should_retrieve
from app.agent_layer.planning.snapshot_builder import build_snapshot
from app.agent_layer.response.block_streamer import stream_to_blocks
from app.agent_layer.response.source_mapper import map_sources
from app.agent_layer.runtime.chat_model import ChatModel
from app.agent_layer.session.editor_context_store import EditorContextStore
from app.agent_layer.session.persistence import SessionPersistence
from app.agent_layer.session.window_store import ConversationWindowStore
from app.service_layer.config.settings import get_settings

logger = logging.getLogger("paper-assistant")

router = APIRouter()

# 模块级单例：不需要 container 的持久化组件
_persistence = SessionPersistence()

# 降级用的内存 fallback
_fallback_window = ConversationWindowStore(max_messages=20)
_fallback_editor = EditorContextStore()


def _build_runner(request: Request) -> TurnRunner:
    container = getattr(request.app.state, "container", None)

    if container is not None:
        window_store = container.conversation_window if container.conversation_window is not None else _fallback_window
        editor_store = container.editor_context_store if container.editor_context_store is not None else _fallback_editor

        redis_mode = "unavailable"
        if container.redis_health.get("status") == "ok":
            redis_mode = "connected"
        elif container.conversation_window is not None:
            redis_mode = "degraded"

        return TurnRunner(
            chat_model=container.chat_model,
            snapshot_builder=build_snapshot,
            retrieval_gate=should_retrieve,
            source_mapper=map_sources,
            block_streamer=stream_to_blocks,
            window_store=window_store,
            editor_context_store=editor_store,
            persistence=_persistence,
            vector_store=container.vector_store,
            keyword_search=container.keyword_search,
            embedding_client=container.embedding_client,
            tool_registry=None,
            redis_mode=redis_mode,
        )

    # Fallback: container 未初始化（E2E 测试 / 未进入 lifespan）
    settings = get_settings()
    return TurnRunner(
        chat_model=ChatModel(settings),
        snapshot_builder=build_snapshot,
        retrieval_gate=should_retrieve,
        source_mapper=map_sources,
        block_streamer=stream_to_blocks,
        window_store=_fallback_window,
        editor_context_store=_fallback_editor,
        persistence=_persistence,
    )


@router.post("/query")
async def query_endpoint(body: AskRequest, request: Request):
    runner = _build_runner(request)

    async def event_stream():
        async for frame in runner.run(body):
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
