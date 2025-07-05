#!/bin/bash

# Build script para Render com correção de migrações

echo "=== INICIANDO DEPLOY NO RENDER ==="

# 1. Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# 2. Verificar e corrigir migrações
echo "🗃️ Verificando migrações..."

# Verificar se há múltiplas heads
if flask db heads | grep -q "Multiple head revisions"; then
    echo "⚠️ Múltiplas heads detectadas, criando merge..."
    flask db merge heads -m "Merge múltiplas heads automaticamente"
fi

# Verificar se há heads não aplicadas
if ! flask db current | grep -q "(head)"; then
    echo "🔄 Aplicando migrações..."
    flask db upgrade
else
    echo "✅ Banco já está atualizado"
fi

# 3. Inicializar banco se necessário
echo "🗄️ Inicializando banco..."
python init_db.py

echo "✅ Build concluído com sucesso!"
