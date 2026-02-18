# Development Guide

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Tesseract OCR installed and on PATH
  - Linux: `sudo apt install tesseract-ocr` or `sudo pacman -S tesseract`
  - Windows: Download installer from https://github.com/UB-Mannheim/tesseract/wiki

## Setup

### Backend
```bash
cd redact-qc
python -m venv .venv
source .venv/bin/activate  # Linux
# .venv\Scripts\activate   # Windows

pip install -e ".[dev]"
python scripts/setup_models.py  # Downloads spaCy model
```

### Frontend
```bash
cd frontend
npm install
```

## Running

### Development Mode
```bash
# Terminal 1: Backend
uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend (with proxy to backend)
cd frontend
npm run dev
```

### Production Mode
```bash
# Build frontend
cd frontend && npm run build && cd ..

# Run (serves frontend from backend)
python -m backend.api.main
```

## Testing
```bash
# All tests
pytest

# Specific test file
pytest backend/tests/test_detector.py

# With coverage
pytest --cov=backend
```

## Building Executable
```bash
pip install -e ".[build]"
python scripts/build.py
```

## Project Conventions

- **Imports**: Use absolute imports from `backend.*`
- **IDs**: UUID4 strings for all primary keys
- **Dates**: ISO 8601 format stored as TEXT in SQLite
- **Config**: All settings in `backend/core/config.py`
- **No network**: Never add code that makes network calls
