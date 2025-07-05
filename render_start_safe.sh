#!/bin/bash
# Script de inicialização seguro para o Render
# Ignora erros de migração e continua com o servidor

echo "🚀 INICIANDO SISTEMA NO RENDER (MODO SEGURO)"

# 1. Inicializar banco
echo "🗄️ Inicializando banco..."
python init_db.py || echo "⚠️ Aviso no init_db, mas continuando..."

# 2. Tentar aplicar migrações (mas não falhar se der erro)
echo "🔄 Tentando aplicar migrações..."
flask db stamp merge_heads_20250705_093743 2>/dev/null || flask db stamp head 2>/dev/null || echo "⚠️ Migrações com aviso"
flask db upgrade 2>/dev/null || echo "⚠️ Upgrade com aviso, mas continuando..."

# 3. Iniciar servidor (isso SEMPRE deve funcionar)
echo "🌐 Iniciando servidor Gunicorn..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class sync --timeout 600 --max-requests 1000 --max-requests-jitter 100 --keep-alive 10 --preload --worker-tmp-dir /dev/shm run:app 