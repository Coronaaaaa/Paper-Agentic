# Claude 配置 - 论文助手项目

## 项目概况

**类型**: 学术写作助手（基于 RAG）
**阶段**: MVP（最小可行产品）
**架构**: 前后端分离 + 本地部署

## 快捷命令

### 四维度决策快照

```bash
# 基于代码事实解剖项目，产出验尸报告
/update-snapshot
```

### 日志系统（调试必用）

日志目录 `log/`（项目根目录），JSON Lines 格式：
| 文件 | 内容 |
|------|------|
| `app.log` | 全部后端运行日志（结构化 JSON Lines） |

**用户说"不成功"/"报错"/"失败了"时 → 先读日志再排查。**

---

## 核心理念：代码不会说谎，文档会

基于第一性原理：**代码是唯一的真实态，文档只是理想态的投影。** 文档的价值不在于描绘"设计应该是什么"，而在于记录"为什么这样选、踩过什么坑、什么还没做"。

**原则**：
- **代码是真相源**，文档是决策记录——两者矛盾时信代码
- **扩展点先写代码**，用 ` TODO` 标注，再同步文档
- **文档只记录"为什么"**：为什么选 A 不选 B，A 的代价是什么，什么条件下会失效
- **快照 ≠ 售前 PPT**，是验尸报告 + 体检报告：记录约束、腐化点、已知风险

**四维度认知模型**（快照必须覆盖）：

| 维度 | 关注点 | 缺失的后果 |
|------|--------|-----------|
| **静态结构** | 模块依赖方向（非分层方块）、API 调用矩阵 | 以为分层清晰，实际有循环依赖/跨层穿透 |
| **动态行为** | 关键路径时序、降级逻辑、状态机 | 以为流程是直线，实际满是分支和重试 |
| **物理部署** | 外部依赖拓扑、端口映射、配置差异 | 本地跑通 ≠ 部署可用（CORS、权限、网络） |
| **演进与债务** | Git 变更热力图、TODO/FIXME 密度、已知风险 | 高频变动文件 = Bug 巢穴，僵尸代码 = 隐藏地雷 |

---

## 技术栈

### 后端
- **框架**: FastAPI (Python 3.13)
- **LLM/VLM**: provider-neutral（通过 `BackendSettings` 统一配置，不硬编码）
- **向量库**: ChromaDB（纯 Python，SQLite 持久化）
- **关键词检索**: BM25 + jieba
- **Embedding**: 可配置（通过 `BackendSettings` 注入）
- **PDF 解析**: MinerU 精准解析 API（唯一处理器，不引入替代方案）
- **缓存**: 进程内内存（无外部缓存依赖）
- **配置管理**: 全部通过 `BackendSettings`（pydantic-settings），支持 `.env` 和 `/config/env` API 热更新

### 前端
- **框架**: Vue 3 + TypeScript
- **构建**: Vite
- **部署**: WPS 插件

---

## 目录结构

```
论文助手/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── data_layer/       # 数据层
│   │   │   ├── preprocessing/
│   │   │   │   ├── mineru_processing/  # MinerU PDF 解析（唯一处理器）
│   │   │   │   │   ├── mineru_client.py    # 编排器：重试 + Key 轮转 + 进度
│   │   │   │   │   ├── api_client.py       # 原始 HTTP 调用
│   │   │   │   │   ├── pdf_splitter.py     # PDF 拆分工具
│   │   │   │   │   ├── pdf_converter.py    # 转换入口（pipeline 调用这里）
│   │   │   │   │   ├── key_pool.py         # API Key 池（当前单 Key 直通）
│   │   │   │   │   └── result_types.py     # 数据类
│   │   │   │   ├── chunking/               # 语义切分
│   │   │   │   ├── cleaning/               # Markdown 清洗
│   │   │   │   ├── vlm_understanding/      # VLM 图片理解
│   │   │   │   ├── transfer/               # Pipeline 编排
│   │   │   │   └── monitor/                # Pipeline 监控
│   │   │   ├── indexing/                   # 索引（ChromaDB + BM25）
│   │   │   ├── retrieval/                  # 检索（Dense + Sparse + RRF 融合）
│   │   │   └── storage/                    # 存储（SQLite + 文件管理）
│   │   ├── agent_layer/      # Agent 层
│   │   │   ├── orchestration/              # 编排（turn_runner + tool_loop）
│   │   │   ├── planning/                   # 规划（input_assembler + snapshot_builder）
│   │   │   ├── response/                   # 回答（block_streamer + citation_resolver）
│   │   │   ├── runtime/                    # 运行时（chat_model + token_budget）
│   │   │   ├── session/                    # 会话（window_store + persistence）
│   │   │   ├── hooks/                      # 钩子（compact + reflection）
│   │   │   └── contracts/                  # 数据契约
│   │   └── service_layer/    # 服务层
│   │       ├── api/                        # API 路由
│   │       ├── bootstrap/                  # 启动（container + import_monitor）
│   │       ├── config/                     # 配置（BackendSettings）
│   │       ├── schemas/                    # Pydantic schemas
│   │       └── sse/                        # SSE 编码
│   ├── tests/                # 按 layer 组织
│   ├── data/                 # 运行态数据
│   ├── main.py               # 入口
│   └── pyproject.toml
├── frontend/                 # Vue 3 + TypeScript + WPS 插件壳
├── docs/                     # 文档与决策记录
├── datasets/                 # 测试样本（不入版本控制）
├── log/                      # 运行日志（不入版本控制）
└── archives/                 # 历史版本归档
```

