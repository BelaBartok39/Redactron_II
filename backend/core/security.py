"""Secure temporary file handling — overwrite before delete."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


def secure_delete(path: Path) -> None:
    """Overwrite file contents with zeros before unlinking."""
    if not path.exists():
        return
    try:
        size = path.stat().st_size
        with open(path, "wb") as f:
            f.write(b"\x00" * size)
            f.flush()
            os.fsync(f.fileno())
        path.unlink()
    except OSError:
        # Best effort — still unlink
        try:
            path.unlink()
        except OSError:
            pass


@contextmanager
def secure_tempfile(
    suffix: str = ".tmp", prefix: str = "rqc_"
) -> Generator[Path, None, None]:
    """Create a temp file that is securely deleted on exit."""
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    path = Path(tmp_path)
    try:
        os.close(fd)
        yield path
    finally:
        secure_delete(path)
