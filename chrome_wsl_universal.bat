@echo off
echo ========================================================
echo CHROME UNIVERSAL PARA WSL - ACEITA TODAS CONEXOES
echo ========================================================
echo.

REM Fechar Chrome se estiver rodando
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 1 >nul

REM Criar pasta temporaria
if not exist "C:\temp\chrome-debug" mkdir "C:\temp\chrome-debug"

REM Detectar Chrome
set CHROME=
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe
    goto found
)
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    set CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
    goto found
)
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
    set CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe
    goto found
)

echo ERRO: Chrome nao encontrado!
pause
exit /b 1

:found
echo Chrome encontrado!
echo.
echo Iniciando Chrome com debug port aberto para TODAS as conexoes...
echo.

REM Iniciar Chrome com 0.0.0.0 para aceitar de qualquer IP
"%CHROME%" ^
    --remote-debugging-port=9222 ^
    --remote-debugging-address=0.0.0.0 ^
    --user-data-dir="C:\temp\chrome-debug" ^
    --disable-gpu ^
    --no-sandbox ^
    --disable-web-security

echo.
echo Chrome iniciado! NAO FECHE ESTA JANELA!
echo.
echo Para testar no WSL, execute:
echo   python testar_chrome_wsl.py
echo.
pause