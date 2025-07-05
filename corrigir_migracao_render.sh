#!/bin/bash
# Script de corre��o de migra��o para Render

echo "Iniciando corre��o de migra��o..."

# Verificar se h� m�ltiplas heads
HEADS_COUNT=$(flask db heads 2>/dev/null | wc -l)

if [ "$HEADS_COUNT" -gt 1 ]; then
    echo "M�ltiplas heads detectadas, fazendo merge..."
    flask db merge heads -m "Merge multiple heads"
fi

# Verificar revis�o problem�tica
if ! flask db show 1d81b88a3038 >/dev/null 2>&1; then
    echo "Revis�o 1d81b88a3038 n�o encontrada, fazendo stamp da head atual..."
    flask db stamp head
fi

# Tentar upgrade
echo "Executando upgrade..."
flask db upgrade

echo "Corre��o de migra��o conclu�da"
