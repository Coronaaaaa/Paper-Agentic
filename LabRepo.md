# 实验记录

本文档记录论文助手项目的实验数据与对比结果。原始数据存储在本地 `backend/test_backend/data/` 目录（不入版本控制）。

---

## 1. MinerU 解析质量对比

### 实验目的

对比 MinerU 不同清洗策略对 PDF 解析质量的影响。

### 测试样本

| 编号 | 语言 | 来源 | 说明 |
|------|------|------|------|
| 2018 | 中文 | 学术论文 | 标准双栏排版 |
| VR | 中文 | 学术论文 | 含大量图表 |
| 刘威 | 中文 | 学术论文 | 单栏排版 |
| 谭明方 | 中文 | 学术论文 | 含公式 |
| 郜清攀 | 中文 | 学术论文 | 含表格 |
| en-1 ~ en-103 | 英文 | 学术论文 | 多篇英文论文批量测试 |

### 测试文件

| 文件 | 说明 |
|------|------|
| `test_mineru_cleaning_ab.py` | A/B 清洗策略对比 |
| `test_mineru_cleaning_mixed.py` | 混合清洗策略测试 |
| `test_mineru_comparison.py` | 多维度解析质量对比 |
| `test_mineru_json_analysis.py` | JSON 结构化分析 |

### 本地数据结构

```
backend/test_backend/data/mineru_json_analysis/
├── {论文名}/
│   ├── full.md          # MinerU 解析的完整 Markdown
│   ├── content_list.json # 结构化内容列表
│   ├── layout.json      # 版面分析结果
│   └── model.json       # 模型配置信息
└── en/
    └── en-{n}/          # 英文论文（同结构）
```

### 运行方式

```bash
cd backend
uv run pytest tests/data_layer/integration/test_mineru_comparison.py -v -s
```

---

## 2. 真实 API 集成测试

### 测试文件

- `test_real_api.py` — 端到端 API 调用测试（需配置 `.env` 中的 API key）

### 依赖服务

| 服务 | 用途 |
|------|------|
| MinerU API | PDF 解析 |
| 硅基流动 | Embedding / Rerank |
| Kimi API | LLM / VLM |

### 运行方式

```bash
cd backend
uv run pytest tests/data_layer/integration/test_real_api.py -v -s
```

---

## 3. 单元测试覆盖

### 测试统计

- **总计**: 443 passed, 7 skipped, 1 xfailed
- **agent_layer**: contracts, hooks, orchestration, planning, response, runtime, session, chain
- **data_layer**: chroma_store, chunking, cleaning, config_embedding, document_service, file_management, preprocessor_monitor, probe, retrieval, transfer, transformation, vlm_understanding
- **service_layer**: container_assembly, import_routes, model_routes, papers_routes, query_routes

### 已知问题

| 问题 | 影响 | 状态 |
|------|------|------|
| `MetadataEvent` 导入路径变更 | 7 个 orchestration 测试 error | 已修复（待下一测试运行验证） |
| `test_llm_exception_yields_error` 断言 | 1 个 chain 测试 failure | 测试断言需更新 |

---

## 4. 数据排除说明

以下数据存储在本地，不推送到远程仓库：

| 路径 | 内容 | 原因 |
|------|------|------|
| `backend/test_backend/data/` | MinerU 解析产物、测试运行时输出 | 体积大，运行时生成 |
| `backend/test_backend/fixtures/pdfs_*/` | PDF 测试样本 | 体积大（500MB+） |
| `backend/data/` | 运行态数据（ChromaDB、SQLite） | 运行时生成 |
| `datasets/` | 外部测试数据集 | 体积大，自行准备 |

通过 `.gitignore` 排除，实验结果通过本文档描述。
