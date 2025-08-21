#!/bin/bash
# Script para iniciar Chrome do Windows a partir do WSL

echo "=========================================="
echo "INICIANDO CHROME NO WINDOWS A PARTIR DO WSL"
echo "=========================================="
echo

# Fechar Chrome se estiver rodando
echo "Fechando Chrome existente..."
taskkill.exe /F /IM chrome.exe 2>/dev/null || true
sleep 2

# Criar diretório temporário no Windows
echo "Criando diretório temporário..."
cmd.exe /c "if not exist C:\\temp\\chrome-debug mkdir C:\\temp\\chrome-debug" 2>/dev/null

# Caminhos possíveis do Chrome no Windows
CHROME_PATHS=(
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
    "/mnt/c/Users/$USER/AppData/Local/Google/Chrome/Application/chrome.exe"
)

# Encontrar Chrome
CHROME_EXE=""
for path in "${CHROME_PATHS[@]}"; do
    if [ -f "$path" ]; then
        CHROME_EXE="$path"
        echo "Chrome encontrado em: $path"
        break
    fi
done

if [ -z "$CHROME_EXE" ]; then
    echo "❌ ERRO: Chrome não encontrado!"
    echo "Instale o Google Chrome no Windows primeiro."
    exit 1
fi

# Converter caminho WSL para Windows
CHROME_WIN=$(echo "$CHROME_EXE" | sed 's|/mnt/c/|C:\\|' | sed 's|/|\\|g')

echo
echo "Iniciando Chrome com debug port..."
echo "NÃO FECHE A JANELA DO CHROME!"
echo

# Iniciar Chrome com todas as flags necessárias
cmd.exe /c start "" "$CHROME_WIN" \
    --remote-debugging-port=9222 \
    --remote-debugging-address=0.0.0.0 \
    --user-data-dir="C:\\temp\\chrome-debug" \
    --disable-gpu \
    --no-sandbox \
    --disable-web-security

sleep 3

# Testar conexão
echo
echo "Testando conexão..."
echo

# Tentar diferentes IPs
for ip in localhost 127.0.0.1 $(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'); do
    echo -n "Testando $ip:9222... "
    if curl -s --connect-timeout 1 http://$ip:9222/json/version > /dev/null 2>&1; then
        echo "✅ FUNCIONANDO!"
        echo
        echo "Chrome está acessível em: http://$ip:9222"
        echo
        echo "Agora execute:"
        echo "  python testar_chrome_wsl.py"
        echo
        # Salvar IP funcionando
        echo "$ip" > .chrome_host
        exit 0
    else
        echo "❌"
    fi
done

echo
echo "⚠️ Chrome iniciado mas não consegui conectar do WSL"
echo "Tente executar: python diagnosticar_wsl_chrome.py"
echo