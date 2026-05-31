#!/bin/bash
# =====================================================================
# Start script — nginx + 2 gunicorn (agente isolado do sistema)
# =====================================================================
# Topologia:
#   nginx :10000 (publico Render)
#     /agente/*       -> gunicorn-agente   :5001  (workers=1 threads=8)
#     /agente-lojas/* -> gunicorn-agente   :5001  (mesmo)
#     /static/*       -> serve do disco
#     resto           -> gunicorn-sistema  :5002  (workers=4 threads=2)
#
# CRITICO: Render injeta `GUNICORN_CMD_ARGS=--bind=0.0.0.0:$PORT`
# que sobrescreve o bind dos configs (gunicorn appendea args do env
# DEPOIS dos explicitos -> last-wins). Sem `unset GUNICORN_CMD_ARGS`,
# ambos gunicorns tentam bindar 0.0.0.0:10000 e o segundo falha com
# Address in use -> restart loop -> 502.
#
# Motivo do split: Claude Agent SDK e per-process. Pattern 2 oficial.
# =====================================================================

echo "================================================="
echo " STARTUP nginx + gunicorn-agente + gunicorn-sistema"
echo "================================================="

# ---------------------------------------------------------------------
# 1. Setup dependencias (Chrome, Playwright, Claude CLI, UTF-8, DB)
# ---------------------------------------------------------------------

echo " Verificando Caddy (proxy split agente x sistema)..."
# Caddy: single binary download. Render Python Runtime NAO permite apt
# nem no build nem no start (start roda como user 'render', sem sudo).
# Caddy resolve: curl + chmod + run. Funcionalmente equivalente ao nginx.
CADDY_VERSION="2.11.3"
CADDY_BIN="${HOME}/bin/caddy"
mkdir -p "${HOME}/bin"
if [ ! -x "$CADDY_BIN" ]; then
    echo " Baixando Caddy v${CADDY_VERSION} (single binary)..."
    CADDY_URL="https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_amd64.tar.gz"
    curl -fsSL "$CADDY_URL" -o /tmp/caddy.tar.gz \
        && tar -xzf /tmp/caddy.tar.gz -C /tmp caddy \
        && mv /tmp/caddy "$CADDY_BIN" \
        && chmod +x "$CADDY_BIN" \
        && rm -f /tmp/caddy.tar.gz
    if [ ! -x "$CADDY_BIN" ]; then
        echo " ❌ FATAL: Caddy nao baixou. Abortando antes de gunicorn."
        exit 1
    fi
fi
echo " ✅ Caddy disponivel: $($CADDY_BIN version 2>&1 | head -1)"
export PATH="${HOME}/bin:$PATH"

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
# 3a. CRITICO: desligar sticky session apos split nginx/Caddy.
# ---------------------------------------------------------------------
# Com gunicorn-agente=1 worker, sticky session vira REDUNDANTE — sempre
# o mesmo "dono". Pior: em rolling deploy do Render, o container antigo
# deixa ownership em Redis com TTL 30min (`agent:session:owner:{sid}`
# = "PID@hostname-antigo"). Container novo (PID@hostname-novo) chega, ve
# dono diferente em Redis, retorna 409 session_owned_by_other_worker
# por ATE 30min apos o deploy. Observado em PROD apos deploy e9b4b9d6:
# owner=236@zxwb9 (morto) me=237@vd9pr (vivo) -> 9 requests 409 em 4min.
#
# Fix: forcar desligado no env. Codigo do sticky_session.py preservado
# para rollback emergencial via env override no dashboard Render.
export AGENT_STICKY_SESSION_ENABLED=false
echo " 🔧 AGENT_STICKY_SESSION_ENABLED=false (1 worker agente = sticky desnecessario)"

# Cleanup defensivo: remove sticky keys de container morto (deploy anterior).
# Roda em background — nao bloqueia o startup. Limpa ownerships com TTL > 0
# que apontam para hostnames diferentes do nosso (containers mortos).
(
    sleep 5
    python -c "
import os, socket
try:
    from app.utils.redis_cache import redis_cache
    if not redis_cache.disponivel:
        print('[STICKY-CLEANUP] Redis off, pulando')
    else:
        me_host = socket.gethostname()
        rc = redis_cache.client
        cursor, total, deletados = 0, 0, 0
        while True:
            cursor, keys = rc.scan(cursor=cursor, match='agent:session:owner:*', count=100)
            for key in keys:
                total += 1
                owner = rc.get(key)
                if owner and me_host not in (owner if isinstance(owner, str) else owner.decode('utf-8', errors='replace')):
                    rc.delete(key)
                    deletados += 1
            if cursor == 0:
                break
        print(f'[STICKY-CLEANUP] varridos={total} deletados={deletados} (hostnames != {me_host})')
except Exception as e:
    print(f'[STICKY-CLEANUP] erro (ignorado): {e}')
" 2>&1 | sed -u 's/^/[STICKY-CLEANUP] /' || true
) &

