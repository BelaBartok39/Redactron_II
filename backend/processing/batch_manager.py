"""Batch lifecycle management: create, start, track, resume batches."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.core.config import settings
from backend.core.database import db
from backend.processing.worker_pool import WorkerPool, WorkerResult

logger = logging.getLogger(__name__)


def create_batch(source_path: str, name: str | None = None) -> str:
    """Create a new batch by scanning a folder for PDF files.

    Args:
        source_path: Path to folder containing PDF files.
        name: Human-readable batch name (defaults to folder name).

    Returns:
        The batch ID.

    Raises:
        FileNotFoundError: If source_path does not exist.
        ValueError: If no PDF files are found.
    """
    folder = Path(source_path)
    if not folder.is_dir():
        raise FileNotFoundError(f"Source folder not found: {source_path}")

    pdf_files = sorted(folder.glob("*.pdf")) + sorted(folder.glob("*.PDF"))
    # Deduplicate (in case *.pdf and *.PDF overlap on case-insensitive FS)
    seen: set[Path] = set()
    unique_pdfs: list[Path] = []
    for f in pdf_files:
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_pdfs.append(f)

    if not unique_pdfs:
        raise ValueError(f"No PDF files found in: {source_path}")

    batch_id = str(uuid.uuid4())
    batch_name = name or folder.name
    now = datetime.now(timezone.utc).isoformat()

    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO batches (id, name, source_path, created_at, status, total_docs) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (batch_id, batch_name, str(folder), now, len(unique_pdfs)),
        )

        for pdf_file in unique_pdfs:
            doc_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO documents (id, batch_id, filename, filepath, status) "
                "VALUES (?, ?, ?, ?, 'pending')",
                (doc_id, batch_id, pdf_file.name, str(pdf_file)),
            )

    logger.info("Created batch %s with %d documents from %s", batch_id, len(unique_pdfs), folder)
    return batch_id


def _get_pending_documents(batch_id: str) -> list[tuple[str, str]]:
    """Get documents in a batch that haven't been processed yet."""
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT id, filepath FROM documents "
            "WHERE batch_id = ? AND status IN ('pending', 'error') "
            "ORDER BY filename",
            (batch_id,),
        ).fetchall()
    return [(row["id"], row["filepath"]) for row in rows]


def _record_result(result: WorkerResult) -> None:
    """Save a single document's processing result to the database."""
    now = datetime.now(timezone.utc).isoformat()

    with db.transaction() as conn:
        if result.success:
            # Update document status
            conn.execute(
                "UPDATE documents SET status = 'completed', page_count = ?, "
                "finding_count = ?, processed_at = ? WHERE id = ?",
                (result.page_count, len(result.findings_data), now, result.doc_id),
            )

            # Insert findings
            for finding in result.findings_data:
                finding_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO findings "
                    "(id, document_id, page_number, pii_type, confidence, "
                    "context_snippet, char_offset, char_length) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        finding_id,
                        result.doc_id,
                        finding["page_num"],
                        finding["pii_type"],
                        finding["confidence"],
                        finding["context_snippet"],
                        finding["start"],
                        finding["end"] - finding["start"],
                    ),
                )

            # Update batch counters
            doc_row = conn.execute(
                "SELECT batch_id FROM documents WHERE id = ?",
                (result.doc_id,),
            ).fetchone()
            if doc_row:
                batch_id = doc_row["batch_id"]
                conn.execute(
                    "UPDATE batches SET processed_docs = processed_docs + 1 WHERE id = ?",
                    (batch_id,),
                )
                if len(result.findings_data) > 0:
                    conn.execute(
                        "UPDATE batches SET docs_with_findings = docs_with_findings + 1 "
                        "WHERE id = ?",
                        (batch_id,),
                    )
        else:
            conn.execute(
                "UPDATE documents SET status = 'error', processed_at = ? WHERE id = ?",
                (now, result.doc_id),
            )
            logger.error(
                "Document %s failed: %s", result.doc_id, result.error
            )


def start_batch(
    batch_id: str,
    worker_count: int | None = None,
    sequential: bool = False,
) -> dict:
    """Start processing a batch of documents.

    Supports resumability: only processes documents that are pending or errored.

    Args:
        batch_id: The batch to process.
        worker_count: Override default worker count.
        sequential: If True, process sequentially (useful for debugging).

    Returns:
        Summary dict with processed/failed/skipped counts.
    """
    with db.transaction() as conn:
        batch = conn.execute(
            "SELECT * FROM batches WHERE id = ?", (batch_id,)
        ).fetchone()
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")

        conn.execute(
            "UPDATE batches SET status = 'processing' WHERE id = ?",
            (batch_id,),
        )

    pending_docs = _get_pending_documents(batch_id)

    if not pending_docs:
        logger.info("No pending documents in batch %s", batch_id)
        with db.transaction() as conn:
            conn.execute(
                "UPDATE batches SET status = 'completed' WHERE id = ?",
                (batch_id,),
            )
        return {"processed": 0, "failed": 0, "skipped": batch["total_docs"]}

    logger.info(
        "Starting batch %s: %d documents to process", batch_id, len(pending_docs)
    )

    pool = WorkerPool(worker_count=worker_count)

    # Process in chunks to manage memory
    chunk_size = settings.chunk_size
    total_processed = 0
    total_failed = 0

    for i in range(0, len(pending_docs), chunk_size):
        chunk = pending_docs[i : i + chunk_size]

        if sequential:
            results = pool.process_batch_sequential(chunk, on_result=_record_result)
        else:
            results = pool.process_batch(chunk, on_result=_record_result)

        for result in results:
            if result.success:
                total_processed += 1
            else:
                total_failed += 1

    # Update batch status
    with db.transaction() as conn:
        conn.execute(
            "UPDATE batches SET status = 'completed' WHERE id = ?",
            (batch_id,),
        )

    skipped = batch["total_docs"] - len(pending_docs)
    summary = {
        "processed": total_processed,
        "failed": total_failed,
        "skipped": skipped,
    }
    logger.info("Batch %s complete: %s", batch_id, summary)
    return summary
