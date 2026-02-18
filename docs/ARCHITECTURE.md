# RedactQC Architecture

## Overview

RedactQC is a local-only PII quality assurance tool. It scans already-redacted legal documents to find PII that redaction software missed.

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    User Browser                       │
│              (localhost:8000)                          │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (localhost only)
┌──────────────────────▼──────────────────────────────┐
│                  FastAPI Server                        │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Static   │  │ API      │  │ Background        │  │
│  │ Files    │  │ Routes   │  │ Processing        │  │
│  │ (React)  │  │          │  │ Manager           │  │
│  └──────────┘  └────┬─────┘  └────────┬──────────┘  │
│                     │                  │              │
│              ┌──────▼──────────────────▼──────┐      │
│              │          SQLite DB             │      │
│              └───────────────────────────────┘      │
│                                                      │
│              ┌───────────────────────────────┐      │
│              │     Worker Pool               │      │
│              │  (multiprocessing)            │      │
│              │  ┌────┐ ┌────┐ ┌────┐        │      │
│              │  │ W1 │ │ W2 │ │ W3 │ ...    │      │
│              │  └────┘ └────┘ └────┘        │      │
│              └───────────────────────────────┘      │
└─────────────────────────────────────────────────────┘
```

## Processing Pipeline

Each document goes through:

1. **Ingestion** — Validate file, record in `documents` table
2. **Page Extraction** — Split PDF into pages using PyMuPDF
3. **Text Extraction** — PyMuPDF for text layers, Tesseract OCR for image pages
4. **PII Detection** — Presidio analyzer with built-in + custom recognizers
5. **Results Storage** — Findings written to SQLite, text discarded

## Key Design Decisions

- **SQLite over Postgres**: Zero config, no daemon, cross-platform, handles our scale
- **Multiprocessing over async**: CPU-bound NLP work benefits from true parallelism
- **Presidio over custom NLP**: Battle-tested PII detection, extensible recognizer API
- **Local-only**: Government data cannot leave the machine, period
- **Text never stored**: Only PII metadata and short context snippets persist

## Privacy Model

Documents and extracted text are NEVER stored. The database contains only:
- Document metadata (filename, page count, status)
- Finding metadata (PII type, confidence, page number, character offset)
- Short context snippets (~20 chars around each finding)
