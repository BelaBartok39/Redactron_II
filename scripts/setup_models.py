#!/usr/bin/env python3
"""Download required models and check external dependencies."""

import shutil
import subprocess
import sys


def check_tesseract() -> bool:
    """Check if Tesseract OCR is installed."""
    path = shutil.which("tesseract")
    if path:
        print(f"[OK] Tesseract found: {path}")
        result = subprocess.run(
            ["tesseract", "--version"], capture_output=True, text=True
        )
        version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
        print(f"     Version: {version_line}")
        return True
    else:
        print("[WARN] Tesseract not found on PATH.")
        print("       OCR for scanned pages will not work.")
        print("       Install: https://github.com/UB-Mannheim/tesseract/wiki")
        return False


def download_spacy_model() -> bool:
    """Download the spaCy English model."""
    print("Downloading spaCy en_core_web_lg model...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "spacy", "download", "en_core_web_lg"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("[OK] spaCy model downloaded successfully.")
            return True
        else:
            print(f"[ERROR] Failed to download spaCy model: {result.stderr}")
            return False
    except FileNotFoundError:
        print("[ERROR] spaCy not installed. Run: pip install -e '.[dev]'")
        return False


def main() -> None:
    print("=" * 50)
    print("RedactQC - Model & Dependency Setup")
    print("=" * 50)
    print()

    check_tesseract()
    print()
    download_spacy_model()
    print()
    print("Setup complete.")


if __name__ == "__main__":
    main()
