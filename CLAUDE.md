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
- **扩展点先写代码**，用 `🔮 未来扩展` 标注，再同步文档
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
- **LLM/VLM**: provider-neutral（通过环境变量配置，不硬编码供应商）
- **向量库**: ChromaDB（纯 Python，SQLite 持久化）
- **关键词检索**: BM25 + jieba
- **Embedding**: 可配置（默认通过 .env 指定 API 地址和模型）
- **PDF 解析**: MinerU 精准解析 API（PP-DocLayoutV2 + SLANet+），支持 PDF/DOCX/DOC/PPTX/XLSX
- **缓存**: 进程内内存（无外部缓存依赖）

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
│   │   ├── data_layer/       # 数据层（预处理 / 索引 / 检索 / 存储）
│   │   ├── agent_layer/      # Agent 层（编排 / 规划 / 回答 / 会话）
│   │   └── service_layer/    # 服务层（API / SSE / 配置 / 启动）
│   ├── tests/                # 按 layer 组织（agent_layer/unit, data_layer/unit, ...）
│   ├── data/                 # 运行态数据（chroma_db, bm25_index, papers, parsed, app.db）
│   ├── main.py               # 入口
│   └── pyproject.toml
├── frontend/                 # Vue 3 + TypeScript + WPS 插件壳
│   ├── src/
│   └── vite.config.ts
├── docs/                     # 文档与决策记录
│   └── backend/              #   活动文档（architecture.md + 三层子文档 + 待办）
├── datasets/                 # 测试样本（不入版本控制）
├── log/                      # 运行日志（不入版本控制）
└── archives/                 # 历史版本归档
```

详细目录树见 [README.md](README.md)。

---

## 开发规则

### 0. Git 提交规则（硬规则）

**禁止主动 commit**：除非用户明确说"提交"/"commit"，否则不创建任何 commit。

**提交格式**：用户发起 commit 时会附带自己的描述。commit message 结构如下：

```
<类型>: <简短标题>

<基于代码 diff 的事实摘要：改了哪些文件、改了什么，只记录事实，不记录推断>

---

"用户原话，一字不改"
```

**事实摘要规范**：
- 只记录从 `git diff` 中能直接读到的事实：哪些文件变了、函数签名改了、参数增删了、逻辑分支变了
- 禁止主观判断：不说"优化了"、"改进了"、"更好地"，只说"将 X 改为 Y"、"删除了 Z"
- 不推断动机：不说"为了支持 XXX"、"为了更好地 YYY"
- 用户的 message 是唯一允许的主观内容，必须原话保留，用 `---` 分隔后加双引号包裹
- 如果用户追问改动细节或技术问题，如实基于代码回答即可

### 1. 数据流架构（重要）

**文档导入流程**：
```
本地 PDF/DOCX → MinerU 精准解析 → Markdown + JSON + images → 清洗 → VLM 图片语义（并行）→ 语义切分 → Embedding → Chroma + BM25
```

**RAG 问答流程**：
```
用户提问 → 三源加权冻结（prompt/selection/written_context）→ 检索决策 → Dense + BM25 + RRF 融合 → LLM 流式生成 → 引用标注 → SSE 返回
```

### 2. 后端三层架构

后端分三层，每层职责明确、互不穿透：

| 层 | 核心职责 | 不负责什么 |
|---|---|---|
| **data_layer** | 文档预处理、清洗、结构化、向量化、混合检索、原文锚点 | 不负责对话编排，不直接暴露 HTTP |
| **agent_layer** | 会话、缓存、输入加权、检索决策、reflection、回答生成、compact | 不直接处理底层文件解析，不直接承载 API 协议 |
| **service_layer** | API、SSE、配置、启动、健康检查、日志、依赖装配 | 不承载业务推理，不直接写检索和总结策略 |

---

## 常用命令

### 后端

```bash
cd backend

# 安装依赖
uv sync

# 启动服务
uv run python main.py

# 或直接用 uvicorn
uv run uvicorn app.main:app --reload

