$ErrorActionPreference = "Stop"

Write-Host "[INFO] Installing Python dependencies with binary-only preference..." -ForegroundColor Cyan

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  throw "Python virtual environment not found at .venv. Run: python -m venv .venv"
}

# Prefer wheels to avoid source builds that may trigger SSL failures in nested build tools.
& $python -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
  throw "pip bootstrap failed with exit code $LASTEXITCODE"
}

& $python -m pip install --only-binary=:all: -r requirements.txt
if ($LASTEXITCODE -ne 0) {
  throw "pip install failed with exit code $LASTEXITCODE"
}

Write-Host "[OK] Dependency installation completed." -ForegroundColor Green
