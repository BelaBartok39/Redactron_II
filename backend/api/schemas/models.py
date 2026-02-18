"""Pydantic request/response models for the RedactQC API."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Requests ──────────────────────────────────────────────────────────────────


class ScanRequest(BaseModel):
    source_path: str
    name: str | None = None
    confidence_threshold: float | None = None
    worker_count: int | None = None


class ReportRequest(BaseModel):
    batch_id: str
    format: str = Field(pattern=r"^(pdf|csv)$")


# ── Findings ──────────────────────────────────────────────────────────────────


class Finding(BaseModel):
    id: str
    document_id: str
    page_number: int
    pii_type: str
    confidence: float
    context_snippet: str
    char_offset: int
    char_length: int


# ── Documents ─────────────────────────────────────────────────────────────────


class DocumentSummary(BaseModel):
    id: str
    batch_id: str
    filename: str
    page_count: int
    status: str
    finding_count: int
    processed_at: str | None = None


class DocumentDetail(DocumentSummary):
    findings: list[Finding] = []


# ── Batches ───────────────────────────────────────────────────────────────────


class BatchSummary(BaseModel):
    id: str
    name: str
    source_path: str
    created_at: str
    status: str
    total_docs: int
    processed_docs: int
    docs_with_findings: int


class BatchDetail(BatchSummary):
    documents: list[DocumentSummary] = []


# ── Dashboard / Stats ────────────────────────────────────────────────────────


class PIITypeCount(BaseModel):
    pii_type: str
    count: int
    avg_confidence: float


class StatsResponse(BaseModel):
    total_batches: int
    total_documents: int
    total_findings: int
    docs_with_findings: int
    pii_type_counts: dict[str, int]


# ── Reports ───────────────────────────────────────────────────────────────────


class ReportResponse(BaseModel):
    id: str
    batch_id: str
    format: str
    status: str
    created_at: str
    filename: str | None = None


# ── Pagination ────────────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