---

## 数据流架构

### 文档导入流程

```
前端上传 PDF
    │
    ▼
import_routes.py: start_import()
    │  文件保存 + SHA-256 去重
    │  创建 ImportTask (SQLite)
    ▼
ImportMonitor.on_pipeline_event()  ←── 统一调度层
    │  ├── SSE bus → 用户实时进度
    │  ├── PipelineMonitor → 开发者指标
    │  └── get_artifacts() → 中间产物查询
    │
    ▼
PipelineOrchestrator.ingest_document()
    │
    ├─→ PipelineOrchestrator.run()
    │       │
    │       ├─→ [阶段1] MinerU 精准解析
    │       │     mineru_client.py (编排器)
    │       │       ├── key_pool.acquire() → 获取 API Key
    │       │       ├── api_client.request_upload_url() → POST /file-urls/batch
    │       │       ├── api_client.upload_file() → PUT 上传
    │       │       ├── api_client.poll_batch() → 轮询结果
    │       │       └── api_client.download_and_extract() → 下载 ZIP
    │       │     超限 PDF 自动切分 (pdf_splitter.py)
    │       │     失败重试：指数退避 + jitter（不换工具）
    │       │
    │       ├─→ [阶段2] VLM 图片理解（与清洗并行）
    │       │     vlm_understanding/vlm_processor.py
    │       │
    │       ├─→ [阶段3] Markdown 清洗
    │       │     cleaning/markdown_cleaner.py
    │       │
    │       ├─→ [阶段4] 语义切分
    │       │     chunking/semantic_chunker.py
    │       │     基于嵌入向量的语义边界检测
    │       │
    │       ├─→ [阶段5] Embedding 向量化
    │       │     embedding/embedding_client.py
    │       │     并发控制：Semaphore(max_concurrency)
    │       │
    │       └─→ [阶段6] 索引写入
    │             ChromaDB (向量) + BM25 (关键词)
    │
    └─→ 产物持久化
          ├── markdown.json (清洗后文本 + 元数据)
          ├── structured.json (chunks + anchors)
          └── extraction_report.json (pipeline 报告)
```

### RAG 问答流程

