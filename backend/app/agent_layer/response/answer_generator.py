"""回答生成器（仅负责回答，不做检索）"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from app.agent_layer.planning.input_assembler import build_source_label, truncate_snippet
from app.agent_layer.runtime.chat_model import ChatModel
from app.data_layer.contracts.conversation import ConversationMessage

logger = logging.getLogger("paper-assistant")

_SYSTEM_PROMPT = """你是一个有帮助的助手。请用中文回答用户的问题。

你必须基于提供的资料回答。
- 只在有证据时下结论，不要编造来源
- 回答中引用证据时，使用方括号编号，如 [1]、[2]
- 同一个段落可引用多个来源，如 [1][3]
- 编号必须对应提供给你的来源顺序
- 优先把结论写清楚，再用编号引用支撑，不要输出文件 hash 或内部 ID

{context}
"""


class AnswerGenerator:
    def __init__(
        self,
        chat_model: ChatModel,
        conversation_repo: object,
    ):
        self._chat_model = chat_model
        self._conversation_repo = conversation_repo

    async def generate(
        self,
        session_id: str,
        query_text: str,
        context: str,
        sources: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """流式回答，yield SSE 事件

        Args:
            session_id: 会话 ID
            query_text: 用户查询文本
            context: 预构建的检索上下文（由调用方负责检索和组装）
            sources: 预构建的来源列表（可选）
        """
        if not query_text:
            yield {"event": "error", "data": {"message": "请提供问题或内容"}}
            return

        if not context:
            yield {
                "event": "metadata",
                "data": {"session_id": session_id, "source_count": 0, "sources": []},
            }
            yield {"event": "chunk", "data": {"content": "未找到相关文献，无法基于文献内容回答该问题。请确认已导入相关文献，或尝试调整问题描述。"}}
            yield {"event": "done", "data": {}}
            return

        sources = sources or []

        # 构建消息
        system_msg = _SYSTEM_PROMPT.format(context=context)
        messages = [{"role": "system", "content": system_msg}]

        # 加载对话历史
        try:
            history = self._conversation_repo.get_messages(session_id, limit=20)
            for msg in history[-10:]:
                messages.append({"role": msg.role, "content": msg.content})
        except Exception:
            pass

        messages.append({"role": "user", "content": query_text})

        # 发送 metadata + 流式 chunk
        yield {
            "event": "metadata",
            "data": {
                "session_id": session_id,
                "source_count": len(sources),
                "sources": sources,
            },
        }

        full_response: list[str] = []
        try:
            async for chunk in self._chat_model.chat_stream(messages):
                full_response.append(chunk)
                yield {"event": "chunk", "data": {"content": chunk}}
        except Exception as e:
            logger.error("LLM 流式调用失败: %s", e)
            yield {"event": "error", "data": {"message": "LLM 服务暂时不可用"}}

        # 保存对话历史
        if full_response:
            from app.data_layer.contracts.library_item import utc_now_iso
            now = utc_now_iso()
            try:
                self._conversation_repo.save_message(
                    ConversationMessage(session_id=session_id, role="user", content=query_text, created_at=now)
                )
                self._conversation_repo.save_message(
                    ConversationMessage(session_id=session_id, role="assistant", content="".join(full_response), created_at=now)
                )
            except Exception as e:
                logger.warning("保存对话失败: %s", e)

        yield {"event": "done", "data": {}}

    async def generate_title(self, first_message: str) -> str:
        """根据首条用户消息生成简短对话标题"""
        from app.agent_layer.planning.input_assembler import sanitize_title
        prompt = (
            "请根据以下用户消息，生成一个简短的对话标题（5-12个汉字）。\n"
            "要求：只输出标题本身，不要解释，不要换行，不要加引号或标点。\n\n"
            f"用户消息：{first_message[:200]}\n\n标题："
        )
        fallback = first_message[:20]
        response = await self._chat_model.chat([{"role": "user", "content": prompt}])
        return sanitize_title(response, fallback)
