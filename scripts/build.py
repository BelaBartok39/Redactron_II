#!/usr/bin/env python3
"""Cross-platform build script using PyInstaller.

Bundles the full RedactQC application including:
- Frontend dist (React build)
- spaCy model (en_core_web_lg)
- Presidio analyzer configs
- Tesseract OCR binary (if found on build machine)
- All required hidden imports for frozen execution
"""

import os
import platform
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
    # shell=True needed on Windows so that npm.cmd is resolved via PATH
    use_shell = platform.system() == "Windows"
    if not (FRONTEND / "node_modules").is_dir():
        subprocess.run(["npm", "install"], cwd=str(FRONTEND), check=True, shell=use_shell)
    subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND), check=True, shell=use_shell)
    print("Frontend built successfully.")


def find_tesseract() -> Path | None:
    """Locate the Tesseract OCR installation directory."""
    if platform.system() == "Windows":
        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR"),
        ]
        for p in candidates:
            if (p / "tesseract.exe").is_file():
                return p
    else:
        # Linux/macOS — find the binary, then bundle its directory
        result = shutil.which("tesseract")
        if result:
            return Path(result).resolve().parent

    return None


def build_executable() -> None:
    """Build the Python executable with PyInstaller."""
    print("=== Building executable ===")

    frontend_dist = FRONTEND / "dist"
    if not frontend_dist.is_dir():
        print("ERROR: frontend/dist not found. Run build_frontend() first.")
        sys.exit(1)

    entry = ROOT / "run.py"
    sep = os.pathsep  # ';' on Windows, ':' on Linux

    # Exclude tests and packages not needed at runtime.
    # NOTE: spacy.lang.* modules must NOT be excluded — spaCy's registry
    # initialization imports all of them, even when only English is used.
    excludes = [
        "spacy.tests",
        "thinc.tests",
        "pydantic.deprecated",
        # Not needed at runtime
        "pytest", "hypothesis", "IPython", "notebook", "tkinter",
    ]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=RedactQC",
        "--onedir",
        f"--distpath={DIST}",
        "--noconfirm",
        "--clean",
        # ── Frontend ──────────────────────────────────────────────────────
        f"--add-data={frontend_dist}{sep}frontend/dist",
        # ── spaCy model data ─────────────────────────────────────────────
        "--collect-data=en_core_web_lg",
        "--collect-data=spacy",
        "--collect-data=thinc",
        "--hidden-import=en_core_web_lg",
        # spaCy core modules (not --collect-all which pulls in tests)
        "--hidden-import=spacy",
        "--hidden-import=spacy.lang.en",
        "--hidden-import=spacy.pipeline",
        "--hidden-import=spacy.tokenizer",
        "--hidden-import=spacy.vocab",
        "--hidden-import=spacy.util",
        # spaCy C-extension dependencies
        "--hidden-import=cymem",
        "--hidden-import=cymem.cymem",
        "--hidden-import=preshed",
        "--hidden-import=preshed.maps",
        "--hidden-import=murmurhash",
        "--hidden-import=murmurhash.mrmr",
        "--hidden-import=blis",
        "--hidden-import=blis.py",
        "--hidden-import=srsly",
        "--hidden-import=srsly.msgpack",
        "--hidden-import=srsly.json_api",
        "--hidden-import=catalogue",
        "--hidden-import=confection",
        "--hidden-import=thinc",
        "--hidden-import=thinc.api",
        "--hidden-import=thinc.backends.numpy_ops",
        "--hidden-import=thinc.shims",
        # ── Presidio ─────────────────────────────────────────────────────
        "--collect-data=presidio_analyzer",
        "--hidden-import=presidio_analyzer",
        "--hidden-import=presidio_anonymizer",
        # ── Pydantic (FastAPI dependency) ─────────────────────────────────
        "--collect-data=pydantic",
        "--hidden-import=pydantic",
        "--hidden-import=pydantic.deprecated.decorator",
        "--hidden-import=pydantic_core",
        # ── ReportLab ─────────────────────────────────────────────────────
        "--collect-data=reportlab",
        "--hidden-import=reportlab",
        # ── Uvicorn ───────────────────────────────────────────────────────
        "--hidden-import=uvicorn",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.http.h11_impl",
        "--hidden-import=uvicorn.protocols.http.httptools_impl",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.protocols.websockets.wsproto_impl",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=uvicorn.lifespan.off",
        # ── FastAPI + Starlette ───────────────────────────────────────────
        "--hidden-import=fastapi",
        "--hidden-import=starlette",
        "--hidden-import=starlette.responses",
        "--hidden-import=starlette.routing",
        "--hidden-import=starlette.middleware",
        "--hidden-import=starlette.middleware.cors",
        # ── Multiprocessing (Windows spawn) ───────────────────────────────
        "--hidden-import=multiprocessing",
        "--hidden-import=multiprocessing.pool",
        "--hidden-import=multiprocessing.process",
        "--hidden-import=multiprocessing.spawn",
        "--hidden-import=multiprocessing.popen_spawn_win32",
        "--hidden-import=multiprocessing.reduction",
        # ── OCR dependencies ──────────────────────────────────────────────
        "--hidden-import=pytesseract",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        # ── PDF handling ──────────────────────────────────────────────────
        "--hidden-import=fitz",
        "--hidden-import=pymupdf",
        # ── Async support ─────────────────────────────────────────────────
        "--hidden-import=aiofiles",
        "--hidden-import=aiofiles.os",
    ]

    # Add excludes
    for mod in excludes:
        cmd.append(f"--exclude-module={mod}")

    # ── Bundle Tesseract OCR if found ─────────────────────────────────────
    tesseract_dir = find_tesseract()
    if tesseract_dir:
        print(f"Bundling Tesseract from: {tesseract_dir}")
        cmd.append(f"--add-data={tesseract_dir}{sep}tesseract")
    else:
        print("WARNING: Tesseract not found on build machine — OCR will require separate install")

    cmd.append(str(entry))
    subprocess.run(cmd, check=True)
    print(f"Executable built at: {DIST / 'RedactQC'}")