```
用户提问 (prompt + selection + written_context)
    │
    ▼
turn_runner.py: run()
    │
    ├─→ [1] 冻结快照 (snapshot_builder.py)
    │     三源输入加权：prompt/selection/written_context
    │     权重从 BackendSettings 读取（可配置）
    │
    ├─→ [2] 历史压缩判断 (compact.py)
    │     剩余空间 < 5% → 触发压缩
    │     LLM 总结 → 失败降级（保留最近 N 条，不丢失上下文）
    │     压缩结果通过 MetadataEvent.degraded_flags 通知前端
    │
    ├─→ [3] 检索决策 (retrieval_gate.py)
    │     判断是否需要 RAG 检索
    │
    ├─→ [4] 混合检索 (如果需要)
    │     │
    │     ├─→ Dense 检索 (vector_retriever.py)
    │     │     ChromaDB 向量相似度查询
    │     │     topk 从 settings 读取（默认 20）
    │     │
    │     ├─→ Sparse 检索 (keyword_retriever.py)
    │     │     BM25 关键词查询
    │     │     topk 从 settings 读取（默认 20）
    │     │
    │     └─→ RRF 融合 (rrf_fusion.py)
    │           Dense + Sparse 结果融合
    │           rrf_k 从 settings 读取（默认 60）
    │           返回全部候选（不预截断）
    │
    ├─→ [5] 上下文构建 (_build_context)
    │     TokenBudget 根据模型上下文动态裁剪
    │     context_window - max_output - system_prompt = 可用空间
    │     逐个 chunk 塞入，塞不下就停
    │
    ├─→ [6] Reflection 自检 (reflection.py)
    │     最多 N 轮（settings.reflection_max_rounds）
    │     证据不足 → 扩大检索范围
    │     方向偏离 → 切换查询（最多 M 次）
    │
    ├─→ [7] LLM 流式生成
    │     chat_model.chat_stream()
    │     支持模型轮转（429 自动切换 fallback）
    │     每个 chunk 推送 DeltaEvent 给前端
    │
    ├─→ [8] 引用解析 + 源码映射
    │     citation_resolver.py → 识别 [1][2] 引用
    │     source_mapper.py → 生成 SourceCard
    │
    ├─→ [9] 结构化输出 (block_streamer.py)
    │     Markdown → ContentBlock 序列
    │     paragraph / heading / list / table / code / citation
    │
    └─→ [10] SSE 返回
          MetadataEvent → ThinkingEvent → BlockEvent(s) → SourcesEvent → DoneEvent
```

### 导入监控数据流

```
PipelineOrchestrator._emit()
    │
    ▼
ImportMonitor.on_pipeline_event()  ←── 统一入口
    │
    ├──→ ImportProgressBus.publish() → SSE 推前端
    │     { status, step, percent, stage_name, message }
    │
    ├──→ PipelineMonitor.start_stage / complete_stage
    │     阶段耗时、成功率指标
    │
    └──→ StorageMonitor.record_latency
          embedding 延迟、存储健康
```

---

## 后端三层架构

后端分三层，每层职责明确、互不穿透：

| 层 | 核心职责 | 不负责什么 |
|---|---|---|
| **data_layer** | 文档预处理、MinerU 解析、清洗、切分、向量化、混合检索、原文锚点 | 不负责对话编排，不直接暴露 HTTP |
| **agent_layer** | 会话、输入加权、检索决策、reflection、回答生成、compact | 不直接处理底层文件解析，不直接承载 API 协议 |
| **service_layer** | API、SSE、配置、启动、健康检查、日志、依赖装配、导入监控 | 不承载业务推理，不直接写检索和总结策略 |

---

## 配置管理

**所有配置统一通过 `BackendSettings`（pydantic-settings）管理**，不硬编码。

配置来源（优先级从高到低）：
1. 环境变量
2. `.env` 文件
3. `BackendSettings` 默认值

配置更新方式：
- 修改 `.env` 文件 → 重启后端
- `POST /api/v1/config/env` → 写入 `.env` → 返回 `restart_required: true`

### 核心配置项

