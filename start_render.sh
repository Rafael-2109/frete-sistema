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

# 🎭 INSTALAR NAVEGADORES DO PLAYWRIGHT SE NECESSÁRIO
echo " Verificando Playwright..."
if ! python -c "import playwright" 2>/dev/null; then
    echo " ⚠️ Playwright não encontrado, instalando..."
    pip install playwright nest-asyncio
fi

# Verificar se os navegadores do Playwright estão instalados
if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    echo " Instalando navegadores do Playwright..."
    python -m playwright install chromium
    python -m playwright install-deps chromium
    echo " ✅ Navegadores do Playwright instalados"
else
    echo " ✅ Navegadores do Playwright já instalados"
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

# 🔄 INICIAR SINCRONIZAÇÃO INCREMENTAL EM BACKGROUND
echo " Iniciando sincronização incremental em background..."
if [ -f "app/scheduler/sincronizacao_incremental_definitiva.py" ]; then
    # Criar diretório de logs se não existir
    mkdir -p logs

    # Usar versão DEFINITIVA: tempos corretos + services fora do contexto
    python -m app.scheduler.sincronizacao_incremental_definitiva > logs/sincronizacao_incremental.log 2>&1 &
    SYNC_PID=$!

    # Aguardar um pouco para verificar se o processo sobreviveu
    sleep 3

    if kill -0 $SYNC_PID 2>/dev/null; then
        echo " ✅ Sincronização incremental iniciada e confirmada (PID: $SYNC_PID)"
        echo "    - Execução imediata para recuperar dados do deploy"
        echo "    - Próximas execuções a cada 30 minutos"
        echo "    - Logs em: logs/sincronizacao_incremental.log"
    else
        echo " ❌ ERRO: Scheduler falhou ao iniciar! Verificando logs..."
        if [ -f "logs/sincronizacao_incremental.log" ]; then
            echo "    Últimas linhas do log:"
            tail -10 logs/sincronizacao_incremental.log | sed 's/^/    /'
        fi
        echo " ⚠️ Sistema continuará sem sincronização automática"
    fi
else
    echo " ⚠️ Script de sincronização não encontrado"
fi

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
workers = 4  # Aumentado para aproveitar melhor 2GB RAM
worker_class = 'gthread'  # Mudado para gthread (melhor para I/O)
threads = 2  # 2 threads por worker = 8 conexões simultâneas
timeout = 300
graceful_timeout = 300  # Tempo para threads non-daemon terminarem durante deploy/reciclagem
max_requests = 1000
max_requests_jitter = 100
keepallive = 10
preload_app = False  # Desabilitar preload para permitir registro de tipos
worker_connections = 1000  # Máximo de conexões por worker

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

def worker_exit(server, worker):
    """Marca tasks running como interrupted quando worker sai (max_requests/graceful shutdown)."""
    try:
        from app import create_app, db
        from app.teams.models import TeamsTask
        app = create_app()
        with app.app_context():
            count = TeamsTask.query.filter(
                TeamsTask.status.in_(['pending', 'processing']),
            ).update({'status': 'timeout'}, synchronize_session=False)
            if count > 0:
                db.session.commit()
                print(f"⚠️ Worker {worker.pid} exit: {count} tasks marcadas como timeout")
            else:
                db.session.rollback()
    except Exception as e:
        print(f"⚠️ Worker {worker.pid} exit cleanup falhou: {e}")
EOF

# Iniciar aplicação com configuração customizada
echo " Iniciando aplicação com configuração customizada..."
exec gunicorn --config /tmp/gunicorn_config.py run:app
