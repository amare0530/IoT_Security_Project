param(
    [switch]$InstallDeps,
    [switch]$SkipBrokerCheck,
    [switch]$DryRun,
    [switch]$SkipVenvBootstrap
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$script:VenvRecreated = $false

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

function Test-PythonUsable([string]$pythonPath) {
    if (-not $pythonPath -or -not (Test-Path $pythonPath)) {
        return $false
    }

    try {
        & $pythonPath -c "import sys; print(sys.version)" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Resolve-VenvPython {
    $root = (Get-Location).Path
    $candidates = @(
        (Join-Path $root ".venv\\Scripts\\python.exe"),
        (Join-Path $root "venv\\Scripts\\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-PythonUsable $candidate) {
            return $candidate
        }

        if (Test-Path $candidate) {
            Write-Warn "Detected broken virtualenv Python: $candidate"
        }
    }

    return $null
}

function Resolve-SystemPython {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $pyPath = (& py -3 -c "import sys; print(sys.executable)" 2>$null)
        if ($LASTEXITCODE -eq 0 -and $pyPath) {
            $resolved = $pyPath.Trim()
            if (Test-PythonUsable $resolved) {
                return $resolved
            }
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        if (Test-PythonUsable $pythonCmd.Source) {
            return $pythonCmd.Source
        }
    }

    return $null
}

function Assert-NotMsysPython([string]$pythonPath) {
    if ($pythonPath -match "msys64") {
        throw "MSYS2 Python detected: $pythonPath. Use Windows Python instead (run: py -0p)."
    }
}

function Ensure-ProjectVenv([string]$rootPath, [string]$systemPython, [bool]$dryRun) {
    $venvDir = Join-Path $rootPath ".venv"
    $venvPy = Join-Path $venvDir "Scripts\\python.exe"

    if (Test-PythonUsable $venvPy) {
        $script:VenvRecreated = $false
        Write-Ok "Using local virtualenv: $venvPy"
        return $venvPy
    }

    if ($dryRun) {
        if (Test-Path $venvDir) {
            Write-Warn "[DryRun] Existing .venv is unusable and would be recreated"
        }
        else {
            Write-Info "[DryRun] Local .venv not found and would be created"
        }
        return $systemPython
    }

    if (Test-Path $venvDir) {
        Write-Warn "Existing .venv is unusable. Recreating local .venv ..."
        Remove-Item $venvDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    else {
        Write-Info "Creating local .venv ..."
    }

    & $systemPython -m venv $venvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-PythonUsable $venvPy)) {
        throw "Failed to create a usable local .venv using: $systemPython"
    }

    $script:VenvRecreated = $true
    Write-Ok "Local .venv is ready: $venvPy"
    return $venvPy
}

function Test-RequiredImports([string]$pythonExe) {
    $importCmd = "import paho.mqtt.client, streamlit, pandas; print('deps-ok')"
    try {
        & $pythonExe -c $importCmd 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
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
    try {
        & $pythonExe -m pip --version 2>$null | Out-Null
    }
    catch {
        # Use LASTEXITCODE check below for a consistent error message.
    }

    if ($LASTEXITCODE -ne 0) {
        throw "pip is not available in current Python: $pythonExe"
    }

    if (Test-RequiredImports $pythonExe) {
        Write-Ok "Dependency check passed (paho-mqtt / streamlit / pandas)"
        return
    }

    if (-not $autoInstall) {
        throw "Required packages are missing. Re-run with -InstallDeps."
    }

    Write-Info "Installing requirements.txt ..."
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r "requirements.txt"

    if (-not (Test-RequiredImports $pythonExe)) {
        throw "Import still fails after install. Check pip output."
    }

    Write-Ok "Dependencies installed and verified"
}

Write-Host "=== IoT Security Project - Auto Start ===" -ForegroundColor Magenta

$pythonExe = Resolve-VenvPython
if (-not $pythonExe) {
    $systemPython = Resolve-SystemPython
    if (-not $systemPython) {
        throw "No usable Python found. Install Python 3 first (run: py -0p)."
    }

    $systemPython = [System.IO.Path]::GetFullPath($systemPython)
    Assert-NotMsysPython $systemPython

    if ($SkipVenvBootstrap) {
        Write-Warn "No usable local .venv/venv found. Falling back to system Python."
        $pythonExe = $systemPython
    }
    else {
        $pythonExe = Ensure-ProjectVenv -rootPath (Get-Location).Path -systemPython $systemPython -dryRun:$DryRun
    }
}
if (-not $pythonExe) {
    throw "No usable Python found. Install Python 3 and create a venv first."
}

$pythonExe = [System.IO.Path]::GetFullPath($pythonExe)
Assert-NotMsysPython $pythonExe
Write-Ok "Using Python: $pythonExe"

$autoInstallDeps = $InstallDeps -or $script:VenvRecreated -or (-not $DryRun)
Ensure-Dependencies -pythonExe $pythonExe -autoInstall:$autoInstallDeps

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
