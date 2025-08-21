@echo off
echo ========================================================
echo CONFIGURACAO (ADMIN) - FIREWALL + TESTE
echo ========================================================
echo.

REM Verificar privilegios de administrador
net session >nul 2>&1
if not %errorlevel%==0 (
  echo [ERRO] Execute este script como ADMINISTRADOR.
  pause
  exit /b 1
)

echo [1/2] Configurando Firewall (porta TCP 9222)...
netsh advfirewall firewall delete rule name="Chrome Debug Port WSL" >nul 2>&1
netsh advfirewall firewall add rule name="Chrome Debug Port WSL" dir=in action=allow protocol=TCP localport=9222
echo [OK] Regra criada.

echo.
echo [2/2] Iniciando Chrome com debug port...
call "%~dp0iniciar_chrome_wsl.bat"

echo.
echo Dicas de teste no WSL:
echo   WIN_HOST=$(awk "/nameserver/ {print \$2}" /etc/resolv.conf) ^&^& curl http://$WIN_HOST:9222/json/version
echo.
pause