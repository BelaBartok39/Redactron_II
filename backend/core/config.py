"""Central configuration for RedactQC."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_data_dir() -> Path:
    """Platform-appropriate data directory."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "redact-qc"


@dataclass
class Settings:
    """Application settings with sensible defaults."""

    # Paths
    data_dir: Path = field(default_factory=_default_data_dir)

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Processing
    worker_count: int = field(default_factory=lambda: max(1, (os.cpu_count() or 2) - 1))
    chunk_size: int = 100  # Documents per processing chunk
    max_file_size_mb: int = 500

    # PII Detection
    confidence_threshold: float = 0.4  # Minimum confidence to record a finding
    context_chars: int = 20  # Characters of context around each finding
    default_language: str = "en"

    # OCR
    tesseract_cmd: str | None = None  # Auto-detect if None
    ocr_dpi: int = 300
    min_text_length: int = 50  # Pages with fewer chars trigger OCR

    # Reports
    reports_dir: Path | None = None  # Defaults to data_dir / "reports"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "redactqc.db"

    @property
    def resolved_reports_dir(self) -> Path:
        return self.reports_dir or (self.data_dir / "reports")

    def ensure_dirs(self) -> None:
        """Create required directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.resolved_reports_dir.mkdir(parents=True, exist_ok=True)


# Global singleton — importable everywhere
settings = Settings()
