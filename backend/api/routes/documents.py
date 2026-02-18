"""Document and findings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.api.schemas.models import (
    DocumentDetail,
    DocumentSummary,
    Finding,
    PaginatedResponse,
)
from backend.core.database import db

router = APIRouter(prefix="/api", tags=["documents"])


@router.get(
    "/batches/{batch_id}/documents",
    response_model=PaginatedResponse[DocumentSummary],
)
def list_documents(
    batch_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort_by: str = Query("filename", pattern=r"^(filename|status|finding_count|processed_at)$"),
    sort_order: str = Query("asc", pattern=r"^(asc|desc)$"),
    pii_type: str | None = None,
    min_confidence: float | None = None,
    has_findings: bool | None = None,
) -> PaginatedResponse[DocumentSummary]:
    """List documents in a batch with pagination and optional filters."""
    with db.get_connection() as conn:
        # Verify batch exists
        batch = conn.execute("SELECT id FROM batches WHERE id = ?", (batch_id,)).fetchone()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")

        conditions = ["d.batch_id = ?"]
        params: list[object] = [batch_id]

        if has_findings is True:
            conditions.append("d.finding_count > 0")
        elif has_findings is False:
            conditions.append("d.finding_count = 0")

        if pii_type is not None:
            conditions.append(
                "d.id IN (SELECT DISTINCT document_id FROM findings WHERE pii_type = ?)"
            )
            params.append(pii_type)

        if min_confidence is not None:
            conditions.append(
                "d.id IN (SELECT DISTINCT document_id FROM findings WHERE confidence >= ?)"
            )
            params.append(min_confidence)

        where_clause = " AND ".join(conditions)

        # Total count
        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM documents d WHERE {where_clause}",  # noqa: S608
            params,
        ).fetchone()["cnt"]

        # Column name is validated by the regex on sort_by, safe for interpolation
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT d.id, d.batch_id, d.filename, d.page_count, d.status, "  # noqa: S608
            f"d.finding_count, d.processed_at "
            f"FROM documents d WHERE {where_clause} "
            f"ORDER BY d.{sort_by} {sort_order} "
            f"LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

    return PaginatedResponse[DocumentSummary](
        items=[DocumentSummary(**dict(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str) -> DocumentDetail:
    """Get document detail with all findings."""
    with db.get_connection() as conn:
        doc = conn.execute(
            "SELECT id, batch_id, filename, page_count, status, finding_count, processed_at "
            "FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        finding_rows = conn.execute(
            "SELECT id, document_id, page_number, pii_type, confidence, "
            "context_snippet, char_offset, char_length "
            "FROM findings WHERE document_id = ? ORDER BY page_number, char_offset",
            (document_id,),
        ).fetchall()

    return DocumentDetail(
        **dict(doc),
        findings=[Finding(**dict(f)) for f in finding_rows],
    )


@router.get(
    "/documents/{document_id}/findings",
    response_model=PaginatedResponse[Finding],
)
def list_findings(
    document_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    pii_type: str | None = None,
    min_confidence: float | None = None,
) -> PaginatedResponse[Finding]:
    """List findings for a document with optional filters."""
    with db.get_connection() as conn:
        doc = conn.execute("SELECT id FROM documents WHERE id = ?", (document_id,)).fetchone()
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        conditions = ["document_id = ?"]
        params: list[object] = [document_id]

        if pii_type is not None:
            conditions.append("pii_type = ?")
            params.append(pii_type)

        if min_confidence is not None:
            conditions.append("confidence >= ?")
            params.append(min_confidence)

        where_clause = " AND ".join(conditions)

        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM findings WHERE {where_clause}",  # noqa: S608
            params,
        ).fetchone()["cnt"]

        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT id, document_id, page_number, pii_type, confidence, "  # noqa: S608
            f"context_snippet, char_offset, char_length "
            f"FROM findings WHERE {where_clause} "
            f"ORDER BY page_number, char_offset "
            f"LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

    return PaginatedResponse[Finding](
        items=[Finding(**dict(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
