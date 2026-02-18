#!/usr/bin/env python3
"""RedactQC application entry point.

Initializes the database, starts the FastAPI server on localhost,
and opens the default browser to the dashboard.
"""

from __future__ import annotations

import multiprocessing
import sys

# CRITICAL: Must be called before any heavy imports for PyInstaller on Windows.
# When multiprocessing spawns a child process in a frozen exe, the child
# re-executes this entry point. freeze_support() detects child processes
# and runs the worker code, preventing them from starting another server.
multiprocessing.freeze_support()

import threading
import time
import webbrowser

import uvicorn


def open_browser(url: str, delay: float = 1.5) -> None:
    """Open the default browser after a short delay."""
    def _open() -> None:
        time.sleep(delay)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


def main() -> None:
    # Lazy-import backend modules so worker child processes (handled by
    # freeze_support above) never execute this code path.
    from backend.core.config import settings
    from backend.core.database import db

    # Ensure data directories exist
    settings.ensure_dirs()

    # Initialize database schema
    db.initialize()

    url = f"http://{settings.host}:{settings.port}"
    print(f"RedactQC starting at {url}")
    print("Press Ctrl+C to stop.")

    # Open browser
    if "--no-browser" not in sys.argv:
        open_browser(url)

    # In frozen mode (PyInstaller), string-based app import fails —
    # pass the app object directly instead.
    if getattr(sys, "frozen", False):
        from backend.api.main import app
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level="info",
        )
    else:
        uvicorn.run(
            "backend.api.main:app",
            host=settings.host,
            port=settings.port,
            log_level="info",
        )


if __name__ == "__main__":
    main()
