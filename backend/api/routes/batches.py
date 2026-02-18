"""Batch scan endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.api.schemas.models import BatchDetail, BatchSummary, DocumentSummary, ScanRequest
from backend.core.config import settings
from backend.core.database import db

router = APIRouter(prefix="/api", tags=["batches"])


def _start_batch_processing(batch_id: str) -> None:
    """Trigger batch processing in background. Imports lazily to avoid circular deps."""
    import logging

    log = logging.getLogger(__name__)
    try:
        from backend.processing.batch_manager import start_batch

        start_batch(batch_id)
    except ImportError:
        # Processing engine not yet available; batch stays in 'pending'
        pass
    except Exception:
        log.exception("Batch processing failed for %s", batch_id)
        # Mark batch as error so the UI doesn't show "Scanning..." forever
        try:
            with db.transaction() as conn:
                conn.execute(
                    "UPDATE batches SET status = 'error' WHERE id = ?",
                    (batch_id,),
                )
        except Exception:
            log.exception("Failed to mark batch %s as error", batch_id)


@router.post("/scan", response_model=BatchSummary)
def start_scan(req: ScanRequest, background_tasks: BackgroundTasks) -> BatchSummary:
    """Start a new batch scan of a folder of PDFs."""
    folder = Path(req.source_path)
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory not found: {req.source_path}")

    pdf_files = sorted(folder.glob("*.pdf")) + sorted(folder.glob("*.PDF"))
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No PDF files found in the specified folder.")

    batch_id = uuid.uuid4().hex
    name = req.name or folder.name
    created_at = datetime.now(timezone.utc).isoformat()

    # Apply optional overrides
    if req.confidence_threshold is not None:
        settings.confidence_threshold = req.confidence_threshold
    if req.worker_count is not None:
        settings.worker_count = req.worker_count

    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO batches (id, name, source_path, created_at, status, total_docs) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (batch_id, name, str(folder), created_at, len(pdf_files)),
        )

        # Pre-create document records
        doc_rows = []
        for pdf_path in pdf_files:
            doc_id = uuid.uuid4().hex
            doc_rows.append((doc_id, batch_id, pdf_path.name, str(pdf_path)))
        conn.executemany(
            "INSERT INTO documents (id, batch_id, filename, filepath) VALUES (?, ?, ?, ?)",
            doc_rows,
        )

    background_tasks.add_task(_start_batch_processing, batch_id)

    return BatchSummary(
        id=batch_id,
        name=name,
        source_path=str(folder),
        created_at=created_at,
        status="pending",
        total_docs=len(pdf_files),
        processed_docs=0,
        docs_with_findings=0,
    )


@router.get("/batches", response_model=list[BatchSummary])
def list_batches() -> list[BatchSummary]:
    """List all batches sorted by creation time (newest first)."""
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, source_path, created_at, status, "
            "total_docs, processed_docs, docs_with_findings "
            "FROM batches ORDER BY created_at DESC"
        ).fetchall()
    return [BatchSummary(**dict(r)) for r in rows]


@router.get("/batches/{batch_id}", response_model=BatchDetail)
def get_batch(batch_id: str) -> BatchDetail:
    """Get batch detail including its documents."""
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, source_path, created_at, status, "
            "total_docs, processed_docs, docs_with_findings "
            "FROM batches WHERE id = ?",
            (batch_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Batch not found")

        doc_rows = conn.execute(
            "SELECT id, batch_id, filename, page_count, status, finding_count, processed_at "
            "FROM documents WHERE batch_id = ? ORDER BY filename",
            (batch_id,),
        ).fetchall()

    return BatchDetail(
        **dict(row),
        documents=[DocumentSummary(**dict(d)) for d in doc_rows],
    )


@router.delete("/batches/{batch_id}")
def delete_batch(batch_id: str) -> dict[str, str]:
    """Delete a batch and cascade to its documents and findings."""
    with db.transaction() as conn:
        row = conn.execute("SELECT id FROM batches WHERE id = ?", (batch_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        # CASCADE handles documents and findings
        conn.execute("DELETE FROM batches WHERE id = ?", (batch_id,))
    return {"status": "deleted", "batch_id": batch_id}
