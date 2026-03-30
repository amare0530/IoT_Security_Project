Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

Write-Host "=== IoT Security Project - Stop All ===" -ForegroundColor Magenta

$targets = @("node.py", "mqtt_bridge.py", "streamlit run", "app.py")

$all = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -in @("python.exe", "python3.exe", "pwsh.exe", "powershell.exe")
}

$matched = @()
foreach ($p in $all) {
    $cmd = [string]$p.CommandLine
    foreach ($t in $targets) {
        if ($cmd -like "*$t*") {
            $matched += $p
            break
        }
    }
}

if (-not $matched -or $matched.Count -eq 0) {
    Write-Warn "No Node/Bridge/Streamlit related process found"
    exit 0
}

$unique = $matched | Sort-Object ProcessId -Unique
Write-Info "Stopping $($unique.Count) process(es)"

foreach ($p in $unique) {
    try {
        $exists = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
        if (-not $exists) {
            Write-Info "PID $($p.ProcessId) already exited"
            continue
        }

        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
        Write-Ok "Stopped PID $($p.ProcessId): $($p.Name)"
    }
    catch {
        if ($_.Exception.Message -match "找不到處理序識別元|Cannot find a process with the process identifier") {
            Write-Info "PID $($p.ProcessId) already exited"
        }
        else {
            Write-Warn "Failed to stop PID $($p.ProcessId): $($_.Exception.Message)"
        }
    }
}

Write-Ok "Stop sequence completed"
