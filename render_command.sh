#!/bin/bash
# Comando otimizado para o Render

echo "🚀 INICIANDO SISTEMA NO RENDER"

# 0. Instalar modelo spaCy português
python install_spacy_model.py || echo "⚠️ Continuando sem modelo spaCy"

# 1. Aplicar migração inicial se necessário
echo "📌 Aplicando migração inicial..."
flask db stamp initial_consolidated_2025 2>/dev/null || true

# 2. Aplicar outras migrações
echo "🔄 Aplicando migrações..."
flask db upgrade || echo "⚠️ Aviso em migrações, mas continuando..."

# 3. Inicializar banco
echo "🗄️ Inicializando banco..."
python init_db.py

# 4. Iniciar servidor
echo "🌐 Iniciando servidor..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --worker-class sync --timeout 600 --max-requests 1000 --max-requests-jitter 100 --keep-alive 10 --preload --worker-tmp-dir /dev/shm run:app
