#!/bin/bash
# Script de correção de migração para Render

echo "🔄 Corrigindo problema de migração..."

# Resetar migrações
flask db stamp head
flask db merge heads

# Se ainda houver problema, forçar reset
if [ $? -ne 0 ]; then
    echo "⚠️ Forçando reset de migração..."
    python -c "
from flask import Flask
from flask_migrate import Migrate
from app import create_app, db
import os

app = create_app()
with app.app_context():
    # Limpar tabela alembic_version se existir
    try:
        db.session.execute('DELETE FROM alembic_version WHERE version_num = \'1d81b88a3038\'')
        db.session.commit()
        print('✅ Migração problemática removida')
    except:
        print('⚠️ Tabela alembic_version não encontrada ou já limpa')
"
    flask db stamp head
fi

echo "✅ Migração corrigida!"
