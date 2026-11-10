# ============================================================
# douyin-catcher full suite launcher
# Starts: LLM API stack (wb2api gateway :7863 + bridge :7864)
#         + douyin-chat-export (:8000) + douyin-catcher (:8787)
# Usage: right-click -> Run with PowerShell, or: powershell -File start.ps1
# ============================================================

$ErrorActionPreference = "Stop"

$catcher = $PSScriptRoot
$parent = Split-Path $catcher -Parent
$exporter = Join-Path $parent "douyin-chat-export"

# LLM API 栈（wb2api-win：网关 7863 + Codex 协议桥 7864）所在目录；路径变化时改这里
$wb2apiDir = "D:\AAA——WorkBuddy工作默认文件夹\积分管理\wb2api-win"

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

# --- 0) LLM API stack (wb2api gateway :7863 + bridge :7864) ---
if (Test-Port 7864) {
    Write-Host "[=] LLM API stack already running on :7864"
} elseif (Test-Path (Join-Path $wb2apiDir "start_all.bat")) {
    Write-Host "[+] starting LLM API stack (gateway :7863 + bridge :7864) ..."
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c", (Join-Path $wb2apiDir "start_all.bat") `
        -WorkingDirectory $wb2apiDir -WindowStyle Minimized
    Write-Host "[...] waiting for LLM bridge :7864 (max 40s) ..."
    $ok7864 = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 2
        if (Test-Port 7864) { $ok7864 = $true; break }
    }
    if ($ok7864) {
        Write-Host "[OK] LLM API              ->  http://127.0.0.1:7864" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] LLM API bridge did not come up" -ForegroundColor Red
        Write-Host "       Check logs: $wb2apiDir\logs\bridge.log / gateway.log" -ForegroundColor Yellow
        Write-Host "       Video processing will fail at the summary step until it is up." -ForegroundColor Yellow
    }
} else {
    Write-Host "[!] wb2api-win not found at $wb2apiDir (skipped)" -ForegroundColor Yellow
    Write-Host "    Edit `$wb2apiDir at the top of this script if the path changed." -ForegroundColor Yellow
}

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

# --- 4) LLM bridge status (started in step 0 via wb2api-win start_all.bat) ---
if (Test-Port 7864) {
    Write-Host "[OK] LLM reverse proxy   ->  http://127.0.0.1:7864" -ForegroundColor Green
} else {
    Write-Host "[WARN] LLM bridge :7864 is DOWN." -ForegroundColor Yellow
    Write-Host "       Re-run this script, or start it manually: $wb2apiDir\start_all.bat" -ForegroundColor Yellow
    Write-Host "       Check logs: $wb2apiDir\logs\bridge.log" -ForegroundColor Yellow
}

# --- 4.5) douyin login state check (real browser probe, may take ~15s) ---
if ($ok8000) {
    Write-Host "[...] checking douyin login state (opens headless browser, ~15s) ..."
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/panel/api/login/check" -TimeoutSec 60
        if ($resp.status -eq "logged_in") {
            Write-Host "[OK] douyin login state: valid (cookie persists, no re-login needed)" -ForegroundColor Green
        } elseif ($resp.status -eq "expired" -or $resp.status -eq "no_profile") {
            Write-Host "[WARN] douyin login state: $($resp.status)" -ForegroundColor Yellow
            Write-Host "       Fix: open http://127.0.0.1:8000/panel -> login section ->" -ForegroundColor Yellow
            Write-Host "       import fresh cookies (cookie-editor JSON) or scan the QR code once." -ForegroundColor Yellow
        } else {
            Write-Host "[WARN] douyin login check returned: $($resp.status) $($resp.message)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[WARN] could not check login state ($($_.Exception.Message))" -ForegroundColor Yellow
        Write-Host "       If the panel has a password set, check manually at http://127.0.0.1:8000/panel" -ForegroundColor Yellow
    }
}

# --- 5) open both stations: collector panel + selection UI ---
if ($ok8000) {
    Write-Host "[+] opening collector panel http://127.0.0.1:8000/panel ..."
    Start-Process "http://127.0.0.1:8000/panel"
}
if ($ok8787) {
    Write-Host "[+] opening selection station http://127.0.0.1:8787/inbox ..."
    Start-Process "http://127.0.0.1:8787/inbox"
}

Write-Host "=== done ===" -ForegroundColor Cyan
Write-Host "Tip: close the minimized server windows (or use Task Manager) to stop the suite."
