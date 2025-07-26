#!/bin/bash
# Claude Code Wrapper - Carrega .env automaticamente
# Uso: ./scripts/claude-code-wrapper.sh [argumentos]

set -e

# Carregar .env se existir
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
    echo "✅ Configurações carregadas do .env"
fi

# Verificar se a API key está configurada
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY não configurada!"
    echo "💡 Configure no arquivo .env"
    exit 1
fi

echo "🔑 API Key configurada (${#ANTHROPIC_API_KEY} caracteres)"

# Executar Claude Code com argumentos
echo "🚀 Iniciando Claude Code..."
exec npx @anthropic-ai/claude-code "$@" 