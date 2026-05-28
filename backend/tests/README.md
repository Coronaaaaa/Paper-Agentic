# 后端测试规范

## 目录结构

```
tests/
├── conftest.py              # 根配置（sys.path）
├── .gitignore               # 排除 output/ fixtures/ _artifacts/ __pycache__/
│
├── unit/                    # 单元测试（纯逻辑，无外部依赖）
│   ├── agent_layer/         # Agent 层单测
│   │   ├── contracts/       # 数据契约测试
│   │   ├── orchestration/   # 编排测试
│   │   ├── planning/        # 规划测试
│   │   ├── response/        # 回答生成测试
│   │   ├── runtime/         # 运行时测试
│   │   └── session/         # 会话测试
│   │
│   ├── data_layer/          # 数据层单测
│   │   ├── conftest.py      # 共享 fixtures（tmp_dir, zh_pdf, en_pdf）
│   │   ├── chroma_store/    # 向量库 + BM25 测试
│   │   ├── chunking/        # 语义切分测试
│   │   ├── cleaning/        # 清洗测试
│   │   ├── config_embedding/ # 配置 + embedding 测试
│   │   ├── document_service/ # 文档服务测试
│   │   ├── file_management/  # 文件管理测试
│   │   ├── preprocessor_monitor/ # 监控测试
│   │   ├── probe/           # 探针测试
│   │   ├── retrieval/       # 检索测试
│   │   ├── transfer/        # 路由调度测试
│   │   ├── transformation/  # 转换测试
│   │   └── vlm_understanding/ # VLM 测试
│   │
│   └── service_layer/       # 服务层单测
│
├── integration/             # 集成测试（需真实 API / 文件）
│   └── data_layer/
│       ├── test_mineru_*.py          # MinerU 解析相关
│       └── test_real_api.py          # 真实 API 测试
│
├── fixtures/                # 测试输入（只读，不修改，不入库）
│   ├── pdfs_zh/             # 中文 PDF 样本（自行准备）
│   ├── pdfs_en/             # 英文 PDF 样本（自行准备）
│   └── README.md
│
└── output/                  # 测试产出（.gitignore，不入库）
    └── mineru_json_analysis/
```

## 分类原则

| 类型 | 目录 | 特征 | 运行频率 |
|------|------|------|----------|
| 单元测试 | `unit/` | 纯逻辑，mock 外部依赖，毫秒级 | 每次提交 |
| 集成测试 | `integration/` | 需要真实 API / 真实文件，秒~分钟级 | 合并前 / 手动 |

## 运行命令

```bash
cd backend

# 运行所有单元测试
uv run pytest tests/unit/ -v

# 运行所有集成测试
uv run pytest tests/integration/ -v -s

# 运行特定模块
uv run pytest tests/unit/data_layer/cleaning/ -v

# 运行全部
uv run pytest tests/ -v
```

## 添加新测试

1. 判断类型：纯逻辑 → `unit/`，需 API → `integration/`
2. 放到对应子目录，保持 `test_<module>.py` 命名
3. 共享 fixtures 写在对应 `conftest.py`
4. 测试产出写入 `output/`（不要写到 fixtures/ 或其他目录）

## PDF 样本

- `fixtures/pdfs_zh/` — 中文论文
- `fixtures/pdfs_en/` — 英文论文
- 这些文件不入库，自行准备
- 新增样本直接放入对应目录即可

## 不入库的内容

| 目录/文件 | 原因 |
|-----------|------|
| `fixtures/pdfs_*/` | PDF 体积大（500MB+），自行准备 |
| `output/` | MinerU 解析产物，运行时生成 |
| `_artifacts/` | soak reports、fault logs，运行时产物 |
| `__pycache__/` | Python 字节码 |
