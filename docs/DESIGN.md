# RedactQC System Design Document

## 1. Purpose

RedactQC is a quality assurance tool for county governments. It scans already-redacted legal documents (affidavits, warrants, court records) to find personally identifiable information (PII) that redaction software missed. It does **not** perform redaction itself — it verifies that redaction was done correctly.

The tool is designed to handle batches of 10,000+ documents entirely on the local machine with zero network connectivity.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      User's Browser                          │
│                   http://127.0.0.1:8000                      │
│                                                              │
│   React + TypeScript SPA (Dashboard, Drill-Down, Reports)    │
└──────────────────────────┬───────────────────────────────────┘
                           │  HTTP REST (localhost only)
┌──────────────────────────▼───────────────────────────────────┐
│                     FastAPI Server                            │
│                  (127.0.0.1:8000)                             │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ │
│  │ Static File  │  │  API Routes │  │ Background Batch     │ │
│  │ Serving      │  │  (REST)     │  │ Processing Manager   │ │
│  │ (React SPA)  │  │             │  │                      │ │
│  └─────────────┘  └──────┬──────┘  └──────────┬───────────┘ │
│                          │                     │              │
│                   ┌──────▼─────────────────────▼──────┐      │
│                   │         SQLite Database           │      │
│                   │     (WAL mode, thread-safe)       │      │
│                   └──────────────────────────────────┘      │
│                                                              │
│                   ┌──────────────────────────────────┐      │
│                   │      Worker Pool                  │      │
│                   │   (Python multiprocessing)        │      │
│                   │                                   │      │
│                   │  ┌──────┐ ┌──────┐ ┌──────┐      │      │
│                   │  │ W1   │ │ W2   │ │ W3   │ ...  │      │
│                   │  │      │ │      │ │      │      │      │
│                   │  │PyMuPDF│ │PyMuPDF│ │PyMuPDF│     │      │
│                   │  │Tess. │ │Tess. │ │Tess. │      │      │
│                   │  │Presid│ │Presid│ │Presid│      │      │
│                   │  └──────┘ └──────┘ └──────┘      │      │
│                   └──────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### Backend (Python 3.11+)

| Component | Library | Version | Role |
|-----------|---------|---------|------|
| Web framework | FastAPI | 0.104+ | REST API server, static file serving |
| ASGI server | Uvicorn | 0.24+ | Runs the FastAPI application |
| Data validation | Pydantic | 2.5+ | Request/response schema validation |
| PII detection | Microsoft Presidio | 2.2+ | Core NLP-based PII detection engine |
| NER model | spaCy (en_core_web_lg) | 3.7+ | Named Entity Recognition for Presidio |
| PDF parsing | PyMuPDF (fitz) | 1.23+ | Text layer extraction, page rendering |
| OCR engine | Tesseract (via pytesseract) | 0.3.10+ | Optical character recognition for scanned pages |
| Image handling | Pillow | 10.0+ | PDF page-to-image conversion for OCR |
| PDF-to-image | pdf2image | 1.16+ | Alternative PDF rendering path |
| Database | SQLite (stdlib) | — | Local data storage, WAL mode |
| PDF reports | ReportLab | 4.0+ | Generates PDF audit reports |
| Parallelism | multiprocessing (stdlib) | — | Parallel document processing |
| Packaging | PyInstaller | 6.0+ | Builds standalone executables |

### Frontend (Node.js 18+)

| Component | Library | Version | Role |
|-----------|---------|---------|------|
| UI framework | React | 18.x | Component-based SPA |
| Language | TypeScript | 5.x | Type-safe frontend code |
| Build tool | Vite | 5.x | Dev server with HMR, production bundler |
| Routing | React Router | 6.x | Client-side page navigation |

### System Dependencies

| Tool | Role | Installation |
|------|------|-------------|
| Tesseract OCR | Text extraction from scanned/image-only PDFs | OS package manager (see Section 11) |
| Python 3.11+ | Backend runtime | OS package manager or mise/pyenv |
| Node.js 18+ | Frontend build toolchain (dev only, not needed at runtime in production) | OS package manager or nvm |

---

## 4. Processing Pipeline

When a user initiates a scan, documents flow through these stages:

