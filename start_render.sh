#!/bin/bash
# =====================================================================
# Start script — nginx + 2 gunicorn (agente isolado do sistema)
# =====================================================================
# Topologia:
#   nginx :10000 (publico Render)
#     /agente/* -> gunicorn-agente   :5001  (workers=1 threads=8)
#     /static/* -> serve direto do disco
#     resto     -> gunicorn-sistema  :5002  (workers=4 threads=2)
#
# Motivo: Claude Agent SDK e per-process. Sticky session (workaround
# do Anthropic Issue #61862) falhava quando worker dono ficava ocupado
# pos-stream. Pattern 2 da doc oficial /hosting.
# =====================================================================

echo "================================================="
echo " STARTUP nginx + gunicorn-agente + gunicorn-sistema"
echo "================================================="

# ---------------------------------------------------------------------
# 1. Setup dependencias (Chrome, Playwright, Claude CLI, UTF-8, DB)
# ---------------------------------------------------------------------

echo " Verificando dependencias do Chrome..."
if ! ldconfig -p | grep -q libnss3; then
    echo " Instalando dependencias do Chrome/Selenium..."
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
        2>/dev/null || echo " WARN: Algumas dependencias Chrome nao instaladas"
fi

echo " Verificando Playwright..."
if ! python -c "import playwright" 2>/dev/null; then
    pip install playwright nest-asyncio
fi

if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    python -m playwright install chromium
    python -m playwright install-deps chromium
fi

echo " Pre-aquecendo Claude CLI..."
CLAUDE_CLI=$(python -c "from pathlib import Path; import claude_agent_sdk; print(Path(claude_agent_sdk.__file__).parent / '_bundled' / 'claude')" 2>/dev/null)
if [ -n "$CLAUDE_CLI" ] && [ -f "$CLAUDE_CLI" ]; then
    timeout 30 "$CLAUDE_CLI" --version 2>/dev/null && echo " ✅ Claude CLI pronto" || echo " WARN: Claude CLI pre-warm falhou"
fi

