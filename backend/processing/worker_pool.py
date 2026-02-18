"""Multiprocessing worker pool for parallel document processing."""

from __future__ import annotations

import logging
import multiprocessing as mp
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Track active multiprocessing pools so they can be terminated on shutdown.
_active_pools: set[mp.pool.Pool] = set()
_pool_lock = threading.Lock()


@dataclass
class WorkerResult:
    """Result from processing a single document in a worker."""

    doc_id: str
    findings_data: list[dict]  # Serialized findings (dicts, not Finding objects)
    page_count: int
    success: bool
    error: str | None = None


# Thread-local storage for caching the Presidio analyzer per thread.
# Avoids rebuilding the spaCy model for every document in threaded mode.
_thread_local = threading.local()


def _worker_process_document(args: tuple[str, str]) -> WorkerResult:
    """Process a single document in a worker process or thread.

    Each worker creates its own Presidio AnalyzerEngine to avoid
    pickling issues with multiprocessing.  In threaded mode, the
    analyzer is cached per-thread to avoid reloading spaCy for
    every document.
    """
    doc_id, doc_path_str = args
    doc_path = Path(doc_path_str)

    try:
        from backend.processing.detector import build_analyzer
        from backend.processing.pipeline import process_document, get_page_count

        # Cache analyzer per thread (helps in ThreadPoolExecutor mode)
        analyzer = getattr(_thread_local, "analyzer", None)
        if analyzer is None:
            analyzer = build_analyzer()
            _thread_local.analyzer = analyzer
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

        In frozen mode (PyInstaller), uses ThreadPoolExecutor to avoid
        multiprocessing spawn issues on Windows. OCR subprocess calls
        release the GIL, so threading is efficient for this workload.

        Args:
            doc_items: List of (document_id, file_path_string) tuples.
            on_result: Optional callback called with each WorkerResult as it completes.

        Returns:
            List of WorkerResult objects.
        """
        if not doc_items:
            return []

        if getattr(sys, "frozen", False):
            return self._process_batch_threaded(doc_items, on_result=on_result)

        results: list[WorkerResult] = []

        pool = mp.Pool(processes=self.worker_count)
        with _pool_lock:
            _active_pools.add(pool)
        try:
            for result in pool.imap_unordered(_worker_process_document, doc_items):
                results.append(result)
                if on_result:
                    on_result(result)
        finally:
            pool.terminate()
            pool.join()
            with _pool_lock:
                _active_pools.discard(pool)

        return results

    def _process_batch_threaded(
        self,
        doc_items: list[tuple[str, str]],
        on_result: callable | None = None,
    ) -> list[WorkerResult]:
        """Process documents using threads (for frozen/PyInstaller mode).

        Avoids multiprocessing spawn issues while still providing parallelism.
        Tesseract OCR runs as a subprocess (releases GIL), so threads give
        good throughput for scanned documents.
        """
        results: list[WorkerResult] = []
        logger.info("Frozen mode: using thread pool (%d workers)", self.worker_count)

        with ThreadPoolExecutor(max_workers=self.worker_count) as executor:
            futures = {
                executor.submit(_worker_process_document, item): item
                for item in doc_items
            }
            for future in as_completed(futures):
                result = future.result()
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


def shutdown_all_pools() -> None:
    """Terminate all active worker pools. Called during application shutdown."""
    with _pool_lock:
        pools = list(_active_pools)
    for pool in pools:
        try:
            pool.terminate()
            pool.join(timeout=5)
        except Exception:
            logger.warning("Failed to terminate a worker pool", exc_info=True)
    with _pool_lock:
        _active_pools.clear()
