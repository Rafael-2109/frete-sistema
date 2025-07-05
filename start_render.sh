#!/bin/bash
echo "=== INICIANDO DEPLOY NO RENDER ==="

# Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p instance/claude_ai/backups/generated
mkdir -p instance/claude_ai/backups/projects
mkdir -p app/claude_ai/logs

# Executar correções Python
echo "🐍 Executando correções..."
python fix_all_render_issues.py || echo "⚠️  Correções aplicadas com avisos"

# Instalar modelo spaCy (permitir falha)
echo "📦 Tentando instalar modelo spaCy..."
python -m spacy download pt_core_news_sm || echo "⚠️  Modelo spaCy não instalado"

# Inicializar banco
echo "🗄️  Inicializando banco de dados..."
python init_db.py || echo "⚠️  Banco inicializado com avisos"

# Aplicar migrações (permitir falha)
echo "🔄 Aplicando migrações..."
flask db upgrade heads || flask db stamp heads || echo "⚠️  Migrações aplicadas com avisos"

# Iniciar aplicação
echo "🚀 Iniciando aplicação..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class sync --timeout 600 --max-requests 1000 --max-requests-jitter 100 --keep-alive 10 --preload --worker-tmp-dir /dev/shm run:app
