#!/bin/bash
# Instalação simples do Playwright no WSL

echo "🚀 INSTALANDO PLAYWRIGHT NO WSL"
echo "================================"
echo

# Instalar Playwright
pip install playwright

# Instalar navegadores (Chromium é suficiente)
playwright install chromium

# Instalar dependências do sistema
playwright install-deps

echo
echo "✅ Playwright instalado com sucesso!"
echo
echo "Próximos passos:"
echo "1. python configurar_sessao_atacadao.py (fazer login uma vez)"
echo "2. python agendar_atacadao.py (usar para agendamentos)"