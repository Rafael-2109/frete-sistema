#!/bin/bash
# Script para corrigir erro "unknown opcode 0" - corrupção de bytecode
# Data: 19/09/2025

echo "🔧 CORREÇÃO DE BYTECODE CORROMPIDO"
echo "=================================="

# 1. Limpar TODOS os arquivos .pyc do projeto
echo "🧹 Limpando arquivos .pyc corrompidos..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null

echo "✅ Arquivos .pyc removidos"

# 2. Recompilar todos os arquivos Python
echo "🔄 Recompilando arquivos Python..."
python3 -m compileall -f app/ 2>/dev/null

echo "✅ Arquivos recompilados"

# 3. Reiniciar aplicação (se usando gunicorn/uwsgi)
echo "🔄 Reiniciando aplicação..."

# Se estiver usando systemd
if systemctl is-active --quiet frete_sistema; then
    sudo systemctl restart frete_sistema
    echo "✅ Serviço reiniciado via systemd"
fi

# Se estiver usando supervisor
if supervisorctl status frete_sistema &>/dev/null; then
    supervisorctl restart frete_sistema
    echo "✅ Serviço reiniciado via supervisor"
fi

# Se estiver em desenvolvimento
if pgrep -f "flask run" > /dev/null; then
    pkill -f "flask run"
    echo "✅ Flask development server será reiniciado manualmente"
fi

echo ""
echo "🎯 CORREÇÃO CONCLUÍDA!"
echo ""
echo "Se o erro persistir, execute:"
echo "  1. pip install --upgrade --force-reinstall sqlalchemy"
echo "  2. Reinicie o servidor/container"