```
[Folder of PDFs]
    │
    ▼
┌─────────────────────────────────────────────┐
│ 1. BATCH CREATION  (batch_manager.py)       │
│    - Scan folder for *.pdf / *.PDF files    │
│    - Deduplicate (case-insensitive FS safe) │
│    - Create batch + document records in DB  │
│    - Status: batch → 'pending'              │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 2. WORKER DISPATCH  (worker_pool.py)        │
│    - Spawn N worker processes (spawn ctx)   │
│    - Each worker gets (doc_id, filepath)    │
│    - Workers are independent — no shared    │
│      state, each builds its own Presidio    │
│      analyzer to avoid pickling issues      │
│    - Status: batch → 'processing'           │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 3. TEXT EXTRACTION  (extractor.py)          │
│    Per page:                                │
│    a. Try PyMuPDF text layer extraction     │
│    b. If < 50 chars → page is image-only    │
│    c. Fall back to Tesseract OCR at 300 DPI │
│    d. Record extraction method + confidence │
│                                             │
│    Output: list of PageText objects         │
│    (page_num, text, method, confidence)     │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 4. PII DETECTION  (detector.py)             │
│    Per page:                                │
│    a. Run Presidio analyzer (built-in +     │
│       10 custom recognizers)                │
│    b. Filter results by confidence threshold│
│       (default: 0.4)                        │
│    c. Extract ~20-char context snippet      │
│       around each finding                   │
│                                             │
│    Output: list of Finding objects          │
│    (pii_type, confidence, start, end,       │
│     page_num, context_snippet)              │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│ 5. RESULTS STORAGE  (batch_manager.py)      │
│    - Write findings to SQLite               │
│    - Update document status → 'completed'   │
│    - Update batch counters                  │
│    - Extracted text is DISCARDED (never     │
│      written to disk or database)           │
│    - Status: batch → 'completed'            │
└─────────────────────────────────────────────┘
```

### Worker Count

By default, the system uses `CPU_COUNT - 1` worker processes. This is configurable per scan via the API or the UI's "New Scan" dialog. Each worker process independently loads:
- PyMuPDF for PDF parsing
- Tesseract for OCR
- spaCy model (en_core_web_lg, ~560 MB in memory per worker)
- Presidio analyzer with all recognizers

Memory usage scales linearly with worker count. On a machine with 16 GB RAM, 3-4 workers is a practical maximum.

### Chunked Processing

Documents are processed in configurable chunks (default: 100 documents per chunk) to manage memory. Within each chunk, workers process documents in parallel via `imap_unordered`, and results are recorded to the database as each document completes.

### Resumability

The batch manager only processes documents with status `'pending'` or `'error'`. If a batch is interrupted (crash, Ctrl+C), restarting the same batch will skip already-completed documents and retry failed ones.

---

## 5. PII Detection Engine

### How It Works

RedactQC uses Microsoft Presidio as its PII detection backbone. Presidio combines:
- **Pattern matching** — Regular expressions for structured PII (SSN, phone, email)
- **Named Entity Recognition (NER)** — spaCy's `en_core_web_lg` model for unstructured PII (names, locations)
- **Context analysis** — Surrounding words boost or reduce confidence scores

### Built-in Presidio Recognizers

These ship with Presidio and are loaded automatically:

| Entity | Examples | Severity |
|--------|----------|----------|
| PERSON | Full/partial person names | 4 |
| EMAIL_ADDRESS | user@domain.com | 3 |
| PHONE_NUMBER | (555) 123-4567 | 3 |
| US_SSN | 123-45-6789 | 5 |
| US_DRIVER_LICENSE | State-specific patterns | 5 |
| US_PASSPORT | 9-digit passport numbers | 5 |
| CREDIT_CARD | Card numbers (Luhn validated) | 5 |
| US_BANK_NUMBER | Variable-length account numbers | 5 |
| US_ITIN | 9XX-XX-XXXX format | 5 |
| IP_ADDRESS | IPv4 and IPv6 | 2 |
| DATE_TIME | Dates, times, durations | 1 |
| LOCATION | Street addresses, cities | 3 |
| URL | Web URLs | 1 |

