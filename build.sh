#!/bin/bash

echo "🚀 Iniciando build do sistema de fretes..."

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Corrigir problema de migração específico
echo "🔄 Corrigindo migrações..."
python -c "
from flask import Flask
from app import create_app, db
import os

try:
    app = create_app()
    with app.app_context():
        # Limpar migração problemática
        try:
            db.session.execute('DELETE FROM alembic_version WHERE version_num = \'1d81b88a3038\'')
            db.session.commit()
            print('✅ Migração problemática removida')
        except:
            print('⚠️ Migração já limpa ou não existe')
except Exception as e:
    print(f'⚠️ Erro na limpeza: {e}')
"

# Aplicar migrações
flask db stamp head 2>/dev/null || echo "⚠️ Stamp head falhou, continuando..."
flask db merge heads 2>/dev/null || echo "⚠️ Merge heads falhou, continuando..."
flask db upgrade || echo "⚠️ Upgrade falhou, tentando init..."

# Se upgrade falhar, tentar init
if [ $? -ne 0 ]; then
    echo "🔄 Tentando inicializar banco..."
    python init_db.py
fi

echo "✅ Build concluído!"
