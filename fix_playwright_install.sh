#!/bin/bash
# Script para instalar Playwright e navegadores no servidor

echo "======================================"
echo "INSTALANDO PLAYWRIGHT E NAVEGADORES"
echo "======================================"

# 1. Instalar playwright se não estiver instalado
echo "1. Verificando Playwright..."
pip show playwright > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "   Instalando Playwright..."
    pip install playwright
else
    echo "   Playwright já instalado"
fi

# 2. Instalar navegadores
echo ""
echo "2. Instalando navegadores..."
python -m playwright install chromium

# 3. Instalar dependências do sistema (se necessário)
echo ""
echo "3. Instalando dependências do sistema..."
# Para Ubuntu/Debian
if command -v apt-get &> /dev/null; then
    python -m playwright install-deps chromium
fi

echo ""
echo "======================================"
echo "✅ INSTALAÇÃO CONCLUÍDA"
echo "======================================"
echo ""
echo "Para verificar:"
echo "  python -m playwright show-browsers"