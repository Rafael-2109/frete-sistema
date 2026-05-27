#!/bin/bash
# =====================================================
# SCRIPT DE INICIALIZAÇÃO DO WORKER NO RENDER
# Para processar agendamentos assíncronos
# =====================================================

echo "=========================================="
echo "🚀 INICIANDO WORKER ATACADÃO/SENDAS NO RENDER"
echo "=========================================="
echo ""

# Verificar variáveis de ambiente
echo "📋 Verificando configuração..."
echo "   REDIS_URL: ${REDIS_URL:0:30}..."  # Mostra apenas início da URL
if [ -z "$DATABASE_URL" ]; then
    echo "   DATABASE_URL: ⚠️ NÃO CONFIGURADA (usando SQLite como fallback)"
    echo "   ⚠️  ATENÇÃO: Worker precisa de DATABASE_URL para PostgreSQL!"
    echo "   ⚠️  Adicione DATABASE_URL nas variáveis de ambiente do Render"
else
    echo "   DATABASE_URL: ${DATABASE_URL:0:30}..."  # Mostra apenas início da URL
fi
echo "   PYTHON: $(python --version)"

echo ""

# Baixar dados de treinamento do Tesseract OCR (para OCR de comprovantes)
# Mesmo procedimento do build.sh do web service
echo "📦 Verificando Tesseract tessdata..."
TESSDATA_DIR="/opt/render/project/src/tessdata"
mkdir -p "$TESSDATA_DIR"
if [ ! -f "$TESSDATA_DIR/por.traineddata" ]; then
    echo "   📥 Baixando por.traineddata..."
    curl -fsSL -o "$TESSDATA_DIR/por.traineddata" \
        "https://github.com/tesseract-ocr/tessdata_fast/raw/main/por.traineddata" \
        && echo "   ✅ Tesseract tessdata baixado com sucesso" \
        || echo "   ⚠️ Falha ao baixar tessdata, OCR pode não funcionar"
else
    echo "   ✅ Tesseract tessdata já existe"
fi
export TESSDATA_PREFIX="$TESSDATA_DIR"
echo "   TESSDATA_PREFIX=$TESSDATA_PREFIX"

echo ""

# Verificar conexão com Redis e limpar workers antigos
echo "🔍 Testando conexão com Redis..."
python -c "
import redis
import os
from rq import Worker
from app.utils.timezone import agora_utc_naive

try:
    r = redis.from_url(os.environ.get('REDIS_URL', ''))
    r.ping()
    print('   ✅ Redis conectado com sucesso!')

    # Limpar workers antigos/mortos
    try:
        workers = Worker.all(connection=r)
        print(f'   📊 Total de workers registrados: {len(workers)}')

        # Método alternativo para detectar workers mortos
        # Workers são considerados mortos se não reportaram heartbeat há mais de 420 segundos
        dead_workers = []
        for w in workers:
            try:
                # Verificar heartbeat (última atividade)
                last_heartbeat = w.last_heartbeat
                if last_heartbeat:
                    # Se o heartbeat é muito antigo, worker está morto
                    time_since_heartbeat = agora_utc_naive() - last_heartbeat
                    if time_since_heartbeat > timedelta(seconds=420):
                        dead_workers.append(w)
                else:
                    # Se não há heartbeat, verificar se o worker está registrado mas inativo
                    # Usar birth_date como fallback
                    if hasattr(w, 'birth_date') and w.birth_date:
                        time_since_birth = agora_utc_naive() - w.birth_date
                        if time_since_birth > timedelta(minutes=10):
                            dead_workers.append(w)
            except:
                # Se houver qualquer erro ao verificar o worker, assumir que está morto
                dead_workers.append(w)

        if dead_workers:
            print(f'   🧹 Limpando {len(dead_workers)} workers antigos/inativos...')
            for w in dead_workers:
                try:
                    # Tentar registrar como morto primeiro
                    w.register_death()
                except:
                    pass
                try:
                    # Remover do registro de workers
                    r.srem('rq:workers', w.key)
                    r.delete(w.key)
                    r.delete(f'{w.key}:heartbeat')
                except:
                    pass
            print('   ✅ Workers antigos removidos')
        else:
            print('   ✅ Nenhum worker antigo para limpar')
    except Exception as worker_error:
        print(f'   ⚠️  Não foi possível limpar workers antigos: {worker_error}')
        print('   ℹ️  Continuando mesmo assim...')

