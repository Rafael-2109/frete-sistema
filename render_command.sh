#!/bin/bash
# Comando otimizado para o Render

echo "🚀 INICIANDO SISTEMA NO RENDER"

# 0. Criar diretórios e arquivos necessários
echo "📁 Criando diretórios necessários..."
mkdir -p instance/claude_ai/backups/generated
mkdir -p instance/claude_ai/backups/projects
mkdir -p instance/claude_ai/logs
mkdir -p app/claude_ai/backups/generated
mkdir -p app/claude_ai/backups/projects
mkdir -p app/claude_ai/logs

# Criar security_config.json se não existir
if [ ! -f instance/claude_ai/security_config.json ]; then
    echo '{"allowed_paths": ["/opt/render/project/src/app", "/opt/render/project/src/instance", "/tmp"], "blocked_extensions": [".env", ".key", ".pem"], "max_file_size": 10485760, "rate_limits": {"requests_per_minute": 60, "requests_per_hour": 1000}, "security_level": "medium"}' > instance/claude_ai/security_config.json
fi

# 1. Instalar modelo spaCy português
python install_spacy_model.py 2>/dev/null || echo "⚠️ Continuando sem modelo spaCy"

# 2. Aplicar migração inicial se necessário
echo "📌 Aplicando migração inicial..."
flask db stamp initial_consolidated_2025 2>/dev/null || true

# 3. Aplicar outras migrações
echo "🔄 Aplicando migrações..."
flask db upgrade || echo "⚠️ Aviso em migrações, mas continuando..."

# 4. Inicializar banco
echo "🗄️ Inicializando banco..."
python init_db.py

# 5. Iniciar servidor
echo "🌐 Iniciando servidor..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class sync --timeout 600 --max-requests 1000 --max-requests-jitter 100 --keep-alive 10 --preload --worker-tmp-dir /dev/shm run:app
