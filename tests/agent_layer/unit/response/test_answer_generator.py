"""AnswerGenerator 测试

AG-U01: 无 context 时 yield 明确提示
AG-U02: 空查询 yield error
AG-U03: 有 context 时流式输出 + 历史保存
AG-U04: context 为空字符串时视为无证据
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.agent_layer.response.answer_generator import AnswerGenerator


def _make_generator(**overrides):
    """构造 AnswerGenerator 实例，所有依赖默认为 MagicMock"""
    defaults = dict(
        chat_model=MagicMock(),
        conversation_repo=MagicMock(),
    )
    defaults.update(overrides)
    return AnswerGenerator(**defaults)


class TestAGU01:
    """无 evidence 处理"""

    @pytest.mark.asyncio
    async def test_no_context_yields_explicit_message(self):
        """无检索结果时 yield '未找到相关文献' 而非裸 chat"""
        gen = _make_generator()
        events = [e async for e in gen.generate("sess1", "不存在的问题", context="")]

        event_types = [e["event"] for e in events]
        assert event_types == ["metadata", "chunk", "done"]

        content = events[1]["data"]["content"]
        assert "未找到相关文献" in content

    @pytest.mark.asyncio
    async def test_no_context_does_not_call_llm(self):
        """无证据时不应调用 LLM"""
        chat_model = MagicMock()
        gen = _make_generator(chat_model=chat_model)

        [e async for e in gen.generate("sess1", "不存在的问题", context="")]

        chat_model.chat_stream.assert_not_called()


class TestAGU02:
    """空查询处理"""

    @pytest.mark.asyncio
    async def test_empty_query_yields_error(self):
        """空查询 yield error 事件"""
        gen = _make_generator()
        events = [e async for e in gen.generate("sess1", "", context="some context")]

        assert len(events) == 1
        assert events[0]["event"] == "error"


class TestAGU03:
    """有 evidence 时的流式输出"""

    @pytest.mark.asyncio
    async def test_success_path_yields_metadata_chunk_done(self):
        """有 context 时 yield metadata -> chunk... -> done"""
        chat_model = MagicMock()

        async def _fake_stream(messages):
            yield "深度学习"
            yield "是AI的子领域"

        chat_model.chat_stream = _fake_stream

        conversation_repo = MagicMock()
        conversation_repo.get_messages.return_value = []

        gen = _make_generator(
            chat_model=chat_model,
            conversation_repo=conversation_repo,
        )

        context = "[1] 深度学习是人工智能的一个子领域"
        sources = [{"paper_id": "p1", "title": "未命名论文", "page": 1, "section": "引言", "content": "深度学习..."}]
        events = [e async for e in gen.generate("sess1", "什么是深度学习", context=context, sources=sources)]

        event_types = [e["event"] for e in events]
        assert event_types[0] == "metadata"
        assert events[0]["data"]["source_count"] == 1
        assert events[-1]["event"] == "done"

        # 中间是 chunk 事件
        chunk_events = [e for e in events if e["event"] == "chunk"]
        assert len(chunk_events) == 2
        assert chunk_events[0]["data"]["content"] == "深度学习"

    @pytest.mark.asyncio
    async def test_sources_passed_through(self):
        """sources 列表原样传递到 metadata 事件"""
        gen = _make_generator()

        async def _fake_stream(messages):
            yield "回答"

        gen._chat_model.chat_stream = _fake_stream
        gen._conversation_repo.get_messages.return_value = []

        sources = [{"paper_id": "p1", "title": "论文A", "page": 3, "section": "方法"}]
        events = [e async for e in gen.generate("sess1", "问题", context="[1] 内容", sources=sources)]

        metadata = next(e for e in events if e["event"] == "metadata")
        assert metadata["data"]["sources"] == sources
