# RedactQC

PII Quality Assurance tool for redacted legal documents. Scans already-redacted PDFs to find personally identifiable information that redaction software missed.

## Features

- **Batch scanning** of 10,000+ document folders
- **PII detection** using Microsoft Presidio + custom legal recognizers
- **OCR support** for scanned/image-based PDFs via Tesseract
- **Dashboard** with drill-down from batch → document → finding
- **Reports** in PDF and CSV format
- **Fully local** — zero network calls, no telemetry, no cloud APIs
- **Cross-platform** — Windows 11 and Linux

## PII Types Detected

| Category | Examples |
|----------|---------|
| Personal | Names, DOB, age |
| Government ID | SSN, driver's license, passport |
| Contact | Phone, email, physical address |
| Financial | Bank accounts, routing numbers, credit cards |
| Legal | Case numbers, judge/attorney/victim/witness names |
| Medical | Medical record numbers |
| Digital | IP addresses, MAC addresses, device IDs |

## Prerequisites

- Python 3.11+
- Node.js 18+
- Tesseract OCR ([install guide](https://github.com/UB-Mannheim/tesseract/wiki))

## Quick Start

```bash
# Clone and setup
cd redact-qc
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -e ".[dev]"
python scripts/setup_models.py

# Build frontend
cd frontend && npm install && npm run build && cd ..

# Run
python run.py
```

The dashboard opens at http://127.0.0.1:8000.

## Development

```bash
# Backend (with auto-reload)
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (with proxy to backend)
cd frontend && npm run dev
```

## Testing

```bash
pytest
```

## Building Executable

```bash
pip install -e ".[build]"
python scripts/build.py
```
