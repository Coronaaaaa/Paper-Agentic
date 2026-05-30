"""Tool Loop 单元测试"""

from __future__ import annotations

import json

import pytest

from app.agent_layer.orchestration.tool_loop import (
    ToolCall,
    ToolLoopEvent,
    ToolLoopResult,
    ToolRegistry,
    ToolResult,
    execute_tool_loop,
)
from app.agent_layer.runtime.chat_model import ChatResponse, ToolCallInfo


def _make_mock_chat_model(responses: list[ChatResponse]):
    """构造 mock ChatModel，按顺序返回 responses"""
    from unittest.mock import AsyncMock

    model = AsyncMock()
    model.chat_with_tools = AsyncMock(side_effect=responses)
    return model


# ── ToolRegistry ──────────────────────────────────────────────────


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        async def my_tool(args): return "ok"
        reg.register("t1", my_tool)
        assert reg.has("t1")
        assert reg.get("t1") is my_tool

    def test_get_missing(self):
        reg = ToolRegistry()
        assert reg.get("nope") is None
        assert not reg.has("nope")

    def test_tool_names(self):
        reg = ToolRegistry()
        async def a(args): return None
        async def b(args): return None
        reg.register("a", a)
        reg.register("b", b)
        assert set(reg.tool_names) == {"a", "b"}

    def test_tool_schemas(self):
        reg = ToolRegistry()
        async def a(args): return None
        schema = {"type": "function", "function": {"name": "a"}}
        reg.register("a", a, schema=schema)
        assert reg.tool_schemas() == [schema]


# ── ToolLoopEvent ─────────────────────────────────────────────────


class TestToolLoopEvent:
    def test_sse_frame(self):
        event = ToolLoopEvent(round=1, tool_name="search", status="calling")
        frame = event.to_sse_frame()
        assert "event: tool_round" in frame
        data = json.loads(frame.split("data: ")[1].split("\n")[0])
        assert data["round"] == 1
        assert data["tool_name"] == "search"


# ── execute_tool_loop ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tool_loop_no_call():
    """LLM 不调用工具，直接结束"""
    model = _make_mock_chat_model([ChatResponse(content="直接回复")])
    result = await execute_tool_loop(model, [{"role": "user", "content": "hi"}], ToolRegistry())
    assert result.rounds_used == 0
    assert result.tool_calls == []
    assert not result.hit_max_rounds


@pytest.mark.asyncio
async def test_tool_loop_single_call():
    """单轮工具调用后 LLM 结束"""
    reg = ToolRegistry()
    async def search(args):
        return {"results": [args.get("query", "")]}
    reg.register("search", search, schema={"type": "function", "function": {"name": "search"}})

    model = _make_mock_chat_model([
        ChatResponse(tool_calls=[ToolCallInfo(id="tc1", name="search", arguments='{"query": "RAG"}')]),
        ChatResponse(content="完成"),
    ])

    result = await execute_tool_loop(model, [{"role": "user", "content": "搜索 RAG"}], reg)
    assert result.rounds_used == 1
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search"
    assert result.tool_results[0].success
    assert not result.hit_max_rounds


@pytest.mark.asyncio
async def test_tool_loop_max_rounds():
    """超过 5 轮硬上限强制停止"""
    reg = ToolRegistry()
    async def noop(args):
        return "ok"
    reg.register("noop", noop)

    always_call = ChatResponse(tool_calls=[ToolCallInfo(id="tc", name="noop", arguments='{}')])
    model = _make_mock_chat_model([always_call] * 6)

    result = await execute_tool_loop(model, [], reg, max_rounds=5)
    assert result.rounds_used == 5
    assert result.hit_max_rounds
    assert len(result.tool_results) == 5
    assert result.tool_results[-1].error == "max rounds reached"


@pytest.mark.asyncio
async def test_tool_loop_tool_not_found():
    """工具不存在时记录错误但继续循环"""
    reg = ToolRegistry()

    model = _make_mock_chat_model([
        ChatResponse(tool_calls=[ToolCallInfo(id="tc1", name="ghost", arguments='{}')]),
        ChatResponse(content="继续"),
    ])

    result = await execute_tool_loop(model, [], reg)
    assert result.rounds_used == 1
    assert not result.tool_results[0].success
    assert "not found" in result.tool_results[0].error


@pytest.mark.asyncio
async def test_tool_loop_tool_exception():
    """工具执行异常时记录错误并继续"""
    reg = ToolRegistry()
    async def fail(args):
        raise ValueError("boom")
    reg.register("fail", fail)

    model = _make_mock_chat_model([
        ChatResponse(tool_calls=[ToolCallInfo(id="tc1", name="fail", arguments='{}')]),
        ChatResponse(content="继续"),
    ])

    result = await execute_tool_loop(model, [], reg)
    assert result.rounds_used == 1
    assert not result.tool_results[0].success
    assert "boom" in result.tool_results[0].error


@pytest.mark.asyncio
async def test_tool_loop_multi_round():
    """多轮工具调用：search → summarize → done"""
    reg = ToolRegistry()
    async def search(args):
        return {"docs": ["doc1", "doc2"]}
    async def summarize(args):
        return {"summary": "这是摘要"}
    reg.register("search", search)
    reg.register("summarize", summarize)

    model = _make_mock_chat_model([
        ChatResponse(tool_calls=[ToolCallInfo(id="tc1", name="search", arguments='{"q": "test"}')]),
        ChatResponse(tool_calls=[ToolCallInfo(id="tc2", name="summarize", arguments='{"text": "docs"}')]),
        ChatResponse(content="完成"),
    ])

    result = await execute_tool_loop(model, [], reg)
    assert result.rounds_used == 2
    assert len(result.tool_calls) == 2
    assert result.tool_calls[0].name == "search"
    assert result.tool_calls[1].name == "summarize"
    assert all(r.success for r in result.tool_results)


@pytest.mark.asyncio
async def test_tool_loop_messages_grow():
    """每次工具调用后 messages 列表增长"""
    reg = ToolRegistry()
    async def echo(args):
        return args
    reg.register("echo", echo)

    model = _make_mock_chat_model([
        ChatResponse(tool_calls=[ToolCallInfo(id="tc1", name="echo", arguments='{"n": 1}')]),
        ChatResponse(tool_calls=[ToolCallInfo(id="tc2", name="echo", arguments='{"n": 2}')]),
        ChatResponse(content="done"),
    ])

    initial = [{"role": "user", "content": "hi"}]
    result = await execute_tool_loop(model, initial, reg)
    # 初始 1 条 → assistant(tool_calls) + tool → assistant(tool_calls) + tool → assistant(content)
    assert result.rounds_used == 2


@pytest.mark.asyncio
async def test_tool_loop_custom_max_rounds():
    """自定义 max_rounds=2"""
    reg = ToolRegistry()
    async def noop(args):
        return "ok"
    reg.register("noop", noop)

    always_call = ChatResponse(tool_calls=[ToolCallInfo(id="tc", name="noop", arguments='{}')])
    model = _make_mock_chat_model([always_call] * 3)

    result = await execute_tool_loop(model, [], reg, max_rounds=2)
    assert result.rounds_used == 2
    assert result.hit_max_rounds
