"""Custom Presidio recognizers for digital PII: MAC addresses, device IDs."""

from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class MACAddressRecognizer(PatternRecognizer):
    """Detects network MAC addresses.

    Matches formats:
    - Colon-separated: AA:BB:CC:DD:EE:FF
    - Dash-separated: AA-BB-CC-DD-EE-FF
    """

    PATTERNS = [
        Pattern(
            "mac_colon",
            r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b",
            0.8,
        ),
        Pattern(
            "mac_dash",
            r"\b[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5}\b",
            0.8,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="MAC_ADDRESS",
            patterns=self.PATTERNS,
            supported_language="en",
            name="MACAddressRecognizer",
        )


class DeviceIDRecognizer(PatternRecognizer):
    """Detects device identifiers: IMEI numbers and serial numbers near device keywords."""

    PATTERNS = [
        Pattern(
            "imei",
            r"(?i)IMEI[\s#:.]*\d{15}\b",
            0.9,
        ),
        Pattern(
            "imei_bare",
            r"\b\d{15}\b",
            0.3,  # Low confidence unless near keyword (filtered by context)
        ),
        Pattern(
            "serial_number",
            r"(?i)(?:serial\s+(?:number|no\.?)|S/?N)[\s#:.]*[A-Z0-9]{6,20}\b",
            0.75,
        ),
        Pattern(
            "device_id_keyword",
            r"(?i)(?:device\s+(?:ID|identifier)|MEID|ESN)[\s#:.]*[A-Z0-9]{8,18}\b",
            0.8,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="DEVICE_ID",
            patterns=self.PATTERNS,
            supported_language="en",
            name="DeviceIDRecognizer",
        )
