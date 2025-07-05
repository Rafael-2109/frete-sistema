#!/bin/bash
# Script de correção de migração para Render

echo "Iniciando correção de migração..."

# Verificar se há múltiplas heads
HEADS_COUNT=$(flask db heads 2>/dev/null | wc -l)

if [ "$HEADS_COUNT" -gt 1 ]; then
    echo "Múltiplas heads detectadas, fazendo merge..."
    flask db merge heads -m "Merge multiple heads"
fi

# Verificar revisão problemática
if ! flask db show 1d81b88a3038 >/dev/null 2>&1; then
    echo "Revisão 1d81b88a3038 não encontrada, fazendo stamp da head atual..."
    flask db stamp head
fi

# Tentar upgrade
echo "Executando upgrade..."
flask db upgrade

echo "Correção de migração concluída"
