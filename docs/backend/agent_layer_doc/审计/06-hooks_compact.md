# hooks_compact 模块审计

## 对照模块

- 代码：`backend/app/agent_layer/hooks/compact.py`
- 设计基线：`docs/backend/architecture.md` 第 6.1.8

## 结论

- 当前 `compact` 已经挂到 `TurnRunner` 主链上，不再只是一个独立函数。

## 发现

- [P1] 当前只有“给一串消息 -> 返回摘要”能力，没有触发条件、没有上下文预算、没有重注入逻辑。
  - 证据：`compact.py:12-34`

- [P1] 现在摘要会写入 `SessionPersistence`，并在 `_build_messages` 中作为历史摘要重注入。

- [P2] `compact` 结果会影响下一轮消息组装；如果后续要暴露给前端，再单独加观测事件。

## 建议

1. `compact` 不应独立漂浮，应挂到 `compact_check -> compacting` 状态。
2. 触发条件至少包含：
   - `context_tokens`
   - `remaining_tokens`
   - `remaining_ratio`
3. 摘要生成后要：
   - 保存到 `SessionPersistence`
   - 清理或截断进程内窗口
   - 进入下一轮上下文组装