### Custom Legal Recognizers

RedactQC adds 10 custom recognizers tailored for legal documents:

| File | Recognizers | What They Detect |
|------|------------|-----------------|
| `legal_pii.py` | CaseNumberRecognizer | Case/docket numbers (XX-CV-XXXXX, Case No. patterns) |
| `legal_pii.py` | LegalRoleNameRecognizer | Names near "judge", "attorney", "victim", "witness", "minor" |
| `government_id.py` | EnhancedSSNRecognizer | Full/partial SSNs with and without dashes |
| `government_id.py` | DriversLicenseRecognizer | State-specific license patterns (CA, NY, TX, FL, etc.) |
| `government_id.py` | PassportRecognizer | 9-digit US passport numbers |
| `financial_pii.py` | RoutingNumberRecognizer | 9-digit ABA routing numbers with check digit validation |
| `financial_pii.py` | BankAccountRecognizer | 8-17 digit sequences near financial context words |
| `medical_pii.py` | MedicalRecordRecognizer | Alphanumeric patterns near "MRN", "patient ID" |
| `digital_pii.py` | MACAddressRecognizer | XX:XX:XX:XX:XX:XX and dash-separated formats |
| `digital_pii.py` | DeviceIDRecognizer | IMEI (15 digits), serial numbers near device keywords |

### Confidence Scoring

Every finding has a confidence score from 0.0 to 1.0. The default threshold is **0.4** — findings below this are discarded. Users can adjust the threshold per scan. Higher thresholds reduce false positives but may miss real PII.

---

## 6. Database

### Engine

SQLite in WAL (Write-Ahead Logging) mode. WAL allows concurrent reads while a write is in progress, which is important because the API serves dashboard queries while batch processing writes results.

### Connection Management

The `Database` class (`backend/core/database.py`) uses thread-local connections. Each thread (API request handler, background worker) gets its own SQLite connection. Connections are created lazily on first use.

SQLite pragmas applied per connection:
- `journal_mode=WAL` — Concurrent read/write support
- `foreign_keys=ON` — Enforce referential integrity
- `busy_timeout=5000` — Wait up to 5 seconds on lock contention

### Schema

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   batches    │     │  documents   │     │   findings   │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id (PK)      │◄────│ batch_id (FK)│     │ id (PK)      │
│ name         │     │ id (PK)      │◄────│ document_id  │
│ source_path  │     │ filename     │     │   (FK)       │
│ created_at   │     │ filepath     │     │ page_number  │
│ status       │     │ page_count   │     │ pii_type     │
│ total_docs   │     │ status       │     │ confidence   │
│ processed_   │     │ finding_     │     │ context_     │
│   docs       │     │   count      │     │   snippet    │
│ docs_with_   │     │ processed_at │     │ char_offset  │
│   findings   │     └──────────────┘     │ char_length  │
└──────────────┘                          └──────────────┘

┌──────────────────┐     ┌──────────────────┐
│ pii_categories   │     │ schema_version   │
├──────────────────┤     ├──────────────────┤
│ id (PK)          │     │ version (PK)     │
│ name             │     └──────────────────┘
│ description      │
│ severity_level   │
└──────────────────┘
```

**Status values:**
- Batches: `pending` → `processing` → `completed` | `error`
- Documents: `pending` → `completed` | `error`

**Indexes** on: `documents.batch_id`, `documents.status`, `findings.document_id`, `findings.pii_type`, `findings.confidence`

### Data Location

The database file is stored at a platform-appropriate location:
- **Linux**: `~/.local/share/redact-qc/redactqc.db`
- **Windows**: `%LOCALAPPDATA%\redact-qc\redactqc.db`

---

## 7. API Layer

FastAPI serves both the REST API and the built frontend as static files. The server binds exclusively to `127.0.0.1` (localhost) — it never listens on external interfaces.

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/scan` | Start a new batch scan. Accepts `source_path`, optional `confidence_threshold` and `worker_count`. Processing runs in a background thread. |
| `GET` | `/api/batches` | List all batches with summary stats. |
| `GET` | `/api/batches/:id` | Single batch detail. |
| `DELETE` | `/api/batches/:id` | Remove a batch and cascade-delete its documents and findings. |
| `GET` | `/api/batches/:id/documents` | Paginated document list for a batch. Supports filters: `pii_type`, `min_confidence`, `has_findings`. |
| `GET` | `/api/documents/:id` | Single document detail. |
| `GET` | `/api/documents/:id/findings` | Paginated findings for a document. Supports filters: `pii_type`, `min_confidence`. |
| `GET` | `/api/stats` | Global statistics (total batches, documents, findings, PII type breakdown). |
| `GET` | `/api/pii-types` | PII type distribution with counts and average confidence. |
| `POST` | `/api/reports/generate` | Generate a PDF or CSV report for a batch. Runs in a background thread. Returns a report ID for polling. |
| `GET` | `/api/reports/:id` | Check report generation status. |
| `GET` | `/api/reports/:id/download` | Download a completed report file. |

