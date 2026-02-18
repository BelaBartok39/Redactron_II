#!/usr/bin/env python3
"""Cross-platform build script using PyInstaller."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
DIST = ROOT / "dist"


def build_frontend() -> None:
    """Build the React frontend."""
    print("=== Building frontend ===")
    if not (FRONTEND / "node_modules").is_dir():
        subprocess.run(["npm", "install"], cwd=str(FRONTEND), check=True)
    subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND), check=True)
    print("Frontend built successfully.")


def build_executable() -> None:
    """Build the Python executable with PyInstaller."""
    print("=== Building executable ===")

    frontend_dist = FRONTEND / "dist"
    if not frontend_dist.is_dir():
        print("ERROR: frontend/dist not found. Run build_frontend() first.")
        sys.exit(1)

    # PyInstaller spec
    entry = ROOT / "run.py"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=RedactQC",
        "--onedir",
        f"--distpath={DIST}",
        "--noconfirm",
        "--clean",
        # Add frontend dist as data
        f"--add-data={frontend_dist}{os.pathsep}frontend/dist",
        # Add backend package
        f"--add-data={BACKEND}{os.pathsep}backend",
        # Hidden imports
        "--hidden-import=uvicorn",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        str(entry),
    ]

    subprocess.run(cmd, check=True)
    print(f"Executable built at: {DIST / 'RedactQC'}")


def main() -> None:
    print("=" * 50)
    print("RedactQC Build")
    print("=" * 50)
    print()

    args = sys.argv[1:]
    if "frontend" in args:
        build_frontend()
    elif "exe" in args:
        build_executable()
    else:
        build_frontend()
        build_executable()

    print()
    print("Build complete!")


if __name__ == "__main__":
    main()
