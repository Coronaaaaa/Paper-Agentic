"""Tool call 循环：多轮工具调用编排，硬上限 5 轮防无限循环"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.agent_layer.runtime.chat_model import ChatModel, ChatResponse

logger = logging.getLogger("paper-assistant")

_MAX_TOOL_ROUNDS = 5


class ToolLoopEvent(BaseModel):
    """SSE 事件：工具调用轮次"""
    event: str = "tool_round"
    round: int
    tool_name: str
    status: str  # "calling" | "success" | "error" | "max_rounds"

    def to_sse_frame(self) -> str:
        payload = {
            "round": self.round,
            "tool_name": self.tool_name,
            "status": self.status,
        }
        return f"event: tool_round\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    success: bool
    data: str | dict | list | None = None
    error: str = ""


@dataclass
class ToolLoopResult:
    final_output: str
    rounds_used: int
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    hit_max_rounds: bool = False


# 工具函数签名：接收参数字典，返回任意结果
ToolFunc = Callable[[dict[str, Any]], Coroutine[Any, Any, str | dict | list | None]]


class ToolRegistry:
    """工具注册表：名称 → 可调用函数 + schema"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolFunc] = {}
        self._schemas: dict[str, dict] = {}

    def register(self, name: str, func: ToolFunc, schema: dict | None = None) -> None:
        self._tools[name] = func
        if schema:
            self._schemas[name] = schema

    def get(self, name: str) -> ToolFunc | None:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def tool_schemas(self) -> list[dict]:
        return list(self._schemas.values())


async def execute_tool_loop(
    chat_model: ChatModel,
    initial_messages: list[dict],
    registry: ToolRegistry,
    max_rounds: int = _MAX_TOOL_ROUNDS,
) -> ToolLoopResult:
    """执行多轮工具调用循环。

    使用标准 OpenAI ToolCalling API：
    1. 发送消息 + tools schema 给 LLM
    2. 如果 LLM 返回 tool_calls，执行对应工具
    3. 将工具结果追加到消息列表，继续循环
    4. 如果 LLM 不返回 tool_calls（直接回复），结束循环

    Args:
        chat_model: LLM 客户端
        initial_messages: 初始消息列表
        registry: 工具注册表
        max_rounds: 最大轮次（默认 5，硬上限）

    Returns:
        ToolLoopResult 包含最终输出、轮次、调用历史
    """
    messages = list(initial_messages)
    tool_calls: list[ToolCall] = []
    tool_results: list[ToolResult] = []
    rounds_used = 0
    hit_max = False
    schemas = registry.tool_schemas()

    for round_num in range(1, max_rounds + 1):
        response: ChatResponse = await chat_model.chat_with_tools(
            messages, tools=schemas if schemas else None,
        )

        if not response.tool_calls:
            # LLM 直接回复，不调用工具 → 结束循环
            if response.content:
                messages.append({"role": "assistant", "content": response.content})
            break

        rounds_used = round_num

        if round_num == max_rounds:
            hit_max = True
            logger.warning("Tool loop hit max rounds (%d), forcing stop", max_rounds)
            for tc in response.tool_calls:
                tool_results.append(ToolResult(
                    tool_name=tc.name,
                    success=False,
                    error="max rounds reached",
                ))
            break

        # 追加 assistant 消息（含 tool_calls）
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if response.content:
            assistant_msg["content"] = response.content
        else:
            assistant_msg["content"] = None
        assistant_msg["tool_calls"] = [
            {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments}}
            for tc in response.tool_calls
        ]
        messages.append(assistant_msg)

        # 执行每个 tool call
        for tc_info in response.tool_calls:
            call = ToolCall(name=tc_info.name, arguments=json.loads(tc_info.arguments) if tc_info.arguments else {})
            tool_calls.append(call)

            func = registry.get(tc_info.name)
            if func is None:
                logger.warning("Tool '%s' not found in registry", tc_info.name)
                tool_results.append(ToolResult(
                    tool_name=tc_info.name,
                    success=False,
                    error=f"tool '{tc_info.name}' not found",
                ))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_info.id,
                    "content": json.dumps({"error": f"tool '{tc_info.name}' not found"}, ensure_ascii=False),
                })
                continue

            try:
                result = await func(call.arguments)
                tool_results.append(ToolResult(
                    tool_name=tc_info.name,
                    success=True,
                    data=result,
                ))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_info.id,
                    "content": json.dumps(
                        {"tool": tc_info.name, "result": result},
                        ensure_ascii=False,
                        default=str,
                    ),
                })
                logger.info("Tool '%s' executed successfully (round %d)", tc_info.name, round_num)
            except Exception as exc:
                logger.warning("Tool '%s' failed: %s", tc_info.name, exc)
                tool_results.append(ToolResult(
                    tool_name=tc_info.name,
                    success=False,
                    error=str(exc),
                ))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_info.id,
                    "content": json.dumps(
                        {"tool": tc_info.name, "error": str(exc)},
                        ensure_ascii=False,
                    ),
                })

    final_output = messages[-1].get("content", "") if messages else ""

    return ToolLoopResult(
        final_output=final_output,
        rounds_used=rounds_used,
        tool_calls=tool_calls,
        tool_results=tool_results,
        hit_max_rounds=hit_max,
    )
