"""Markdown 清洗器 — 数据驱动架构

通用引擎 + 纯数据规则，消除逐函数样板代码。
新增规则只需加一行数据，无需写函数。
"""

from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("paper-assistant")


# ═══════════════════════════════════════════════════════════════════════════════
# 结果类型
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CleaningResult:
    """清洗结果"""
    markdown: str
    stats: dict
    logs: list[dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# 规则数据类
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LineRule:
    """行级过滤规则：匹配 → 删除整行"""
    name: str
    patterns: tuple[re.Pattern, ...]
    limit: int | None = None       # 只检查前 N 行（None = 全文）
    full: bool = False             # True=fullmatch, False=search


@dataclass(frozen=True)
class RegexRule:
    """正则替换规则：pattern.subn → 替换"""
    name: str
    pattern: re.Pattern
    repl: str | callable | None = None   # None = 删除匹配内容，callable = 动态替换


# ═══════════════════════════════════════════════════════════════════════════════
# 通用引擎
# ═══════════════════════════════════════════════════════════════════════════════

def _line_filter(text: str, rules: list[LineRule]) -> tuple[str, int]:
    """单次遍历，批量执行所有行级过滤规则。

    比逐函数 split/join 快 N 倍（N = 规则数）。
    """
    lines = text.split("\n")
    result = []
    removed = 0
    for i, line in enumerate(lines):
        s = line.strip()
        matched = False
        if s:
            for rule in rules:
                if rule.limit is not None and i >= rule.limit:
                    continue
                for p in rule.patterns:
                    if (rule.full and p.fullmatch(s)) or (not rule.full and p.search(s)):
                        matched = True
                        break
                if matched:
                    break
        if matched:
            removed += 1
        else:
            result.append(line)
    return "\n".join(result), removed


def _regex_subs(text: str, rules: list[RegexRule]) -> tuple[str, int]:
    """批量执行正则替换规则。"""
    total = 0
    for rule in rules:
        text, n = rule.pattern.subn(rule.repl or "", text)
        total += n
    return text, total


# ═══════════════════════════════════════════════════════════════════════════════
# 正则模式常量
# ═══════════════════════════════════════════════════════════════════════════════

# ── 通用 ─────────────────────────────────────────────────────────────────────

_GARBLED_RE = re.compile(r"[\x00-\x08\x0e-\x1f]{3,}")
_BREAK_NEWLINES_RE = re.compile(r"\n{6,}")
_BREAK_REPEAT_RE = re.compile(r"([^\s\-\.=\*|_~#])\1{50,}")
_PAGE_FOOTER_RE = re.compile(r"^第\s*\d+\s*页\s*共\s*\d+\s*页\s*$", re.MULTILINE)
_OCR_CJK_SPACE_RE = re.compile(r"([一-鿿])(?:\s+([一-鿿]))+")
_URL_SPACE_RE = re.compile(r"(https?://\S*)\s+(\S+)")

# ── MinerU 专用 ──────────────────────────────────────────────────────────────

_COVER_META_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^分类号[：:]\s*\S+"),
    re.compile(r"^中图分类号[：:]\s*\S+"),
    re.compile(r"^单位代码[：:]\s*\S+"),
    re.compile(r"^密级[：:]\s*\S+"),
    re.compile(r"^学号[：:]\s*\S+"),
    re.compile(r"^UDC[：:]\s*\S+"),
    re.compile(r"^学校代码[：:]\s*\S+"),
    re.compile(r"^文献标志码[：:]\s*\S+"),
    re.compile(r"^文章编号[：:]\s*\S+"),
    re.compile(r"^ISSN[：:]\s*\S+"),
    re.compile(r"^收稿日期[：:]\s*\S+"),
    # 英文学术元数据
    re.compile(r"^©\s*\d{4}"),
    re.compile(r"^Article history", re.IGNORECASE),
    re.compile(r"^Received\s+\d{1,2}\s+\w+\s+\d{4}"),
    re.compile(r"^Accepted\s+\d{1,2}\s+\w+\s+\d{4}"),
    re.compile(r"^Available online", re.IGNORECASE),
    re.compile(r"^Keywords?\s*[:：]", re.IGNORECASE),
    re.compile(r"^A\s+R\s+T\s+I\s+C\s+L\s+E\s+I\s+N\s+F\s+O"),
    re.compile(r"^A\s+B\s+S\s+T\s+R\s+A\s+C\s+T"),
    re.compile(r"^Corresponding author", re.IGNORECASE),
    re.compile(r"^E-mail\s*[:：]", re.IGNORECASE),
    re.compile(r"^[A-Z][a-z]+ [A-Z][a-z]+\s+[\w.]+@[\w.]+\.\w+$"),
)

