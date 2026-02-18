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


@app.on_event("shutdown")
def shutdown() -> None:
    """Terminate any active worker pools so child processes don't hold the port."""
    from backend.processing.worker_pool import shutdown_all_pools

    shutdown_all_pools()


# Serve the built frontend if it exists.
# In frozen mode (PyInstaller), assets are under sys._MEIPASS.
import sys as _sys

if getattr(_sys, "frozen", False):
    _frontend_dist = Path(_sys._MEIPASS) / "frontend" / "dist"
else:
    _frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
