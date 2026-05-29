"""预处理 Pipeline 调度器

类似 Scrapy 的 engine + scheduler 复合体。
负责整个预处理流程的编排 + 文档级生命周期管理。

唯一入口：ingest / delete / rebuild / list。
内部调度：transform → clean → vlm → chunk → embed → index。

关键优化：VLM 在 MinerU 返回图片的那一刻就开始异步执行，
与 transformation 的剩余工作（表单/表格提取）和 cleaning 并行。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger("paper-assistant")

# 当前仅支持 PDF（其他格式需验证清洗策略后再放行）
SUPPORTED_SUFFIXES = {".pdf"}


# ── 数据类型 ──────────────────────────────────────────────────


class PipelineStage(str, Enum):
    """Pipeline 阶段"""
    QUEUED = "queued"
    TRANSFORMING = "transforming"
    CLEANING = "cleaning"
    VLM_ENRICHING = "vlm_enriching"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    DONE = "done"
    FAILED = "failed"
    DEGRADED = "degraded"


@dataclass
class PipelineEvent:
    """Pipeline 事件"""
    event: str
    stage: PipelineStage
    task_id: str
    message: str
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class PipelineState:
    """Pipeline 状态"""
    task_id: str
    file_path: Path
    stage: PipelineStage = PipelineStage.QUEUED
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    events: list[PipelineEvent] = field(default_factory=list)


@dataclass
class IngestResult:
    """文档导入结果"""
    paper_id: str
    success: bool
    error: str | None = None
    chunk_count: int = 0
    elapsed_s: float = 0.0
    structured_path: str | None = None
    report_path: str | None = None
    logs: list[dict] = field(default_factory=list)


# ── 编排器 ────────────────────────────────────────────────────


class PipelineOrchestrator:
    """Pipeline 编排器

    唯一入口：文档导入、删除、重建、列表。
    内部调度：transform → clean → vlm → chunk → embed → index。
    """

    def __init__(
        self,
        monitor_callback=None,
        *,
        embedding_client=None,
        vector_index=None,
        keyword_index=None,
        directory_manager=None,
        soft_delete_manager=None,
        pipeline_monitor=None,
        storage_monitor=None,
    ):
        self._monitor_callback = monitor_callback
        self._states: dict[str, PipelineState] = {}
        # pipeline 依赖
        self._embedding_client = embedding_client
        self._vector_index = vector_index
        self._keyword_index = keyword_index
        # 文档级依赖
        self._directory_manager = directory_manager
        self._soft_delete_manager = soft_delete_manager
        # 监控
        self._pipeline_monitor = pipeline_monitor
        self._storage_monitor = storage_monitor

    # ── 文档级操作（外部入口）──────────────────────────────────

    async def ingest_document(
        self,
        file_path: Path,
        paper_id: str | None = None,
    ) -> IngestResult:
        """完整闭环导入文档

        convert -> clean -> vlm -> chunk -> embed -> index -> persist
        """
        t0 = time.perf_counter()
        logs: list[dict] = []

        if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            return IngestResult(
                paper_id=paper_id or file_path.stem,
                success=False,
                error=f"不支持的文件格式: {file_path.suffix}，支持: {', '.join(sorted(SUPPORTED_SUFFIXES))}",
                elapsed_s=0.0,
                logs=[_log("error", f"不支持的文件格式: {file_path.suffix}")],
            )

        if not file_path.exists():
            return IngestResult(
                paper_id=paper_id or file_path.stem,
                success=False,
                error=f"文件不存在: {file_path}",
                elapsed_s=0.0,
                logs=[_log("error", f"文件不存在: {file_path}")],
            )

        # 生成 paper_id
        if paper_id is None:
            paper_id = _generate_paper_id(file_path)

        logs.append(_log("info", f"开始导入文档: {file_path.name}", paper_id=paper_id))

        try:
            # 1. 创建目录，复制文件
            dm = self._directory_manager
            if dm is not None:
                paths = dm.create_document_dirs(paper_id)
                stored_path = dm.copy_paper(file_path, paper_id)
                images_dir = paths.images_dir
                logs.append(_log("info", f"文件已复制: {stored_path}"))
            else:
                stored_path = file_path
                images_dir = None

            # 2. 运行 Pipeline
            state = await self.run(stored_path, output_dir=images_dir)
            logs.extend([
                _log("info", f"Pipeline 完成: stage={state.stage.value}", stage=state.stage.value)
            ])

            if state.stage.value == "failed":
                return IngestResult(
                    paper_id=paper_id,
                    success=False,
                    error=state.error or "Pipeline 失败",
                    elapsed_s=round(time.perf_counter() - t0, 2),
                    logs=logs,
                )

            # 3. 获取结果
            chunks = getattr(state, "_chunks", [])
            final_markdown = getattr(state, "_final_markdown", "")
            conversion_result = getattr(state, "_conversion_result", None)
            vlm_result = getattr(state, "_vlm_result", None)

            # 4. 持久化产物
            if dm is not None:
                # markdown.json
                metadata = {}
                if conversion_result:
                    metadata = dict(conversion_result.metadata)
                metadata["doc_type"] = file_path.suffix.lstrip(".").lower()
                metadata["source_file_path"] = str(file_path)
                metadata["file_name"] = file_path.name
                dm.save_markdown(paper_id, final_markdown, metadata)
                logs.append(_log("info", "markdown.json 已保存"))

                # structured.json
                structured = _build_structured(paper_id, chunks, metadata, vlm_result, dm)
                dm.save_structured(paper_id, structured)
                logs.append(_log("info", "structured.json 已保存"))

                # extraction_report.json
                report = _build_report(paper_id, state, chunks, metadata)
                dm.save_report(paper_id, report)
                logs.append(_log("info", "extraction_report.json 已保存"))

                result_paths = dm.get_document_paths(paper_id)
                structured_path = str(result_paths.structured_path)
                report_path = str(result_paths.report_path)
            else:
                structured_path = None
                report_path = None

            elapsed = round(time.perf_counter() - t0, 2)
            logs.append(_log("info", f"导入完成，共 {len(chunks)} 个 chunk，耗时 {elapsed}s"))

            return IngestResult(
                paper_id=paper_id,
                success=True,
                chunk_count=len(chunks),
                elapsed_s=elapsed,
                structured_path=structured_path,
                report_path=report_path,
                logs=logs,
            )

        except Exception as e:
            elapsed = round(time.perf_counter() - t0, 2)
            logs.append(_log("error", f"导入失败: {e}"))
            logger.error("文档导入失败 [%s]: %s", paper_id, e, exc_info=True)
            return IngestResult(
                paper_id=paper_id,
                success=False,
                error=str(e),
                elapsed_s=elapsed,
                logs=logs,
            )

    def delete_document(self, paper_id: str) -> None:
        """软删除文档"""
        if self._soft_delete_manager is None:
            raise RuntimeError("soft_delete_manager 未配置")
        self._soft_delete_manager.mark_deleted(paper_id)
        logger.info("文档已标记软删除: %s", paper_id)

    def hard_delete_document(self, paper_id: str) -> None:
        """硬删除文档（索引 + 文件）"""
        if self._vector_index:
            self._vector_index.delete_paper(paper_id)
        if self._keyword_index:
            self._keyword_index.delete_paper(paper_id)
        if self._directory_manager:
            self._directory_manager.delete_document(paper_id)
        logger.info("文档已硬删除: %s", paper_id)

    async def rebuild_document(self, paper_id: str) -> IngestResult:
        """重建文档索引（原子性）

        策略：ingest 到 tmp_id → rename tmp→backup → rename backup→paper_id → 清理
        任何步骤失败 → 旧索引数据保留。
        """
        dm = self._directory_manager
        if dm is None:
            return IngestResult(
                paper_id=paper_id,
                success=False,
                error="directory_manager 未配置",
            )

        # 备份
        dm.backup_document(paper_id)

        # 找到原始文件
        paper_dir = dm._papers_dir / paper_id
        source_files = [
            f for f in paper_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES
        ]
        if not source_files:
            return IngestResult(
                paper_id=paper_id,
                success=False,
                error=f"找不到原始文件: {paper_dir}",
            )

        # 用临时 paper_id 先建新索引
        tmp_id = f"{paper_id}__rebuild_tmp"
        backup_id = f"{paper_id}__rebuild_backup"
        result = await self.ingest_document(source_files[0], paper_id=tmp_id)

        if not result.success:
            if self._vector_index:
                self._vector_index.delete_paper(tmp_id)
            if self._keyword_index:
                self._keyword_index.delete_paper(tmp_id)
            _cleanup_tmp_dirs(dm, tmp_id)
            logger.error("重建失败，旧索引保留: %s, error=%s", paper_id, result.error)
            return IngestResult(
                paper_id=paper_id,
                success=False,
                error=result.error,
                elapsed_s=result.elapsed_s,
                logs=result.logs,
            )

        # rename tmp → backup
        try:
            if self._vector_index:
                self._vector_index.rename_paper(tmp_id, backup_id)
            if self._keyword_index:
                self._keyword_index.rename_paper(tmp_id, backup_id)
        except Exception as e:
            if self._vector_index:
                self._vector_index.delete_paper(tmp_id)
            if self._keyword_index:
                self._keyword_index.delete_paper(tmp_id)
            _cleanup_tmp_dirs(dm, tmp_id)
            logger.error("rename tmp→backup 失败: %s, %s", paper_id, e)
            return IngestResult(
                paper_id=paper_id, success=False, error=f"rename tmp→backup 失败: {e}",
                elapsed_s=result.elapsed_s, logs=result.logs,
            )

        # rename backup → paper_id
        try:
            if self._vector_index:
                self._vector_index.rename_paper(backup_id, paper_id)
            if self._keyword_index:
                self._keyword_index.rename_paper(backup_id, paper_id)
        except Exception as e:
            if self._vector_index:
                self._vector_index.delete_paper(backup_id)
            if self._keyword_index:
                self._keyword_index.delete_paper(backup_id)
            _cleanup_tmp_dirs(dm, tmp_id)
            logger.error("rename backup→final 失败: %s, %s", paper_id, e)
            return IngestResult(
                paper_id=paper_id, success=False, error=f"rename backup→final 失败: {e}",
                elapsed_s=result.elapsed_s, logs=result.logs,
            )

        # 清理
        if self._vector_index:
            self._vector_index.delete_paper(backup_id)
        if self._keyword_index:
            self._keyword_index.delete_paper(backup_id)
        _cleanup_tmp_dirs(dm, tmp_id)

        logger.info("重建成功: %s", paper_id)
        return IngestResult(
            paper_id=paper_id,
            success=True,
            chunk_count=result.chunk_count,
            elapsed_s=result.elapsed_s,
            structured_path=result.structured_path,
            report_path=result.report_path,
            logs=result.logs,
        )

    def list_documents(self) -> list[dict]:
        """列出所有已导入文档及其状态"""
        dm = self._directory_manager
        if dm is None:
            return []

        docs = []
        papers_dir = dm._papers_dir
        if not papers_dir.exists():
            return docs

        for paper_dir in papers_dir.iterdir():
            if not paper_dir.is_dir():
                continue
            paper_id = paper_dir.name
            is_deleted = (
                self._soft_delete_manager.is_deleted(paper_id)
                if self._soft_delete_manager else False
            )
            parsed_dir = dm._parsed_dir / paper_id
            has_parsed = parsed_dir.exists()
            files = [
                f.name for f in paper_dir.iterdir()
                if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES
            ]
            docs.append({
                "paper_id": paper_id,
                "is_deleted": is_deleted,
                "has_parsed": has_parsed,
                "files": files,
            })

        return docs

    # ── 内部 Pipeline ────────────────────────────────────────

    async def run(
        self,
        file_path: Path,
        output_dir: Path | None = None,
    ) -> PipelineState:
        """运行内部 pipeline（transform → clean → vlm → chunk → embed → index）"""
        task_id = str(uuid.uuid4())[:8]
        state = PipelineState(task_id=task_id, file_path=file_path)
        self._states[task_id] = state

        # 启动监控
        if self._pipeline_monitor:
            self._pipeline_monitor.start_task(task_id, str(file_path))

        try:
            # 阶段 1：转换（内部会提前启动 VLM）
            vlm_task = await self._run_transformation(state, output_dir)

            # 阶段 2：清洗 + 等待 VLM（并行）
            await self._run_cleaning_and_vlm(state, vlm_task)

            # 阶段 3：切分
            await self._run_chunking(state)

            # 阶段 4：Embedding + 索引（可选，需要外部依赖）
            if self._embedding_client and self._vector_index and self._keyword_index:
                await self._run_embedding_and_indexing(state)

            # 完成
            state.stage = PipelineStage.DONE
            state.completed_at = time.time()
            self._emit(state, "pipeline.completed", "预处理完成")

            if self._pipeline_monitor:
                self._pipeline_monitor.complete_task(task_id)

        except Exception as e:
            state.stage = PipelineStage.FAILED
            state.error = str(e)
            state.completed_at = time.time()
            self._emit(state, "pipeline.failed", f"预处理失败: {e}")
            logger.error("Pipeline 失败 [%s]: %s", task_id, e, exc_info=True)

            if self._pipeline_monitor:
                self._pipeline_monitor.fail_task(task_id, str(e))

        return state

    async def _run_transformation(self, state: PipelineState, output_dir: Path | None):
        """执行转换，返回已启动的 VLM 任务"""
        state.stage = PipelineStage.TRANSFORMING
        self._emit(state, "transformation.started", "开始转换")

        def _on_mineru_progress(progress):
            self._emit(state, "transformation.mineru_progress", progress.message, {
                "state": progress.state.value,
                "extracted_pages": progress.extracted_pages,
                "total_pages": progress.total_pages,
            })

        from ..transformation import convert_pdf
        result = await convert_pdf(
            state.file_path,
            output_dir=output_dir,
            on_mineru_progress=_on_mineru_progress,
        )

        if not result.success:
            raise RuntimeError(f"转换失败: {result.error}")

        state._conversion_result = result
        self._emit(state, "transformation.completed", "转换完成", {
            "char_count": len(result.markdown),
            "image_count": len(result.images),
        })

        # 关键优化：图片一到手就启动 VLM
        mineru_image_paths = result.mineru_metadata.get("image_paths", [])
        vlm_task = None
        has_vlm = bool(mineru_image_paths) or bool(result.images)
        if has_vlm:
            state.stage = PipelineStage.VLM_ENRICHING
            self._emit(state, "vlm.started", "VLM 理解已提前启动（与 transformation 剩余工作并行）")
            vlm_task = asyncio.create_task(self._run_vlm(result))

        return vlm_task

    async def _run_cleaning_and_vlm(self, state: PipelineState, vlm_task):
        """并行执行清洗，等待 VLM 完成"""
        conversion_result = getattr(state, "_conversion_result", None)
        if not conversion_result:
            return

        state.stage = PipelineStage.CLEANING
        self._emit(state, "cleaning.started", "开始清洗")
        cleaning_task = asyncio.create_task(self._run_cleaning(conversion_result))

        tasks_to_wait = [cleaning_task]
        task_labels = ["cleaning"]

        if vlm_task is not None:
            tasks_to_wait.append(vlm_task)
            task_labels.append("vlm")

        results = await asyncio.gather(*tasks_to_wait, return_exceptions=True)

        if not isinstance(results[0], Exception):
            state._cleaning_result = results[0]
        else:
            logger.warning("清洗失败: %s", results[0])
            self._emit(state, "pipeline.degraded", "清洗失败，使用原始 markdown")

        if vlm_task is not None:
            vlm_idx = 1
            if not isinstance(results[vlm_idx], Exception):
                state._vlm_result = results[vlm_idx]
            else:
                logger.warning("VLM 失败: %s", results[vlm_idx])
                self._emit(state, "pipeline.degraded", f"VLM 降级: {results[vlm_idx]}")

    async def _run_cleaning(self, conversion_result):
        """执行 MinerU 专用清洗"""
        from ..cleaning import clean_mineru_output
        metadata = getattr(conversion_result, "mineru_metadata", {})
        return clean_mineru_output(conversion_result.markdown, metadata=metadata)

    async def _run_vlm(self, conversion_result):
        """执行 VLM 理解"""
        from ..vlm_understanding import process_images
        mineru_metadata = getattr(conversion_result, "mineru_metadata", {})
        return await process_images(conversion_result.images, mineru_metadata=mineru_metadata)

    async def _run_chunking(self, state: PipelineState):
        """执行切分"""
        state.stage = PipelineStage.CHUNKING
        self._emit(state, "chunking.started", "开始切分")

        conversion_result = getattr(state, "_conversion_result", None)
        if not conversion_result:
            return

        cleaning_result = getattr(state, "_cleaning_result", None)
        markdown = cleaning_result.markdown if cleaning_result else conversion_result.markdown

        vlm_result = getattr(state, "_vlm_result", None)
        if vlm_result and vlm_result.analyses:
            from ..vlm_understanding import merge_vlm_into_markdown
            markdown = merge_vlm_into_markdown(markdown, vlm_result)

        state._final_markdown = markdown

        from ..chunking import semantic_chunk
        mineru_metadata = getattr(conversion_result, "mineru_metadata", {})
        chunks = semantic_chunk(markdown, source_file_path=str(state.file_path), mineru_metadata=mineru_metadata)
        state._chunks = chunks

        self._emit(state, "chunking.completed", f"切分完成，共 {len(chunks)} 个 chunk")

    async def _run_embedding_and_indexing(self, state: PipelineState):
        """执行 embedding + 索引（Chroma + BM25）"""
        chunks = getattr(state, "_chunks", None)
        if not chunks:
            return

        paper_id = state.file_path.stem
        sm = self._storage_monitor  # 简写

        # Embedding
        state.stage = PipelineStage.EMBEDDING
        self._emit(state, "embedding.started", f"开始 embedding，共 {len(chunks)} 个 chunk")

        texts = [c.content for c in chunks]
        try:
            t0 = time.perf_counter()
            vectors = await self._embedding_client.embed(texts)
            embed_ms = int((time.perf_counter() - t0) * 1000)
            state._vectors = vectors
            self._emit(state, "embedding.completed", f"embedding 完成，共 {len(vectors)} 个向量")
            if sm:
                sm.record_latency("embedding", embed_ms, chunk_count=len(chunks))
        except Exception as e:
            self._emit(state, "embedding.failed", f"embedding 失败: {e}")
            raise

        # Indexing
        state.stage = PipelineStage.INDEXING
        self._emit(state, "indexing.started", "开始索引")

        chunk_dicts = []
        for c in chunks:
            anchor = c.anchors[0] if c.anchors else None
            chunk_dicts.append({
                "content": c.content,
                "chunk_type": c.chunk_type,
                "section_title": c.section_title,
                "has_image": str(c.has_image),
                "parent_chunk_id": c.parent_chunk_id,
                "source_page": anchor.page if anchor else 0,
                "file_hash": anchor.source_text_hash if anchor else "",
                "anchors": [
                    {
                        "anchor_id": a.anchor_id,
                        "page": a.page,
                        "block_id": a.block_id,
                        "block_type": a.block_type,
                        "heading_path": a.heading_path,
                        "char_start": a.char_start,
                        "char_end": a.char_end,
                        "bbox": a.bbox,
                        "parent_anchor_id": a.parent_anchor_id,
                        "source_text_hash": a.source_text_hash,
                    }
                    for a in c.anchors
                ],
            })

        inserted = self._vector_index.insert_chunks(paper_id, chunk_dicts, vectors)
        doc_ids = [f"{paper_id}_{i}" for i in range(len(chunks))]
        contents = [c.content for c in chunks]
        metadatas = [
            {
                "content": c.content,
                "paper_id": paper_id,
                "source_page": chunk_dicts[i].get("source_page", 0),
                "section_title": chunk_dicts[i].get("section_title", ""),
                "chunk_index": i,
                "parent_chunk_id": c.parent_chunk_id,
                "anchors": chunk_dicts[i].get("anchors", []),
            }
            for i, c in enumerate(chunks)
        ]
        self._keyword_index.add_documents(doc_ids, contents, metadatas=metadatas)

        self._emit(state, "indexing.completed", f"索引完成，Chroma: {inserted}，BM25: {len(doc_ids)}")

        # 更新存储健康
        if sm:
            try:
                chroma_count = self._vector_index._collection.count() if self._vector_index._collection else 0
                bm25_count = len(self._keyword_index._doc_ids) if hasattr(self._keyword_index, "_doc_ids") else 0
                sm.update_health(chroma_doc_count=chroma_count, bm25_doc_count=bm25_count)
            except Exception:
                pass  # 监控不应阻断主链

    def get_state(self, task_id: str) -> PipelineState | None:
        """获取 pipeline 状态"""
        return self._states.get(task_id)

    def _emit(self, state: PipelineState, event: str, message: str, data: dict = None):
        """发送事件"""
        pipeline_event = PipelineEvent(
            event=event,
            stage=state.stage,
            task_id=state.task_id,
            message=message,
            data=data or {},
        )
        state.events.append(pipeline_event)

        if self._monitor_callback:
            self._monitor_callback(pipeline_event)

        logger.info("[%s] %s: %s", state.task_id, event, message)

        # 桥接到 PipelineMonitor
        self._bridge_to_monitor(state, event, data or {})

    def _bridge_to_monitor(self, state: PipelineState, event: str, data: dict):
        """将 pipeline 事件桥接到 PipelineMonitor"""
        monitor = self._pipeline_monitor
        if monitor is None:
            return

        task_id = state.task_id

        # 阶段开始
        if event.endswith(".started") and not event.startswith("pipeline"):
            stage = event.rsplit(".", 1)[0]
            monitor.start_stage(task_id, stage)

        # 阶段完成
        elif event.endswith(".completed") and not event.startswith("pipeline"):
            stage = event.rsplit(".", 1)[0]
            monitor.complete_stage(task_id, stage, details=data)

        # 阶段失败
        elif event.endswith(".failed") and not event.startswith("pipeline"):
            stage = event.rsplit(".", 1)[0]
            monitor.fail_stage(task_id, stage, data.get("error", "unknown"))

        # 降级
        elif event == "pipeline.degraded":
            monitor.degrade_stage(task_id, state.stage.value, message=data.get("reason", "degraded"))


# ── 模块级辅助函数 ────────────────────────────────────────────


def _generate_paper_id(file_path: Path) -> str:
    """从文件路径生成 paper_id"""
    name = file_path.stem
    if len(name) > 50:
        h = hashlib.md5(name.encode()).hexdigest()[:8]
        name = f"{name[:40]}_{h}"
    return name


def _build_structured(
    paper_id: str,
    chunks: list,
    metadata: dict,
    vlm_result=None,
    directory_manager=None,
) -> dict:
    """构建 structured.json"""
    anchors = []
    for chunk in chunks:
        for anchor in chunk.anchors:
            anchors.append({
                "anchor_id": anchor.anchor_id,
                "source_file_path": anchor.source_file_path,
                "doc_type": anchor.doc_type,
                "page": anchor.page,
                "block_id": anchor.block_id,
                "block_type": anchor.block_type,
                "heading_path": anchor.heading_path,
                "paragraph_index": anchor.paragraph_index,
                "char_start": anchor.char_start,
                "char_end": anchor.char_end,
                "bbox": anchor.bbox,
                "parent_anchor_id": anchor.parent_anchor_id,
                "source_text_hash": anchor.source_text_hash,
            })

    visual_blocks = []
    if vlm_result and hasattr(vlm_result, "visual_blocks"):
        visual_blocks = _resolve_visual_block_anchors(
            vlm_result.visual_blocks, chunks, anchors,
        )

    paths = directory_manager.get_document_paths(paper_id) if directory_manager else None

    return {
        "document_id": paper_id,
        "paper_id": paper_id,
        "doc_type": metadata.get("doc_type", "pdf"),
        "source_file_path": metadata.get("source_file_path", ""),
        "pipeline_version": "v4",
        "markdown_path": str(paths.markdown_path) if paths else "",
        "images_dir": str(paths.images_dir) if paths else "",
        "doc_level": {
            "file_name": metadata.get("file_name", ""),
            "page_count": metadata.get("page_count", 0),
            "char_count": metadata.get("char_count", 0),
        },
        "anchors": anchors,
        "visual_blocks": visual_blocks,
        "stats": {
            "chunk_count": len(chunks),
            "anchor_count": len(anchors),
            "visual_block_count": len(visual_blocks),
        },
    }


def _build_report(
    paper_id: str,
    state,
    chunks: list,
    metadata: dict,
) -> dict:
    """构建 extraction_report.json"""
    events = [
        {
            "event": e.event,
            "stage": e.stage.value,
            "message": e.message,
            "timestamp": e.timestamp,
        }
        for e in state.events
    ]

    return {
        "paper_id": paper_id,
        "status": state.stage.value,
        "error": state.error,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
        "elapsed_s": round(state.completed_at - state.started_at, 2) if state.completed_at else 0,
        "chunk_count": len(chunks),
        "metadata": metadata,
        "events": events,
    }


def _resolve_visual_block_anchors(
    visual_blocks: list[dict],
    chunks: list,
    anchors: list[dict],
) -> list[dict]:
    """为 visual_blocks 解析真实的 parent_anchor_id"""
    resolved = []
    for vb in visual_blocks:
        if vb.get("parent_anchor_id"):
            resolved.append(vb)
            continue

        vb_page = vb.get("page", 0)
        vb_bbox = vb.get("bbox", [])
        best_anchor_id = ""
        best_score = float("inf")

        for anchor_dict in anchors:
            a_page = anchor_dict.get("page", 0)
            if a_page and vb_page and a_page != vb_page:
                continue

            a_bbox = anchor_dict.get("bbox", [])
            if vb_bbox and a_bbox and len(vb_bbox) >= 4 and len(a_bbox) >= 4:
                dist = sum((a - b) ** 2 for a, b in zip(vb_bbox[:4], a_bbox[:4])) ** 0.5
            else:
                dist = 0 if a_page == vb_page else 9999

            if dist < best_score:
                best_score = dist
                best_anchor_id = anchor_dict.get("anchor_id", "")

        new_vb = dict(vb)
        new_vb["parent_anchor_id"] = best_anchor_id
        resolved.append(new_vb)

    return resolved


def _cleanup_tmp_dirs(directory_manager, tmp_id: str) -> None:
    """清理 rebuild 临时目录"""
    for base_dir in (directory_manager._papers_dir, directory_manager._parsed_dir):
        tmp_dir = base_dir / tmp_id
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _log(level: str, message: str, **kwargs) -> dict:
    """生成日志条目"""
    import datetime
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "level": level,
        "message": message,
    }
    entry.update(kwargs)
    return entry
