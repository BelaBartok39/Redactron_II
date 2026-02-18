"""Tests for the text extraction layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.processing.extractor import (
    PageText,
    extract_page_pymupdf,
    extract_pages,
    is_image_page,
)


class TestIsImagePage:
    """Tests for image page detection."""

    def test_short_text_is_image(self):
        assert is_image_page("abc", min_text_length=50) is True

    def test_empty_text_is_image(self):
        assert is_image_page("", min_text_length=50) is True

    def test_whitespace_only_is_image(self):
        assert is_image_page("   \n\t  ", min_text_length=50) is True

    def test_long_text_is_not_image(self):
        text = "This is a paragraph with enough text content to pass the threshold."
        assert is_image_page(text, min_text_length=50) is False

    def test_exactly_at_threshold(self):
        text = "x" * 50
        assert is_image_page(text, min_text_length=50) is False

    def test_one_below_threshold(self):
        text = "x" * 49
        assert is_image_page(text, min_text_length=50) is True


class TestExtractPagePyMuPDF:
    """Tests for PyMuPDF text extraction."""

    def test_extracts_text(self):
        page = MagicMock()
        page.get_text.return_value = "Hello World"
        assert extract_page_pymupdf(page) == "Hello World"

    def test_returns_empty_for_none(self):
        page = MagicMock()
        page.get_text.return_value = None
        assert extract_page_pymupdf(page) == ""


class TestExtractPages:
    """Tests for full document extraction."""

    @patch("backend.processing.extractor.fitz")
    def test_text_pages(self, mock_fitz):
        """Test extraction of pages with native text."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)

        page1 = MagicMock()
        page1.get_text.return_value = "Page one has enough text to be considered a text page with native content."
        page2 = MagicMock()
        page2.get_text.return_value = "Page two also has enough text to be considered a text page with native content."
        mock_doc.__getitem__ = MagicMock(side_effect=[page1, page2])

        mock_fitz.open.return_value = mock_doc

        results = extract_pages(Path("/fake/doc.pdf"))

        assert len(results) == 2
        assert results[0].page_num == 1
        assert results[0].method == "pymupdf"
        assert results[0].confidence == 1.0
        assert results[1].page_num == 2

    @patch("backend.processing.extractor.extract_page_ocr")
    @patch("backend.processing.extractor.fitz")
    def test_image_page_triggers_ocr(self, mock_fitz, mock_ocr):
        """Test that pages with little text fall back to OCR."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)

        page = MagicMock()
        page.get_text.return_value = "ab"  # Below threshold
        mock_doc.__getitem__ = MagicMock(return_value=page)

        mock_fitz.open.return_value = mock_doc
        mock_ocr.return_value = ("OCR extracted text for the full page", 0.92)

        results = extract_pages(Path("/fake/scanned.pdf"))

        assert len(results) == 1
        assert results[0].method == "ocr"
        assert results[0].confidence == 0.92
        assert "OCR extracted" in results[0].text

    @patch("backend.processing.extractor.fitz")
    def test_failed_open_returns_empty(self, mock_fitz):
        """Test that a failed PDF open returns an empty list."""
        mock_fitz.open.side_effect = RuntimeError("corrupt file")

        results = extract_pages(Path("/fake/bad.pdf"))
        assert results == []

    @patch("backend.processing.extractor.extract_page_ocr")
    @patch("backend.processing.extractor.fitz")
    def test_ocr_failure_falls_back_to_sparse_text(self, mock_fitz, mock_ocr):
        """Test that OCR failure still returns the sparse native text."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)

        page = MagicMock()
        page.get_text.return_value = "tiny"
        mock_doc.__getitem__ = MagicMock(return_value=page)

        mock_fitz.open.return_value = mock_doc
        mock_ocr.side_effect = RuntimeError("tesseract not found")

        results = extract_pages(Path("/fake/doc.pdf"))

        assert len(results) == 1
        assert results[0].method == "pymupdf"
        assert results[0].confidence == 0.5
        assert results[0].text == "tiny"

    @patch("backend.processing.extractor.fitz")
    def test_page_extraction_error_continues(self, mock_fitz):
        """Test that a single page error doesn't stop other pages."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)

        def getitem(idx):
            if idx == 0:
                raise RuntimeError("page 0 corrupt")
            page = MagicMock()
            page.get_text.return_value = "Page two is fine with enough text content here."
            return page

        mock_doc.__getitem__ = MagicMock(side_effect=getitem)
        mock_fitz.open.return_value = mock_doc

        results = extract_pages(Path("/fake/doc.pdf"))

        assert len(results) == 2
        assert results[0].page_num == 1
        assert results[0].text == ""
        assert results[0].confidence == 0.0
        assert results[1].page_num == 2
        assert results[1].method == "pymupdf"
