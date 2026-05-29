# session_memory_runtime 模块测试设计

## 目标

- 验证窗口、编辑器上下文、摘要持久化、freeze / compact 在内存态下的协作。

## 用例

1. `SES-U01`：`ConversationWindowStore.add_message()` 后能读回消息列表，`clear()` 能清空指定 session。
2. `SES-U02`：`EditorContextStore.put()` 后能读回完整上下文对象，`freeze()` / `get_frozen()` 能返回冻结副本。
3. `SES-U03`：`SessionPersistence.save_message()` 和 `save_summary()` 都能按 session 隔离保存。
4. `SES-C01`：compact 触发后，摘要要写入 persistence，旧 window 要清理，下一轮消息组装要能读到摘要。

## ClaudeCode 执行要求

- 测试文件建议：
  - `backend/test_backend/agent_layer/unit/session/test_window_store.py`
  - `backend/test_backend/agent_layer/unit/session/test_editor_context.py`
  - `backend/test_backend/agent_layer/unit/session/test_persistence.py`
  - `backend/test_backend/agent_layer/unit/orchestration/test_turn_runner.py`
- 不再引入外部缓存 fixture 或 fake cache。
