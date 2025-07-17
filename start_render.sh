#!/bin/bash

# Script de início para o Render com correções UTF-8

echo " Configurando ambiente do Render..."

# Configurar encoding UTF-8
export PYTHONIOENCODING=utf-8
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# Configurar PostgreSQL
if [[ -n "$DATABASE_URL" ]]; then
    echo " Configurando PostgreSQL com UTF-8..."
    
    # Corrigir URL do PostgreSQL
    if [[ $DATABASE_URL == postgres://* ]]; then
        DATABASE_URL=${DATABASE_URL/postgres:\/\//postgresql:\/\/}
    fi
    
    # Adicionar parâmetros de encoding se não existirem
    if [[ $DATABASE_URL != *"client_encoding"* ]]; then
        if [[ $DATABASE_URL == *"?"* ]]; then
            DATABASE_URL="${DATABASE_URL}&client_encoding=utf8"
        else
            DATABASE_URL="${DATABASE_URL}?client_encoding=utf8"
        fi
    fi
    
    export DATABASE_URL
    echo " DATABASE_URL configurada"
fi

# Configurar Flask para pular criação automática de tabelas
export SKIP_DB_CREATE=true

# Configurar logs sem emojis
export NO_EMOJI_LOGS=true

# Executar migrações se necessário
echo " Executando migrações..."
python -m flask db upgrade || echo " Migrações não executadas (pode ser normal)"

# Iniciar aplicação
echo " Iniciando aplicação..."
exec gunicorn --bind 0.0.0.0:$PORT \
    --worker-class sync \
    --timeout 300 \
    --workers 1 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --keep-alive 10 \
    --preload \
    run:app
