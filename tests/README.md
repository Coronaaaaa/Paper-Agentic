# 前后端联调测试

本目录用于**前后端集成测试**，验证前端与后端的交互是否正确。

## 定位

| 目录 | 用途 |
|------|------|
| `backend/test_backend/` | 后端单元测试、集成测试 |
| `frontend/test_frontend/` | 前端单元测试、组件测试 |
| **`tests/`（本目录）** | 前后端联调 / E2E 测试 |

## 目录结构

```
tests/
├── e2e/              # 端到端测试（Playwright / Cypress）
├── api_contract/     # API 契约测试（前后端接口对齐）
├── fixtures/         # 共享测试数据
└── README.md
```

## 运行方式

```bash
# E2E 测试（需要前后端都启动）
# 前端：pnpm dev（端口 5173）
# 后端：uv run python main.py（端口 8000）

# API 契约测试
pytest tests/api_contract/ -v
```

## 注意事项

- 测试前确保前后端服务均已启动
- API 契约测试不依赖浏览器，只需后端运行
- E2E 测试需要完整环境（前后端 + 数据库）
