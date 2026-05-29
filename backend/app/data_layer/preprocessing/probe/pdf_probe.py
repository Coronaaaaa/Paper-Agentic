"""PDF 轻量探针。

用于导入前的路由分流和复杂度判断。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_FORMULA_MARKERS = (
    r"\\frac",
    r"\\sum",
    r"\\int",
    r"\\sqrt",
    r"\\alpha",
    r"\\beta",
    r"\\gamma",
    r"\\lambda",
    r"\\pi",
    r"\\theta",
)

_MATH_SYMBOL_RE = re.compile(r"[∑∫√≤≥×÷≈±αβγδλμπσΩ]")
_FORMULA_RE = re.compile("|".join(_FORMULA_MARKERS))


@dataclass(frozen=True)
class ProbeResult:
    file_path: str
    page_count: int
    has_text_layer: bool
    text_density: float
    is_scan_like: bool
    has_images: bool
    image_density: float
    image_count: int
    has_form_fields: bool
    has_formula_signals: bool
    has_table_signals: bool
    doc_complexity_level: Literal["simple", "moderate", "complex"]
    recommended_route: Literal["A", "B", "C", "D", "E"]


def probe_pdf(file_path: Path | str) -> ProbeResult:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"不是 PDF 文件: {path}")

    page_count = _get_page_count(path)
    total_text_chars = 0
    text_pages = 0
    image_count = 0
    image_pages = 0
    table_pages = 0
    formula_pages = 0

    has_form_fields = _has_form_fields(path)

    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text = _safe_extract_text(page)
                if text:
                    text_pages += 1
                    total_text_chars += len(text)
                    if _looks_formula_like(text):
                        formula_pages += 1
                    if _looks_table_like(text):
                        table_pages += 1

                images = _safe_images(page)
                if images:
                    image_pages += 1
                    image_count += len(images)

                if _safe_extract_tables(page):
                    table_pages += 1
    except Exception:
        # 探针只做轻量判断，单页解析失败不应阻断整体扫描。
        pass

    has_text_layer = text_pages > 0 and total_text_chars > 0
    text_density = round(total_text_chars / max(page_count, 1), 2)
    image_density = round(image_count / max(page_count, 1), 2)
    has_images = image_count > 0
    has_formula_signals = formula_pages > 0
    has_table_signals = table_pages > 0
    is_scan_like = (not has_text_layer) or (text_density < 35 and image_density >= 0.5)

    doc_complexity_level = _classify_complexity(
        page_count=page_count,
        has_images=has_images,
        has_form_fields=has_form_fields,
        has_formula_signals=has_formula_signals,
        has_table_signals=has_table_signals,
        is_scan_like=is_scan_like,
    )
    recommended_route = _recommend_route(
        has_text_layer=has_text_layer,
        has_images=has_images,
        has_form_fields=has_form_fields,
        has_formula_signals=has_formula_signals,
        has_table_signals=has_table_signals,
        is_scan_like=is_scan_like,
    )

    return ProbeResult(
        file_path=str(path),
        page_count=page_count,
        has_text_layer=has_text_layer,
        text_density=float(text_density),
        is_scan_like=is_scan_like,
        has_images=has_images,
        image_density=float(image_density),
        image_count=image_count,
        has_form_fields=has_form_fields,
        has_formula_signals=has_formula_signals,
        has_table_signals=has_table_signals,
        doc_complexity_level=doc_complexity_level,
        recommended_route=recommended_route,
    )


def _get_page_count(path: Path) -> int:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        count = len(reader.pages)
        if count > 0:
            return count
    except Exception:
        pass

    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0


def _has_form_fields(path: Path) -> bool:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        fields = reader.get_fields() or {}
        return bool(fields)
    except Exception:
        return False


def _safe_extract_text(page) -> str:
    try:
        text = page.extract_text() or ""
        return text.strip()
    except Exception:
        return ""


def _safe_images(page) -> list:
    try:
        return list(page.images or [])
    except Exception:
        return []


def _safe_extract_tables(page) -> list:
    try:
        return list(page.extract_tables() or [])
    except Exception:
        return []


def _looks_formula_like(text: str) -> bool:
    return bool(_FORMULA_RE.search(text) or _MATH_SYMBOL_RE.search(text))


def _looks_table_like(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    pipe_lines = sum(1 for line in lines if "|" in line)
    tab_lines = sum(1 for line in lines if "\t" in line)
    numeric_lines = sum(1 for line in lines if len(re.findall(r"\d", line)) >= 4)
    return pipe_lines > 0 or tab_lines > 0 or numeric_lines >= max(1, math.ceil(len(lines) / 4))


def _classify_complexity(
    *,
    page_count: int,
    has_images: bool,
    has_form_fields: bool,
    has_formula_signals: bool,
    has_table_signals: bool,
    is_scan_like: bool,
) -> Literal["simple", "moderate", "complex"]:
    score = 0
    if page_count >= 20:
        score += 1
    if has_images:
        score += 1
    if has_form_fields:
        score += 1
    if has_formula_signals:
        score += 1
    if has_table_signals:
        score += 1
    if is_scan_like:
        score += 2

    if score <= 1:
        return "simple"
    if score <= 3:
        return "moderate"
    return "complex"


def _recommend_route(
    *,
    has_text_layer: bool,
    has_images: bool,
    has_form_fields: bool,
    has_formula_signals: bool,
    has_table_signals: bool,
    is_scan_like: bool,
) -> Literal["A", "B", "C", "D", "E"]:
    if is_scan_like or not has_text_layer:
        return "E"
    if has_images and (has_form_fields or has_formula_signals or has_table_signals):
        return "D"
    if has_form_fields or has_formula_signals or has_table_signals:
        return "C"
    if has_images:
        return "B"
    return "A"


__all__ = ["ProbeResult", "probe_pdf"]
