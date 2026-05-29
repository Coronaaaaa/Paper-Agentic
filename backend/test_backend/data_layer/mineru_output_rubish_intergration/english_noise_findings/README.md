# 英文噪音发现测试数据

## 扫描概况

| 指标 | 数值 |
|------|------|
| 英文 PDF 总数 | 111 |
| MinerU 转换成功 | 105 |
| 黑板扫描覆盖 | 106 文件（含合成测试文件） |
| LLM 噪音发现 | 6473 条 |
| 使用模型 | nv-minimax (minimaxai/minimax-m2.7) via NVIDIA NIM |

## 噪音类型分布

| 噪音类型 | 数量 | 说明 |
|----------|------|------|
| table_noise | 2197 | HTML 表格标签、异常表格 |
| image_or_caption_noise | 2178 | 图片引用、图注残留 |
| ocr_spacing | 776 | OCR 异常空格（英文标题逐字母空格） |
| pua_or_control | 616 | Unicode 私有区字符、控制字符 |
| cover_metadata | 355 | 封面元数据（©、Article history、Keywords 等） |
| suspect | 118 | 可疑但不确定的噪音 |
| toc_residue | 76 | 目录残留 |
| header_footer | 73 | 页眉页脚（Check for updates、doi 等） |
| repeated_garbage | 43 | 超长重复乱码 |
| watermark | 41 | 水印、版权标记 |

## 文件说明

| 文件 | 说明 |
|------|------|
| `test_input.md` | 合成英文 markdown 测试输入 |
| `kimi_findings.jsonl` | nv-kimi 单文件测试结果（22 条） |
| `minimax_findings.jsonl` | nv-minimax 单文件测试结果（10 条） |
| `all_findings.jsonl` | 全量扫描结果（6473 条，106 文件） |

## 数据来源

- **PDF**: `datasets/外文文献-测试-PDF/外文文献-测试/其他重要外文文献/`（111 篇英文论文）
- **MinerU 转换**: `Dev_Tools/clean_md_tool/output_english_md/`（105 个 markdown）
- **黑板扫描**: PostgreSQL `md_noise_blackboard` 数据库
- **扫描脚本**: `Dev_Tools/clean_md_tool/scan_english_simple.py`

## 模型测试对比

| 模型 | 响应速度 | 发现数量 | 可用性 |
|------|----------|----------|--------|
| nv-kimi | ~1s/请求 | 16（单文件） | 间歇性超时 |
| nv-minimax | ~1.5s/请求 | 7（单文件） | 稳定 |
| nv-dsv4f | ~51s/请求 | - | 太慢 |
| nv-stepfun | ~1s/请求 | - | 返回空内容 |

结论：**nv-minimax 最稳定**，适合批量扫描。nv-kimi 更快但间歇性不可用。

## 对 markdown_cleaner.py 的扩展

基于黑板扫描发现的高频英文噪音，已将以下规则集成到生产清洗器：

### 新增模式常量

```python
# 英文学术元数据（_COVER_META_PATTERNS 扩展）
r"^©\s*\d{4}"                           # © 2023 Elsevier
r"^Article history"                      # Article history: Received ...
r"^Received\s+\d{1,2}\s+\w+\s+\d{4}"    # Received 27 May 2023
r"^Accepted\s+\d{1,2}\s+\w+\s+\d{4}"    # Accepted 11 October 2023
r"^Available online"                     # Available online 1 November 2023
r"^Keywords?\s*[:：]"                    # Keywords: digital twin
r"^A\s+R\s+T\s+I\s+C\s+L\s+E\s+I\s+N\s+F\s+O"
r"^A\s+B\s+S\s+T\s+R\s+A\s+C\s+T"
r"^Corresponding author"
r"^E-mail\s*[:：]"

# 英文页眉页脚（_EN_HEADER_FOOTER_PATTERNS）
r"^Check for updates$"
r"^Publisher'?s?\s+note"
r"^Contents lists? available"
r"^journal homepage"
r"^doi\s*:\s*10\."
r"^\d+\s*$"                              # 纯页码行

# HTML 表格标签（_HTML_TABLE_TAGS）
r"</?(?:table|tr|td|th|thead|tbody)\b[^>]*>"

# 英文标题逐字母空格（_EN_HEADING_SPACE_RE）
r"^(#{1,6}\s+)([A-Za-z](?:\s+[A-Za-z]){2,})\s*$"
```

### 新增清洗函数

| 函数 | 位置 | 作用 |
|------|------|------|
| `_strip_html_table_tags()` | Step 2 | 移除 `<table>/<tr>/<td>` 标签，保留文本 |
| `_remove_en_header_footer()` | Step 10 | 移除英文页眉页脚 |
| `_fix_heading_spaces_english()` | Step 13 | `## A B S T R A C T` → `## ABSTRACT` |

### 流水线变化

`clean_mineru_output()` 从 14 步扩展到 17 步。

## 验证命令

```bash
cd D:\真项目\论文助手\backend
uv run python -c "
from app.data_layer.preprocessing.cleaning import clean_mineru_output

# 英文封面元数据
raw = '© 2023 Elsevier\nArticle history: Received 27 May 2023\nKeywords: digital twin\n# Introduction\n正文'
r = clean_mineru_output(raw)
assert '© 2023' not in r.markdown
assert 'Keywords' not in r.markdown

# HTML 表格
raw2 = '<table><tr><td>A</td></tr></table>\n正文'
r2 = clean_mineru_output(raw2)
assert '<table>' not in r2.markdown

# 英文标题空格
raw3 = '## A B S T R A C T\n\n正文'
r3 = clean_mineru_output(raw3)
assert '## ABSTRACT' in r3.markdown

print('All checks passed')
"
```