### Route Organization

```
backend/api/routes/
├── batches.py      # /api/scan, /api/batches, /api/batches/:id
├── dashboard.py    # /api/stats, /api/pii-types
├── documents.py    # /api/batches/:id/documents, /api/documents/:id, /api/documents/:id/findings
└── reports.py      # /api/reports/*
```

### Background Processing

Batch scans and report generation run in background threads so the API remains responsive. The frontend polls `GET /api/batches/:id` every 2 seconds during active scans to update progress in real time.

---

## 8. Frontend

### Stack

The frontend is a React 18 SPA written in TypeScript and built with Vite. In development, Vite runs on port 5173 and proxies `/api/*` requests to the backend at port 8000. In production, the frontend is pre-built to `frontend/dist/` and served directly by FastAPI as static files — no Node.js runtime required.

### Pages and Navigation

```
Dashboard (/)
  ├── Stats cards (total batches, documents, findings, docs with findings)
  ├── PII Type Distribution (horizontal bar chart)
  ├── Quick Actions ("New Scan" button + scan dialog)
  └── Recent Batches (clickable cards)
         │
         ▼
Batch Detail (/batches/:id)
  ├── Batch status badge + summary stats
  ├── Paginated document table (sortable, filterable)
  └── Click a document row →
         │
         ▼
Document Detail (/documents/:id)
  ├── Document metadata (filename, pages, finding count)
  └── Findings list (PII type badges, confidence bars, context snippets)

Reports (/reports)
  ├── Lists all completed batches
  └── Generate PDF or CSV buttons per batch
      └── Download link appears when ready
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| App | `App.tsx` | Layout shell (sidebar + header + content area), route definitions |
| DashboardPage | `pages/DashboardPage.tsx` | Main dashboard with stats, scan dialog, batch list |
| BatchDetailPage | `pages/BatchDetailPage.tsx` | Drill-down into a single batch's documents |
| DocumentPage | `pages/DocumentPage.tsx` | Drill-down into a single document's findings |
| ReportsPage | `pages/ReportsPage.tsx` | Report generation and download |
| StatsOverview | `components/StatsOverview.tsx` | Stats card grid |
| BatchCard | `components/BatchCard.tsx` | Batch summary card with status badge |
| DocumentTable | `components/DocumentTable.tsx` | Sortable, paginated document table |
| FindingsList | `components/FindingsList.tsx` | Finding rows with PII badges and confidence bars |
| FilterPanel | `components/FilterPanel.tsx` | Filter controls for PII type and confidence |
| PIIBadge | `components/PIIBadge.tsx` | Color-coded PII type label |
| ConfidenceBar | `components/ConfidenceBar.tsx` | Visual confidence score indicator |

### API Client

All backend communication goes through `frontend/src/api/client.ts`. It wraps the `fetch` API with:
- Automatic JSON content-type headers
- Error handling via a custom `ApiError` class with HTTP status codes
- Type-safe return types matching the TypeScript interfaces in `types/index.ts`

---

## 9. Report Generation

Reports are generated on demand and saved to the local reports directory:
- **Linux**: `~/.local/share/redact-qc/reports/`
- **Windows**: `%LOCALAPPDATA%\redact-qc\reports\`

### PDF Reports (`backend/reports/pdf_report.py`)

Generated using ReportLab. Contents include:
- Batch summary header (name, date, document count, finding count)
- Per-document breakdown with findings table
- PII type, confidence score, page number, and context snippet for each finding

### CSV Reports (`backend/reports/csv_export.py`)

Flat CSV export with one row per finding. Columns include document filename, page number, PII type, confidence, and context snippet. Suitable for import into Excel or other analysis tools.

### Workflow

1. User clicks "Generate PDF" or "Generate CSV" on the Reports page
2. Frontend sends `POST /api/reports/generate` with batch ID and format
3. Backend spawns a background thread to generate the report
4. Backend returns a report ID immediately
5. Frontend uses the report ID to construct a download link
6. User clicks the download link to retrieve the file via `GET /api/reports/:id/download`

---

## 10. Data Locality and Privacy

This is a core design principle. RedactQC handles sensitive government legal documents. **No data ever leaves the machine.**

### How Data Stays Local

| Concern | How It Is Enforced |
|---------|--------------------|
| **Network binding** | FastAPI binds exclusively to `127.0.0.1`. The server is unreachable from other machines on the network. |
| **No outbound calls** | Zero network calls anywhere in the codebase — no telemetry, no update checks, no cloud APIs, no analytics. All NLP models (spaCy, Presidio) run locally. |
| **No cloud dependencies** | All processing (OCR, NLP, PII detection) uses local libraries and models. Tesseract runs locally, spaCy model is downloaded once during setup and stored on disk. |
| **Transient text** | Extracted document text exists only in memory during processing. It is never written to disk, never stored in the database, and is garbage-collected after each document completes. |
| **Minimal DB storage** | The database stores only metadata: PII type, confidence score, page number, character offset, and a ~20-character context snippet. The full document text is never persisted. |
| **Secure temp files** | The `security.py` module provides `secure_delete()` which overwrites file contents with zeros before unlinking, and `secure_tempfile()` context manager that guarantees cleanup. |
| **CORS locked down** | CORS middleware only allows origins from `localhost` and `127.0.0.1` on expected ports. |
| **No user accounts** | No authentication, no user accounts, no session tokens. The tool runs as a local desktop application. |
| **Local reports** | Generated reports (PDF/CSV) are saved to the local filesystem only. |
| **Database location** | SQLite database is stored in the user's local app data directory, not in a shared or networked location. |

### What Is Stored on Disk

1. **SQLite database** — Batch metadata, document metadata (filename, path, status), finding metadata (PII type, confidence, page, offset, ~20 char snippet)
2. **Generated reports** — PDF and CSV files in the reports directory
3. **NLP models** — spaCy `en_core_web_lg` model (~560 MB, downloaded once during setup)
4. **Application files** — The Python backend, built frontend, and dependencies

### What Is NOT Stored on Disk

1. Extracted document text
2. Full document content
3. OCR output beyond the processing session
4. Any network request logs
5. User activity or analytics data

---

## 11. Cross-Platform Support

RedactQC runs on **Windows 11** and **Linux**. The codebase handles platform differences in the following areas:

### Data Directory

The `config.py` module detects the OS and uses the appropriate base path:

| OS | Data Directory | Example |
|----|---------------|---------|
| Windows | `%LOCALAPPDATA%\redact-qc\` | `C:\Users\Alice\AppData\Local\redact-qc\` |
| Linux | `$XDG_DATA_HOME/redact-qc/` or `~/.local/share/redact-qc/` | `/home/alice/.local/share/redact-qc/` |

### Tesseract OCR Installation

Tesseract is the only system-level dependency that must be installed separately:

| OS | Installation | Notes |
|----|-------------|-------|
| **Windows** | Download the installer from the [UB Mannheim Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki) | Adds `tesseract.exe` to PATH. If installed to a non-standard location, set `settings.tesseract_cmd` to the full path. |
| **Arch Linux** | `sudo pacman -S tesseract tesseract-data-eng` | Includes the English language data. |
| **Ubuntu/Debian** | `sudo apt install tesseract-ocr` | English data included by default. |

### Multiprocessing

The worker pool uses the `spawn` multiprocessing context (`mp.get_context("spawn")`), which is the default on Windows and the safest option on Linux. This avoids issues with `fork` and non-fork-safe libraries (PyMuPDF, spaCy, Presidio).

### Path Handling

All file paths use Python's `pathlib.Path`, which handles `/` vs `\` automatically. PDF file discovery uses case-insensitive deduplication to handle Windows filesystems where `file.pdf` and `FILE.PDF` resolve to the same file.

### PyInstaller Packaging

The `scripts/build.py` script packages the application into a standalone executable using PyInstaller:

```bash
python scripts/build.py           # Build both frontend and executable
python scripts/build.py frontend  # Build frontend only
python scripts/build.py exe       # Build executable only
```

The output is a directory-mode bundle (`--onedir`) at `dist/RedactQC/` containing:
- The Python runtime and all dependencies (no Python installation required)
- The built React frontend (served as static files)
- spaCy model and Presidio resources

The user runs the application by executing `RedactQC` (Linux) or `RedactQC.exe` (Windows). It opens a browser to `http://127.0.0.1:8000` automatically.

