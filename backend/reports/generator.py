"""Report orchestration — delegates to PDF or CSV generators."""

from __future__ import annotations

from pathlib import Path

from backend.core.config import settings
from backend.core.database import db


def _fetch_batch_data(batch_id: str) -> dict:
    """Fetch all data needed for a report."""
    with db.get_connection() as conn:
        batch = conn.execute(
            "SELECT id, name, source_path, created_at, status, "
            "total_docs, processed_docs, docs_with_findings "
            "FROM batches WHERE id = ?",
            (batch_id,),
        ).fetchone()
        if batch is None:
            raise ValueError(f"Batch not found: {batch_id}")

        documents = conn.execute(
            "SELECT id, batch_id, filename, page_count, status, finding_count, processed_at "
            "FROM documents WHERE batch_id = ? ORDER BY filename",
            (batch_id,),
        ).fetchall()

        findings = conn.execute(
            "SELECT f.id, f.document_id, f.page_number, f.pii_type, f.confidence, "
            "f.context_snippet, f.char_offset, f.char_length "
            "FROM findings f "
            "JOIN documents d ON f.document_id = d.id "
            "WHERE d.batch_id = ? "
            "ORDER BY d.filename, f.page_number, f.char_offset",
            (batch_id,),
        ).fetchall()

    # Group findings by document_id
    findings_by_doc: dict[str, list[dict]] = {}
    for f in findings:
        fd = dict(f)
        findings_by_doc.setdefault(fd["document_id"], []).append(fd)

    return {
        "batch": dict(batch),
        "documents": [dict(d) for d in documents],
        "findings_by_doc": findings_by_doc,
    }


def generate_report(batch_id: str, fmt: str) -> Path:
    """Generate a report and return the file path.

    Args:
        batch_id: The batch to report on.
        fmt: Either "pdf" or "csv".

    Returns:
        Path to the generated report file.
    """
    data = _fetch_batch_data(batch_id)
    settings.ensure_dirs()
    reports_dir = settings.resolved_reports_dir

    batch_name = data["batch"]["name"].replace(" ", "_")

    if fmt == "pdf":
        from backend.reports.pdf_report import generate_pdf

        filename = f"RedactQC_{batch_name}_{batch_id[:8]}.pdf"
        output_path = reports_dir / filename
        generate_pdf(data, output_path)
    elif fmt == "csv":
        from backend.reports.csv_export import generate_csv

        filename = f"RedactQC_{batch_name}_{batch_id[:8]}.csv"
        output_path = reports_dir / filename
        generate_csv(data, output_path)
    else:
        raise ValueError(f"Unsupported report format: {fmt}")

    return output_path
