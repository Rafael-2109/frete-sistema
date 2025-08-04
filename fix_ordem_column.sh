#!/bin/bash

# URL do banco de dados Render
DATABASE_URL="postgresql://sistema_fretes_user:4p6B5VhHW0QMNfaC1pMJZeMpRJvDlLxs@dpg-cr89t5lds78s73dd0680-a.oregon-postgres.render.com/sistema_fretes"

# Adicionar coluna ordem na tabela permission_module usando -c para executar comando diretamente
psql "$DATABASE_URL" -c "ALTER TABLE permission_module ADD COLUMN IF NOT EXISTS ordem INTEGER DEFAULT 0;"

echo "✅ Coluna 'ordem' adicionada com sucesso!"