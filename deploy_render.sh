#!/bin/bash
# Script para execução no Render Shell
# Data: 05/08/2025

echo "=================================================="
echo "🚀 DEPLOYMENT SISTEMA HÍBRIDO - RENDER"
echo "=================================================="
echo "📅 Data/Hora: $(date)"
echo "=================================================="

# Verificar ambiente Python
echo "🐍 Verificando ambiente Python..."
python --version

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
    echo "📦 Ativando ambiente virtual..."
    source venv/bin/activate
fi

# Instalar dependências necessárias se não existirem
echo "📦 Verificando dependências..."
pip list | grep -q "APScheduler" || pip install APScheduler

# Executar script de deployment
echo "🚀 Executando deployment..."
python deploy_sistema_hibrido.py

# Capturar código de saída
EXIT_CODE=$?

echo "=================================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ DEPLOYMENT CONCLUÍDO COM SUCESSO!"
    echo "Reinicie a aplicação para ativar o sistema híbrido"
else
    echo "❌ DEPLOYMENT FALHOU - Código de saída: $EXIT_CODE"
    echo "Verifique os logs acima para detalhes"
fi
echo "=================================================="

exit $EXIT_CODE