# bootstrap_container 模块测试设计

## 目标

- 验证容器装配、共享内存态和健康检查对 Agent 能力的表达。

## 用例

1. `BTS-U01`：`AppContainer` 必须一次性初始化共享内存态，不再每次请求重建。
2. `BTS-U02`：`AppContainer.initialize()` 必须完成 SQLite / 向量索引 / BM25 初始化，并暴露 `cache=memory`。
3. `BTS-U03`：health 输出必须包含 `cache / chroma / bm25 / llm_config / embedding_config`，且 `cache` 固定为 `memory`。
4. `BTS-I01`：当 LLM 不可用但 SQLite / 内存态可用时，整体 health 应为 `degraded`，不是直接 `error`。
5. `BTS-I02`：`AppContainer.turn_runner` 应该是缓存单例，重复读取不会重建共享内存态。

## ClaudeCode 执行要求

- 测试文件建议：
  - `backend/test_backend/service_layer/bootstrap/test_container.py`
  - `backend/test_backend/service_layer/bootstrap/test_health_agent_flags.py`
- `BTS-U01` 需要保留为回归用例，防止共享内存态再次被拆散。
