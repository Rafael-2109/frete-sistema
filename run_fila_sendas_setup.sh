#!/bin/bash

# Script para criar a tabela fila_agendamento_sendas no banco de dados
# Executar este script no ambiente com DATABASE_URL configurado

echo "================================================"
echo "SETUP DA FILA DE AGENDAMENTO SENDAS"
echo "================================================"
echo ""

# Verificar se DATABASE_URL está configurado
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERRO: DATABASE_URL não está configurado"
    echo "Por favor, configure a variável de ambiente DATABASE_URL antes de executar este script"
    exit 1
fi

echo "✅ DATABASE_URL detectado"
echo ""

# Executar o SQL no banco
echo "📋 Criando tabela fila_agendamento_sendas..."
psql $DATABASE_URL -f create_fila_sendas_table.sql

if [ $? -eq 0 ]; then
    echo "✅ Tabela criada com sucesso!"
    echo ""
    
    # Verificar se a tabela foi criada
    echo "📊 Verificando estrutura da tabela..."
    psql $DATABASE_URL -c "\d fila_agendamento_sendas"
    
    echo ""
    echo "📈 Contando registros na tabela..."
    psql $DATABASE_URL -c "SELECT COUNT(*) as total_registros FROM fila_agendamento_sendas;"
    
    echo ""
    echo "================================================"
    echo "✅ SETUP CONCLUÍDO COM SUCESSO!"
    echo "================================================"
else
    echo "❌ ERRO ao criar tabela"
    exit 1
fi