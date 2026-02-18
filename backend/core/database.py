"""SQLite database setup and connection management."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from backend.core.config import settings

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS pii_categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    severity_level INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE IF NOT EXISTS batches (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'pending',
    total_docs INTEGER NOT NULL DEFAULT 0,
    processed_docs INTEGER NOT NULL DEFAULT 0,
    docs_with_findings INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    page_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    finding_count INTEGER NOT NULL DEFAULT 0,
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    pii_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    context_snippet TEXT NOT NULL DEFAULT '',
    char_offset INTEGER NOT NULL DEFAULT 0,
    char_length INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_documents_batch_id ON documents(batch_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_findings_document_id ON findings(document_id);
CREATE INDEX IF NOT EXISTS idx_findings_pii_type ON findings(pii_type);
CREATE INDEX IF NOT EXISTS idx_findings_confidence ON findings(confidence);
"""

DEFAULT_PII_CATEGORIES = [
    ("PERSON", "Person Name", "Full or partial person name", 4),
    ("EMAIL_ADDRESS", "Email Address", "Email address", 3),
    ("PHONE_NUMBER", "Phone Number", "Phone or fax number", 3),
    ("US_SSN", "Social Security Number", "US Social Security Number", 5),
    ("US_DRIVER_LICENSE", "Driver's License", "US driver's license number", 5),
    ("US_PASSPORT", "Passport Number", "US passport number", 5),
    ("CREDIT_CARD", "Credit Card", "Credit or debit card number", 5),
    ("US_BANK_NUMBER", "Bank Account", "US bank account number", 5),
    ("US_ITIN", "ITIN", "Individual Taxpayer Identification Number", 5),
    ("IP_ADDRESS", "IP Address", "IPv4 or IPv6 address", 2),
    ("DATE_TIME", "Date/Time", "Date or time expression", 1),
    ("LOCATION", "Location", "Physical address or location", 3),
    ("MEDICAL_LICENSE", "Medical License", "Medical license number", 4),
    ("URL", "URL", "Web URL", 1),
    ("CASE_NUMBER", "Case Number", "Legal case or docket number", 3),
    ("LEGAL_ROLE_NAME", "Legal Role Name", "Judge, attorney, victim, witness, or minor name", 5),
    ("ROUTING_NUMBER", "Routing Number", "Bank routing number", 4),
    ("MEDICAL_RECORD", "Medical Record Number", "Medical record or patient ID", 5),
    ("MAC_ADDRESS", "MAC Address", "Network MAC address", 2),
    ("DEVICE_ID", "Device Identifier", "Device serial or IMEI", 2),
]


class Database:
    """Thread-safe SQLite database manager."""

    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or settings.db_path
        self._local = threading.local()

    def _get_connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "connection", None)
        if conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path), timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.connection = conn
        return conn

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a thread-local database connection."""
        yield self._get_connection()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Execute within a transaction (auto-commit/rollback)."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def initialize(self) -> None:
        """Create schema and seed data."""
        with self.transaction() as conn:
            conn.executescript(SCHEMA_SQL)
            # Check if already seeded
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM pii_categories"
            ).fetchone()
            if row["cnt"] == 0:
                conn.executemany(
                    "INSERT INTO pii_categories (id, name, description, severity_level) "
                    "VALUES (?, ?, ?, ?)",
                    DEFAULT_PII_CATEGORIES,
                )
                conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )

    def close(self) -> None:
        """Close the thread-local connection if open."""
        conn = getattr(self._local, "connection", None)
        if conn is not None:
            conn.close()
            self._local.connection = None


# Global singleton
db = Database()
