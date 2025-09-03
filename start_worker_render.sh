#!/bin/bash
# =====================================================
# SCRIPT DE INICIALIZAÇÃO DO WORKER NO RENDER
# Para processar agendamentos assíncronos
# =====================================================

echo "=========================================="
echo "🚀 INICIANDO WORKER ATACADÃO NO RENDER"
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

# Verificar conexão com Redis e limpar workers antigos
echo "🔍 Testando conexão com Redis..."
python -c "
import redis
import os
from rq import Worker

try:
    r = redis.from_url(os.environ.get('REDIS_URL', ''))
    r.ping()
    print('   ✅ Redis conectado com sucesso!')
    
    # Limpar workers antigos/mortos
    workers = Worker.all(connection=r)
    dead_workers = [w for w in workers if not w.is_alive()]
    if dead_workers:
        print(f'   🧹 Limpando {len(dead_workers)} workers antigos...')
        for w in dead_workers:
            w.unregister_death()
        print('   ✅ Workers antigos removidos')
    
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

# Configurar número de workers
WORKER_COUNT=${WORKER_CONCURRENCY:-2}
echo "👷 Configuração do Worker:"
echo "   Workers paralelos: $WORKER_COUNT"
echo "   Timeout padrão: 30 minutos"
echo "   Filas: atacadao, high, default"
echo ""

# Iniciar worker
echo "=========================================="
echo "🔄 WORKER INICIADO - Aguardando jobs..."
echo "=========================================="
echo ""

# Executar worker com configurações do Render
exec python worker_atacadao.py \
    --workers $WORKER_COUNT \
    --queues atacadao,high,default \
    --verbose


