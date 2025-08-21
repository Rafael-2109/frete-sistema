#!/bin/bash
# Instalação de dependências para Ubuntu 24 (Noble)

echo "🔧 Instalando dependências do Chromium para Ubuntu 24"
echo "====================================================="

# Instalar as versões corretas para Ubuntu 24
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libcups2t64 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    libatspi2.0-0t64 \
    libxshmfence1 \
    libdrm2 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxss1 \
    libglib2.0-0t64 \
    libgtk-3-0t64 \
    libdbus-1-3 \
    libexpat1 \
    libxcursor1 \
    libxi6 \
    libxtst6

echo "✅ Dependências instaladas!"