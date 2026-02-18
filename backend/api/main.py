"""FastAPI application for RedactQC."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import batches, dashboard, documents, reports
from backend.core.database import db

app = FastAPI(title="RedactQC API", version="0.1.0")

# CORS for localhost development (Vite dev server on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(batches.router)
app.include_router(documents.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


@app.on_event("startup")
def startup() -> None:
    """Initialize the database on startup."""
    db.initialize()


# Serve the built frontend if it exists
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
