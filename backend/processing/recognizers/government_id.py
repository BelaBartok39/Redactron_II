"""Custom Presidio recognizers for government IDs: SSN variants, driver's license, passport."""

from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class EnhancedSSNRecognizer(PatternRecognizer):
    """Enhanced SSN detection including partial SSN patterns.

    Matches:
    - Full SSN: 123-45-6789
    - No dashes: 123456789
    - Partial (last 4 near keyword): SSN: XXXX or SSN ending in 1234
    """

    PATTERNS = [
        Pattern(
            "ssn_full_dashes",
            r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b",
            0.85,
        ),
        Pattern(
            "ssn_no_dashes",
            r"(?i)(?:SSN|social\s+security)[\s:]*(?!000|666|9\d\d)\d{3}(?!00)\d{2}(?!0000)\d{4}\b",
            0.8,
        ),
        Pattern(
            "ssn_last4",
            r"(?i)(?:SSN|social\s+security)[\s:]*(?:(?:ending\s+(?:in\s+)?)|(?:last\s+(?:four|4)\s*:?\s*))\d{4}\b",
            0.7,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="US_SSN",
            patterns=self.PATTERNS,
            supported_language="en",
            name="EnhancedSSNRecognizer",
        )


class DriversLicenseRecognizer(PatternRecognizer):
    """Detects US driver's license numbers for common state formats.

    Covers several common state patterns with proximity to keywords.
    """

    PATTERNS = [
        # General: letter followed by digits (many states)
        Pattern(
            "dl_letter_digits",
            r"(?i)(?:driver'?s?\s*license|DL|D\.?L\.?)[\s#:]*[A-Z]\d{6,14}\b",
            0.75,
        ),
        # CA: letter + 7 digits
        Pattern(
            "dl_ca",
            r"(?i)(?:driver'?s?\s*license|DL)[\s#:]*[A-Z]\d{7}\b",
            0.8,
        ),
        # FL: letter + 12 digits
        Pattern(
            "dl_fl",
            r"(?i)(?:driver'?s?\s*license|DL)[\s#:]*[A-Z]\d{12}\b",
            0.8,
        ),
        # TX: 8 digits
        Pattern(
            "dl_tx",
            r"(?i)(?:driver'?s?\s*license|DL)[\s#:]*\d{8}\b",
            0.7,
        ),
        # NY: 9 digits
        Pattern(
            "dl_ny",
            r"(?i)(?:driver'?s?\s*license|DL)[\s#:]*\d{9}\b",
            0.7,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="US_DRIVER_LICENSE",
            patterns=self.PATTERNS,
            supported_language="en",
            name="DriversLicenseRecognizer",
        )


class PassportRecognizer(PatternRecognizer):
    """Detects US passport numbers (9 digits near 'passport' keyword)."""

    PATTERNS = [
        Pattern(
            "passport_9digit",
            r"(?i)passport[\s#:]*\d{9}\b",
            0.85,
        ),
        Pattern(
            "passport_no",
            r"(?i)passport\s+(?:number|no\.?)[\s#:]*\d{9}\b",
            0.9,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="US_PASSPORT",
            patterns=self.PATTERNS,
            supported_language="en",
            name="PassportRecognizer",
        )