except Exception as e:
    print(f'   ❌ Erro ao conectar ao Redis: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Falha na conexão com Redis. Abortando..."
    exit 1
fi

echo ""

# Verificar e criar tabelas necessárias
echo "📊 Verificando tabelas do banco de dados..."
python -c "
import os
import sys
sys.path.insert(0, '.')

try:
    from app import create_app, db
    
    app = create_app()
    with app.app_context():
        # Tentar criar tabelas se não existirem
        from app.portal.models import PortalIntegracao, PortalLog
        
        # Verificar se a tabela existe
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'portal_integracoes' not in tables:
            print('   ⚠️  Tabela portal_integracoes não existe')
            print('   📦 Tentando criar tabelas do portal...')
            try:
                db.create_all()
                print('   ✅ Tabelas criadas com sucesso')
            except Exception as e:
                print(f'   ⚠️  Não foi possível criar tabelas: {e}')
                print('   ℹ️  Worker continuará, mas agendamentos do portal falharão')
        else:
            print('   ✅ Tabela portal_integracoes já existe')
            
except Exception as e:
    print(f'   ⚠️  Erro ao verificar banco: {e}')
    print('   ℹ️  Worker continuará mesmo assim')
"

echo ""

# Verificar e instalar Playwright + Chromium
echo "🎭 Verificando Playwright e navegadores..."
if playwright --version > /dev/null 2>&1; then
    echo "   ✅ Playwright instalado"
    
    # Verificar se o Chromium está instalado
    if [ -d "/opt/render/.cache/ms-playwright/chromium-"* ] || [ -d "$HOME/.cache/ms-playwright/chromium-"* ]; then
        echo "   🔍 Diretório do Chromium encontrado, verificando binários..."
    else
        echo "   ⚠️  Chromium não encontrado no cache"
    fi
    
    # Sempre tentar instalar/atualizar o Chromium
    echo "   📦 Instalando/Atualizando Chromium..."
    if playwright install chromium; then
        echo "   ✅ Chromium instalado/atualizado com sucesso"
    else
        echo "   ⚠️  Falha ao instalar Chromium"
    fi
    
    # Instalar chromium headless shell também (usado pelo Playwright em modo headless)
    echo "   📦 Instalando Chromium Headless Shell..."
    if playwright install chromium-headless-shell 2>/dev/null; then
        echo "   ✅ Chromium Headless Shell instalado"
    else
        echo "   ℹ️  Chromium Headless Shell pode não estar disponível"
    fi
    
    # Tentar instalar deps do sistema (provavelmente falhará no Render)
    echo "   📦 Tentando instalar dependências do sistema..."
    if playwright install-deps chromium 2>/dev/null; then
        echo "   ✅ Dependências do sistema instaladas"
    else
        echo "   ⚠️  Não foi possível instalar deps do sistema (esperado no Render)"
        echo "   ℹ️  Algumas funcionalidades podem estar limitadas"
    fi
else
    echo "   ❌ Playwright não está instalado"
    echo "   ℹ️  O worker funcionará, mas Portal Atacadão não estará disponível"
fi

echo ""

# Node.js 18+ via NVM (lazy install) — necessario para fila 'artifacts'
# (build de bundle.html via npm + parcel pela skill gerando-artifact).
# Se Node ja esta no PATH (ex: dev local), pula.
NODE_REQUIRED_MAJOR=18
if command -v node &> /dev/null; then
    NODE_VERSION_MAJOR=$(node -v | sed 's/v//' | cut -d'.' -f1)
    echo "🟢 Node ja instalado: $(node -v)"
    if [ "$NODE_VERSION_MAJOR" -lt "$NODE_REQUIRED_MAJOR" ]; then
        echo "⚠️  Node $NODE_VERSION_MAJOR < $NODE_REQUIRED_MAJOR — instalando 20 via NVM..."
        INSTALL_NODE=1
    fi
else
    echo "📦 Node nao encontrado — instalando via NVM (necessario para fila 'artifacts')..."
    INSTALL_NODE=1
fi

if [ "$INSTALL_NODE" = "1" ]; then
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    if [ ! -s "$NVM_DIR/nvm.sh" ]; then
        echo "📥 Baixando NVM..."
        curl -fsSL -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    fi
    # shellcheck source=/dev/null
    . "$NVM_DIR/nvm.sh"
    nvm install 20
    nvm use 20
    nvm alias default 20
    echo "🟢 Node instalado: $(node -v) / npm $(npm -v)"
fi

# Ativar pnpm via corepack (Node 16.10+ built-in package manager manager).
# pnpm e necessario para o build de artifacts — npm falha no Render com
# node_modules/@parcel/config-default AUSENTE apos exit 0 (ver logs 2026-05-13
# srv-d2muidggjchc73d4segg). pnpm tem CAS store + hoisting deterministico.
if command -v corepack &> /dev/null; then
    corepack enable 2>&1 | tail -3
    corepack prepare pnpm@latest --activate 2>&1 | tail -3
    echo "🟢 pnpm ativado via corepack: $(pnpm -v 2>&1)"
elif ! command -v pnpm &> /dev/null; then
    echo "📦 Corepack indisponivel — instalando pnpm via npm -g..."
    npm install -g pnpm 2>&1 | tail -5
    echo "🟢 pnpm instalado: $(pnpm -v 2>&1)"
else
    echo "🟢 pnpm ja disponivel: $(pnpm -v 2>&1)"
fi

# CRITICAL: exportar PATH do Node para subprocess via `exec python worker_render.py`.
# Sem isso, RQ jobs chamando `node`/`pnpm` via subprocess.run() recebem PATH herdado
# do gunicorn (sem Node) e falham com "command not found". Detectar bin atual do
# Node e prepender ao PATH antes do exec.
NODE_BIN_PATH=$(dirname "$(command -v node 2>/dev/null)" 2>/dev/null || true)
if [ -n "$NODE_BIN_PATH" ]; then
    export PATH="$NODE_BIN_PATH:$PATH"
    echo "🔧 Node bin exportado para PATH: $NODE_BIN_PATH"
else
    echo "⚠️  Node bin nao localizado — builds de artifacts podem falhar"
fi

# pnpm via corepack/global pode ter shim em path diferente do node bin.
# Prepender o bin do pnpm se diferente, para garantir PATH herdado pelo subprocess.
PNPM_BIN_PATH=$(dirname "$(command -v pnpm 2>/dev/null)" 2>/dev/null || true)
if [ -n "$PNPM_BIN_PATH" ] && [ "$PNPM_BIN_PATH" != "$NODE_BIN_PATH" ]; then
    export PATH="$PNPM_BIN_PATH:$PATH"
    echo "🔧 pnpm bin exportado para PATH: $PNPM_BIN_PATH"
fi

echo ""

# Configurar número de workers
# NOTA 2026-05-12: 3 perfis isolados (ver worker_render.py:184+):
#   Worker 0 [LIGHT-RESERVED] — so high/hora_nfe/artifacts/atacadao/default/agent_validation.
#     NUNCA pega pesadas → sempre disponivel para HORA interativo + artifacts.
#   Worker 1 [FULL] — tudo, INCLUSIVE impostos (fila exclusiva).
#   Worker 2 [GENERAL] — tudo SEM impostos (absorve outras pesadas).
# Pesadas (impostos/odoo_lancamento/recebimento/hora_backfill) consomem Odoo+RAM
# e ficam capadas em max 2 workers. WORKER_CONCURRENCY<3 perde o LIGHT-RESERVED.
WORKER_COUNT=${WORKER_CONCURRENCY:-3}
echo "👷 Configuração do Worker:"
echo "   Workers paralelos: $WORKER_COUNT"
echo "   Timeout padrão: 30 minutos"
echo "   Perfis:"
echo "     - Worker 0 [LIGHT-RESERVED]: high, hora_nfe, artifacts, atacadao, agent_background, default, agent_validation"
echo "     - Worker 1 [FULL]: todas as filas (impostos exclusivo)"
echo "     - Worker 2+ [GENERAL]: todas exceto impostos"
echo "   Filas (ordem = prioridade): high, hora_nfe, artifacts, atacadao, agent_background, odoo_lancamento, impostos, recebimento, hora_backfill, sped_ecd, default"
echo "   ↑ hora_nfe alta prioridade: operador aguarda emissao NFe interativamente"
echo "   ↑ artifacts media-alta: usuario aguarda build no chat web (30-60s)"
echo "   ↓ hora_backfill / odoo_lancamento / impostos / recebimento / sped_ecd: PESADAS — bloqueadas no Worker 0"
echo ""

# Iniciar worker
echo "=========================================="
echo "🔄 WORKER INICIADO - Aguardando jobs..."
echo "=========================================="
echo ""

# Executar worker otimizado com configurações do Render
echo "⚡ Usando worker_render.py otimizado para evitar importações circulares"
exec python worker_render.py \
    --workers $WORKER_COUNT \
    --queues high,hora_nfe,artifacts,atacadao,agent_background,odoo_lancamento,impostos,recebimento,hora_backfill,sped_ecd,inventario,default \
    --verbose


