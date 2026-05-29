# 论文助手

基于 RAG 的学术写作助手，当前以 WPS 插件形态运行。

## 架构

```text
┌─────────────┐    HTTP/SSE    ┌─────────────────┐
│  Vue 3 前端  │ ◄────────────► │  FastAPI 后端    │
│  (WPS 插件)  │                │                 │
└─────────────┘                ├─────────────────┤
                               │ service_layer   │  ← API 路由 / DI / 配置
                               │ agent_layer     │  ← LLM 编排 / 检索 / 流式生成
                               │ data_layer      │  ← PDF 解析 / 向量库 / BM25
                               └─────────────────┘
```

**主链**:
```text
PDF 上传 → MinerU 解析 → VLM 图片描述 → 清洗 → 语义切块 → Embedding → Chroma + BM25

用户提问 → Query 改写 → Dense + BM25 融合检索 → LLM 流式生成 → 引用标注 → 返回前端
```

## 目录结构

```text
论文助手/
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── data_layer/               # 数据层：文档预处理 / 向量化 / 检索 / 存储
│   │   │   ├── contracts/            #   数据契约（LibraryItem, Conversation, Errors）
│   │   │   ├── preprocessing/        #   预处理
│   │   │   │   ├── transfer/         #     调度中枢（PipelineOrchestrator）
│   │   │   │   ├── transformation/   #     MinerU 解析（PDF/DOCX → Markdown + JSON + images）
│   │   │   │   ├── cleaning/         #     清洗（格式规范化、去噪）
│   │   │   │   ├── vlm_understanding/ #    VLM 图片语义理解
│   │   │   │   ├── chunking/         #     语义切分 + 锚点生成
│   │   │   │   └── monitor/          #     进度监控
│   │   │   ├── indexing/             #   索引
│   │   │   │   ├── embedding/        #     向量化（远程 API）
│   │   │   │   └── chroma_store/     #     向量库（增删改查 + 软删除）
│   │   │   ├── retrieval/            #   检索
│   │   │   │   ├── dense/            #     向量检索
│   │   │   │   ├── sparse/           #     BM25 关键词检索
│   │   │   │   └── fusion/           #     RRF 融合
│   │   │   └── storage/              #   持久化
│   │   │       ├── file_management/  #     文件与产物目录管理
│   │   │       ├── sqlite_runtime/   #     SQLite（元数据 / 导入任务 / 会话）
│   │   │       ├── config/           #     数据层配置
│   │   │       └── monitor/          #     存储监控
│   │   ├── agent_layer/              # Agent 层：LLM 编排 / 检索决策 / 流式生成
│   │   │   ├── contracts/            #   数据契约（AskRequest, ContentBlock, SourceCard, SSE 事件）
│   │   │   ├── orchestration/        #   编排
│   │   │   │   ├── turn_runner.py    #     单轮请求主编排器
│   │   │   │   └── tool_loop.py      #     内部工具调用循环
│   │   │   ├── planning/             #   规划
│   │   │   │   ├── snapshot_builder.py  # 冻结输入快照 + 权重计算
│   │   │   │   ├── retrieval_gate.py #     检索决策（是否需要 RAG）
│   │   │   │   └── input_assembler.py #   查询组装
│   │   │   ├── response/             #   回答生成
│   │   │   │   ├── block_streamer.py #     ContentBlock 流式输出
│   │   │   │   ├── citation_resolver.py # 引用解析
│   │   │   │   └── source_mapper.py  #     来源映射
│   │   │   ├── session/              #   会话管理
│   │   │   │   ├── persistence.py    #     消息持久化
│   │   │   │   ├── window_store.py   #     活动窗口
│   │   │   │   └── editor_context_store.py # 编辑器上下文
│   │   │   ├── hooks/                #   钩子
│   │   │   │   ├── compact.py        #     上下文压缩
│   │   │   │   └── reflection.py     #     证据反思判定
│   │   │   └── runtime/              #   运行时
│   │   │       ├── chat_model.py     #     LLM 调用封装
│   │   │       └── token_budget.py   #     Token 预算管理
│   │   └── service_layer/            # 服务层：API / SSE / 配置 / 启动
│   │       ├── api/                  #   FastAPI 路由（health/library/import/papers/conversation/assistant/query/model）
│   │       ├── schemas/              #   请求/响应 schema
│   │       ├── sse/                  #   SSE 事件编码 + 导入进度总线
│   │       ├── config/               #   BackendSettings
│   │       └── bootstrap/            #   App Factory / DI Container / Lifespan / Logging
│   ├── tests/                        # 测试（unit / integration / e2e / soak）
│   ├── main.py                       # 入口
│   └── pyproject.toml
├── frontend/                         # Vue 3 + TypeScript + WPS 插件壳
│   ├── src/
│   └── vite.config.ts
├── docs/                             # 文档与决策记录
│   └── backend/
│       ├── architecture.md           #   后端总纲（活动真相源）
│       ├── agent_layer_doc/          #   Agent 层设计
│       ├── data_layer_doc/           #   数据层设计
│       ├── server_layer_doc/         #   API 接口文档
│       └── 代办/                     #   偏差清单 + 已锁定决策
├── datasets/                         # 测试样本（不入版本控制）
├── log/                              # 运行日志（不入版本控制）
└── archives/                         # 历史版本归档
```