**Note:** Tesseract OCR must still be installed separately on the target machine — it is not bundled into the executable.

---

## 12. Development vs. Production

| Aspect | Development | Production |
|--------|------------|------------|
| Frontend serving | Vite dev server on port 5173 with HMR | Pre-built `frontend/dist/` served by FastAPI on port 8000 |
| API proxy | Vite proxies `/api/*` to `127.0.0.1:8000` | Direct — frontend and API on same origin |
| Backend startup | `uvicorn backend.api.main:app --reload` | `python run.py` or the PyInstaller executable |
| Hot reload | Yes (both frontend and backend with `--reload`) | No |
| Node.js required | Yes (runs Vite dev server) | No (frontend is pre-built static HTML/JS/CSS) |
| Browser auto-open | No | Yes (run.py opens default browser after 1.5s delay) |

### Development Setup

```bash
# Terminal 1: Backend
cd redact-qc
source .venv/bin/activate          # Linux
# .venv\Scripts\activate           # Windows
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend
cd redact-qc/frontend
npm run dev                         # Starts Vite on port 5173
```

### Production Build

```bash
# Build frontend
cd redact-qc/frontend
npm run build                       # Outputs to frontend/dist/

# Run server (serves frontend + API on port 8000)
cd redact-qc
python run.py

# Or build standalone executable
pip install -e ".[build]"
python scripts/build.py
# Output: dist/RedactQC/
```

