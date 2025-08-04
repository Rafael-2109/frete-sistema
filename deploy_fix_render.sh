#!/bin/bash

# Script para aplicar correções no Render
echo "🔧 Iniciando correções no banco de dados do Render..."

# Verificar se DATABASE_URL está definida
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Erro: DATABASE_URL não está definida"
    echo "Configure a variável de ambiente DATABASE_URL com a URL do banco do Render"
    exit 1
fi

echo "📊 Executando correção da tabela saldo_estoque_cache..."
python fix_render_saldo_estoque.py

if [ $? -eq 0 ]; then
    echo "✅ Correção aplicada com sucesso!"
    
    # Verificar a estrutura final
    echo ""
    echo "📋 Verificando estrutura final da tabela..."
    psql $DATABASE_URL -c "\d saldo_estoque_cache" 2>/dev/null || echo "⚠️ Não foi possível verificar a estrutura (psql não disponível)"
    
    # Contar registros
    echo ""
    echo "📊 Contando registros na tabela..."
    psql $DATABASE_URL -c "SELECT COUNT(*) as total_registros FROM saldo_estoque_cache;" 2>/dev/null || echo "⚠️ Não foi possível contar registros"
    
else
    echo "❌ Erro ao aplicar correções"
    exit 1
fi

echo ""
echo "🎉 Processo concluído!"
echo ""
echo "📝 Próximos passos:"
echo "1. Reinicie o serviço no Render se necessário"
echo "2. Teste o acesso ao workspace da carteira"
echo "3. Verifique se os erros foram resolvidos"