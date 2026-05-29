# assistant_context_api 模块审计

## 对照模块

- 代码：`backend/app/service_layer/api/assistant_routes.py`
- 相关存储：`backend/app/agent_layer/session/editor_context_store.py`

## 结论

- `written_context / selection` 已经写入进程内内存单例，并会在 `query` 的 snapshot freeze 阶段被消费。

## 发现

- `PUT /assistant/written-context` 和 `PUT /assistant/selection` 现在是覆盖同一份内存快照，写入后可被后续 query 读取。

- 两个 GET 现在都会返回完整的 `ContextState`，包含 `written_context` 和 `selection`。

- `/api/v1/query` 与 `/api/v1/conversations/chat` 现在共享同一个 `TurnRunner`，并在 `_freeze_snapshot` 阶段读取 editor context。

- 该接口不再需要外部缓存降级分支，前端和日志层看到的是稳定的内存态。

## 建议

1. 如果后续需要统一读取对象，可以再补 `GET /assistant/context/{session_id}`。
2. editor context 存储对象至少带：
   - `session_id`
   - `written_context`
   - `selection`
   - `updated_at`
   - `snapshot_version`
3. `/api/v1/query` 继续在 snapshot freeze 阶段统一读取 editor context。
