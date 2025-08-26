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
echo "   PYTHON: $(python --version)"
echo ""

# Verificar conexão com Redis
echo "🔍 Testando conexão com Redis..."
python -c "
import redis
import os
try:
    r = redis.from_url(os.environ.get('REDIS_URL', ''))
    r.ping()
    print('   ✅ Redis conectado com sucesso!')
except Exception as e:
    print(f'   ❌ Erro ao conectar ao Redis: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Falha na conexão com Redis. Abortando..."
    exit 1
fi

echo ""

# Verificar se Playwright está instalado
echo "🎭 Verificando Playwright..."
if playwright --version > /dev/null 2>&1; then
    echo "   ✅ Playwright instalado"
else
    echo "   📦 Instalando Playwright..."
    playwright install chromium
    playwright install-deps
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