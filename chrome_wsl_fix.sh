#!/bin/bash
# Script CORRIGIDO para iniciar Chrome com acesso do WSL

echo "=========================================="
echo "CHROME WSL FIX - VERSÃO CORRIGIDA"
echo "=========================================="
echo

# 1. Fechar TODOS os processos Chrome
echo "1. Fechando TODOS os processos Chrome..."
taskkill.exe /F /IM chrome.exe 2>/dev/null || true
sleep 3

# Verificar se ainda tem Chrome rodando
if tasklist.exe | grep -q chrome.exe; then
    echo "⚠️ Ainda tem Chrome rodando. Fechando novamente..."
    taskkill.exe /F /IM chrome.exe 2>/dev/null || true
    sleep 2
fi

# 2. Limpar diretório temporário
echo "2. Limpando diretório temporário..."
cmd.exe /c "rmdir /S /Q C:\\temp\\chrome-debug" 2>/dev/null || true
cmd.exe /c "mkdir C:\\temp\\chrome-debug" 2>/dev/null

# 3. Iniciar Chrome com comando COMPLETO via PowerShell
echo "3. Iniciando Chrome com configuração especial..."
echo

# Usar PowerShell para ter mais controle
powershell.exe -Command "& {
    \$chrome = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
    if (-not (Test-Path \$chrome)) {
        \$chrome = 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
    }
    
    # Iniciar Chrome com TODOS os parâmetros necessários
    Start-Process \$chrome -ArgumentList @(
        '--remote-debugging-port=9222',
        '--remote-debugging-address=0.0.0.0',
        '--user-data-dir=C:\\temp\\chrome-debug',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--allow-running-insecure-content',
        '--disable-blink-features=AutomationControlled',
        '--no-first-run',
        '--no-default-browser-check',
        '--window-size=1280,720'
    )
}" 2>/dev/null

echo "Aguardando Chrome iniciar..."
sleep 5

# 4. Verificar se está escutando corretamente
echo
echo "4. Verificando configuração..."
echo

# Ver em que endereço está escutando
echo -n "Porta 9222 está: "
if netstat.exe -an | grep -q "0.0.0.0:9222"; then
    echo "✅ Escutando em 0.0.0.0 (CORRETO!)"
elif netstat.exe -an | grep -q "127.0.0.1:9222"; then
    echo "⚠️ Escutando apenas em 127.0.0.1"
    echo
    echo "TENTANDO SOLUÇÃO ALTERNATIVA..."
    echo
    
    # Fechar e tentar novamente com método diferente
    taskkill.exe /F /IM chrome.exe 2>/dev/null || true
    sleep 2
    
    # Tentar iniciar diretamente via cmd.exe
    cmd.exe /c "start \"\" \"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir=C:\\temp\\chrome-debug --disable-gpu --no-sandbox" &
    
    sleep 5
else
    echo "❌ Não detectada"
fi

# 5. Testar conexão com diferentes métodos
echo
echo "5. Testando conexão..."
echo

# Método 1: Tentar todos os IPs possíveis
IPS=(
    "localhost"
    "127.0.0.1"
    "$(ip route | grep default | awk '{print $3}')"
    "$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')"
    "host.docker.internal"
)

WORKING_IP=""
for ip in "${IPS[@]}"; do
    if [ -z "$ip" ]; then continue; fi
    
    echo -n "Testando $ip:9222... "
    
    # Tentar com curl
    if curl -s --connect-timeout 1 "http://$ip:9222/json/version" > /dev/null 2>&1; then
        echo "✅ FUNCIONANDO!"
        WORKING_IP="$ip"
        break
    else
        # Tentar com nc (netcat)
        if nc -z -w1 "$ip" 9222 2>/dev/null; then
            echo "✅ Porta aberta (netcat)"
            WORKING_IP="$ip"
            break
        else
            echo "❌"
        fi
    fi
done

# 6. Resultado final
echo
echo "=========================================="
echo "RESULTADO:"
echo "=========================================="

if [ -n "$WORKING_IP" ]; then
    echo
    echo "✅ SUCESSO! Chrome acessível em: $WORKING_IP:9222"
    echo
    
    # Salvar IP funcionando
    echo "$WORKING_IP" > .chrome_host
    
    # Atualizar automaticamente os arquivos Python
    echo "Atualizando arquivos para usar $WORKING_IP..."
    
    # Atualizar browser_manager_simples.py
    sed -i "s/localhost:9222/$WORKING_IP:9222/g" app/portal/browser_manager_simples.py 2>/dev/null || true
    
    # Atualizar testar_chrome_wsl.py
    sed -i "s/'http:\/\/localhost:9222/'http:\/\/$WORKING_IP:9222/g" testar_chrome_wsl.py 2>/dev/null || true
    
    echo
    echo "📋 PRÓXIMOS PASSOS:"
    echo "1. Execute: python executar_migracao_protocolo.py"
    echo "2. Execute: python testar_chrome_wsl.py"
    echo
else
    echo
    echo "❌ NÃO FOI POSSÍVEL CONECTAR!"
    echo
    echo "🔧 SOLUÇÃO MANUAL:"
    echo
    echo "1. No Windows, abra o PowerShell como Administrador"
    echo "2. Execute estes comandos:"
    echo
    echo "   # Configurar firewall"
    echo "   New-NetFirewallRule -DisplayName 'Chrome Debug WSL' -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow"
    echo
    echo "   # Iniciar Chrome"
    echo '   & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir="C:\temp\chrome-debug" --no-sandbox'
    echo
    echo "3. No WSL, teste novamente:"
    echo "   python diagnosticar_wsl_chrome.py"
    echo
fi