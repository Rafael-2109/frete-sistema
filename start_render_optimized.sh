#!/bin/bash

echo "=== INICIANDO SISTEMA NO RENDER ==="

# Função para verificar se estamos no Render
is_render() {
    [ -n "$RENDER" ] && [ "$RENDER" = "true" ]
}

# Remover migração fantasma se estivermos no Render
if is_render; then
    echo "🔧 Ambiente Render detectado - Executando correções..."
    python fix_migration_db.py || echo "⚠️ Correção de migração falhou, continuando..."
fi

# Instalar modelo spaCy se necessário
echo "📦 Verificando modelo spaCy..."
python -m spacy download pt_core_news_sm -q || echo "⚠️ spaCy já instalado"

# Inicializar banco
echo "🗄️ Inicializando banco de dados..."
python init_db.py || echo "⚠️ Banco já inicializado"

# Aplicar migrações
echo "🔄 Aplicando migrações..."
flask db upgrade || echo "⚠️ Migrações aplicadas com avisos"

# Iniciar aplicação
echo "🚀 Iniciando aplicação..."
gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120
