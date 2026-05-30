"""TurnRunner 参数分组 dataclass"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.agent_layer.runtime.chat_model import ChatModel
    from app.agent_layer.session.editor_context_store import EditorContextStore
    from app.agent_layer.session.persistence import SessionPersistence
    from app.agent_layer.session.window_store import ConversationWindowStore
    from app.data_layer.indexing.chroma_store.keyword_index import KeywordIndex
    from app.data_layer.indexing.chroma_store.vector_index import VectorIndex
    from app.data_layer.indexing.embedding.embedding_client import EmbeddingClient


class VectorStoreProto(Protocol):
    def query(self, vector: list[float], topk: int, paper_ids: list[str] | None = None) -> list: ...


class KeywordSearchProto(Protocol):
    def query(self, query_text: str, topk: int, paper_ids: list[str] | None = None) -> list: ...


class EmbeddingClientProto(Protocol):
    async def embed_single(self, text: str) -> list[float]: ...


@dataclass
class RetrievalServices:
    """检索相关依赖"""
    vector_store: VectorStoreProto | None = None
    keyword_search: KeywordSearchProto | None = None
    embedding_client: EmbeddingClientProto | None = None


@dataclass
class SessionServices:
    """会话相关依赖"""
    window_store: ConversationWindowStore
    editor_context_store: EditorContextStore
    persistence: SessionPersistence


@dataclass
class TurnConfig:
    """Turn 执行配置"""
    cache_mode: str = "memory"
    reflection_model: ChatModel | None = None
