"""Custom Presidio recognizers for legal PII: case numbers and legal role names."""

from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult, EntityRecognizer
from presidio_analyzer.nlp_engine import NlpArtifacts


class CaseNumberRecognizer(PatternRecognizer):
    """Detects legal case number patterns.

    Matches formats like:
    - 24-CV-12345, 2024-CR-123456
    - Case No. 12-345678
    - Docket No. 2024-12345
    """

    PATTERNS = [
        Pattern(
            "case_number_dashed",
            r"\b\d{2,4}-(?:CV|CR|CIV|CRIM|MC|MJ|JV|DR|PR|AP|BK)-\d{4,8}\b",
            0.85,
        ),
        Pattern(
            "case_no_prefix",
            r"(?i)\bCase\s+No\.?\s*[:\s]?\s*\d{2,4}[-\s]?\d{3,8}\b",
            0.9,
        ),
        Pattern(
            "docket_no",
            r"(?i)\bDocket\s+(?:No\.?\s*)?[:\s]?\s*\d{2,4}[-\s]?\d{3,8}\b",
            0.9,
        ),
        Pattern(
            "cause_no",
            r"(?i)\bCause\s+No\.?\s*[:\s]?\s*\d{2,4}[-\s]?\d{3,8}\b",
            0.85,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="CASE_NUMBER",
            patterns=self.PATTERNS,
            supported_language="en",
            name="CaseNumberRecognizer",
        )


LEGAL_ROLE_KEYWORDS = (
    r"(?i)\b(?:judge|justice|attorney|counsel|lawyer|defendant|plaintiff|"
    r"victim|witness|minor|juvenile|suspect|respondent|petitioner|"
    r"complainant|informant|officer|detective|agent)\b"
)


class LegalRoleNameRecognizer(EntityRecognizer):
    """Detects person names appearing near legal role keywords.

    Relies on spaCy NER to find PERSON entities, then checks if they appear
    within a window of legal role keywords like 'judge', 'attorney', 'victim', etc.
    """

    WINDOW = 100  # characters to search for keyword proximity

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["LEGAL_ROLE_NAME"],
            supported_language="en",
            name="LegalRoleNameRecognizer",
        )

    def load(self) -> None:
        """No external resources to load."""

    def analyze(
        self, text: str, entities: list[str], nlp_artifacts: NlpArtifacts = None
    ) -> list[RecognizerResult]:
        import re

        results: list[RecognizerResult] = []
        if nlp_artifacts is None or nlp_artifacts.entities is None:
            return results

        # Find all legal role keyword positions
        keyword_positions: list[tuple[int, int]] = []
        for match in re.finditer(LEGAL_ROLE_KEYWORDS, text):
            keyword_positions.append((match.start(), match.end()))

        if not keyword_positions:
            return results

        for entity in nlp_artifacts.entities:
            if entity.label_ != "PERSON":
                continue

            start = entity.start_char
            end = entity.end_char

            # Check proximity to any legal role keyword
            for kw_start, kw_end in keyword_positions:
                distance = min(abs(start - kw_end), abs(kw_start - end))
                if distance <= self.WINDOW:
                    confidence = 0.75 if distance > 50 else 0.85
                    results.append(
                        RecognizerResult(
                            entity_type="LEGAL_ROLE_NAME",
                            start=start,
                            end=end,
                            score=confidence,
                        )
                    )
                    break  # One match per entity

        return results