_INSTITUTION_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^培养单位"),
    re.compile(r"^专业名称[：:.]"),
    re.compile(r"^指导教师"),
    re.compile(r"^合作导师[：:.]"),
    re.compile(r"^一级学科[：:.]"),
    re.compile(r"^二级学科[：:.]"),
    re.compile(r"^研究方向[：:.]"),
    re.compile(r"^作者[：:]\s*\S+$"),
    re.compile(r"^作者姓名"),
    re.compile(r"^学位授予单位"),
    re.compile(r"^申请学位"),
    re.compile(r"^Research Supervisor", re.IGNORECASE),
    re.compile(r"^Candidate[：:.]", re.IGNORECASE),
    re.compile(r"^College[：:.]", re.IGNORECASE),
    re.compile(r"^Specialty[：:.]", re.IGNORECASE),
    re.compile(r"^Supervisor[：:.]", re.IGNORECASE),
    re.compile(r"^Dissertation Submitted", re.IGNORECASE),
    re.compile(r"^硕士学位论文$"),
    re.compile(r"^博士学位论文$"),
    re.compile(r"^学士学位论文$"),
    re.compile(r"^Thesis for Master", re.IGNORECASE),
    re.compile(r"^Dissertation for Doctor", re.IGNORECASE),
    re.compile(r"^\d{4}年\d{1,2}月\d{1,2}日$"),
    re.compile(r"^\d{4}年\d{1,2}月$"),
    re.compile(r"大学学位评定委员会$"),
    re.compile(r"University.*Degree", re.IGNORECASE),
    re.compile(r"^东北师范大学.*研究生"),
)

_TOC_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百千\d]+[篇章节部]")
_JOURNAL_HEADER_RE = re.compile(r"^·.{2,40}·\s*$")
_CNKI_RE = re.compile(r"^.*中国知网.*cnki.*$", re.MULTILINE)
_AUTHOR_BIO_RE = re.compile(r"作者简介[：:].*$", re.MULTILINE)
_HTML_TABLE_TAGS_RE = re.compile(r"</?(?:table|tr|td|th|thead|tbody)\b[^>]*>", re.IGNORECASE)
_EN_HEADING_SPACE_RE = re.compile(r"^(#{1,6}\s+)([A-Za-z](?:\s+[A-Za-z]){2,})\s*$", re.MULTILINE)

_EN_HEADER_FOOTER_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^Check for updates$", re.IGNORECASE),
    re.compile(r"^Publisher'?s?\s+note", re.IGNORECASE),
    re.compile(r"^Contents lists? available", re.IGNORECASE),
    re.compile(r"^journal homepage", re.IGNORECASE),
    re.compile(r"^doi\s*:\s*10\.", re.IGNORECASE),
    re.compile(r"^\d+\s*$"),
    re.compile(r"^ORIGINAL\s+PAPER$", re.IGNORECASE),
    re.compile(r"^Original\s+article$", re.IGNORECASE),
    re.compile(r"^REVIEWED\s+BY$", re.IGNORECASE),
    re.compile(r"^OPEN\s+ACCESS$", re.IGNORECASE),
    re.compile(r"^Index\s+\d+\s*$", re.IGNORECASE),
)

_JOURNAL_UI_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^Submit your article to this journal", re.IGNORECASE),
    re.compile(r"^View (?:related )?articles", re.IGNORECASE),
    re.compile(r"^View Crossmark data", re.IGNORECASE),
    re.compile(r"^Article views?:\s*\d+", re.IGNORECASE),
    re.compile(r"^Citing articles?:\s*\d+", re.IGNORECASE),
    re.compile(r"^This page intentionally left blank", re.IGNORECASE),
    re.compile(r"^This article was submitted to\b", re.IGNORECASE),
)

