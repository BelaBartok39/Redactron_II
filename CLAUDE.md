# RedactQC - PII Quality Assurance Tool

## Project Purpose
RedactQC is a **QA tool** for county governments. It scans already-redacted legal documents (affidavits, warrants, court records) to find PII that redaction software missed. It does NOT perform redaction itself.

## Key Requirements
- Handle 10,000+ document batches
- Fully local - zero network calls, no telemetry, no cloud APIs
- Cross-platform: Windows 11 and Linux
- Dashboard with drill-down into findings

## Tech Stack
- **Python 3.11+** - Backend processing, API, NLP pipeline
- **FastAPI** - Local API server (localhost only, 127.0.0.1)
- **React + TypeScript + Vite** - Dashboard UI
- **SQLite** - Local database
- **Microsoft Presidio** - PII detection engine (local)
- **spaCy (en_core_web_lg)** - NER model for Presidio
- **Tesseract OCR** - Text extraction from scanned pages
- **PyMuPDF (fitz)** - PDF text extraction + rendering
- **pdf2image + Pillow** - PDF to image for OCR
- **Python multiprocessing** - Parallel batch processing
- **ReportLab** - PDF audit report generation
- **PyInstaller** - Executable packaging

## Architecture

### Processing Pipeline
```
[Folder of PDFs]
  → Document Ingestion (inventory + metadata)
  → Page Extraction (split into pages)
  → Text Extraction (PyMuPDF for text layers, Tesseract for image pages)
  → PII Detection (Presidio + custom legal recognizers, confidence scoring)
  → Results Storage (findings → SQLite, extracted text never stored)
  → Dashboard + Reports
```

### Privacy Architecture
- Zero network calls - no telemetry, cloud APIs, or update checks
- Transient text - extracted text only in memory, never on disk
- Minimal storage - DB stores PII type, confidence, page, offset, ~20 char context snippet
- Localhost only - API binds to 127.0.0.1
- No content in logs

### Database Schema
```sql
-- Core tables
batches: id (TEXT PK), name (TEXT), source_path (TEXT), created_at (TEXT),
         status (TEXT), total_docs (INT), processed_docs (INT), docs_with_findings (INT)

documents: id (TEXT PK), batch_id (TEXT FK), filename (TEXT), filepath (TEXT),
           page_count (INT), status (TEXT), finding_count (INT), processed_at (TEXT)

findings: id (TEXT PK), document_id (TEXT FK), page_number (INT), pii_type (TEXT),
          confidence (REAL), context_snippet (TEXT), char_offset (INT), char_length (INT)

pii_categories: id (TEXT PK), name (TEXT), description (TEXT), severity_level (INT)
```

### API Endpoints
```
POST   /api/scan                      - Start new batch scan
GET    /api/batches                    - List all batches
GET    /api/batches/:id               - Batch detail
DELETE /api/batches/:id               - Remove batch
GET    /api/batches/:bid/documents    - Documents in batch (paginated)
GET    /api/documents/:id             - Document detail
GET    /api/documents/:id/findings    - Document findings (filterable)
GET    /api/stats                     - Global statistics
GET    /api/pii-types                 - PII type breakdown
POST   /api/reports/generate          - Generate report
GET    /api/reports/:id/download      - Download report
```

### PII Types Detected
| Category | Types |
|----------|-------|
| **Personal** | Full names, DOB, age, gender, ethnicity |
| **Government ID** | SSN, driver's license, passport, state ID |
| **Contact** | Phone, email, physical address |
| **Financial** | Bank account, routing number, credit card |
| **Legal** | Case numbers, judge/attorney names, victim/witness/minor names |
| **Medical** | Medical record numbers, health conditions |
| **Digital** | IP addresses, MAC addresses, device IDs |

### Dashboard Drill-Down
```
Dashboard (all batches, stats)
  → Batch Detail (document list, filters)
    → Document Detail (page-by-page findings)
      → Finding Detail (PII type, confidence, context)
```

## Project Structure
```
redact-qc/
├── CLAUDE.md
├── docs/ (ARCHITECTURE.md, PII_TYPES.md, DEVELOPMENT.md)
├── backend/
│   ├── api/ (main.py, routes/, schemas/)
│   ├── core/ (config.py, database.py, security.py)
│   ├── processing/ (pipeline.py, extractor.py, detector.py, recognizers/, batch_manager.py, worker_pool.py)
│   ├── reports/ (generator.py, pdf_report.py, csv_export.py)
│   └── tests/
├── frontend/
│   ├── src/ (App.tsx, api/, pages/, components/, hooks/, types/)
│   ├── package.json, tsconfig.json, vite.config.ts
├── scripts/ (build.py, setup_models.py)
├── pyproject.toml
└── README.md
```