# UTF-8
export PYTHONIOENCODING=utf-8
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# PostgreSQL URL fix
if [[ -n "$DATABASE_URL" ]]; then
    if [[ $DATABASE_URL == postgres://* ]]; then
        DATABASE_URL=${DATABASE_URL/postgres:\/\//postgresql:\/\/}
    fi
    if [[ $DATABASE_URL != *"client_encoding"* ]]; then
        if [[ $DATABASE_URL == *"?"* ]]; then
            DATABASE_URL="${DATABASE_URL}&client_encoding=utf8"
        else
            DATABASE_URL="${DATABASE_URL}?client_encoding=utf8"
        fi
    fi
    export DATABASE_URL
fi

export SKIP_DB_CREATE=true
export NO_EMOJI_LOGS=true

# ---------------------------------------------------------------------
# 2. Pre-start hooks e migracoes
# ---------------------------------------------------------------------

echo " Executando pre_start.py..."
python pre_start.py || echo " WARN: pre_start.py falhou (nao critico)"

echo " Verificando migracoes do banco..."
python -m flask db upgrade 2>/dev/null || echo " Migracoes ja aplicadas"

# Sincronizacao incremental em background
if [ -f "app/scheduler/sincronizacao_incremental_definitiva.py" ]; then
    mkdir -p logs
    python -m app.scheduler.sincronizacao_incremental_definitiva &
    SYNC_PID=$!
    sleep 3
    if kill -0 $SYNC_PID 2>/dev/null; then
        echo " ✅ Sincronizacao incremental iniciada (PID: $SYNC_PID)"
    else
        echo " ⚠️ Scheduler de sincronizacao falhou"
    fi
fi

if [ "$MCP_ENABLED" = "true" ]; then
    echo " Iniciando MCP em background..."
    cd app/mcp_sistema && uvicorn main:app --host 0.0.0.0 --port 8000 &
    cd ../..
    sleep 5
fi

# ---------------------------------------------------------------------
# 3. Sobe gunicorn-agente (porta 5001) e gunicorn-sistema (porta 5002)
# ---------------------------------------------------------------------

echo "================================================="
echo " Subindo gunicorn-AGENTE (workers=1 threads=8 :5001)"
echo "================================================="
# Process substitution: $! captura PID do gunicorn (nao do sed),
# permitindo kill correto no cleanup/watchdog.
gunicorn --config gunicorn_config_agente.py run:app \
    > >(sed -u 's/^/[AGENTE] /') 2> >(sed -u 's/^/[AGENTE] /' >&2) &
GUNICORN_AGENTE_PID=$!
echo " Gunicorn-agente PID: $GUNICORN_AGENTE_PID"

echo "================================================="
echo " Subindo gunicorn-SISTEMA (workers=4 threads=2 :5002)"
echo "================================================="
gunicorn --config gunicorn_config_sistema.py run:app \
    > >(sed -u 's/^/[SISTEMA] /') 2> >(sed -u 's/^/[SISTEMA] /' >&2) &
GUNICORN_SISTEMA_PID=$!
echo " Gunicorn-sistema PID: $GUNICORN_SISTEMA_PID"

# Aguarda gunicorns subirem (health check antes do nginx)
echo " Aguardando gunicorns ficarem prontos..."
for attempt in $(seq 1 30); do
    # Health: /agente/api/health (agente_bp) e /login (sistema — sempre 200 GET)
    if curl -fs http://127.0.0.1:5001/agente/api/health > /dev/null 2>&1 \
       && curl -fs http://127.0.0.1:5002/login > /dev/null 2>&1; then
        echo " ✅ Ambos gunicorns prontos (attempt $attempt)"
        break
    fi
    # Verifica se algum morreu cedo
    if ! kill -0 $GUNICORN_AGENTE_PID 2>/dev/null; then
        echo " ❌ FATAL: gunicorn-agente morreu na inicializacao"
        kill $GUNICORN_SISTEMA_PID 2>/dev/null
        exit 1
    fi
    if ! kill -0 $GUNICORN_SISTEMA_PID 2>/dev/null; then
        echo " ❌ FATAL: gunicorn-sistema morreu na inicializacao"
        kill $GUNICORN_AGENTE_PID 2>/dev/null
        exit 1
    fi
    sleep 2
done

# ---------------------------------------------------------------------
# 4. Trap SIGTERM/SIGINT: encaminha para children + nginx
# ---------------------------------------------------------------------
NGINX_PID=""

cleanup() {
    echo "================================================="
    echo " SHUTDOWN: encaminhando SIGTERM aos children"
    echo "================================================="
    # Nginx primeiro (para parar de aceitar requests)
    if [ -n "$NGINX_PID" ] && kill -0 $NGINX_PID 2>/dev/null; then
        echo " Parando nginx (PID $NGINX_PID)..."
        kill -TERM $NGINX_PID 2>/dev/null
    fi
    # Gunicorns (graceful_timeout=1740s para drenar SSE)
    if kill -0 $GUNICORN_AGENTE_PID 2>/dev/null; then
        echo " Parando gunicorn-agente (PID $GUNICORN_AGENTE_PID)..."
        kill -TERM $GUNICORN_AGENTE_PID 2>/dev/null
    fi
    if kill -0 $GUNICORN_SISTEMA_PID 2>/dev/null; then
        echo " Parando gunicorn-sistema (PID $GUNICORN_SISTEMA_PID)..."
        kill -TERM $GUNICORN_SISTEMA_PID 2>/dev/null
    fi
    # Aguarda todos sairem (Render manda SIGKILL apos timeout proprio)
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

# ---------------------------------------------------------------------
# 5. Watchdog: se gunicorn morrer, mata tudo (Render reinicia container)
# ---------------------------------------------------------------------
watchdog() {
    while true; do
        if ! kill -0 $GUNICORN_AGENTE_PID 2>/dev/null; then
            echo " ❌ gunicorn-agente morreu — encerrando container"
            kill $$ 2>/dev/null  # mata o script principal
            exit 1
        fi
        if ! kill -0 $GUNICORN_SISTEMA_PID 2>/dev/null; then
            echo " ❌ gunicorn-sistema morreu — encerrando container"
            kill $$ 2>/dev/null
            exit 1
        fi
        sleep 10
    done
}
watchdog &
WATCHDOG_PID=$!

# ---------------------------------------------------------------------
# 6. Sobe nginx em FOREGROUND (PID 1 do container apos exec)
# ---------------------------------------------------------------------
echo "================================================="
echo " Subindo nginx em :10000 (foreground)"
echo "================================================="

# Valida config primeiro
nginx -t -c $(pwd)/nginx.conf 2>&1 | sed -u 's/^/[NGINX-TEST] /'
NGINX_TEST_RC=${PIPESTATUS[0]}
if [ $NGINX_TEST_RC -ne 0 ]; then
    echo " ❌ FATAL: nginx config invalida"
    cleanup
    exit 1
fi

# nginx em foreground; logs prefixados pra debug (process substitution
# preserva PID do nginx em $!)
nginx -c "$(pwd)/nginx.conf" -g 'daemon off;' \
    > >(sed -u 's/^/[NGINX] /') 2> >(sed -u 's/^/[NGINX] /' >&2) &
NGINX_PID=$!
echo " Nginx PID: $NGINX_PID"

# Aguarda nginx (trap captura signals em paralelo)
wait $NGINX_PID
NGINX_RC=$?

echo " nginx encerrou (rc=$NGINX_RC) — derrubando gunicorns"
cleanup
exit $NGINX_RC
