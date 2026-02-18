"""Tests for the processing pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.processing.detector import Finding
from backend.processing.extractor import PageText
from backend.processing.pipeline import process_document, get_page_count


class TestProcessDocument:
    """Tests for the document processing pipeline."""

    @patch("backend.processing.pipeline.detect_pii")
    @patch("backend.processing.pipeline.extract_pages")
    def test_basic_processing(self, mock_extract, mock_detect):
        """Test that pages are extracted and PII detected."""
        mock_extract.return_value = [
            PageText(page_num=1, text="John Smith SSN 123-45-6789", method="pymupdf", confidence=1.0),
            PageText(page_num=2, text="More text on page two here.", method="pymupdf", confidence=1.0),
        ]

        finding1 = Finding(
            pii_type="US_SSN", confidence=0.85, start=15, end=26,
            page_num=1, context_snippet="Smith SSN 123-45-6789",
        )
        mock_detect.side_effect = [[finding1], []]

        analyzer = MagicMock()
        results = process_document(Path("/fake/doc.pdf"), "doc-1", analyzer=analyzer)

        assert len(results) == 1
        assert results[0].pii_type == "US_SSN"
        assert results[0].page_num == 1

    @patch("backend.processing.pipeline.extract_pages")
    def test_no_pages_returns_empty(self, mock_extract):
        """Test that a document with no extractable pages returns empty."""
        mock_extract.return_value = []

        analyzer = MagicMock()
        results = process_document(Path("/fake/empty.pdf"), "doc-2", analyzer=analyzer)
        assert results == []

    @patch("backend.processing.pipeline.detect_pii")
    @patch("backend.processing.pipeline.extract_pages")
    def test_empty_pages_skipped(self, mock_extract, mock_detect):
        """Test that pages with no text content are skipped."""
        mock_extract.return_value = [
            PageText(page_num=1, text="", method="pymupdf", confidence=0.0),
            PageText(page_num=2, text="   ", method="pymupdf", confidence=0.0),
            PageText(page_num=3, text="Real content here.", method="pymupdf", confidence=1.0),
        ]

        mock_detect.return_value = []

        analyzer = MagicMock()
        process_document(Path("/fake/doc.pdf"), "doc-3", analyzer=analyzer)

        # detect_pii should only be called for page 3
        assert mock_detect.call_count == 1

    @patch("backend.processing.pipeline.detect_pii")
    @patch("backend.processing.pipeline.extract_pages")
    def test_multiple_findings_per_page(self, mock_extract, mock_detect):
        """Test that multiple findings per page are all collected."""
        mock_extract.return_value = [
            PageText(
                page_num=1,
                text="Email: test@example.com, Phone: 555-123-4567",
                method="pymupdf",
                confidence=1.0,
            ),
        ]

        findings = [
            Finding(
                pii_type="EMAIL_ADDRESS", confidence=0.95, start=7, end=23,
                page_num=1, context_snippet="Email: test@example.com",
            ),
            Finding(
                pii_type="PHONE_NUMBER", confidence=0.8, start=32, end=44,
                page_num=1, context_snippet="Phone: 555-123-4567",
            ),
        ]
        mock_detect.return_value = findings

        analyzer = MagicMock()
        results = process_document(Path("/fake/doc.pdf"), "doc-4", analyzer=analyzer)

        assert len(results) == 2
        assert results[0].pii_type == "EMAIL_ADDRESS"
        assert results[1].pii_type == "PHONE_NUMBER"

    @patch("backend.processing.pipeline.build_analyzer")
    @patch("backend.processing.pipeline.detect_pii")
    @patch("backend.processing.pipeline.extract_pages")
    def test_creates_analyzer_if_none(self, mock_extract, mock_detect, mock_build):
        """Test that an analyzer is created if none is provided."""
        mock_extract.return_value = []
        mock_build.return_value = MagicMock()

        process_document(Path("/fake/doc.pdf"), "doc-5")
        mock_build.assert_called_once()


class TestGetPageCount:
    """Tests for page count extraction."""

    @patch("backend.processing.pipeline.fitz")
    def test_page_count(self, mock_fitz):
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=5)
        mock_fitz.open.return_value = mock_doc

        count = get_page_count(Path("/fake/doc.pdf"))
        assert count == 5

    @patch("backend.processing.pipeline.fitz")
    def test_page_count_error(self, mock_fitz):
        mock_fitz.open.side_effect = RuntimeError("bad file")

        count = get_page_count(Path("/fake/bad.pdf"))
        assert count == 0
