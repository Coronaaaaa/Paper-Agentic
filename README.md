# 论文助手

基于 RAG 的学术写作助手，当前以 WPS 插件形态运行。

## 架构

```text
┌─────────────┐    HTTP/SSE    ┌─────────────────┐
│  Vue 3 前端  │ ◄────────────► │  FastAPI 后端    │
│  (WPS 插件)  │                │                 │
└─────────────┘                ├─────────────────┤
                               │ service_layer   │  ← API 路由 / DI / 配置 / 监控
                               │ agent_layer     │  ← LLM 编排 / 检索 / 流式生成
                               │ data_layer      │  ← PDF 解析 / 向量库 / BM25
                               └─────────────────┘
```

**文档导入链路**：
```text
PDF 上传 → MinerU 精准解析 → VLM 图片语义（并行）→ 清洗 → 语义切分 → Embedding → Chroma + BM25
```

**RAG 问答链路**：
```text
用户提问 → 三源加权冻结 → 检索决策 → Dense + BM25 → RRF 融合 → TokenBudget 动态裁剪 → LLM 流式生成 → 引用标注 → SSE 返回
```

## 目录结构

```text
论文助手/
├── backend/                              # FastAPI 后端
│   ├── app/
│   │   ├── data_layer/                   # 数据层
│   │   │   ├── preprocessing/
│   │   │   │   ├── mineru_processing/    #   MinerU PDF 解析（唯一处理器）
│   │   │   │   │   ├── mineru_client.py  #     编排器：重试 + Key 轮转 + 进度
│   │   │   │   │   ├── api_client.py     #     原始 HTTP 调用
│   │   │   │   │   ├── pdf_splitter.py   #     PDF 拆分工具
│   │   │   │   │   ├── pdf_converter.py  #     转换入口
│   │   │   │   │   ├── key_pool.py       #     API Key 池（预留）
│   │   │   │   │   └── result_types.py   #     数据类
│   │   │   │   ├── chunking/             #   语义切分
│   │   │   │   ├── cleaning/             #   Markdown 清洗
│   │   │   │   ├── vlm_understanding/    #   VLM 图片理解
│   │   │   │   ├── transfer/             #   Pipeline 编排
│   │   │   │   └── monitor/              #   Pipeline 监控
│   │   │   ├── indexing/                 #   索引（ChromaDB + BM25）
│   │   │   │   ├── chroma_store/         #     向量库 + 关键词索引 + 软删除
│   │   │   │   └── embedding/            #     Embedding 客户端
│   │   │   ├── retrieval/                #   检索
│   │   │   │   ├── dense/                #     向量检索
│   │   │   │   ├── sparse/               #     BM25 关键词检索
│   │   │   │   └── fusion/               #     RRF 融合
│   │   │   └── storage/                  #   持久化
│   │   │       ├── sqlite_runtime/       #     SQLite（元数据 / 导入任务 / 会话）
│   │   │       ├── file_management/      #     文件与产物目录管理
│   │   │       └── monitor/              #     存储监控
│   │   ├── agent_layer/                  # Agent 层
│   │   │   ├── orchestration/            #   编排（turn_runner + tool_loop）
│   │   │   ├── planning/                 #   规划（input_assembler + snapshot_builder）
│   │   │   ├── response/                 #   回答（block_streamer + citation_resolver）
│   │   │   ├── runtime/                  #   运行时（chat_model + token_budget）
│   │   │   ├── session/                  #   会话（window_store + persistence）
│   │   │   ├── hooks/                    #   钩子（compact + reflection）
│   │   │   └── contracts/                #   数据契约
│   │   └── service_layer/                # 服务层
│   │       ├── api/                      #   API 路由（含 /config/env 配置热更新）
│   │       ├── bootstrap/                #   启动（container + import_monitor）
│   │       ├── config/                   #   BackendSettings
│   │       ├── schemas/                  #   Pydantic schemas
│   │       └── sse/                      #   SSE 编码
│   ├── tests/                            # 测试（按 layer 组织）
│   ├── data/                             # 运行态数据
│   ├── main.py                           # 入口
│   └── pyproject.toml
├── frontend/                             # Vue 3 + TypeScript + WPS 插件壳
├── docs/                                 # 文档与决策记录
├── datasets/                             # 测试样本（不入版本控制）
└── log/                                  # 运行日志（不入版本控制）
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

参见 `backend/.env.example`，所有配置通过 `BackendSettings` 管理。

核心配置：

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` | LLM 服务 |
| `LLM_CONTEXT_WINDOW` | LLM 上下文长度（0 = 自动发现） |
| `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` | Embedding 服务 |
| `EMBEDDING_CONTEXT_WINDOW` | Embedding 上下文长度 |
| `MINERU_API_KEY` | MinerU PDF 解析（多 Key 逗号分隔，预留） |
| `VLM_API_KEY` / `VLM_BASE_URL` | VLM 图片理解 |
| `RETRIEVAL_TOPK_DENSE` / `RETRIEVAL_TOPK_SPARSE` | 检索候选数 |
| `RETRIEVAL_RRF_K` | RRF 融合常数 |
| `CONTEXT_WINDOW_TOKENS` / `MAX_OUTPUT_TOKENS` | 会话窗口 |

> 运行态缓存使用进程内内存，无需外部服务。

## 测试

```bash
cd backend

# 单元测试
uv run pytest tests/agent_layer/unit tests/data_layer/unit tests/service_layer/unit -v

# 集成测试（需真实 API key）
uv run pytest tests/data_layer/integration -v -s

# 全部测试
uv run pytest tests/ -v
```

## API 接口

主要端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET/POST | `/api/v1/config/env` | 配置读取/更新 |
| POST | `/api/v1/import/start` | 上传导入 |
| GET | `/api/v1/import/stream/{id}` | 导入进度（SSE） |
| GET | `/api/v1/import/artifacts/{id}` | 导入中间产物查询 |
| POST | `/api/v1/query` | Agent 查询（SSE 流式） |
| POST | `/api/v1/conversations/chat` | 对话（SSE 流式） |
| GET | `/api/v1/papers` | 论文列表 |
| GET | `/api/v1/library/items` | 文献库列表 |
| POST | `/api/v1/models` | 模型发现 |

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + TypeScript + Vite + WPS JS SDK |
| 后端 | FastAPI + Pydantic + asyncio |
| LLM | OpenAI 兼容 API（provider-neutral） |
| Embedding | 可配置（通过 BackendSettings） |
| 向量库 | ChromaDB (SQLite) |
| 关键词 | BM25 + jieba |
| PDF 解析 | MinerU API（唯一处理器） |
| 存储 | SQLite（对话/文献/任务） |
| 缓存 | 进程内内存 |
