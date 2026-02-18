"""Multiprocessing worker pool for parallel document processing."""

from __future__ import annotations

import logging
import multiprocessing as mp
from dataclasses import dataclass
from pathlib import Path

from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WorkerResult:
    """Result from processing a single document in a worker."""

    doc_id: str
    findings_data: list[dict]  # Serialized findings (dicts, not Finding objects)
    page_count: int
    success: bool
    error: str | None = None


def _worker_process_document(args: tuple[str, str]) -> WorkerResult:
    """Process a single document in a worker process.

    Each worker creates its own Presidio AnalyzerEngine to avoid
    pickling issues with multiprocessing.
    """
    doc_id, doc_path_str = args
    doc_path = Path(doc_path_str)

    try:
        from backend.processing.detector import build_analyzer
        from backend.processing.pipeline import process_document, get_page_count

        analyzer = build_analyzer()
        page_count = get_page_count(doc_path)
        findings = process_document(doc_path, doc_id, analyzer=analyzer)

        findings_data = [
            {
                "pii_type": f.pii_type,
                "confidence": f.confidence,
                "start": f.start,
                "end": f.end,
                "page_num": f.page_num,
                "context_snippet": f.context_snippet,
            }
            for f in findings
        ]

        return WorkerResult(
            doc_id=doc_id,
            findings_data=findings_data,
            page_count=page_count,
            success=True,
        )
    except Exception as exc:
        logger.exception("Worker failed for document %s", doc_id)
        return WorkerResult(
            doc_id=doc_id,
            findings_data=[],
            page_count=0,
            success=False,
            error=str(exc),
        )


class WorkerPool:
    """Manages a pool of worker processes for batch document processing."""

    def __init__(self, worker_count: int | None = None):
        self.worker_count = worker_count or settings.worker_count

    def process_batch(
        self,
        doc_items: list[tuple[str, str]],
        on_result: callable | None = None,
    ) -> list[WorkerResult]:
        """Process a list of (doc_id, doc_path) tuples in parallel.

        Args:
            doc_items: List of (document_id, file_path_string) tuples.
            on_result: Optional callback called with each WorkerResult as it completes.

        Returns:
            List of WorkerResult objects.
        """
        if not doc_items:
            return []

        results: list[WorkerResult] = []

        # Use spawn context for cross-platform safety
        ctx = mp.get_context("spawn")

        with ctx.Pool(processes=self.worker_count) as pool:
            for result in pool.imap_unordered(_worker_process_document, doc_items):
                results.append(result)
                if on_result:
                    on_result(result)

        return results

    def process_batch_sequential(
        self,
        doc_items: list[tuple[str, str]],
        on_result: callable | None = None,
    ) -> list[WorkerResult]:
        """Process documents sequentially (useful for debugging or single-worker mode).

        Same interface as process_batch but runs in the current process.
        """
        results: list[WorkerResult] = []

        for item in doc_items:
            result = _worker_process_document(item)
            results.append(result)
            if on_result:
                on_result(result)

        return results
