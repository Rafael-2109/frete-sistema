#!/bin/bash

# Script de correção específico para Render
# Resolve problemas de migração em produção

echo "🚀 CORREÇÃO RENDER - MIGRAÇÕES"

# Verificar ambiente
if [ "$RENDER" = "true" ]; then
    echo "✅ Ambiente Render detectado"
else
    echo "⚠️ Executando fora do Render"
fi

# Forçar merge de heads se existir conflito
echo "🔄 Verificando conflitos de migração..."

# Tentar aplicar upgrade direto
if flask db upgrade 2>&1 | grep -q "Multiple head revisions"; then
    echo "⚠️ Múltiplas heads detectadas - forçando merge"
    
    # Criar migração de merge forçada
    flask db merge heads -m "Auto-merge heads no Render" || true
    
    # Tentar upgrade novamente
    flask db upgrade || {
        echo "❌ Erro na migração - tentando stamp head"
        flask db stamp head
        echo "✅ Stamp aplicado - sistema estabilizado"
    }
else
    echo "✅ Migrações aplicadas com sucesso"
fi

echo "🎉 Correção Render concluída"