_WATERMARK_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^Copyright[:\s].*(?:Licensee|Publisher|Published by)", re.IGNORECASE),
    re.compile(r"^©?\s*The Author\(s\)\s+\d{4}", re.IGNORECASE),
    re.compile(r"^Disclaimer/Publisher", re.IGNORECASE),
    re.compile(r"^\(c\)\s*\d{4}\s+.*(?:Published by|Licensee)", re.IGNORECASE),
)

_BARE_IMAGE_RE = re.compile(
    r"^!\[\]\(images?/[a-f0-9\-]+\.(?:jpg|jpeg|png|gif|bmp|webp)\)\s*$", re.IGNORECASE,
)

_TABLE_PLACEHOLDER_RE = re.compile(r"^\[Insert\s+Table\s+\d+.*?\]$", re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════════════════
# 规则表（纯数据 — 新增规则只需加一行）
# ═══════════════════════════════════════════════════════════════════════════════

# ── MinerU 行级规则 ──────────────────────────────────────────────────────────

_TOC_ENTRY_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"^目\s*录\s*$"),
    re.compile(r"^Table of Contents", re.IGNORECASE),
    re.compile(r"^CONTENTS\s*$", re.IGNORECASE),
    re.compile(r"^\s*[一-鿿\w].*[\.\．\…]{2,}\s*\d+\s*$"),
    re.compile(r"^\s*[一-鿿\w].*\.\.\s*[\.\s]*\d+\s*$"),
    re.compile(r"^[一-鿿\w].*\.\.\s*[\.\s]*\d+\s*$"),
    re.compile(r"^[一-鿿\w].*\.\.\s*$"),
)

_MINERU_LINE_RULES: list[LineRule] = [
    LineRule("封面元数据", _COVER_META_PATTERNS),
    LineRule("机构行", _INSTITUTION_PATTERNS),
    LineRule("英文页眉页脚", _EN_HEADER_FOOTER_PATTERNS),
    LineRule("期刊UI", _JOURNAL_UI_PATTERNS),
    LineRule("版权声明", _WATERMARK_PATTERNS),
    LineRule("裸图片", (_BARE_IMAGE_RE,)),
    LineRule("表格占位符", (_TABLE_PLACEHOLDER_RE,)),
    LineRule("期刊头", (_JOURNAL_HEADER_RE,), limit=20, full=True),
    LineRule("目录条目", _TOC_ENTRY_PATTERNS),
]

# ── MinerU 正则规则 ──────────────────────────────────────────────────────────


def _fix_heading_space_match(m: re.Match) -> str:
    """英文标题逐字母空格修复的替换函数"""
    return m.group(1) + m.group(2).replace(" ", "")


_MINERU_REGEX_RULES: list[RegexRule] = [
    RegexRule("中文页眉页脚", _PAGE_FOOTER_RE),
    RegexRule("CNKI水印", _CNKI_RE),
    RegexRule("作者简介", _AUTHOR_BIO_RE),
    RegexRule("HTML表格标签", _HTML_TABLE_TAGS_RE),
    RegexRule("英文标题空格", _EN_HEADING_SPACE_RE, repl=_fix_heading_space_match),
]


# ═══════════════════════════════════════════════════════════════════════════════
# 通用格式化函数
# ═══════════════════════════════════════════════════════════════════════════════

