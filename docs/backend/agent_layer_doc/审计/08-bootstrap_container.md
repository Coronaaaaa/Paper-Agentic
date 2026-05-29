# bootstrap_container 模块审计

## 对照模块

- 代码：`backend/app/service_layer/bootstrap/container.py`

## 结论

- 当前容器层已经转成 AppContainer + 单例内存态，不再靠外部缓存兜底。

## 发现

- [P0] `AppContainer` 现在应一次性持有 `conversation_window`、`editor_context_store`、`session_persistence` 和缓存后的 `turn_runner`。
  - 证据：`container.py`

- [P1] 容器 health 现在应该暴露 `cache=memory`，而不是外部缓存状态。
  - 证据：`container.py`

- [P1] `turn_runner` 应该是缓存单例，避免每次请求重新装配共享内存态。
  - 证据：`container.py`

## 建议

1. 继续保持 `AppContainer` 只装配一次共享内存态。
2. 健康检查重点看 `cache=memory`、`query_route_ready` 和 `compact` 路径是否还能跑通。
3. 如果后续再扩 `assistant/context` 读接口，再由容器统一挂进去。
