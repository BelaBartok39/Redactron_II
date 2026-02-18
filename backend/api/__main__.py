"""Allow running with: python -m backend.api"""

from backend.api.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn
    from backend.core.config import settings
    from backend.core.database import db

    settings.ensure_dirs()
    db.initialize()
    uvicorn.run(app, host=settings.host, port=settings.port)
