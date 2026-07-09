@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Python nao encontrado no PATH.
  echo Instale Python 3.11+ e marque a opcao "Add Python to PATH".
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo [INIT] Criando ambiente virtual...
  python -m venv venv
)

call venv\Scripts\activate.bat

if "%APP_PORT%"=="" set APP_PORT=5050

python -c "import flask,pymysql,openpyxl,requests" >nul 2>&1
if errorlevel 1 (
  echo [INIT] Instalando dependencias iniciais...
  python -m pip install --upgrade pip
  pip install -r requirements_fullstack.txt
  if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
  )
)

set FLASK_APP=app.py
set FLASK_ENV=development

start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='http://127.0.0.1:%APP_PORT%/login'; for($i=0; $i -lt 30; $i++){ try { $tcp = New-Object Net.Sockets.TcpClient; $a = $tcp.BeginConnect('127.0.0.1', %APP_PORT%, $null, $null); if($a.AsyncWaitHandle.WaitOne(300)){ $tcp.EndConnect($a); $tcp.Close(); Start-Process $u; break }; $tcp.Close() } catch {}; Start-Sleep -Milliseconds 500 }"
echo [START] Iniciando Troubleshooting em http://127.0.0.1:%APP_PORT%
python app.py