## Development
```bash
# Backend
cd redact-qc
pip install -e ".[dev]"
python scripts/setup_models.py
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm install
npm run dev    # Dev mode (port 5173, proxies to 8000)
npm run build  # Production build (served by FastAPI)

# Tests
pytest backend/tests/
```

## Environment Setup (Arch Linux)
```bash
# Prerequisites already installed:
# - Python 3.13 (via mise)
# - Tesseract OCR 5.5.2 (sudo pacman -S tesseract tesseract-data-eng)
# - Node.js (for frontend build)
# - opencv-python (pip, for redaction box counting experiment)

# Virtual environment
cd /home/babynicky/Work/redact-qc
source .venv/bin/activate

# Start backend (port 8000)
python -m backend.api
# OR: uvicorn backend.api.main:app --host 127.0.0.1 --port 8000

# Start frontend dev server (port 5173, proxies /api to 8000)
cd frontend && npx vite --port 5173

# Build frontend for production (served by FastAPI at port 8000)
cd frontend && npx vite build
```

## Test Data
Three test PDFs in `all_phi/` directory:
- **Easy** (`PDF_Deid_Deidentification_0.pdf`): 3 pages, 42 redaction boxes, all correctly redacted
- **Medium** (`PDF_Deid_Deidentification_Medium_0.pdf`): 4 pages, 47 redaction boxes, all correctly redacted
- **Hard** (`PDF_Deid_Deidentification_Hard_0.pdf`): 2 pages, 43 redaction boxes (includes small vertical boxes), has one unredacted name "Julie Terry"

All are scanned image-only PDFs (zero text layer). OCR via Tesseract extracts text. Redaction boxes appear as `I`, `|`, `[]`, `NG` characters in OCR output.

Scan results from successful test:
- Easy: 3 findings (false positives from date/time patterns)
- Medium: 1 finding (false positive)
- Hard: 6 findings (includes correctly detected "Julie Terry" as PERSON - this is the real leaked PII)

## Current Issues (Priority Order)

### 1. Dashboard UI Is Blank (CRITICAL)
The React dashboard at `http://localhost:5173` or `http://localhost:8000` renders the sidebar correctly (nav links work) but the **main content area is blank**. The backend API works perfectly - all endpoints return correct JSON. The issue is in the frontend rendering.

**What needs investigation:**
- The DashboardPage.tsx code looks correct and should render stats cards, "New Scan" button, PII distribution, and batch list
- API calls through Vite proxy (port 5173→8000) work (`curl http://localhost:5173/api/stats` returns data)
- Production build (port 8000 serves frontend/dist) also serves correct HTML
- Likely a React rendering error that silently crashes - needs browser console debugging
- Could be a missing React error boundary causing silent failures
- CSS issue is unlikely since sidebar renders fine

**What to try:**
1. Open Chrome DevTools console on `http://localhost:5173` to see JavaScript errors
2. Add an error boundary wrapper around `<Routes>` in App.tsx
3. Check if the component renders at all (add a simple `<h1>Test</h1>` to DashboardPage)
4. Verify the fetch calls work in the browser (not just curl)

### 2. Scan Workflow Works Backend-Only
The scanning pipeline works perfectly via API:
```bash
curl -X POST http://127.0.0.1:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{"source_path": "/home/babynicky/Work/redact-qc/all_phi"}'
```
Returns a batch ID, background processing runs, documents get scanned with OCR+Presidio, findings stored in SQLite. Status polling works. But the UI can't trigger this because of Issue #1.

### 3. Redaction Box Counting (DEFERRED)
Experimental feature in `scripts/count_redaction_boxes.py` to count black redaction rectangles in scanned PDFs (validates OCR calibration). Uses OpenCV connected components analysis. Results were inconsistent across difficulty levels - deferred in favor of getting core UI working.

## Status
- [x] Project scaffolding created
- [x] Processing engine (extractor, detector, recognizers, pipeline, batch manager, worker pool)
- [x] API + database layer (routes, schemas, report generation)
- [x] Dashboard frontend (all pages, components, CSS) — **code written but rendering is broken**
- [x] Integration (entry point, build script, static file serving)
- [x] Tests (extractor, detector, recognizers, pipeline)
- [x] Backend scan tested end-to-end with 3 PDFs (works correctly, finds "Julie Terry" in Hard)
- [ ] **FIX: Dashboard UI blank page** — debug React rendering error
- [ ] **FIX: Verify full UI workflow** — scan from UI → view results → drill down
- [ ] Redaction box counting (deferred)
