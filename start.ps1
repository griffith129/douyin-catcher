# ============================================================
# douyin-catcher full suite launcher
# Starts: douyin-chat-export (:8000) + douyin-catcher (:8787)
# Health-checks: LLM reverse proxy (:7864, owned by WorkBuddy)
# Usage: right-click -> Run with PowerShell, or: powershell -File start.ps1
# ============================================================

$ErrorActionPreference = "Stop"

$catcher = $PSScriptRoot
$parent = Split-Path $catcher -Parent
$exporter = Join-Path $parent "douyin-chat-export"

function Test-Port([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync("127.0.0.1", $port)
        if (-not $task.Wait(1500)) { return $false }
        return $client.Connected
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

Write-Host "=== douyin-catcher suite launcher ===" -ForegroundColor Cyan

# --- 1) douyin-chat-export (port 8000) ---
if (Test-Port 8000) {
    Write-Host "[=] douyin-chat-export already running on :8000"
} elseif (Test-Path (Join-Path $exporter ".venv\Scripts\python.exe")) {
    Write-Host "[+] starting douyin-chat-export on :8000 ..."
    Start-Process -FilePath (Join-Path $exporter ".venv\Scripts\python.exe") `
        -ArgumentList "start_server.py" -WorkingDirectory $exporter -WindowStyle Minimized
} else {
    Write-Host "[!] douyin-chat-export not found at $exporter (skipped)" -ForegroundColor Yellow
}

# --- 2) douyin-catcher (port 8787) ---
if (Test-Port 8787) {
    Write-Host "[=] douyin-catcher already running on :8787"
} else {
    Write-Host "[+] starting douyin-catcher on :8787 ..."
    Start-Process -FilePath "uv" `
        -ArgumentList "run", "uvicorn", "douyin_catcher.server:app", "--host", "127.0.0.1", "--port", "8787" `
        -WorkingDirectory $catcher -WindowStyle Minimized
}

# --- 3) wait for services to come up ---
Write-Host "[...] waiting for services (max 30s) ..."
$ok8000 = $false
$ok8787 = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 2
    if (-not $ok8000) { $ok8000 = Test-Port 8000 }
    if (-not $ok8787) { $ok8787 = Test-Port 8787 }
    if ($ok8000 -and $ok8787) { break }
}

if ($ok8000) { Write-Host "[OK] douyin-chat-export  ->  http://127.0.0.1:8000" -ForegroundColor Green }
else        { Write-Host "[FAIL] douyin-chat-export did not come up (check its window/logs)" -ForegroundColor Red }

if ($ok8787) { Write-Host "[OK] douyin-catcher      ->  http://127.0.0.1:8787" -ForegroundColor Green }
else         { Write-Host "[FAIL] douyin-catcher did not come up (check its window/logs)" -ForegroundColor Red }

# --- 4) LLM reverse proxy health check (owned by WorkBuddy, cannot be started here) ---
if (Test-Port 7864) {
    Write-Host "[OK] LLM reverse proxy   ->  http://127.0.0.1:7864" -ForegroundColor Green
} else {
    Write-Host "[WARN] LLM reverse proxy :7864 is DOWN." -ForegroundColor Yellow
    Write-Host "       It belongs to WorkBuddy - start/keep the WorkBuddy app running." -ForegroundColor Yellow
    Write-Host "       Video processing will fail at the summary step until it is up." -ForegroundColor Yellow
}

# --- 5) open the selection UI ---
if ($ok8787) {
    Write-Host "[+] opening http://127.0.0.1:8787/inbox in browser ..."
    Start-Process "http://127.0.0.1:8787/inbox"
}

Write-Host "=== done ===" -ForegroundColor Cyan
Write-Host "Tip: close the minimized server windows (or use Task Manager) to stop the suite."
