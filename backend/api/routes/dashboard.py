"""Dashboard statistics endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.schemas.models import PIITypeCount, StatsResponse
from backend.core.database import db

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    """Global statistics across all batches."""
    with db.get_connection() as conn:
        batch_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM batches"
        ).fetchone()["cnt"]

        doc_row = conn.execute(
            "SELECT COUNT(*) as cnt, "
            "COALESCE(SUM(CASE WHEN finding_count > 0 THEN 1 ELSE 0 END), 0) as with_findings "
            "FROM documents"
        ).fetchone()

        finding_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM findings"
        ).fetchone()["cnt"]

        pii_rows = conn.execute(
            "SELECT pii_type, COUNT(*) as cnt FROM findings GROUP BY pii_type ORDER BY cnt DESC"
        ).fetchall()

    return StatsResponse(
        total_batches=batch_count,
        total_documents=doc_row["cnt"],
        total_findings=finding_count,
        docs_with_findings=doc_row["with_findings"],
        pii_type_counts={row["pii_type"]: row["cnt"] for row in pii_rows},
    )


@router.get("/pii-types", response_model=list[PIITypeCount])
def get_pii_types() -> list[PIITypeCount]:
    """PII type breakdown with counts and average confidence."""
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT pii_type, COUNT(*) as count, AVG(confidence) as avg_confidence "
            "FROM findings GROUP BY pii_type ORDER BY count DESC"
        ).fetchall()

    return [
        PIITypeCount(
            pii_type=row["pii_type"],
            count=row["count"],
            avg_confidence=round(row["avg_confidence"], 4),
        )
        for row in rows
    ]
