@echo off
REM Sistema de Análise de Inspeção de Aeronaves Mexicana
REM ===================================================

cd /d "%~dp0"

echo.
echo ========================================
echo  Mexicana Aircraft Inspection Analysis
echo ========================================
echo.

REM Verificar se ambiente virtual existe
if not exist "venv\Scripts\python.exe" (
    echo [SETUP] Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual!
        pause
        exit /b 1
    )
    
    echo [SETUP] Instalando dependências...
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependências!
        pause
        exit /b 1
    )
    echo [OK] Ambiente configurado com sucesso!
    echo.
)

REM Executar aplicação
echo [INICIANDO] Carregando aplicativo...
echo.
venv\Scripts\python.exe src\main.py

if errorlevel 1 (
    echo.
    echo [ERRO] A aplicação terminou com erro!
    pause
    exit /b 1
)

REM Se chegou aqui, tudo OK
echo.
echo [OK] Aplicação encerrada normalmente.
timeout /t 3 >nul

