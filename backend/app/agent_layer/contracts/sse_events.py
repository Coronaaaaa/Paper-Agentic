from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

from .content_block import ContentBlock
from .source_card import SourceCard


class ThinkingEvent(BaseModel):
    event: Literal["thinking"] = "thinking"
    text: str
    time_ms: int

    def to_sse_frame(self) -> str:
        payload = {"text": self.text, "time_ms": self.time_ms}
        return f"event: thinking\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class BlockEvent(BaseModel):
    event: Literal["block"] = "block"
    data: ContentBlock

    def to_sse_frame(self) -> str:
        from pydantic import TypeAdapter

        ta = TypeAdapter(ContentBlock)
        payload = ta.dump_json(self.data).decode()
        return f"event: block\ndata: {payload}\n\n"


class SourcesEvent(BaseModel):
    event: Literal["sources"] = "sources"
    data: list[SourceCard]

    def to_sse_frame(self) -> str:
        payload = json.dumps(
            [s.model_dump(exclude_none=True) for s in self.data],
            ensure_ascii=False,
        )
        return f"event: sources\ndata: {payload}\n\n"


class DoneEvent(BaseModel):
    event: Literal["done"] = "done"
    data: dict = {}

    def to_sse_frame(self) -> str:
        return f"event: done\ndata: {json.dumps(self.data)}\n\n"


class ErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    message: str

    def to_sse_frame(self) -> str:
        payload = {"message": self.message}
        return f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class ReflectionEvent(BaseModel):
    event: Literal["reflection"] = "reflection"
    round: int
    verdict: str
    reason: str

    def to_sse_frame(self) -> str:
        payload = {"round": self.round, "verdict": self.verdict, "reason": self.reason}
        return f"event: reflection\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class MetadataEvent(BaseModel):
    event: Literal["metadata"] = "metadata"
    request_id: str
    session_id: str
    used_inputs: dict
    context_tokens: int
    remaining_tokens: int
    remaining_ratio: float
    retrieval_planned: bool
    degraded_flags: list[str]
    cache_mode: str

    def to_sse_frame(self) -> str:
        payload = {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "used_inputs": self.used_inputs,
            "context_tokens": self.context_tokens,
            "remaining_tokens": self.remaining_tokens,
            "remaining_ratio": self.remaining_ratio,
            "retrieval_planned": self.retrieval_planned,
            "degraded_flags": self.degraded_flags,
            "cache_mode": self.cache_mode,
        }
        return f"event: metadata\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
