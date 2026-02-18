"""Tests for the PII detection engine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.processing.detector import Finding, detect_pii, extract_context


class TestExtractContext:
    """Tests for context snippet extraction."""

    def test_basic_context(self):
        text = "Hello my name is John Smith and I live here."
        # "John Smith" is at positions 17-27
        context = extract_context(text, 17, 27, window=10)
        assert "John Smith" in context
        assert len(context) <= 30  # roughly 10 + 10 + 10

    def test_context_at_start(self):
        text = "John Smith is here."
        context = extract_context(text, 0, 10, window=20)
        assert "John Smith" in context

    def test_context_at_end(self):
        text = "The name is John Smith"
        context = extract_context(text, 12, 22, window=20)
        assert "John Smith" in context

    def test_newlines_replaced(self):
        text = "before\n\nJohn Smith\n\nafter"
        context = extract_context(text, 8, 18, window=10)
        assert "\n" not in context

    def test_empty_text(self):
        context = extract_context("", 0, 0, window=20)
        assert context == ""


class TestDetectPII:
    """Tests for PII detection with known samples."""

    @pytest.fixture
    def mock_analyzer(self):
        analyzer = MagicMock()
        return analyzer

    def test_empty_text_returns_no_findings(self, mock_analyzer):
        findings = detect_pii("", page_num=1, analyzer=mock_analyzer)
        assert findings == []

    def test_whitespace_text_returns_no_findings(self, mock_analyzer):
        findings = detect_pii("   \n\t  ", page_num=1, analyzer=mock_analyzer)
        assert findings == []

    def test_findings_returned_with_context(self, mock_analyzer):
        text = "Contact me at john.doe@example.com for details."

        mock_result = MagicMock()
        mock_result.entity_type = "EMAIL_ADDRESS"
        mock_result.score = 0.95
        mock_result.start = 14
        mock_result.end = 34

        mock_analyzer.analyze.return_value = [mock_result]

        findings = detect_pii(text, page_num=3, analyzer=mock_analyzer)

        assert len(findings) == 1
        assert findings[0].pii_type == "EMAIL_ADDRESS"
        assert findings[0].confidence == 0.95
        assert findings[0].page_num == 3
        assert findings[0].start == 14
        assert findings[0].end == 34
        assert "john.doe@example.com" in findings[0].context_snippet

    def test_below_threshold_filtered(self, mock_analyzer):
        text = "Some text with possible PII."

        mock_result = MagicMock()
        mock_result.entity_type = "PERSON"
        mock_result.score = 0.2
        mock_result.start = 0
        mock_result.end = 4

        mock_analyzer.analyze.return_value = [mock_result]

        findings = detect_pii(text, page_num=1, analyzer=mock_analyzer, threshold=0.5)
        assert findings == []

    def test_multiple_findings(self, mock_analyzer):
        text = "SSN: 123-45-6789, Email: test@example.com"

        result1 = MagicMock()
        result1.entity_type = "US_SSN"
        result1.score = 0.85
        result1.start = 5
        result1.end = 16

        result2 = MagicMock()
        result2.entity_type = "EMAIL_ADDRESS"
        result2.score = 0.95
        result2.start = 25
        result2.end = 41

        mock_analyzer.analyze.return_value = [result1, result2]

        findings = detect_pii(text, page_num=1, analyzer=mock_analyzer)
        assert len(findings) == 2
        assert findings[0].pii_type == "US_SSN"
        assert findings[1].pii_type == "EMAIL_ADDRESS"

    def test_analyzer_exception_returns_empty(self, mock_analyzer):
        mock_analyzer.analyze.side_effect = RuntimeError("engine error")

        findings = detect_pii("Some text", page_num=1, analyzer=mock_analyzer)
        assert findings == []

    def test_custom_threshold(self, mock_analyzer):
        text = "John Smith at 555-1234"

        result = MagicMock()
        result.entity_type = "PHONE_NUMBER"
        result.score = 0.6
        result.start = 14
        result.end = 22

        mock_analyzer.analyze.return_value = [result]

        # Below custom threshold
        findings = detect_pii(text, page_num=1, analyzer=mock_analyzer, threshold=0.7)
        assert findings == []

        # Above custom threshold
        findings = detect_pii(text, page_num=1, analyzer=mock_analyzer, threshold=0.5)
        assert len(findings) == 1