---

## 13. Project Structure

```
redact-qc/
├── CLAUDE.md                          # AI assistant context
├── README.md                          # Project overview
├── pyproject.toml                     # Python dependencies + build config
├── run.py                             # Production entry point
│
├── backend/
│   ├── api/
│   │   ├── __main__.py                # python -m backend.api entry point
│   │   ├── main.py                    # FastAPI app, CORS, route registration, static files
│   │   ├── routes/
│   │   │   ├── batches.py             # Scan + batch CRUD endpoints
│   │   │   ├── dashboard.py           # Stats + PII type aggregation
│   │   │   ├── documents.py           # Document + findings endpoints
│   │   │   └── reports.py             # Report generation + download
│   │   └── schemas/
│   │       └── models.py              # Pydantic request/response models
│   │
│   ├── core/
│   │   ├── config.py                  # Settings dataclass (paths, thresholds, defaults)
│   │   ├── database.py                # SQLite setup, schema, thread-safe connections
│   │   └── security.py                # Secure file deletion utilities
│   │
│   ├── processing/
│   │   ├── batch_manager.py           # Batch lifecycle (create → process → complete)
│   │   ├── detector.py                # Presidio PII detection wrapper
│   │   ├── extractor.py               # PDF text extraction (PyMuPDF + Tesseract)
│   │   ├── pipeline.py                # Single-document processing orchestrator
│   │   ├── worker_pool.py             # Multiprocessing pool for parallel scans
│   │   └── recognizers/
│   │       ├── legal_pii.py           # Case numbers, legal role names
│   │       ├── government_id.py       # SSN, driver's license, passport
│   │       ├── financial_pii.py       # Routing numbers, bank accounts
│   │       ├── medical_pii.py         # Medical record numbers
│   │       └── digital_pii.py         # MAC addresses, device IDs
│   │
│   ├── reports/
│   │   ├── generator.py               # Report orchestration (fetch data, delegate)
│   │   ├── pdf_report.py              # PDF report generation (ReportLab)
│   │   └── csv_export.py              # CSV export generation
│   │
│   └── tests/
│       ├── test_detector.py           # PII detection tests
│       ├── test_extractor.py          # Text extraction tests
│       ├── test_pipeline.py           # Pipeline integration tests
│       └── test_recognizers.py        # Custom recognizer tests
│
├── frontend/
│   ├── index.html                     # SPA entry point
│   ├── package.json                   # npm dependencies
│   ├── vite.config.ts                 # Vite config (proxy, build output)
│   ├── tsconfig.json                  # TypeScript config
│   └── src/
│       ├── main.tsx                   # React entry point (BrowserRouter)
│       ├── App.tsx                    # Layout + route definitions
│       ├── App.css                    # Global styles (~800 lines)
│       ├── api/
│       │   └── client.ts             # Typed API client (fetch wrapper)
│       ├── types/
│       │   └── index.ts              # TypeScript interfaces (Batch, Document, Finding, etc.)
│       ├── pages/
│       │   ├── DashboardPage.tsx      # Main dashboard with stats + scan dialog
│       │   ├── BatchDetailPage.tsx    # Batch drill-down (document table)
│       │   ├── DocumentPage.tsx       # Document drill-down (findings list)
│       │   └── ReportsPage.tsx        # Report generation + download
│       └── components/
│           ├── StatsOverview.tsx       # Stats card grid
│           ├── BatchCard.tsx           # Batch summary card
│           ├── DocumentTable.tsx       # Sortable document table
│           ├── FindingsList.tsx        # Findings display list
│           ├── FilterPanel.tsx         # PII type + confidence filters
│           ├── PIIBadge.tsx            # Color-coded PII type badge
│           └── ConfidenceBar.tsx       # Visual confidence indicator
│
├── scripts/
│   ├── build.py                       # PyInstaller build script
│   └── setup_models.py               # Download spaCy model
│
└── docs/
    ├── DESIGN.md                      # This document
    ├── ARCHITECTURE.md                # Architecture overview
    ├── DEVELOPMENT.md                 # Developer setup guide
    └── PII_TYPES.md                   # PII type catalog
```

