"""PII detection engine wrapping Microsoft Presidio."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import spacy
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import SpacyNlpEngine

from backend.core.config import settings
from backend.processing.recognizers.legal_pii import (
    CaseNumberRecognizer,
    LegalRoleNameRecognizer,
)
from backend.processing.recognizers.government_id import (
    DriversLicenseRecognizer,
    EnhancedSSNRecognizer,
    PassportRecognizer,
)
from backend.processing.recognizers.financial_pii import (
    BankAccountRecognizer,
    RoutingNumberRecognizer,
)
from backend.processing.recognizers.medical_pii import MedicalRecordRecognizer
from backend.processing.recognizers.digital_pii import (
    DeviceIDRecognizer,
    MACAddressRecognizer,
)

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    """A single PII detection finding."""

    pii_type: str
    confidence: float
    start: int
    end: int
    page_num: int
    context_snippet: str


CUSTOM_RECOGNIZERS = [
    CaseNumberRecognizer,
    LegalRoleNameRecognizer,
    EnhancedSSNRecognizer,
    DriversLicenseRecognizer,
    PassportRecognizer,
    RoutingNumberRecognizer,
    BankAccountRecognizer,
    MedicalRecordRecognizer,
    MACAddressRecognizer,
    DeviceIDRecognizer,
]


def _load_spacy_model():
    """Load the spaCy NER model.

    In frozen (PyInstaller) mode, loads by path from the bundled data
    directory.  This avoids Presidio's fallback which tries to run
    ``pip install`` via ``sys.executable`` — which in a frozen app
    re-launches the entire exe instead of pip.
    """
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        model_base = bundle_dir / "en_core_web_lg"
        if model_base.is_dir():
            # Find the versioned subdirectory (e.g. en_core_web_lg-3.8.0)
            for subdir in sorted(model_base.iterdir(), reverse=True):
                if subdir.is_dir() and subdir.name.startswith("en_core_web_lg"):
                    logger.info("Loading spaCy model from bundle: %s", subdir)
                    return spacy.load(str(subdir))
        raise RuntimeError(
            "Bundled spaCy model 'en_core_web_lg' not found in frozen app"
        )
    return spacy.load("en_core_web_lg")


def build_analyzer() -> AnalyzerEngine:
    """Create a Presidio AnalyzerEngine with built-in + custom recognizers.

    Pre-loads the spaCy model and injects it into the NLP engine so
    Presidio never attempts to download it at runtime.
    """
    nlp = _load_spacy_model()

    # Build a SpacyNlpEngine with the pre-loaded model so Presidio
    # skips its own load/download logic.
    nlp_engine = SpacyNlpEngine(
        models=[{"lang_code": "en", "model_name": "en_core_web_lg"}],
    )
    nlp_engine.nlp["en"] = nlp

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()

    for recognizer_cls in CUSTOM_RECOGNIZERS:
        registry.add_recognizer(recognizer_cls())

    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)
    return analyzer


def extract_context(text: str, start: int, end: int, window: int | None = None) -> str:
    """Extract a context snippet around a finding.

    Returns ~window chars before and after the match location,
    with the matched text replaced by the PII type placeholder.
    """
    window = window if window is not None else settings.context_chars
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    snippet = text[ctx_start:ctx_end]
    # Replace newlines with spaces for cleaner display
    return " ".join(snippet.split())


def detect_pii(
    text: str,
    page_num: int,
    analyzer: AnalyzerEngine,
    language: str | None = None,
    threshold: float | None = None,
) -> list[Finding]:
    """Run PII detection on text and return findings above the confidence threshold.

    Args:
        text: Text content to scan.
        page_num: Page number for this text (1-indexed).
        analyzer: Presidio AnalyzerEngine instance.
        language: Language code (defaults to settings.default_language).
        threshold: Minimum confidence threshold (defaults to settings.confidence_threshold).

    Returns:
        List of Finding objects for detected PII.
    """
    if not text or not text.strip():
        return []

    language = language or settings.default_language
    threshold = threshold if threshold is not None else settings.confidence_threshold

    try:
        results = analyzer.analyze(text=text, language=language)
    except Exception:
        logger.exception("PII detection failed for page %d", page_num)
        return []

    findings: list[Finding] = []
    for result in results:
        if result.score < threshold:
            continue

        context = extract_context(text, result.start, result.end)

        findings.append(Finding(
            pii_type=result.entity_type,
            confidence=result.score,
            start=result.start,
            end=result.end,
            page_num=page_num,
            context_snippet=context,
        ))

    return findings
