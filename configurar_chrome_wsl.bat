@echo off
echo ========================================================
echo CONFIGURACAO COMPLETA CHROME PARA WSL
echo ========================================================
echo.

REM Verificar se está rodando como Admin
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Rodando como Administrador
) else (
    echo [ERRO] Este script precisa rodar como ADMINISTRADOR!
    echo.
    echo Clique com botao direito e escolha "Executar como administrador"
    pause
    exit /b 1
)

echo.
echo ========================================================
echo PASSO 1: Configurar Firewall do Windows
echo ========================================================

REM Remover regra antiga se existir
netsh advfirewall firewall delete rule name="Chrome Debug Port WSL" >nul 2>&1

REM Adicionar nova regra para porta 9222
netsh advfirewall firewall add rule name="Chrome Debug Port WSL" dir=in action=allow protocol=TCP localport=9222
echo [OK] Firewall configurado para porta 9222

echo.
echo ========================================================
echo PASSO 2: Obter IP do WSL
echo ========================================================

REM Obter IP do adaptador WSL
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /C:"vEthernet (WSL)" /A:2 ^| findstr /C:"IPv4"') do (
    for /f "tokens=1" %%j in ("%%i") do set WSL_ADAPTER_IP=%%j
)

if defined WSL_ADAPTER_IP (
    echo IP do Adaptador WSL: %WSL_ADAPTER_IP%
) else (
    echo [AVISO] Nao encontrou adaptador WSL. Usando localhost.
    set WSL_ADAPTER_IP=localhost
)

echo.
echo ========================================================
echo PASSO 3: Iniciar Chrome com Debug Port
echo ========================================================

REM Fechar Chrome existente
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 >nul

REM Criar diretorio temporario
if not exist "C:\temp\chrome-debug" mkdir "C:\temp\chrome-debug"

REM Encontrar Chrome
set CHROME_PATH=
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=%ProgramFiles%\Google\Chrome\Application\chrome.exe
) else if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
) else if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=%LocalAppData%\Google\Chrome\Application\chrome.exe
)

if not defined CHROME_PATH (
    echo [ERRO] Chrome nao encontrado!
    echo Instale o Google Chrome primeiro.
    pause
    exit /b 1
)

echo Iniciando Chrome com debug port...
echo.
echo IMPORTANTE: NAO FECHE A JANELA DO CHROME!
echo.

REM Iniciar Chrome com todas as flags necessárias para WSL
start "" "%CHROME_PATH%" ^
    --remote-debugging-port=9222 ^
    --remote-debugging-address=0.0.0.0 ^
    --user-data-dir="C:\temp\chrome-debug" ^
    --disable-gpu ^
    --no-sandbox ^
    --disable-dev-shm-usage ^
    --disable-web-security ^
    --allow-insecure-localhost

timeout /t 3 >nul

echo.
echo ========================================================
echo PASSO 4: Testar Conexao
echo ========================================================

REM Testar se Chrome está respondendo
curl -s http://localhost:9222/json/version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Chrome respondendo em localhost:9222
) else (
    echo [AVISO] Chrome pode demorar alguns segundos para iniciar...
)

echo.
echo ========================================================
echo CONFIGURACAO CONCLUIDA!
echo ========================================================
echo.
echo NO WSL, teste com um destes comandos:
echo.
echo   curl http://localhost:9222/json/version
echo   curl http://%WSL_ADAPTER_IP%:9222/json/version
echo   curl http://host.docker.internal:9222/json/version
echo.
echo Se nenhum funcionar, execute no WSL:
echo   python diagnosticar_wsl_chrome.py
echo.
echo ========================================================
echo.
pause