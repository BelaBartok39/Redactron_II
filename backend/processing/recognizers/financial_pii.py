"""Custom Presidio recognizers for financial PII: routing numbers, bank accounts."""

from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult, EntityRecognizer
from presidio_analyzer.nlp_engine import NlpArtifacts


class RoutingNumberRecognizer(EntityRecognizer):
    """Detects ABA routing numbers (9 digits with valid check digit).

    ABA check digit algorithm: the sum of
      3*(d1+d4+d7) + 7*(d2+d5+d8) + (d3+d6+d9)
    must be divisible by 10.
    """

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["ROUTING_NUMBER"],
            supported_language="en",
            name="RoutingNumberRecognizer",
        )

    def load(self) -> None:
        """No external resources to load."""

    def analyze(
        self, text: str, entities: list[str], nlp_artifacts: NlpArtifacts = None
    ) -> list[RecognizerResult]:
        import re

        results: list[RecognizerResult] = []
        # Look for 9-digit sequences near financial keywords
        for match in re.finditer(r"\b(\d{9})\b", text):
            digits = match.group(1)
            if self._valid_aba_check(digits):
                # Check proximity to financial keywords
                window_start = max(0, match.start() - 80)
                window_end = min(len(text), match.end() + 80)
                window = text[window_start:window_end].lower()

                keywords = ("routing", "aba", "transit", "bank", "wire", "ach")
                if any(kw in window for kw in keywords):
                    score = 0.85
                else:
                    score = 0.5

                results.append(
                    RecognizerResult(
                        entity_type="ROUTING_NUMBER",
                        start=match.start(),
                        end=match.end(),
                        score=score,
                    )
                )

        return results

    @staticmethod
    def _valid_aba_check(digits: str) -> bool:
        """Validate ABA routing number check digit."""
        d = [int(c) for c in digits]
        checksum = 3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])
        return checksum % 10 == 0


class BankAccountRecognizer(PatternRecognizer):
    """Detects bank account numbers (8-17 digits near financial keywords)."""

    PATTERNS = [
        Pattern(
            "bank_account_keyword",
            r"(?i)(?:account|acct)[\s#:.]*\d{8,17}\b",
            0.75,
        ),
        Pattern(
            "bank_account_number",
            r"(?i)(?:bank|checking|savings|deposit)\s+(?:account|acct)[\s#:.]*\d{8,17}\b",
            0.85,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="US_BANK_NUMBER",
            patterns=self.PATTERNS,
            supported_language="en",
            name="BankAccountRecognizer",
        )
