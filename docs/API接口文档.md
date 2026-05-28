# API 接口文档

> Base URL: `http://127.0.0.1:8000/api/v1`
>
> 当前无认证，所有接口可直接访问。

---

## 目录

- [健康检查](#健康检查)
- [论文管理](#论文管理)
- [文档导入](#文档导入)
- [对话管理](#对话管理)
- [助手接口](#助手接口)
- [查询接口](#查询接口)
- [模型发现](#模型发现)
- [SSE 事件格式](#sse-事件格式)
- [错误码](#错误码)

---

## 健康检查

### `GET /health`

返回后端各组件状态。

**响应**:
```json
{
  "status": "ok",
  "components": {
    "chroma": {"status": "ok", "collection_count": 5, "total_vectors": 1234},
    "bm25": {"status": "ok", "doc_count": 1234},
    "redis": {"status": "unavailable", "detail": "not initialized"},
    "llm_config": {"status": "ok"},
    "embedding_config": {"status": "ok"}
  }
}
```

`status` 取值: `ok` | `degraded` | `error`

---

## 论文管理

### `GET /papers`

获取已导入论文列表。

**响应**:
```json
{
  "papers": [
    {
      "paper_id": "abc123",
      "title": "论文标题",
      "authors": "",
      "file_path": "/path/to/file.pdf",
      "file_hash": "a1b2c3d4e5f6",
      "chunk_count": 42,
      "total_pages": 15,
      "import_time": "2025-01-01T00:00:00",
      "status": "ready"
    }
  ]
}
```

### `GET /papers/{paper_id}/open`

下载/打开论文原始文件。返回 `FileResponse`（PDF 或 DOCX）。

**参数**: `paper_id` (路径参数)

**响应**: 文件流，`Content-Type: application/pdf` 或 `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

**错误**: 404 论文不存在 / 论文文件不存在

### `DELETE /papers/{paper_id}`

软删除论文（不立即从索引移除，保留期后自动清理）。

**参数**: `paper_id` (路径参数)

**响应**:
```json
{"status": "ok", "message": "已删除: 论文标题"}
```

**错误**: 404 论文不存在

---

## 文档导入

### `POST /import/start`

上传文件并开始导入。

**请求**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | 是 | PDF/DOCX/DOC/PPTX/XLSX 文件 |

**响应**:
```json
{"task_id": "a1b2c3d4e5f6", "status": "queued"}
```

`status` 取值: `queued` | `duplicate`

**错误**: 400 不支持的文件格式

### `GET /import/status/{task_id}`

查询导入任务状态。

**参数**: `task_id` (路径参数)

**响应**:
```json
{
  "task_id": "a1b2c3d4e5f6",
  "paper_id": "abc123",
  "status": "completed",
  "current_step": "completed",
  "error_msg": null,
  "file_name": "paper.pdf",
  "percent": null
}
```

`status` 取值: `queued` | `running` | `completed` | `failed`

**错误**: 404 任务不存在

### `GET /import/stream/{task_id}`

SSE 流式推送导入进度。

**参数**: `task_id` (路径参数)

**响应**: `text/event-stream`

```
event: progress
data: {"status": "running", "step": "transforming", "paper_id": null}

event: progress
data: {"status": "running", "step": "chunking", "paper_id": null}

event: progress
data: {"status": "completed", "step": "done", "paper_id": "abc123"}

event: progress
data: {"status": "done", "step": null, "paper_id": null}
```

---

## 对话管理

### `GET /conversations`

获取对话列表。

**响应**: `list[ConversationSessionOut]`

### `POST /conversations`

新建对话。

**请求体**:
```json
{"title": "新对话"}
```

**响应**: `ConversationSessionOut`

### `GET /conversations/{session_id}`

获取对话详情。

### `DELETE /conversations/{session_id}`

删除对话及其所有消息。

### `GET /conversations/{session_id}/messages`

获取对话的所有消息。

### `POST /conversations/chat`

发送消息（非流式）。

**请求体**: `ChatRequest`

---

## 助手接口

### `PUT /assistant/written-context`

更新编辑器上下文（WPS 插件推送选区/文档内容）。

**请求体**:
```json
{
  "session_id": "xxx",
  "content": "用户当前正在编辑的内容..."
}
```

### `GET /assistant/written-context/{session_id}`

获取当前编辑器上下文。

### `PUT /assistant/selection`

更新用户选中的文本。

**请求体**:
```json
{
  "session_id": "xxx",
  "selection": "用户选中的文本..."
}
```

### `GET /assistant/selection/{session_id}`

获取当前选中文本。

---

## 查询接口

### `POST /query`

主链：提问 → 检索 → 生成 → 流式返回。

**请求体**:
```json
{
  "session_id": "xxx",
  "prompt": "这篇论文的主要贡献是什么？",
  "selection": "可选：用户选中的文本",
  "draft": "可选：用户当前草稿",
  "paper_ids": ["paper1", "paper2"],
  "enable_rag": true,
  "model": "可选：指定模型",
  "thinking": false,
  "reflection": false
}
```

**响应**: `text/event-stream`（详见 [SSE 事件格式](#sse-事件格式)）

---

## 模型发现

### `POST /models`

从 LLM 提供商获取可用模型列表。

**请求体**:
```json
{
  "api_key": "sk-xxx",
  "api_url": "https://api.openai.com/v1"
}
```

**响应**:
```json
{
  "models": [
    {"id": "gpt-4", "name": "gpt-4", "provider": "openai", "support_thinking": null},
    {"id": "gpt-3.5-turbo", "name": "gpt-3.5-turbo", "provider": "openai", "support_thinking": null}
  ]
}
```

**错误**: 502 模型列表获取失败

---

## SSE 事件格式

`POST /query` 返回 `text/event-stream`，事件类型：

### `thinking` — 思考过程

```
event: thinking
data: {"text": "让我分析这篇论文...", "time_ms": 1234}
```

### `block` — 内容块

```
event: block
data: {"type": "paragraph", "text": "这篇论文的主要贡献是..."}
```

块类型: `paragraph` | `heading` | `list` | `citation_text` | `table` | `code` | `divider`

### `sources` — 引用来源

```
event: sources
data: [
  {
    "id": "src_1",
    "paper_id": "abc123",
    "title": "论文标题",
    "page": 3,
    "section": "Abstract",
    "content": "相关段落文本..."
  }
]
```

### `done` — 流结束

```
event: done
data: {}
```

### `error` — 错误

```
event: error
data: {"message": "检索失败，请稍后重试"}
```

### `reflection` — 反思事件（启用 reflection 时）

```
event: reflection
data: {"round": 1, "verdict": "unsupported", "direction": "refine"}
```

---

## 错误码

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 成功 |
| 400 | 请求参数错误 / 不支持的文件格式 |
| 404 | 资源不存在 |
| 409 | 冲突（如重复导入） |
| 422 | 请求体校验失败 |
| 500 | 服务器内部错误 |
| 502 | 外部服务调用失败（模型发现） |
| 503 | 服务不可用 |
