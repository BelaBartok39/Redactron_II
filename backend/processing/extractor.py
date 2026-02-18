"""Text extraction from PDF documents using PyMuPDF and Tesseract OCR."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    """Extracted text for a single page."""

    page_num: int
    text: str
    method: str  # "pymupdf" or "ocr"
    confidence: float  # 1.0 for native text, OCR confidence for scanned


def extract_page_pymupdf(page: fitz.Page) -> str:
    """Extract text from a single PyMuPDF page object."""
    return page.get_text("text") or ""


def extract_page_ocr(page: fitz.Page, dpi: int | None = None) -> tuple[str, float]:
    """Run Tesseract OCR on a page rendered as an image.

    Returns (text, confidence) tuple.
    """
    import pytesseract
    from PIL import Image
    import io

    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    dpi = dpi or settings.ocr_dpi
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img = Image.open(io.BytesIO(pix.tobytes("png")))

    # Get detailed OCR data for confidence
    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    # Compute average confidence from words that have a valid confidence score
    confidences = [
        int(c) for c in ocr_data.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) >= 0
    ]
    avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

    text = pytesseract.image_to_string(img)
    return text.strip(), avg_confidence


def is_image_page(text: str, min_text_length: int | None = None) -> bool:
    """Determine if a page is image-only (very little extractable text)."""
    threshold = min_text_length if min_text_length is not None else settings.min_text_length
    return len(text.strip()) < threshold


def extract_pages(pdf_path: Path) -> list[PageText]:
    """Extract text from all pages of a PDF document.

    Uses PyMuPDF for text-layer pages and falls back to Tesseract OCR
    for image-only pages. Each page is processed independently so one
    bad page does not prevent extraction of others.
    """
    results: list[PageText] = []

    try:
        doc = fitz.open(str(pdf_path))
    except Exception:
        logger.exception("Failed to open PDF: %s", pdf_path)
        return results

    try:
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                native_text = extract_page_pymupdf(page)

                if is_image_page(native_text):
                    # Fall back to OCR
                    try:
                        ocr_text, confidence = extract_page_ocr(page)
                        results.append(PageText(
                            page_num=page_num + 1,  # 1-indexed
                            text=ocr_text,
                            method="ocr",
                            confidence=confidence,
                        ))
                    except Exception:
                        logger.warning(
                            "OCR failed for page %d of %s, using sparse native text",
                            page_num + 1,
                            pdf_path,
                        )
                        results.append(PageText(
                            page_num=page_num + 1,
                            text=native_text,
                            method="pymupdf",
                            confidence=0.5,
                        ))
                else:
                    results.append(PageText(
                        page_num=page_num + 1,
                        text=native_text,
                        method="pymupdf",
                        confidence=1.0,
                    ))
            except Exception:
                logger.exception("Failed to extract page %d from %s", page_num + 1, pdf_path)
                results.append(PageText(
                    page_num=page_num + 1,
                    text="",
                    method="pymupdf",
                    confidence=0.0,
                ))
    finally:
        doc.close()

    return results
