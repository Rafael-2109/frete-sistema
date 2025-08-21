#!/bin/bash

# Script de início para o Render com correções UTF-8

echo " Configurando ambiente do Render..."

# 🔧 INSTALAR DEPENDÊNCIAS DO CHROME/SELENIUM SE NECESSÁRIO
echo " Verificando dependências do Chrome..."
if ! ldconfig -p | grep -q libnss3; then
    echo " Instalando dependências do Chrome/Selenium..."
    apt-get update && apt-get install -y \
        libnss3 \
        libnspr4 \
        libnssutil3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libatspi2.0-0 \
        libx11-6 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libxcb1 \
        libxkbcommon0 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 \
        chromium-browser \
        2>/dev/null || echo " Aviso: Algumas dependências não puderam ser instaladas"
else
    echo " ✅ Dependências do Chrome já instaladas"
fi

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

# 🔥 EXECUTAR CONFIGURAÇÕES PRÉ-APLICAÇÃO
echo " Executando configurações pré-aplicação..."
python pre_start.py || echo " Aviso: Erro no pre_start.py (não crítico)"

# Executar migrações se necessário (pode falhar se já foram executadas)
echo " Verificando migrações do banco..."
python -m flask db upgrade 2>/dev/null || echo " Migrações não executadas (pode ser normal)"

# Sistema de estoque em tempo real é inicializado automaticamente pelo pre_start.py
# Para desabilitar, defina INIT_ESTOQUE_TEMPO_REAL=false

if [ "$MCP_ENABLED" = "true" ]; then
    echo "Iniciando MCP em background..."
    cd app/mcp_sistema && uvicorn main:app --host 0.0.0.0 --port 8000 &
    cd ../..
    sleep 5
fi

# Criar arquivo de configuração do Gunicorn temporário
cat > /tmp/gunicorn_config.py << 'EOF'
import os

# Configurações básicas
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1
worker_class = 'sync'
timeout = 300
max_requests = 1000
max_requests_jitter = 100
keepallive = 10
preload_app = False  # Desabilitar preload para permitir registro de tipos

def on_starting(server):
    """Executado ANTES do Gunicorn iniciar"""
    print("🚀 Gunicorn iniciando...")
    try:
        import register_pg_types
        print("✅ Tipos PostgreSQL registrados via Gunicorn!")
    except Exception as e:
        print(f"⚠️ Erro ao registrar tipos via Gunicorn: {e}")

def post_fork(server, worker):
    """Executado DEPOIS de fazer fork do worker"""
    print(f"✅ Worker {worker.pid} iniciado")
    try:
        import register_pg_types
        print(f"✅ Tipos PostgreSQL registrados no worker {worker.pid}")
    except Exception as e:
        print(f"⚠️ Erro ao registrar tipos no worker {worker.pid}: {e}")
EOF

# Iniciar aplicação com configuração customizada
echo " Iniciando aplicação com configuração customizada..."
exec gunicorn --config /tmp/gunicorn_config.py run:app
