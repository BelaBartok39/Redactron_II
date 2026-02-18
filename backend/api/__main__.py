"""Allow running with: python -m backend.api"""

from backend.api.main import app  # noqa: F401

if __name__ == "__main__":
    import atexit
    import signal
    import sys

    import uvicorn
    from backend.core.config import settings
    from backend.core.database import db

    def _cleanup() -> None:
        from backend.processing.worker_pool import shutdown_all_pools
        shutdown_all_pools()

    def _signal_handler(sig: int, frame: object) -> None:
        _cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    atexit.register(_cleanup)

    settings.ensure_dirs()
    db.initialize()
    uvicorn.run(app, host=settings.host, port=settings.port)