def _compress_empty_lines(text: str) -> tuple[str, int]:
    """压缩连续 2+ 空行为 1 个空行"""
    original = len(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, max(0, (original - len(text)) // 2)


def _normalize_headings(text: str) -> tuple[str, int]:
    """标准化标题层级（修正跳级）"""
    lines = text.split("\n")
    result = []
    normalized = 0
    last_level = 0
    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            if level > last_level + 1 and last_level > 0:
                level = last_level + 1
                normalized += 1
            last_level = level
            result.append(f"{'#' * level} {title}")
        else:
            result.append(line)
    return "\n".join(result), normalized


def _fix_url_spaces(text: str) -> tuple[str, int]:
    """修复 URL 中的空格（如 "https://www. cnki. net"）"""
    count = 0

    def _fix(m: re.Match) -> str:
        nonlocal count
        count += 1
        return m.group(0).replace(" ", "")

    # 循环直到无更多匹配（一次 sub 只处理一个空格）
    while True:
        new_text = _URL_SPACE_RE.sub(_fix, text)
        if new_text == text:
            break
        text = new_text
    return text, count


def _normalize_width(text: str) -> str:
    """统一全角半角（数字和英文字母 → 半角）"""
    result = []
    for char in text:
        code = ord(char)
        if 0xFF10 <= code <= 0xFF19:
            result.append(chr(code - 0xFF10 + 0x30))
        elif 0xFF21 <= code <= 0xFF3A:
            result.append(chr(code - 0xFF21 + 0x41))
        elif 0xFF41 <= code <= 0xFF5A:
            result.append(chr(code - 0xFF41 + 0x61))
        else:
            result.append(char)
    return "".join(result)


def _remove_trailing_spaces(text: str) -> str:
    """去除行尾空格"""
    return "\n".join(line.rstrip() for line in text.split("\n"))


def _normalize_newlines(text: str) -> str:
    """标准化换行（6+ 换行压缩为 2 个）"""
    text = _BREAK_NEWLINES_RE.sub("\n\n", text)
    return re.sub(r"\n{3,}", "\n\n", text)


# ═══════════════════════════════════════════════════════════════════════════════
# 复杂函数（无法数据化的逻辑）
# ═══════════════════════════════════════════════════════════════════════════════

def _remove_ocr_spaces_chinese(text: str) -> tuple[str, int]:
    """移除 OCR 产生的中文字符间空格（连续 2+ CJK 被空格隔开）"""
    matches = _OCR_CJK_SPACE_RE.findall(text)
    text = _OCR_CJK_SPACE_RE.sub(lambda m: re.sub(r"\s+", "", m.group(0)), text)
    return text, len(matches)


def _fix_heading_ocr_spaces(text: str) -> tuple[str, int]:
    """修复标题内的 OCR 空格（仅 heading 行）"""
    lines = text.split("\n")
    result = []
    fixed = 0
    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            prefix, title = match.group(1), match.group(2)
            new_title = _OCR_CJK_SPACE_RE.sub(
                lambda m: re.sub(r"\s+", "", m.group(0)), title,
            )
            if new_title != title:
                fixed += 1
            result.append(f"{prefix} {new_title}")
        else:
            result.append(line)
    return "\n".join(result), fixed


def _remove_toc_from_content_list(
    text: str, content_list: list[dict],
) -> tuple[str, int]:
    """利用 content_list 元数据移除目录块（page_idx≤1 且含 30+ TOC 行）"""
    total_removed = 0
    for item in content_list:
        if item.get("type") != "text" or item.get("page_idx", 999) > 1:
            continue
        block_text = item.get("text", "")
        if not block_text:
            continue
        lines = block_text.split("\n")
        toc_count = sum(1 for line in lines if _TOC_CHAPTER_RE.match(line.strip()))
        if toc_count >= 30:
            for line in lines:
                stripped = line.strip()
                if stripped and stripped in text:
                    text = text.replace(stripped, "", 1)
                    total_removed += 1
    if total_removed > 0:
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text, total_removed


def _remove_toc_heuristic(text: str) -> tuple[str, int]:
    """启发式检测无点状目录块（连续 10+ TOC 行 → 删除）"""
    lines = text.split("\n")
    result = []
    removed = 0
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not re.match(r"^[日目]\s*[求录]\s*$", stripped):
            result.append(lines[i])
            i += 1
            continue
        toc_lines = [lines[i]]
        j = i + 1
        while j < len(lines):
            s = lines[j].strip()
            if not s:
                k = j + 1
                while k < len(lines) and not lines[k].strip():
                    k += 1
                if k < len(lines) and _TOC_CHAPTER_RE.match(lines[k].strip()):
                    toc_lines.extend(lines[j:k])
                    j = k
                    continue
                break
            if _TOC_CHAPTER_RE.match(s) or re.match(r"^[一二三四五六七八九十]+[、.]", s):
                toc_lines.append(lines[j])
                j += 1
            else:
                break
        if len(toc_lines) >= 10:
            removed += len(toc_lines)
            i = j
        else:
            result.extend(toc_lines)
            i = j
    return "\n".join(result), removed


def _remove_toc(text: str, metadata: dict | None = None) -> tuple[str, int]:
    """移除目录（metadata 可用时用策略 1，否则用启发式）"""
    if metadata and "content_list" in metadata:
        return _remove_toc_from_content_list(text, metadata["content_list"])
    return _remove_toc_heuristic(text)


def _remove_table_residue(text: str) -> tuple[str, int]:
    """去除表格残留（MarkItDown 在排版密集页面产生的伪表格）

    策略：检测连续表格行块，平均单元格字符数 < 50 → 伪表格。
    """
    lines = text.split("\n")
    result = []
    removed = 0
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("|"):
            table_start = i
            table_end = i
            while table_end < len(lines):
                s = lines[table_end].strip()
                if s.startswith("|") or (not s and table_end > table_start):
                    table_end += 1
                else:
                    break
            table_lines = [l for l in lines[table_start:table_end] if l.strip()]
            sep_pattern = re.compile(r"^\|[\s\-:]+(\|[\s\-:]+)+")
            data_lines = [l for l in table_lines if not sep_pattern.match(l.strip())]
            total_chars = sum(
                len(cell.strip())
                for dl in data_lines
                for cell in dl.strip().strip("|").rstrip().split("|")
            )
            avg = total_chars / max(len(data_lines), 1)
            if avg < 50 and len(data_lines) >= 2:
                extracted = _extract_text_from_table(data_lines)
                result.extend(extracted)
                removed += len(table_lines) - len(extracted)
                i = table_end
                continue
        result.append(lines[i])
        i += 1
    return "\n".join(result), removed


def _extract_text_from_table(table_data_lines: list[str]) -> list[str]:
    """从伪表格中提取纯文本"""
    fragments = [
        cell.strip()
        for line in table_data_lines
        for cell in line.strip().strip("|").split("|")
        if cell.strip()
    ]
    if not fragments:
        return []
    merged = "".join(fragments)
    return [merged[i:i + 80] for i in range(0, len(merged), 80)]


def _merge_broken_lines(text: str) -> tuple[str, int]:
    """合并碎片行（≤10 字符的连续短行拼接）"""
    _SHORT = 10
    lines = text.split("\n")
    result = []
    merge_count = 0
    buffer: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and (stripped[0] in "#|`" or stripped.startswith("```")):
            if buffer:
                result.append("".join(buffer))
                merge_count += 1
                buffer = []
            result.append(line)
            continue
        if stripped:
            if len(stripped) <= _SHORT:
                buffer.append(stripped)
            else:
                if buffer:
                    result.append("".join(buffer))
                    merge_count += 1
                    buffer = []
                result.append(stripped)
        else:
            if buffer:
                result.append("".join(buffer))
                merge_count += 1
                buffer = []
            result.append("")
    if buffer:
        result.append("".join(buffer))
        merge_count += 1
    return "\n".join(result), merge_count


def _merge_ultra_short_lines(text: str) -> tuple[str, int]:
    """合并极短碎片行（跨空行，≤2 字符）"""
    _ULTRA = 2
    lines = text.split("\n")
    result = []
    merge_count = 0
    buffer: list[str] = []
    empty_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and (stripped[0] in "#|`" or stripped.startswith("```")):
            if buffer:
                result.append("".join(buffer))
                merge_count += 1
                buffer = []
                empty_count = 0
            result.append(line)
            continue
        if stripped:
            if len(stripped) <= _ULTRA:
                buffer.append(stripped)
                empty_count = 0
            else:
                if buffer and empty_count == 0:
                    buffer.append(stripped)
                elif buffer and empty_count > 0:
                    if len(stripped) <= 10:
                        buffer.append(stripped)
                    else:
                        result.append("".join(buffer))
                        merge_count += 1
                        buffer = []
                        result.append(stripped)
                else:
                    result.append(stripped)
                empty_count = 0
        else:
            empty_count += 1
            if empty_count >= 2:
                if buffer:
                    result.append("".join(buffer))
                    merge_count += 1
                    buffer = []
                result.append("")
    if buffer:
        result.append("".join(buffer))
        merge_count += 1
    return "\n".join(result), merge_count


# ═══════════════════════════════════════════════════════════════════════════════
# 流水线编排器
# ═══════════════════════════════════════════════════════════════════════════════

def _log(level: str, message: str) -> dict:
    import datetime
    return {"timestamp": datetime.datetime.now().isoformat(), "level": level, "message": message}


def _record(logs: list[dict], message: str, count: int) -> None:
    if count > 0:
        logs.append(_log("info", f"{message} {count} 处"))


def clean_mineru_output(markdown: str, metadata: dict | None = None) -> CleaningResult:
    """MinerU 输出的专用清洗（数据驱动，行级规则单次遍历）"""
    logs: list[dict] = []
    t0 = time.perf_counter()
    original_length = len(markdown)

    # Phase 1: 行级过滤（单次遍历，批量执行所有规则）
    markdown, n = _line_filter(markdown, _MINERU_LINE_RULES)
    _record(logs, "行级过滤", n)

    # Phase 2: 正则替换（页眉页脚、CNKI、作者简介、HTML 标签、英文标题空格）
    markdown, n = _regex_subs(markdown, _MINERU_REGEX_RULES)
    _record(logs, "正则替换", n)

    # Phase 3: 复杂逻辑（必须在 OCR 修复之前，否则 CJK 行合并会破坏 TOC 检测）
    markdown, n = _remove_toc(markdown, metadata)
    _record(logs, "移除目录", n)
    markdown, n = _remove_table_residue(markdown)
    _record(logs, "去除表格残留", n)

    # Phase 4: OCR 修复
    markdown, n = _remove_ocr_spaces_chinese(markdown)
    _record(logs, "修复 OCR 中文空格", n)
    markdown, n = _fix_heading_ocr_spaces(markdown)
    _record(logs, "修复标题内空格", n)

    # Phase 5: 格式化
    markdown, n = _compress_empty_lines(markdown)
    _record(logs, "压缩过多空行", n)
    markdown, n = _normalize_headings(markdown)
    _record(logs, "标准化标题层级", n)
    markdown, n = _fix_url_spaces(markdown)
    _record(logs, "修复 URL 空格", n)
    markdown = _remove_trailing_spaces(markdown)

    elapsed = round(time.perf_counter() - t0, 3)
    logs.append(_log("info", f"MinerU 清洗完成，耗时 {elapsed}s"))
    return CleaningResult(
        markdown=markdown,
        stats={
            "original_length": original_length,
            "cleaned_length": len(markdown),
            "reduction_ratio": round(1 - len(markdown) / max(original_length, 1), 3),
            "elapsed_ms": int(elapsed * 1000),
            "mode": "mineru",
        },
        logs=logs,
    )


# ── 通用流水线规则 ───────────────────────────────────────────────────────────

_GENERIC_REGEX_RULES: list[RegexRule] = [
    RegexRule("PUA字符", re.compile(r"[-]")),
    RegexRule("控制字符", re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")),
    RegexRule("乱码碎片", _GARBLED_RE),
    RegexRule("中文页眉页脚", _PAGE_FOOTER_RE),
    RegexRule("重复字符", _BREAK_REPEAT_RE, repl=lambda m: m.group(1) * 3),
]


def clean_markdown(markdown: str) -> CleaningResult:
    """通用 markdown 清洗"""
    logs: list[dict] = []
    t0 = time.perf_counter()
    original_length = len(markdown)

    # Phase 1: 正则替换
    markdown, n = _regex_subs(markdown, _GENERIC_REGEX_RULES)
    _record(logs, "正则清理", n)

    # Phase 2: 表格残留
    markdown, n = _remove_table_residue(markdown)
    _record(logs, "去除表格残留", n)

    # Phase 3: 全角半角
    markdown = _normalize_width(markdown)

    # Phase 4: 行合并
    markdown, n = _compress_empty_lines(markdown)
    _record(logs, "压缩过多空行", n)
    markdown, n = _merge_broken_lines(markdown)
    _record(logs, "合并碎片行", n)
    markdown, n = _merge_ultra_short_lines(markdown)
    _record(logs, "合并极短碎片行", n)

    # Phase 5: 格式化
    markdown = _normalize_newlines(markdown)
    markdown = _remove_trailing_spaces(markdown)
    markdown, n = _normalize_headings(markdown)
    _record(logs, "标准化标题层级", n)

    elapsed = round(time.perf_counter() - t0, 3)
    logs.append(_log("info", f"清洗完成，耗时 {elapsed}s"))
    return CleaningResult(
        markdown=markdown,
        stats={
            "original_length": original_length,
            "cleaned_length": len(markdown),
            "reduction_ratio": round(1 - len(markdown) / max(original_length, 1), 3),
            "elapsed_ms": int(elapsed * 1000),
        },
        logs=logs,
    )
