"""query_routes 单元测试"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(*, redis_ok=False, has_editor_store=True, has_window_store=True):
    """构造带 mock container 的 FastAPI app"""
    from app.service_layer.api.query_routes import router

    app = FastAPI()
    app.include_router(router)

    container = MagicMock()
    container.chat_model = MagicMock()
    container.chat_model.max_context_tokens = 32000
    container.vector_store = MagicMock()
    container.keyword_search = MagicMock()
    container.embedding_client = MagicMock()
    container.redis_health = {"status": "ok" if redis_ok else "unavailable"}
    container.conversation_window = MagicMock() if has_window_store else None
    container.editor_context_store = MagicMock() if has_editor_store else None

    app.state.container = container
    return app, container


class TestQueryMetadataEvent:
    """验证首个 SSE 帧是 metadata 事件"""

    def test_first_frame_is_metadata(self):
        app, container = _build_app()
        client = TestClient(app)

        mock_runner = MagicMock()

        async def fake_run(request):
            yield 'event: metadata\ndata: {"request_id":"r1","session_id":"s1","used_inputs":{"prompt":1.0,"selection":0.0,"written_context":0.0,"rag_evidence":0.0},"context_tokens":10,"remaining_tokens":31990,"remaining_ratio":0.9997,"retrieval_planned":true,"degraded_flags":[],"cache_mode":"unavailable"}\n\n'
            yield 'event: done\ndata: {}\n\n'

        mock_runner.run = fake_run

        with patch("app.service_layer.api.query_routes._build_runner", return_value=mock_runner):
            resp = client.post(
                "/query",
                json={"session_id": "s1", "prompt": "hello"},
                headers={"Accept": "text/event-stream"},
            )

        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        # 找到第一个 event 行
        first_event = None
        for line in lines:
            if line.startswith("event:"):
                first_event = line.split(":", 1)[1].strip()
                break
        assert first_event == "metadata"

    def test_metadata_contains_required_fields(self):
        app, container = _build_app()
        client = TestClient(app)

        mock_runner = MagicMock()

        async def fake_run(request):
            yield 'event: metadata\ndata: {"request_id":"r1","session_id":"s1","used_inputs":{"prompt":1.0},"context_tokens":10,"remaining_tokens":31990,"remaining_ratio":0.9997,"retrieval_planned":true,"degraded_flags":[],"cache_mode":"unavailable"}\n\n'
            yield 'event: done\ndata: {}\n\n'

        mock_runner.run = fake_run

        with patch("app.service_layer.api.query_routes._build_runner", return_value=mock_runner):
            resp = client.post(
                "/query",
                json={"session_id": "s1", "prompt": "hello"},
            )

        assert resp.status_code == 200
        # 解析 metadata data
        for line in resp.text.split("\n"):
            if line.startswith("data:") and '"request_id"' in line:
                data = json.loads(line[5:].strip())
                assert "request_id" in data
                assert "session_id" in data
                assert "used_inputs" in data
                assert "context_tokens" in data
                assert "remaining_tokens" in data
                assert "remaining_ratio" in data
                assert "retrieval_planned" in data
                assert "degraded_flags" in data
                assert "cache_mode" in data
                break


class TestQueryEmptyPrompt:
    def test_empty_prompt_returns_error(self):
        app, _ = _build_app()
        client = TestClient(app)

        mock_runner = MagicMock()

        async def fake_run(request):
            yield 'event: error\ndata: {"message": "请提供问题或内容"}\n\n'

        mock_runner.run = fake_run

        with patch("app.service_layer.api.query_routes._build_runner", return_value=mock_runner):
            resp = client.post(
                "/query",
                json={"session_id": "s1", "prompt": ""},
            )

        assert resp.status_code == 200
        assert "error" in resp.text


class TestRunnerContainerInjection:
    """验证 _build_runner 从 container 取依赖"""

    def test_runner_uses_container_turn_runner(self):
        """container 存在时直接返回 container.turn_runner"""
        from app.service_layer.api.query_routes import _build_runner

        mock_request = MagicMock()
        expected_runner = MagicMock()
        container = MagicMock()
        container.turn_runner = expected_runner
        mock_request.app.state.container = container

        runner = _build_runner(mock_request)
        assert runner is expected_runner

    def test_runner_fallback_when_no_container(self):
        """container 不存在时构建 fallback TurnRunner"""
        from app.service_layer.api.query_routes import _build_runner

        mock_request = MagicMock()
        mock_request.app.state.container = None

        runner = _build_runner(mock_request)
        assert runner is not None
        assert hasattr(runner, "_chat_model")
