# session_memory_runtime 模块审计

## 对照模块

- 代码：`backend/app/agent_layer/session/window_store.py`
- 代码：`backend/app/agent_layer/session/editor_context_store.py`
- 代码：`backend/app/agent_layer/session/persistence.py`

## 结论

- 进程内内存会话态已经是主实现，负责短期窗口、编辑器上下文和历史摘要。

## 发现

- [P1] `ConversationWindowStore`、`EditorContextStore`、`SessionPersistence` 现在各司其职，已经不再依赖外部缓存层。
- [P1] `compact` 需要同时完成三件事：
  - 保存 summary
  - 清理旧 live window
  - 让下一轮 `_build_messages` 读取 summary
- [P2] `EditorContextStore.freeze()` 的语义已经可用，应该在 `TurnRunner` 的 snapshot freeze 阶段直接使用。

## 建议

1. 把共享内存态视为唯一活动态。
2. compact 后只保留摘要和本轮交换，不要再回读旧 window。
3. 长期事实继续交给 SQLite，别把历史事实再塞回缓存层。
