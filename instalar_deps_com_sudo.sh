#!/bin/bash
# Script para instalar dependências do Playwright com sudo

echo "🔧 INSTALANDO DEPENDÊNCIAS DO PLAYWRIGHT"
echo "========================================"
echo

# Atualizar lista de pacotes
echo "1. Atualizando lista de pacotes..."
sudo apt-get update

# Instalar dependências do Chromium
echo "2. Instalando dependências do Chromium..."
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
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

# Alternativa: usar o comando do Playwright
echo "3. Instalando via Playwright..."
sudo playwright install-deps chromium

echo
echo "✅ DEPENDÊNCIAS INSTALADAS!"
echo
echo "Agora teste com:"
echo "  python testar_playwright_instalacao.py"