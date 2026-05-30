# 论文助手

学术写作助手（RAG），前后端分离 + 本地部署。

## 快捷命令

```bash
cd backend

# 启动
uv run python main.py

# 测试
uv run pytest test_backend/ -v

# Docker
docker compose up --build -d

# 日志
# log/app.log — JSON Lines，报错时先读这个
```

## 核心规则

### Git
- **禁止主动 commit**，用户说"提交"才提交
- commit message：`<类型>: <标题>` + 基于 diff 的事实摘要 + `---` + 用户原话

### 配置
- **全部通过 `BackendSettings`**，不硬编码
- `.env` 或 `POST /api/v1/config/env` 更新，改完重启生效
- MinerU 是唯一 PDF 处理器，不引入替代方案

### 架构约束
- 三层分离：data_layer / agent_layer / service_layer，不跨层调用
- 代码是真相源，文档是决策记录

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI + Python 3.13 |
| LLM/VLM | OpenAI 兼容 API（provider-neutral） |
| 向量库 | ChromaDB (SQLite) |
| 检索 | BM25 + Dense + RRF 融合（topk 由 TokenBudget 动态裁剪） |
| PDF | MinerU API（唯一处理器） |
| 配置 | BackendSettings + .env + /config/env API |
| 认证 | API Key（可选，空值 = 不启用） |
| 限流 | 内存滑动窗口（可选，默认不限） |
| 部署 | Docker + Docker Compose |
| CI | GitHub Actions（后端单元测试 + Docker 构建） |

## 详细文档

- **架构 + 数据流** → `docs/backend/architecture.md`
- **Agent 层** → `docs/backend/agent_layer_doc/`
- **数据层** → `docs/backend/data_layer_doc/`
- **API 接口** → `docs/backend/server_layer_doc/API接口文档.md`
- **配置清单** → `docs/backend/architecture.md` 或 `.env.example`
- **测试规范** → `backend/test_backend/README.md`