```env
# ── LLM ──
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
LLM_MAX_TOKENS=4096
LLM_CONTEXT_WINDOW=0          # 0 = 从 API 自动发现

# ── Embedding ──
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
EMBEDDING_DIMENSIONS=1536
EMBEDDING_CONTEXT_WINDOW=0    # 0 = 用 chunk_max_context

# ── MinerU ──
MINERU_API_KEY=               # 多 Key 用逗号分隔（预留）
MINERU_BASE_URL=https://mineru.net/api/v4
MINERU_POLL_INTERVAL=5
MINERU_TIMEOUT=300
MINERU_MAX_RETRIES=3
MINERU_MAX_PAGES_PER_CHUNK=180
MINERU_MAX_PER_KEY=2

# ── VLM ──
VLM_API_KEY=
VLM_BASE_URL=
VLM_MODEL=
VLM_MAX_TOKENS=1024
VLM_MAX_RETRIES=3

# ── 检索 ──
RETRIEVAL_TOPK_DENSE=20
RETRIEVAL_TOPK_SPARSE=20
RETRIEVAL_MAX_DISTANCE=2.0
RETRIEVAL_RRF_K=60

# ── 切分 ──
CHUNK_MAX_CONTEXT=32000
CHUNK_TARGET_SIZE=24000
CHUNK_OVERLAP_BUFFER=8000
CHUNK_MIN_TOKENS=128
CHUNK_MAX_TOKENS=512
CHUNK_OVERLAP_RATIO=0.10
CHUNK_SIMILARITY_THRESHOLD=0.3
CHUNK_EMBEDDING_WINDOW=3

# ── 会话 ──
CONTEXT_WINDOW_TOKENS=32000
MAX_OUTPUT_TOKENS=4096
COMPACT_MAX_SUMMARY_TOKENS=500
COMPACT_FALLBACK_KEEP_RECENT=6
COMPACT_TRIGGER_RATIO=0.05

# ── Reflection ──
REFLECTION_MAX_ROUNDS=3
REFLECTION_MAX_DIRECTION_SWITCHES=2

# ── 其他 ──
SOFT_DELETE_RETENTION_DAYS=7
AVG_MESSAGE_TOKENS=500
SYSTEM_PROMPT_TOKENS=2000
SOURCE_SNIPPET_MAX_LENGTH=220
TITLE_MAX_LENGTH=20
```

**配置约束**：
- 所有供应商信息通过 `BackendSettings` 注入，不在代码中硬编码
- 更换 Embedding 模型会导致向量库失效，需要重建索引
- 运行态缓存使用进程内内存，无需外部服务

---

## 检索动态计算

**检索 topk 不是固定值**，而是根据模型上下文动态计算：

```
模型上下文窗口 (context_window_tokens)
  - 最大输出 (max_output_tokens)
  - 系统提示 (system_prompt_tokens)
  = 可用空间

可用空间 / 平均 chunk 大小 = 实际能放入的 chunk 数
```

流程：
1. Dense + Sparse 各取 20 个候选（`retrieval_topk_dense/sparse`）
2. RRF 融合全部候选（不预截断）
3. `TokenBudget` 根据可用空间逐个塞入，塞不下就停

`TokenBudget` 在 `token_budget.py` 中实现，读取 `context_window_tokens` 和 `max_output_tokens`。

---

## 已知问题与限制

### 已修复
- [x] PDF 解析：从本地 PyMuPDF 改为 MinerU API（唯一处理器）
- [x] 向量库：从 zvec（RocksDB）改为 ChromaDB（SQLite），根治 Windows 锁问题
- [x] Redis 依赖：移除 Redis，运行态缓存改为进程内内存
- [x] 切分策略：实现基于嵌入向量的语义切分（非固定 token 切分）
- [x] 架构重构：从混合态迁移到三层结构（data_layer / agent_layer / service_layer）
- [x] SSE 协议：thinking/block/sources/done/error + StatusEvent + DeltaEvent
- [x] ContentBlock：结构化回答块（paragraph/heading/list/table/code/citation）
- [x] 输入加权：三种输入源冻结 + 权重可配置
- [x] RRF 融合：Dense + BM25 动态融合，topk 由 TokenBudget 裁剪
- [x] 配置统一：所有硬编码值迁移到 BackendSettings，支持 .env 和 API 配置
- [x] MinerU 重构：拆分为 mineru_processing/ 模块，支持多 Key 池（预留）
- [x] 导入监控：ImportMonitor 统一调度层（SSE + PipelineMonitor + StorageMonitor）
- [x] 压缩降级：compact 失败不丢失上下文，降级保留最近消息
- [x] 配置热更新 API：GET/POST /config/env

### 待完成
- [ ] MinerU 多 Key 轮转（等 3+ Key 时实现 key_pool.py）
- [ ] 用户自选文献功能（接口已预留）
- [ ] 多模态资源支持（视频、文档、笔记）
- [ ] 知识图谱集成
- [ ] Rerank 启用（当前未启用）

---

## 参考实现

- Novel_Agents RAG 工具: `D:/真项目/Novel_Agents/.tools/rag`
- z_ai-mcp-server: `D:/开发区/L2Demo/z_ai-mcp-server-0.1.3`