---

## 14. End-to-End Workflow

Here is what happens from the moment a user launches RedactQC to viewing scan results:

1. **Launch** — User runs `python run.py` (or the PyInstaller executable). The backend starts on `127.0.0.1:8000`, initializes the SQLite database, and opens the browser.

2. **Dashboard loads** — The React SPA loads and fetches `GET /api/stats`, `GET /api/batches`, and `GET /api/pii-types` to populate the dashboard with any existing data.

3. **Start a scan** — User clicks "New Scan", enters a folder path (e.g., `C:\Cases\Batch_042` or `/srv/documents/batch_042`), optionally adjusts confidence threshold and worker count, then clicks "Start Scan".

4. **Backend creates batch** — `POST /api/scan` is called. The backend scans the folder for PDFs, creates batch and document records in SQLite, and spawns a background thread that starts the worker pool.

5. **Workers process documents** — Each worker process independently loads PyMuPDF, Tesseract, and Presidio. For each document: extract text from each page (native text or OCR), run PII detection, and return findings. Results stream back to the main process and are written to SQLite as each document completes.

6. **Frontend polls progress** — While the scan runs, the dashboard polls `GET /api/batches/:id` every 2 seconds to update the progress indicator (processed_docs / total_docs).

7. **Scan complete** — When all documents are processed, the batch status changes to `'completed'`. The frontend detects this, stops polling, and refreshes the dashboard data.

8. **Review results** — User clicks a batch card to see the document list. Clicks a document to see its findings. Each finding shows the PII type, confidence score, page number, and a short context snippet.

9. **Generate report** — User navigates to Reports, selects a completed batch, and clicks "Generate PDF" or "Generate CSV". The report is generated in the background and a download link appears.

10. **Cleanup** — User can delete batches via the API. Cascade deletes remove all associated documents and findings. The original PDF files are never modified or moved.
