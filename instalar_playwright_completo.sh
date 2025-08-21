#!/bin/bash
# Script completo para instalar Playwright após ter sudo

echo "🚀 INSTALAÇÃO COMPLETA DO PLAYWRIGHT"
echo "===================================="
echo

# Verificar se sudo funciona
echo "Verificando sudo..."
if ! sudo -n true 2>/dev/null; then 
    echo "❌ Sudo precisa de senha. Digite sua senha:"
    sudo echo "✅ Sudo funcionando!"
fi

# Atualizar sistema
echo
echo "1. Atualizando sistema..."
sudo apt-get update

# Instalar dependências
echo
echo "2. Instalando dependências do Chromium..."
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1

# Instalar via Playwright também
echo
echo "3. Instalando via Playwright..."
playwright install-deps chromium

# Reinstalar o Chromium
echo
echo "4. Reinstalando Chromium..."
playwright install chromium --force

# Testar
echo
echo "5. Testando instalação..."
python testar_playwright_instalacao.py

echo
echo "✅ INSTALAÇÃO CONCLUÍDA!"
echo
echo "Se funcionou, execute:"
echo "  python configurar_sessao_atacadao.py"