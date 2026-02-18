"""Custom Presidio recognizers for medical PII: medical record numbers."""

from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class MedicalRecordRecognizer(PatternRecognizer):
    """Detects medical record numbers near relevant keywords.

    Matches patterns like:
    - MRN: 12345678
    - Medical Record No. 12345678
    - Patient ID: 12345678
    """

    PATTERNS = [
        Pattern(
            "mrn_keyword",
            r"(?i)MRN[\s#:.]*\d{5,12}\b",
            0.9,
        ),
        Pattern(
            "medical_record_no",
            r"(?i)medical\s+record[\s#:.]*(?:number|no\.?)?[\s#:.]*\d{5,12}\b",
            0.85,
        ),
        Pattern(
            "patient_id",
            r"(?i)patient\s+(?:ID|identifier|number|no\.?)[\s#:.]*\d{5,12}\b",
            0.85,
        ),
        Pattern(
            "health_record",
            r"(?i)health\s+record[\s#:.]*(?:number|no\.?)?[\s#:.]*\d{5,12}\b",
            0.8,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="MEDICAL_RECORD",
            patterns=self.PATTERNS,
            supported_language="en",
            name="MedicalRecordRecognizer",
        )
