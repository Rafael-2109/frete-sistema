#!/bin/bash
# Teste rápido de conexão Chrome WSL

echo "🔍 Detectando IP do Windows..."
WIN_HOST=$(awk '/nameserver/ {print $2}' /etc/resolv.conf)
echo "   IP: $WIN_HOST"

echo
echo "🧪 Testando conexão com Chrome..."
if curl -s --connect-timeout 2 "http://$WIN_HOST:9222/json/version" > /dev/null 2>&1; then
    echo "✅ SUCESSO! Chrome acessível!"
    echo
    echo "Informações do Chrome:"
    curl -s "http://$WIN_HOST:9222/json/version" | python3 -m json.tool | head -5
    echo
    echo "📋 Próximos passos:"
    echo "1. python executar_migracao_protocolo.py"
    echo "2. python testar_chrome_wsl.py"
else
    echo "❌ Chrome não acessível em $WIN_HOST:9222"
    echo
    echo "📋 Checklist:"
    echo "1. Chrome está rodando no Windows?"
    echo "   Execute: iniciar_chrome_wsl.bat"
    echo
    echo "2. Firewall configurado?"
    echo "   Execute como Admin: setup_chrome_wsl_admin.bat"
    echo
    echo "3. Teste com telnet:"
    echo "   telnet $WIN_HOST 9222"
fi