"""POST /api/v1/query — Agent 层对话入口"""

from __future__ import annotations

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

router = APIRouter()


def _build_runner(request: Request) -> TurnRunner:
    container = getattr(request.app.state, "container", None)
    if container is not None:
        runner = getattr(container, "turn_runner", None)
        if isinstance(runner, TurnRunner):
            return runner

        settings = getattr(container, "settings", get_settings())
        window_store = getattr(container, "conversation_window", None)
        if window_store is None:
            window_store = ConversationWindowStore.from_context_window(
                context_window_tokens=settings.context_window_tokens,
                max_output_tokens=settings.max_output_tokens,
            )
        editor_context_store = getattr(container, "editor_context_store", None) or EditorContextStore()
        persistence = getattr(container, "session_persistence", None) or SessionPersistence()
        return TurnRunner(
            chat_model=container.chat_model,
            snapshot_builder=build_snapshot,
            retrieval_gate=should_retrieve,
            source_mapper=map_sources,
            block_streamer=stream_to_blocks,
            window_store=window_store,
            editor_context_store=editor_context_store,
            persistence=persistence,
            vector_store=getattr(container, "vector_store", None),
            keyword_search=getattr(container, "keyword_search", None),
            embedding_client=getattr(container, "embedding_client", None),
            reflection_model=getattr(container, "reflection_chat_model", None),
        )

    # Fallback: container 未初始化（E2E 测试 / 未进入 lifespan）
    settings = get_settings()
    return TurnRunner(
        chat_model=ChatModel(settings),
        snapshot_builder=build_snapshot,
        retrieval_gate=should_retrieve,
        source_mapper=map_sources,
        block_streamer=stream_to_blocks,
        window_store=ConversationWindowStore.from_context_window(
            context_window_tokens=settings.context_window_tokens,
            max_output_tokens=settings.max_output_tokens,
        ),
        editor_context_store=EditorContextStore(),
        persistence=SessionPersistence(),
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
