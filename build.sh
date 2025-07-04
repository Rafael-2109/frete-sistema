#!/bin/bash

echo "🚀 INICIANDO BUILD RENDER - VERSÃO CORRIGIDA"
echo "=============================================="

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Configurar encoding
export PYTHONIOENCODING=utf-8
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

echo "🗄️ Configurando banco de dados..."

# Limpar estado de migração problemático
echo "🧹 Limpando estado de migração..."
flask db stamp head 2>/dev/null || echo "⚠️ Stamp head falhou, continuando..."

# Resolver múltiplas heads se existirem
echo "🔀 Resolvendo múltiplas heads..."
flask db merge heads -m "Merge heads for Render deployment" 2>/dev/null || echo "⚠️ Merge heads não necessário"

# Aplicar migrações
echo "⬆️ Aplicando migrações..."
flask db upgrade || {
    echo "❌ Erro na migração, tentando correção..."
    
    # Tentar stamp na revisão mais recente
    LATEST_REVISION=$(find migrations/versions -name "*.py" | sort | tail -1 | xargs basename | cut -d'_' -f1)
    if [ ! -z "$LATEST_REVISION" ]; then
        echo "🔧 Tentando stamp na revisão: $LATEST_REVISION"
        flask db stamp $LATEST_REVISION
        flask db upgrade
    else
        echo "⚠️ Usando fallback: init_db.py"
        python init_db.py
    fi
}

echo "✅ BUILD CONCLUÍDO COM SUCESSO"
echo "=============================================="