# ---------------------------------------------------------------------
# 3b. CRITICO: neutralizar Render GUNICORN_CMD_ARGS injection
# ---------------------------------------------------------------------
# Render seta GUNICORN_CMD_ARGS=--bind=0.0.0.0:$PORT no env, que
# sobrescreve o bind do config (last-wins na linha de comando).
# Para split de 2 gunicorn internos, precisamos do bind ser
# 127.0.0.1:5001 e :5002 do arquivo de config. Unset.
if [ -n "${GUNICORN_CMD_ARGS:-}" ]; then
    echo " 🔧 Removendo GUNICORN_CMD_ARGS injetado pelo Render: '$GUNICORN_CMD_ARGS'"
    unset GUNICORN_CMD_ARGS
fi
# Defesa em profundidade: limpa qualquer variante
unset GUNICORN_BIND
unset WEB_BIND
unset PORT_BIND

# ---------------------------------------------------------------------
# 4. Sobe gunicorn-agente (porta 5001) e gunicorn-sistema (porta 5002)
# ---------------------------------------------------------------------

echo "================================================="
echo " Subindo gunicorn-AGENTE (workers=1 threads=8 :5001)"
echo "================================================="
# Process substitution: $! captura PID do gunicorn (nao do sed)
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
echo " Aguardando gunicorns ficarem prontos (max 90s)..."
GUNICORNS_READY=false
for attempt in $(seq 1 45); do
    # Health: /agente/api/health (agente_bp url_prefix=/agente) e /auth/login
    # (auth_bp url_prefix=/auth — rota /login GET retorna 200 sem auth).
    # NAO usar /login direto (404) nem / (302 redirect).
    AGENTE_RC=$(curl -fs -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/agente/api/health 2>/dev/null || echo "000")
    SISTEMA_RC=$(curl -fs -o /dev/null -w '%{http_code}' http://127.0.0.1:5002/auth/login 2>/dev/null || echo "000")

    if [ "$AGENTE_RC" = "200" ] && [ "$SISTEMA_RC" = "200" ]; then
        echo " ✅ Ambos gunicorns prontos (attempt $attempt — agente=$AGENTE_RC sistema=$SISTEMA_RC)"
        GUNICORNS_READY=true
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

    if [ $((attempt % 5)) -eq 0 ]; then
        echo "   attempt $attempt/45 agente=$AGENTE_RC sistema=$SISTEMA_RC"
    fi
    sleep 2
done

if [ "$GUNICORNS_READY" != "true" ]; then
    echo " ❌ FATAL: gunicorns nao ficaram prontos em 90s"
    kill $GUNICORN_AGENTE_PID $GUNICORN_SISTEMA_PID 2>/dev/null
    exit 1
fi

# ---------------------------------------------------------------------
# 5. Trap SIGTERM/SIGINT: encaminha para children + nginx
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
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

# ---------------------------------------------------------------------
# 6. Watchdog: se gunicorn morrer, mata tudo (Render reinicia container)
# ---------------------------------------------------------------------
watchdog() {
    while true; do
        if ! kill -0 $GUNICORN_AGENTE_PID 2>/dev/null; then
            echo " ❌ gunicorn-agente morreu — encerrando container"
            kill $$ 2>/dev/null
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
# 7. Sobe Caddy em FOREGROUND (binda 0.0.0.0:10000 para Render detectar)
# ---------------------------------------------------------------------
echo "================================================="
echo " Subindo Caddy em :10000 (foreground)"
echo "================================================="

# Valida Caddyfile primeiro
"$CADDY_BIN" validate --config "$(pwd)/Caddyfile" --adapter caddyfile 2>&1 | sed -u 's/^/[CADDY-VALIDATE] /'
CADDY_TEST_RC=${PIPESTATUS[0]}
if [ $CADDY_TEST_RC -ne 0 ]; then
    echo " ❌ FATAL: Caddyfile invalido"
    cleanup
    exit 1
fi

# Caddy em foreground; logs prefixados
"$CADDY_BIN" run --config "$(pwd)/Caddyfile" --adapter caddyfile \
    > >(sed -u 's/^/[CADDY] /') 2> >(sed -u 's/^/[CADDY] /' >&2) &
NGINX_PID=$!
echo " Caddy PID: $NGINX_PID"

# Aguarda Caddy (trap captura signals em paralelo)
wait $NGINX_PID
NGINX_RC=$?

echo " Caddy encerrou (rc=$NGINX_RC) — derrubando gunicorns"
cleanup
exit $NGINX_RC
