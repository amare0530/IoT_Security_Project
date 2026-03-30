param(
    [switch]$InstallDeps,
    [switch]$SkipBrokerCheck,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

function Resolve-VenvPython {
    $root = (Get-Location).Path
    $candidates = @(
        (Join-Path $root ".venv\\Scripts\\python.exe"),
        (Join-Path $root "venv\\Scripts\\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

function Resolve-SystemPython {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $pyPath = (& py -3 -c "import sys; print(sys.executable)" 2>$null)
        if ($LASTEXITCODE -eq 0 -and $pyPath) {
            return $pyPath.Trim()
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }

    return $null
}

function Assert-NotMsysPython([string]$pythonPath) {
    if ($pythonPath -match "msys64") {
        throw "MSYS2 Python detected: $pythonPath. Use Windows Python instead (run: py -0p)."
    }
}

function Test-TcpReachable([string]$targetHost, [int]$port, [int]$timeoutMs = 2500) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect($targetHost, $port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($timeoutMs, $false)
        if (-not $ok) {
            return $false
        }
        $client.EndConnect($iar)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Ensure-Dependencies([string]$pythonExe, [bool]$autoInstall) {
    & $pythonExe -m pip --version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "pip is not available in current Python: $pythonExe"
    }

    $importCmd = "import paho.mqtt.client, streamlit, pandas; print('deps-ok')"
    & $pythonExe -c $importCmd *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Dependency check passed (paho-mqtt / streamlit / pandas)"
        return
    }

    if (-not $autoInstall) {
        throw "Required packages are missing. Re-run with -InstallDeps."
    }

    Write-Info "Installing requirements.txt ..."
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r "requirements.txt"

    & $pythonExe -c $importCmd *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Import still fails after install. Check pip output."
    }

    Write-Ok "Dependencies installed and verified"
}

Write-Host "=== IoT Security Project - Auto Start ===" -ForegroundColor Magenta

$pythonExe = Resolve-VenvPython
if (-not $pythonExe) {
    Write-Warn "No local .venv/venv found. Falling back to system Python."
    $pythonExe = Resolve-SystemPython
}
if (-not $pythonExe) {
    throw "No usable Python found. Install Python 3 and create a venv first."
}

$pythonExe = [System.IO.Path]::GetFullPath($pythonExe)
Assert-NotMsysPython $pythonExe
Write-Ok "Using Python: $pythonExe"

Ensure-Dependencies -pythonExe $pythonExe -autoInstall:$InstallDeps

if (-not $SkipBrokerCheck) {
    Write-Info "Checking broker.emqx.io:1883 reachability ..."
    if (-not (Test-TcpReachable -targetHost "broker.emqx.io" -port 1883)) {
        throw "Cannot reach broker.emqx.io:1883. Check network/firewall or switch broker."
    }
    Write-Ok "Broker is reachable"
}

$streamlitBusy = Get-NetTCPConnection -State Listen -LocalPort 8501 -ErrorAction SilentlyContinue
if ($streamlitBusy) {
    throw "Port 8501 is in use. Stop existing Streamlit process first."
}
Write-Ok "Port 8501 is available"

$root = (Get-Location).Path
$nodeScript = Join-Path $root "node.py"
$bridgeScript = Join-Path $root "mqtt_bridge.py"
$appScript = Join-Path $root "app.py"

$nodeCmd = "& '$pythonExe' '$nodeScript'"
$bridgeCmd = "& '$pythonExe' '$bridgeScript'"
$appCmd = "& '$pythonExe' -m streamlit run '$appScript'"

Write-Info "Preparing to launch 3 processes..."
if ($DryRun) {
    Write-Host "[DryRun] Node:   $nodeCmd"
    Write-Host "[DryRun] Bridge: $bridgeCmd"
    Write-Host "[DryRun] App:    $appCmd"
    Write-Ok "Dry run finished"
    exit 0
}

$nodeProc = Start-Process powershell -ArgumentList @("-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $nodeCmd) -PassThru
Start-Sleep -Milliseconds 300
$bridgeProc = Start-Process powershell -ArgumentList @("-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $bridgeCmd) -PassThru
Start-Sleep -Milliseconds 300
$appProc = Start-Process powershell -ArgumentList @("-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $appCmd) -PassThru

Write-Ok "All terminals started"
Write-Host "Node terminal PID:   $($nodeProc.Id)"
Write-Host "Bridge terminal PID: $($bridgeProc.Id)"
Write-Host "App terminal PID:    $($appProc.Id)"
Write-Host "UI URL: http://localhost:8501"
Write-Host ""
Write-Host "To stop all processes run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\\scripts\\stop_all.ps1"