## 快速开始

### 环境要求

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Node.js 18+ / pnpm

### 1. 启动后端

```bash
cd backend
uv sync
cp .env.example .env
# 编辑 .env 填入 API key
uv run python main.py
```

后端运行在 `http://127.0.0.1:8000`。Swagger 文档: `http://127.0.0.1:8000/docs`

### 2. 构建前端

```bash
cd frontend
pnpm install
pnpm build
cd dist
npx wpsjs debug
```

### 3. 环境变量

参见 `backend/.env.example`，核心配置：

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | LLM 服务配置 |
| `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL` | Embedding 服务 |
| `EMBEDDING_DIMENSIONS` | Embedding 维度（默认 1536） |
| `MINERU_API_KEY` | MinerU PDF 解析 API |
| `VLM_API_KEY` / `VLM_BASE_URL` | VLM 图片理解 |
| `REFLECTION_API_KEY` / `REFLECTION_MODEL` | 反思模型（可选，不配则用主模型） |

> 运行态缓存默认使用进程内内存，无需外部服务。

## 测试

```bash
cd backend

# 单元测试（每次提交）
uv run pytest test_backend/agent_layer/unit test_backend/data_layer/unit test_backend/service_layer/unit -v

# 集成测试（需真实 API key）
uv run pytest test_backend/data_layer/integration -v -s

# 全部后端测试
uv run pytest test_backend/ -v
```

测试按 layer 组织：`backend/test_backend/{layer}/{unit,integration,e2e,soak}/`。
前后端联调测试在根目录 `tests/`。

## 实验记录

实验数据与对比结果见 [LabRepo.md](LabRepo.md)。

## API 接口

详见 [API 接口文档](docs/backend/server_layer_doc/API接口文档.md)。

主要端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/papers` | 论文列表 |
| POST | `/api/v1/import/start` | 上传导入（multipart/form-data） |
| GET | `/api/v1/import/stream/{id}` | 导入进度（SSE） |
| POST | `/api/v1/query` | Agent 查询（SSE 流式） |
| POST | `/api/v1/conversations/chat` | 对话（SSE 流式） |
| GET | `/api/v1/library/items` | 文献库列表 |
| PUT | `/api/v1/assistant/selection` | 更新选中文本 |
| PUT | `/api/v1/assistant/written-context` | 更新已写内容 |
| POST | `/api/v1/models` | 模型发现 |

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + TypeScript + Vite + WPS JS SDK |
| 后端 | FastAPI + Pydantic + asyncio |
| LLM | OpenAI 兼容 API（Kimi / LiteLLM） |
| Embedding | 硅基流动 Qwen3-Embedding-4B (1536 维) |
| 向量库 | ChromaDB (SQLite) |
| 关键词 | BM25 + jieba |
| PDF 解析 | MinerU API（远程） |
| 存储 | SQLite（对话/文献/任务） |
| 缓存 | 进程内内存 |
