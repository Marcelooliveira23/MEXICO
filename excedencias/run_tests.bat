@echo off
REM ================================================================
REM SCRIPT DE TESTES COMPLETO
REM Executa toda a suite de testes do sistema
REM ================================================================

echo.
echo ================================================================
echo SISTEMA DE ANALISE DE EXCEDENCIAS - TESTES
echo ================================================================
echo.

REM Ativar ambiente virtual
call venv\Scripts\activate.bat

REM Verificar se ativou corretamente
if errorlevel 1 (
    echo ERRO: Falha ao ativar ambiente virtual
    pause
    exit /b 1
)

echo [OK] Ambiente virtual ativado
echo.

REM Instalar dependencias de teste (se necessario)
echo Verificando dependencias...
pip install --quiet psutil 2>nul
echo [OK] Dependencias verificadas
echo.

REM Executar testes
cd tests
echo ================================================================
echo EXECUTANDO SUITE DE TESTES
echo ================================================================
echo.

python run_all_tests.py

REM Capturar codigo de saida
set TEST_RESULT=%errorlevel%

cd ..

echo.
echo ================================================================
if %TEST_RESULT% equ 0 (
    echo RESULTADO: TODOS OS TESTES PASSARAM
    echo ================================================================
    echo.
    echo Sistema certificado e pronto para uso!
) else (
    echo RESULTADO: ALGUNS TESTES FALHARAM
    echo ================================================================
    echo.
    echo Verifique os erros acima e corrija antes de prosseguir.
)
echo.

REM Desativar ambiente
deactivate

pause
exit /b %TEST_RESULT%