def verify_build() -> bool:
    """Check the build output contains critical files."""
    print("\n=== Verifying build ===")
    build_dir = DIST / "RedactQC"

    if not build_dir.is_dir():
        print("ERROR: Build directory not found")
        return False

    exe_name = "RedactQC.exe" if platform.system() == "Windows" else "RedactQC"
    # PyInstaller 6.x puts --add-data assets under _internal/
    search_dirs = [build_dir, build_dir / "_internal"]

    all_ok = True

    # Check executable
    exe_path = build_dir / exe_name
    if exe_path.exists():
        print(f"  [OK] Executable: {exe_name}")
    else:
        print(f"  [MISSING] Executable: {exe_name}")
        all_ok = False

    # Check frontend (could be at top level or under _internal)
    frontend_found = False
    for search_dir in search_dirs:
        candidate = search_dir / "frontend" / "dist" / "index.html"
        if candidate.exists():
            print(f"  [OK] Frontend: {candidate.relative_to(build_dir)}")
            frontend_found = True
            break
    if not frontend_found:
        print("  [MISSING] Frontend: frontend/dist/index.html")
        all_ok = False

    # Check for spaCy model data
    spacy_found = False
    for search_dir in search_dirs:
        if list(search_dir.rglob("en_core_web_lg/meta.json")):
            spacy_found = True
            break

    # Check for Presidio config
    presidio_found = False
    for search_dir in search_dirs:
        if list(search_dir.rglob("presidio_analyzer/conf*")):
            presidio_found = True
            break

    if spacy_found:
        print("  [OK] spaCy model (en_core_web_lg)")
    else:
        print("  [MISSING] spaCy model (en_core_web_lg) — PII detection will fail")
        all_ok = False

    if presidio_found:
        print("  [OK] Presidio analyzer config")
    else:
        print("  [MISSING] Presidio analyzer config — PII detection may fail")
        all_ok = False

    # Check for bundled Tesseract
    tesseract_exe = "tesseract.exe" if platform.system() == "Windows" else "tesseract"
    tesseract_bundled = list(build_dir.rglob(f"tesseract/{tesseract_exe}"))
    if tesseract_bundled:
        print(f"  [OK] Tesseract OCR bundled")
    else:
        print("  [INFO] Tesseract OCR not bundled — OCR requires separate install")

    # Report size
    total_size = sum(f.stat().st_size for f in build_dir.rglob("*") if f.is_file())
    print(f"\n  Total build size: {total_size / (1024 * 1024):.0f} MB")

    return all_ok


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
        verify_build()
    elif "verify" in args:
        verify_build()
    else:
        build_frontend()
        build_executable()
        if verify_build():
            print("\nBuild complete! Run dist/RedactQC/RedactQC to test.")
        else:
            print("\nBuild completed with warnings — check missing items above.")
            sys.exit(1)

    print()


if __name__ == "__main__":
    main()
