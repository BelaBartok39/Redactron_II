"""Processing pipeline: orchestrates extraction and PII detection for a single document."""

from __future__ import annotations

import logging
from pathlib import Path

import fitz

from presidio_analyzer import AnalyzerEngine

from backend.processing.extractor import extract_pages
from backend.processing.detector import Finding, build_analyzer, detect_pii

logger = logging.getLogger(__name__)


def process_document(
    doc_path: Path,
    doc_id: str,
    analyzer: AnalyzerEngine | None = None,
) -> list[Finding]:
    """Process a single document: extract text per page, then detect PII.

    Args:
        doc_path: Path to the PDF file.
        doc_id: Document identifier (for logging).
        analyzer: Optional pre-built Presidio AnalyzerEngine.
                  If None, a new one is created (useful for single-doc processing).

    Returns:
        List of all PII findings across all pages.
    """
    if analyzer is None:
        analyzer = build_analyzer()

    logger.info("Processing document %s: %s", doc_id, doc_path)

    pages = extract_pages(doc_path)
    if not pages:
        logger.warning("No pages extracted from %s", doc_path)
        return []

    all_findings: list[Finding] = []

    for page in pages:
        if not page.text.strip():
            continue

        page_findings = detect_pii(
            text=page.text,
            page_num=page.page_num,
            analyzer=analyzer,
        )
        all_findings.extend(page_findings)

    logger.info(
        "Document %s: %d pages, %d findings",
        doc_id,
        len(pages),
        len(all_findings),
    )

    return all_findings


def get_page_count(doc_path: Path) -> int:
    """Get the number of pages in a PDF without full extraction."""
    try:
        doc = fitz.open(str(doc_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        logger.exception("Failed to get page count for %s", doc_path)
        return 0
