#!/usr/bin/env python3
"""RedactQC application entry point.

Initializes the database, starts the FastAPI server on localhost,
and opens the default browser to the dashboard.
"""

from __future__ import annotations

import sys
import threading
import time
import webbrowser

import uvicorn

from backend.core.config import settings
from backend.core.database import db


def open_browser(url: str, delay: float = 1.5) -> None:
    """Open the default browser after a short delay."""
    def _open() -> None:
        time.sleep(delay)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


def main() -> None:
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

    uvicorn.run(
        "backend.api.main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