# 单元测试（按层运行）
uv run pytest tests/agent_layer/unit tests/data_layer/unit tests/service_layer/unit -v

# 集成测试（需真实 API key）
uv run pytest tests/data_layer/integration -v -s

# 全部测试
uv run pytest tests/ -v
```

### 测试目录规范

```
backend/test_backend/    # 后端测试（单元/集成/e2e/soak）
frontend/test_frontend/  # 前端测试（组件/store/service）
tests/                   # 前后端联调测试（E2E / API 契约）
```

详细规范见 `backend/test_backend/README.md`。

### 前端

```bash
cd frontend

# 安装依赖
pnpm install

# 开发模式
pnpm dev

# 构建
pnpm build
```

---

## 配置管理

所有配置通过 `.env` 文件管理（参见 `backend/.env.example`）：

```env
# LLM 服务（provider-neutral）
LLM_API_KEY=your_key
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=model-name

# Embedding 服务
EMBEDDING_API_KEY=your_key
EMBEDDING_BASE_URL=https://api.example.com/v1
EMBEDDING_MODEL=model-name
EMBEDDING_DIMENSIONS=1536

# MinerU PDF 解析
MINERU_API_KEY=your_key

# VLM 图片理解
VLM_API_KEY=your_key
VLM_BASE_URL=https://api.example.com/v1
VLM_MODEL=model-name

# 反思模型（可选，不配则用主模型）
REFLECTION_API_KEY=your_key
REFLECTION_MODEL=model-name
```

**配置约束**：
- 所有供应商信息通过环境变量注入，不在代码中硬编码
- 更换 Embedding 模型会导致向量库失效，需要重建索引
- 运行态缓存默认使用进程内内存，无需外部服务

---

## 🔮 未来扩展标注规范

所有未来扩展点在代码中用 `🔮 未来扩展` 标记：

```python
async def retrieve(
    query: str,
    resource_types: list[str] | None = None,  # 🔮 未来扩展：用户自选数据类型
    selected_papers: list[str] | None = None,  # 🔮 未来扩展：用户自选文献
) -> dict[str, Any]:
    """
    ═════════════════════════════════════════════════════════════════════
    🔮 未来扩展：Collection 过滤逻辑
    ═════════════════════════════════════════════════════════════════════

    # 实现代码写在这里

    产品价值：
    - 提高准确性：用户知道答案在哪些文献里
    - 增强掌控感：用户主动选择
    - 减少干扰：排除不相关文献
    """
```

**快速定位所有扩展点**：
```bash
grep -r "🔮 未来扩展" app/
```

---

## 已知问题与限制

### 已修复
- [x] PDF 解析：从本地 PyMuPDF 改为 MinerU API
- [x] 向量库：从 zvec（RocksDB）改为 ChromaDB（SQLite），根治 Windows 锁问题
- [x] Redis 依赖：移除 Redis，运行态缓存改为进程内内存
- [x] 切分策略：实现基于嵌入向量的语义切分（非固定 token 切分）
- [x] 探针/路由：删除 probe/ 和 routing（MinerU 直接处理所有格式）
- [x] 架构重构：从混合态迁移到三层结构（data_layer / agent_layer / service_layer）
- [x] SSE 协议：切换到 thinking/block/sources/done/error
- [x] ContentBlock：实现结构化回答块（paragraph/heading/list/table/code/divider/citation）
- [x] 输入加权：三种输入源冻结 + 四种起手权重
- [x] RRF 融合：Dense + BM25 融合检索

### 待完成
- [ ] 用户自选文献功能（接口已预留）
- [ ] 多模态资源支持（视频、文档、笔记）
- [ ] 知识图谱集成
- [ ] Rerank 启用（当前未启用）

---

## 参考实现

- Novel_Agents RAG 工具: `D:/真项目/Novel_Agents/.tools/rag`
- z_ai-mcp-server: `D:/开发区/L2Demo/z_ai-mcp-server-0.1.3`
