#!/bin/bash
echo "=== INICIANDO SISTEMA COM CLAUDE AI ==="

# Verificar API Key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  AVISO: ANTHROPIC_API_KEY não configurada!"
    echo "   Claude AI funcionará em modo simulado"
else
    echo "✅ ANTHROPIC_API_KEY detectada"
fi

# Criar diretórios necessários para Claude
echo "📁 Criando diretórios do Claude..."
mkdir -p instance/claude_ai/backups/generated
mkdir -p instance/claude_ai/backups/projects
mkdir -p app/claude_ai/logs

# Limpar migração fantasma se existir
echo "🔧 Verificando migrações..."
python fix_migration_db.py 2>/dev/null || echo "✅ Migrações OK"

# Instalar spaCy (opcional mas útil para Claude)
echo "📦 Instalando modelo spaCy..."
python -m spacy download pt_core_news_sm 2>/dev/null || echo "⚠️  spaCy opcional não instalado"

# Iniciar aplicação
echo "🚀 Iniciando aplicação com Claude AI..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class sync --timeout 600 --max-requests 1000 --max-requests-jitter 100 --keep-alive 10 --preload --worker-tmp-dir /dev/shm run:app 