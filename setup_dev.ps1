#!/usr/bin/env pwsh

param(
    [int]$Port = 5050
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERRO] Python nao encontrado no PATH." -ForegroundColor Red
    Write-Host "Instale Python 3.11+ e habilite 'Add Python to PATH'." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path '.env') -and (Test-Path '.env.example')) {
    Copy-Item '.env.example' '.env'
}

if (-not (Test-Path 'venv')) {
    python -m venv venv
}

& .\venv\Scripts\Activate.ps1

python -c "import flask,pymysql,openpyxl,requests" *>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dependencias nao encontradas. Instalando requirements_fullstack.txt..."
    python -m pip install --upgrade pip | Out-Null
    pip install -r requirements_fullstack.txt
}

Write-Host "Ambiente pronto. Iniciando app em http://127.0.0.1:$Port"
Start-Job -Name "ts_open_browser_$Port" -ScriptBlock {
    param($TargetPort)
    $targetUrl = "http://127.0.0.1:$TargetPort/login"
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $client = [System.Net.Sockets.TcpClient]::new()
            $async = $client.BeginConnect('127.0.0.1', $TargetPort, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(300)) {
                $client.EndConnect($async)
                $client.Close()
                Start-Process $targetUrl | Out-Null
                break
            }
            $client.Close()
        }
        catch {
            # Ignore transient startup errors while server is booting
        }
        Start-Sleep -Milliseconds 500
    }
} -ArgumentList $Port | Out-Null
python app.py
