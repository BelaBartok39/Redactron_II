"""Report generation and download endpoints."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.api.schemas.models import ReportRequest, ReportResponse
from backend.core.config import settings
from backend.core.database import db

router = APIRouter(prefix="/api", tags=["reports"])

# In-memory report metadata store (keyed by report ID)
_reports: dict[str, dict] = {}


def _generate_report_background(report_id: str, batch_id: str, fmt: str) -> None:
    """Run report generation in a background thread."""
    try:
        from backend.reports.generator import generate_report

        path = generate_report(batch_id, fmt)
        _reports[report_id]["status"] = "completed"
        _reports[report_id]["filename"] = path.name
        _reports[report_id]["filepath"] = str(path)
    except Exception as exc:
        _reports[report_id]["status"] = "failed"
        _reports[report_id]["error"] = str(exc)


@router.post("/reports/generate", response_model=ReportResponse)
def generate_report_endpoint(req: ReportRequest) -> ReportResponse:
    """Generate a PDF or CSV report for a batch."""
    with db.get_connection() as conn:
        batch = conn.execute(
            "SELECT id FROM batches WHERE id = ?", (req.batch_id,)
        ).fetchone()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")

    report_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()

    _reports[report_id] = {
        "id": report_id,
        "batch_id": req.batch_id,
        "format": req.format,
        "status": "generating",
        "created_at": created_at,
        "filename": None,
        "filepath": None,
    }

    thread = threading.Thread(
        target=_generate_report_background,
        args=(report_id, req.batch_id, req.format),
        daemon=True,
    )
    thread.start()

    return ReportResponse(
        id=report_id,
        batch_id=req.batch_id,
        format=req.format,
        status="generating",
        created_at=created_at,
    )


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report_status(report_id: str) -> ReportResponse:
    """Check the status of a report."""
    meta = _reports.get(report_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse(
        id=meta["id"],
        batch_id=meta["batch_id"],
        format=meta["format"],
        status=meta["status"],
        created_at=meta["created_at"],
        filename=meta.get("filename"),
    )


@router.get("/reports/{report_id}/download")
def download_report(report_id: str) -> FileResponse:
    """Download a generated report file."""
    meta = _reports.get(report_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if meta["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Report is not ready (status: {meta['status']})",
        )

    filepath = meta.get("filepath")
    if filepath is None:
        raise HTTPException(status_code=500, detail="Report file path missing")

    content_type = (
        "application/pdf" if meta["format"] == "pdf" else "text/csv"
    )
    return FileResponse(
        path=filepath,
        filename=meta["filename"],
        media_type=content_type,
    )
