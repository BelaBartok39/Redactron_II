# RedactQC - Windows Setup & Run Script
# Run directly: powershell -ExecutionPolicy Bypass -File setup-and-run.ps1
# Or double-click setup-and-run.bat

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Err  { param($msg) Write-Host "  [ERROR] $msg" -ForegroundColor Red }

function Exit-WithPause {
    param($code = 1)
    Write-Host "`nPress Enter to exit..." -ForegroundColor Gray
    Read-Host | Out-Null
    exit $code
}

# ── 1. Check Python ──────────────────────────────────────────────────────────
Write-Step "Checking Python"

$python = $null
# Try py launcher first (standard on Windows Python installs)
try {
    $ver = & py -3 --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $ver -match "Python 3\.(\d+)") {
        $minor = [int]$Matches[1]
        if ($minor -ge 11) {
            $python = "py -3"
            Write-Ok $ver
        } else {
            Write-Err "Python 3.11+ required, found $ver"
            Write-Host "  Download from https://www.python.org/downloads/" -ForegroundColor Gray
            Exit-WithPause
        }
    }
} catch {}

if (-not $python) {
    try {
        $ver = & python --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 11) {
                $python = "python"
                Write-Ok $ver
            } else {
                Write-Err "Python 3.11+ required, found $ver"
                Write-Host "  Download from https://www.python.org/downloads/" -ForegroundColor Gray
                Exit-WithPause
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Err "Python not found. Install Python 3.11+ from https://www.python.org/downloads/"
    Write-Host "  Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Gray
    Exit-WithPause
}

# ── 2. Check Tesseract OCR ───────────────────────────────────────────────────
Write-Step "Checking Tesseract OCR"

$tesseractPath = $null
$standardPaths = @(
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
)

foreach ($p in $standardPaths) {
    if (Test-Path $p) {
        $tesseractPath = $p
        break
    }
}

if (-not $tesseractPath) {
    # Check PATH
    $tesseractPath = (Get-Command tesseract -ErrorAction SilentlyContinue).Source
}

if ($tesseractPath) {
    $tver = & $tesseractPath --version 2>&1 | Select-Object -First 1
    Write-Ok "Tesseract found: $tesseractPath ($tver)"

    # Add Tesseract dir to session PATH if not already there
    $tesseractDir = Split-Path -Parent $tesseractPath
    if ($env:PATH -notlike "*$tesseractDir*") {
        $env:PATH = "$tesseractDir;$env:PATH"
        Write-Ok "Added Tesseract to session PATH"
    }
} else {
    Write-Warn "Tesseract OCR not found (needed for scanned PDF processing)"
    Write-Host "  Install from: https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Gray
    Write-Host "  Default install path: C:\Program Files\Tesseract-OCR" -ForegroundColor Gray
    Write-Host "  Continuing without OCR support..." -ForegroundColor Gray
}

# ── 3. Create virtual environment ────────────────────────────────────────────
Write-Step "Setting up virtual environment"

$venvDir = Join-Path $ROOT ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "  Creating .venv..."
    if ($python -eq "py -3") {
        & py -3 -m venv $venvDir
    } else {
        & python -m venv $venvDir
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to create virtual environment"
        Exit-WithPause
    }
    Write-Ok "Virtual environment created"
} else {
    Write-Ok "Virtual environment already exists"
}

# ── 4. Install dependencies ──────────────────────────────────────────────────
Write-Step "Installing Python dependencies"

Push-Location $ROOT
& $venvPython -m pip install -e ".[dev]" --quiet
$pipExit = $LASTEXITCODE
Pop-Location
if ($pipExit -ne 0) {
    Write-Err "Failed to install dependencies. Check the output above."
    Exit-WithPause
}
Write-Ok "Dependencies installed"

# ── 5. Download spaCy model ──────────────────────────────────────────────────
Write-Step "Setting up NLP models"

$setupScript = Join-Path $ROOT "scripts\setup_models.py"
if (Test-Path $setupScript) {
    & $venvPython $setupScript
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to download NLP models. Check your internet connection."
        Exit-WithPause
    }
    Write-Ok "NLP models ready"
} else {
    Write-Warn "scripts/setup_models.py not found, skipping model setup"
}

# ── 6. Build frontend (if needed) ────────────────────────────────────────────
Write-Step "Checking frontend build"

$frontendDist = Join-Path $ROOT "frontend\dist\index.html"
if (Test-Path $frontendDist) {
    Write-Ok "Frontend already built"
} else {
    $nodeAvailable = $null
    try { $nodeAvailable = Get-Command node -ErrorAction SilentlyContinue } catch {}

    if ($nodeAvailable) {
        Write-Host "  Building frontend (this may take a minute)..."
        $frontendDir = Join-Path $ROOT "frontend"

        if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
            & npm install --prefix $frontendDir
            if ($LASTEXITCODE -ne 0) {
                Write-Warn "npm install failed, frontend will not be available"
            }
        }

        & npm run build --prefix $frontendDir
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "Frontend build failed. The API will still work but no dashboard UI."
        } else {
            Write-Ok "Frontend built"
        }
    } else {
        Write-Warn "Node.js not found, skipping frontend build"
        Write-Host "  The API will work but there will be no dashboard UI." -ForegroundColor Gray
        Write-Host "  Install Node.js from https://nodejs.org/" -ForegroundColor Gray
    }
}

# ── 7. Launch RedactQC ───────────────────────────────────────────────────────
Write-Step "Starting RedactQC"

$runScript = Join-Path $ROOT "run.py"
Write-Host "  Launching server on http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Press Ctrl+C to stop.`n" -ForegroundColor Gray

& $venvPython $runScript
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Err "RedactQC exited with code $exitCode"
    Exit-WithPause $exitCode
}
