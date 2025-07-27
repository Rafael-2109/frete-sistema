#!/bin/bash
# Script para ser executado após deploy no Render
# Adicione este script ao Build Command ou como um Job no Render

echo "🚀 Iniciando configuração pós-deploy..."

# 1. Executar migrações
echo "📦 Aplicando migrações do banco..."
flask db upgrade

# 2. Executar script de migração de dados
echo "📊 Migrando dados do sistema de permissões..."
python migrations/upgrade_permissions_system.py

# 3. Configurar usuário admin (opcional via variável de ambiente)
if [ ! -z "$SETUP_ADMIN" ]; then
    echo "👤 Configurando usuário administrador..."
    python scripts/setup_admin_production.py $ADMIN_EMAIL
fi

echo "✅ Configuração pós-deploy concluída!"