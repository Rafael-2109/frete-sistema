#!/bin/bash

# Script para executar migração de alertas de separações COTADAS
# Data: 2025-01-08

echo "🚀 Executando migração: Tabela de Alertas de Separações COTADAS"
echo "=================================================="

# Usar variáveis de ambiente para conexão segura
psql "${DATABASE_URL}" < migrations/add_alertas_separacao_cotada.sql

if [ $? -eq 0 ]; then
    echo "✅ Migração executada com sucesso!"
    echo ""
    echo "📊 Verificando tabela criada..."
    psql "${DATABASE_URL}" -c "\dt alertas_separacao_cotada"
    echo ""
    echo "📋 Estrutura da tabela:"
    psql "${DATABASE_URL}" -c "\d alertas_separacao_cotada"
else
    echo "❌ Erro ao executar migração!"
    exit 1
fi

echo ""
echo "✨ Migração concluída!"